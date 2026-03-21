from __future__ import annotations

from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db.models import Count, Max, QuerySet, Sum

from .models import AcademicService, CoAuthor, IntellectualProperty, Paper, Project, TeachingAchievement


def parse_bool_query_param(value: str | None) -> bool | None:
    normalized = (value or '').strip().lower()
    if normalized in {'1', 'true', 'yes'}:
        return True
    if normalized in {'0', 'false', 'no'}:
        return False
    return None


def normalize_year(raw_value):
    if raw_value in (None, ''):
        return None

    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def build_management_data_meta():
    return {
        'source_note': '学院级看板当前基于 MySQL 业务数据实时聚合，聚焦教师、论文、项目、知识产权、教学成果、学术服务与合作网络的管理分析视图。',
        'acceptance_scope': '本能力属于当前阶段扩展方向，以轻量管理分析看板交付。',
        'future_extension_hint': '当前优先保留实时聚合与轻量导出；后续如数据规模和统计口径稳定，再评估离线聚合、预计算排行榜和更复杂的学院级分析。',
        'realtime_metrics': [
            '当前筛选下的教师数、论文数、总成果数、合作关系数',
            '年度成果趋势与院系分布',
            '教师排行、院系排行与合作概览',
        ],
        'offline_candidate_metrics': [
            '跨年度大盘趋势长期缓存',
            '大范围学院级排行榜预计算',
            '复杂导出报表与多口径历史对比',
        ],
        'export_note': '导出功能当前基于前端对实时聚合结果生成 CSV，不额外引入报表任务链路。',
    }


def apply_year_filter(queryset: QuerySet, year: int | None) -> QuerySet:
    if year:
        return queryset.filter(date_acquired__year=year)
    return queryset


def build_scope_querysets(teacher_ids: list[int], year: int | None) -> dict:
    paper_queryset = apply_year_filter(Paper.objects.filter(teacher_id__in=teacher_ids), year)
    project_queryset = apply_year_filter(Project.objects.filter(teacher_id__in=teacher_ids), year)
    ip_queryset = apply_year_filter(IntellectualProperty.objects.filter(teacher_id__in=teacher_ids), year)
    teaching_queryset = apply_year_filter(TeachingAchievement.objects.filter(teacher_id__in=teacher_ids), year)
    service_queryset = apply_year_filter(AcademicService.objects.filter(teacher_id__in=teacher_ids), year)
    collaboration_queryset = CoAuthor.objects.filter(paper__teacher_id__in=teacher_ids)
    if year:
        collaboration_queryset = collaboration_queryset.filter(paper__date_acquired__year=year)

    return {
        'paper': paper_queryset,
        'project': project_queryset,
        'ip': ip_queryset,
        'teaching': teaching_queryset,
        'service': service_queryset,
        'collaboration': collaboration_queryset,
    }


def build_yearly_trend(querysets: dict) -> list[dict]:
    yearly_counter = defaultdict(
        lambda: {
            'paper': 0,
            'project': 0,
            'ip': 0,
            'teaching': 0,
            'service': 0,
            'achievement_total': 0,
        }
    )

    for model_name, queryset in (
        ('paper', querysets['paper']),
        ('project', querysets['project']),
        ('ip', querysets['ip']),
        ('teaching', querysets['teaching']),
        ('service', querysets['service']),
    ):
        for item in queryset.values_list('date_acquired', flat=True):
            if not item:
                continue
            year = item.year
            yearly_counter[year]['achievement_total'] += 1
            yearly_counter[year][model_name] += 1

    return [
        {
            'year': year,
            'paper_count': payload['paper'],
            'project_count': payload['project'],
            'ip_count': payload['ip'],
            'teaching_count': payload['teaching'],
            'service_count': payload['service'],
            'achievement_total': payload['achievement_total'],
        }
        for year, payload in sorted(yearly_counter.items())
    ]


def build_trend_summary(yearly_trend: list[dict]) -> dict:
    if not yearly_trend:
        return {
            'latest_year': None,
            'previous_year': None,
            'latest_total': 0,
            'previous_total': 0,
            'total_delta': 0,
            'paper_delta': 0,
            'project_delta': 0,
            'direction': 'flat',
            'description': '当前筛选范围内暂无足够的年度成果数据。',
        }

    latest = yearly_trend[-1]
    previous = yearly_trend[-2] if len(yearly_trend) > 1 else None
    total_delta = latest['achievement_total'] - (previous['achievement_total'] if previous else 0)
    paper_delta = latest['paper_count'] - (previous['paper_count'] if previous else 0)
    project_delta = latest['project_count'] - (previous['project_count'] if previous else 0)
    direction = 'up' if total_delta > 0 else 'down' if total_delta < 0 else 'flat'

    if previous:
        description = (
            f"{latest['year']} 年总成果较 {previous['year']} 年"
            f"{'提升' if total_delta > 0 else '下降' if total_delta < 0 else '持平'} {abs(total_delta)} 项，"
            f"其中论文变化 {paper_delta:+d}、项目变化 {project_delta:+d}。"
        )
    else:
        description = f"{latest['year']} 年当前累计成果 {latest['achievement_total']} 项，后续可继续通过新增数据形成年度对比。"

    return {
        'latest_year': latest['year'],
        'previous_year': previous['year'] if previous else None,
        'latest_total': latest['achievement_total'],
        'previous_total': previous['achievement_total'] if previous else 0,
        'total_delta': total_delta,
        'paper_delta': paper_delta,
        'project_delta': project_delta,
        'direction': direction,
        'description': description,
    }


def build_department_distribution(teachers) -> list[dict]:
    distribution = (
        teachers.values('department')
        .annotate(count=Count('id'))
        .order_by('-count', 'department')
    )
    return [
        {
            'name': item['department'] or '未填写院系',
            'value': item['count'],
        }
        for item in distribution
    ]


def build_department_breakdown(teachers, querysets: dict) -> list[dict]:
    teacher_counts = {
        item['department'] or '未填写院系': item['teacher_count']
        for item in teachers.values('department').annotate(teacher_count=Count('id'))
    }
    paper_counts = {
        item['teacher__department'] or '未填写院系': item['count']
        for item in querysets['paper'].values('teacher__department').annotate(count=Count('id'))
    }
    project_counts = {
        item['teacher__department'] or '未填写院系': item['count']
        for item in querysets['project'].values('teacher__department').annotate(count=Count('id'))
    }
    ip_counts = {
        item['teacher__department'] or '未填写院系': item['count']
        for item in querysets['ip'].values('teacher__department').annotate(count=Count('id'))
    }
    teaching_counts = {
        item['teacher__department'] or '未填写院系': item['count']
        for item in querysets['teaching'].values('teacher__department').annotate(count=Count('id'))
    }
    service_counts = {
        item['teacher__department'] or '未填写院系': item['count']
        for item in querysets['service'].values('teacher__department').annotate(count=Count('id'))
    }
    collaboration_counts = {
        item['paper__teacher__department'] or '未填写院系': item['count']
        for item in querysets['collaboration'].values('paper__teacher__department').annotate(count=Count('id'))
    }

    breakdown = []
    for department_name, teacher_count in teacher_counts.items():
        breakdown.append(
            {
                'department': department_name,
                'teacher_count': teacher_count,
                'achievement_total': (
                    paper_counts.get(department_name, 0)
                    + project_counts.get(department_name, 0)
                    + ip_counts.get(department_name, 0)
                    + teaching_counts.get(department_name, 0)
                    + service_counts.get(department_name, 0)
                ),
                'paper_count': paper_counts.get(department_name, 0),
                'project_count': project_counts.get(department_name, 0),
                'collaboration_count': collaboration_counts.get(department_name, 0),
            }
        )

    breakdown.sort(
        key=lambda item: (item['achievement_total'], item['teacher_count'], item['department']),
        reverse=True,
    )
    return breakdown[:8]


def build_teacher_rank(teachers, querysets: dict) -> list[dict]:
    teacher_rank = []
    paper_stats = {
        item['teacher_id']: item
        for item in querysets['paper']
        .values('teacher_id')
        .annotate(
            paper_count=Count('id'),
            citation_total=Sum('citation_count'),
            latest_active_year=Max('date_acquired__year'),
        )
    }
    project_stats = {
        item['teacher_id']: item
        for item in querysets['project'].values('teacher_id').annotate(project_count=Count('id'), latest_active_year=Max('date_acquired__year'))
    }
    ip_stats = {
        item['teacher_id']: item
        for item in querysets['ip'].values('teacher_id').annotate(ip_count=Count('id'), latest_active_year=Max('date_acquired__year'))
    }
    teaching_stats = {
        item['teacher_id']: item
        for item in querysets['teaching']
        .values('teacher_id')
        .annotate(teaching_count=Count('id'), latest_active_year=Max('date_acquired__year'))
    }
    service_stats = {
        item['teacher_id']: item
        for item in querysets['service']
        .values('teacher_id')
        .annotate(service_count=Count('id'), latest_active_year=Max('date_acquired__year'))
    }
    collaboration_stats = {
        item['paper__teacher_id']: item
        for item in querysets['collaboration'].values('paper__teacher_id').annotate(collaboration_count=Count('id'))
    }

    for teacher in teachers:
        paper_stat = paper_stats.get(teacher.id, {})
        project_stat = project_stats.get(teacher.id, {})
        ip_stat = ip_stats.get(teacher.id, {})
        teaching_stat = teaching_stats.get(teacher.id, {})
        service_stat = service_stats.get(teacher.id, {})
        collaboration_stat = collaboration_stats.get(teacher.id, {})
        latest_year_candidates = [
            paper_stat.get('latest_active_year'),
            project_stat.get('latest_active_year'),
            ip_stat.get('latest_active_year'),
            teaching_stat.get('latest_active_year'),
            service_stat.get('latest_active_year'),
        ]

        teacher_rank.append(
            {
                'user_id': teacher.id,
                'teacher_name': teacher.real_name or teacher.username,
                'department': teacher.department or '未填写院系',
                'title': getattr(teacher, 'title', '') or '未填写职称',
                'paper_count': paper_stat.get('paper_count', 0),
                'project_count': project_stat.get('project_count', 0),
                'ip_count': ip_stat.get('ip_count', 0),
                'teaching_count': teaching_stat.get('teaching_count', 0),
                'service_count': service_stat.get('service_count', 0),
                'collaboration_count': collaboration_stat.get('collaboration_count', 0),
                'citation_total': paper_stat.get('citation_total', 0) or 0,
                'achievement_total': (
                    paper_stat.get('paper_count', 0)
                    + project_stat.get('project_count', 0)
                    + ip_stat.get('ip_count', 0)
                    + teaching_stat.get('teaching_count', 0)
                    + service_stat.get('service_count', 0)
                ),
                'latest_active_year': max((item for item in latest_year_candidates if item), default=None),
            }
        )

    teacher_rank.sort(
        key=lambda item: (
            item['achievement_total'],
            item['paper_count'],
            item['project_count'],
            item['collaboration_count'],
        ),
        reverse=True,
    )
    return teacher_rank


def build_collaboration_overview(paper_queryset, collaboration_queryset, paper_total: int) -> dict:
    teachers_with_collaboration = paper_queryset.filter(coauthors__isnull=False).values('teacher').distinct().count()
    collaboration_total = collaboration_queryset.count()
    return {
        'coauthor_relation_total': collaboration_total,
        'teachers_with_collaboration': teachers_with_collaboration,
        'paper_with_collaboration': paper_queryset.filter(coauthors__isnull=False).distinct().count(),
        'average_coauthors_per_paper': round(collaboration_total / paper_total, 2) if paper_total else 0,
    }


def build_comparison_summary(current_metrics: dict, baseline_metrics: dict, year: int | None) -> dict:
    baseline_teacher_total = baseline_metrics['teacher_total'] or 1
    baseline_achievement_total = baseline_metrics['achievement_total'] or 1
    scope_label = '当前筛选范围'
    compare_label = f'{year} 年全校口径' if year else '全校口径'

    return {
        'scope_label': scope_label,
        'compare_label': compare_label,
        'teacher_total': current_metrics['teacher_total'],
        'teacher_share': round(current_metrics['teacher_total'] / baseline_teacher_total * 100, 1),
        'achievement_total': current_metrics['achievement_total'],
        'achievement_share': round(current_metrics['achievement_total'] / baseline_achievement_total * 100, 1),
        'collaboration_total': current_metrics['collaboration_total'],
        'collaboration_density': round(
            current_metrics['collaboration_total'] / current_metrics['teacher_total'],
            2,
        )
        if current_metrics['teacher_total']
        else 0,
        'description': (
            f"当前筛选范围覆盖 {current_metrics['teacher_total']} 位教师，约占 {compare_label}教师规模的 "
            f"{round(current_metrics['teacher_total'] / baseline_teacher_total * 100, 1)}%，"
            f"成果量占比 {round(current_metrics['achievement_total'] / baseline_achievement_total * 100, 1)}%。"
        ),
    }


def build_filter_options():
    user_model = get_user_model()
    teachers = user_model.objects.filter(is_superuser=False).order_by('department', 'id')
    years = sorted(
        {
            item.year
            for item in list(Paper.objects.values_list('date_acquired', flat=True))
            + list(Project.objects.values_list('date_acquired', flat=True))
            + list(IntellectualProperty.objects.values_list('date_acquired', flat=True))
            + list(TeachingAchievement.objects.values_list('date_acquired', flat=True))
            + list(AcademicService.objects.values_list('date_acquired', flat=True))
            if item
        }
    )
    return {
        'departments': sorted({item for item in teachers.values_list('department', flat=True) if item}),
        'teacher_titles': sorted({item for item in teachers.values_list('title', flat=True) if item}),
        'teachers': [
            {
                'user_id': teacher.id,
                'teacher_name': teacher.real_name or teacher.username,
                'department': teacher.department or '未填写院系',
                'title': getattr(teacher, 'title', '') or '未填写职称',
            }
            for teacher in teachers
        ],
        'years': years,
    }
