from __future__ import annotations

import csv
import io
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db.models import Count, Max, QuerySet, Sum

from .models import AcademicService, CoAuthor, IntellectualProperty, Paper, Project, TeachingAchievement
from .visibility import APPROVED_STATUS

ACHIEVEMENT_TYPE_LABELS = {
    'all': '全部成果',
    'paper': '论文成果',
    'project': '科研项目',
    'ip': '知识产权',
    'teaching': '教学成果',
    'service': '学术服务',
}

RANKING_MODE_LABELS = {
    'achievement_total': '总成果',
    'paper_count': '论文数',
    'project_count': '项目数',
    'citation_total': '总被引',
    'collaboration_count': '合作关系',
}

DEFAULT_TEACHER_TITLE_FILTERS = ['教授', '副教授', '讲师']


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
            '年度成果趋势、范围对比趋势与院系分布',
            '教师排行、院系钻取、教师钻取与合作概览',
        ],
        'offline_candidate_metrics': [
            '跨年度大盘趋势长期缓存',
            '大范围学院级排行榜预计算',
            '复杂导出报表与多口径历史对比',
        ],
        'export_note': '导出功能当前由后端基于实时聚合结果生成 CSV，未引入独立报表任务链路。',
        'drilldown_scope_note': '当前支持院系、教师、成果类型三级钻取；暂不扩展为复杂 BI 多维切片平台。',
        'statistics_boundary_note': '当前统计口径以业务入库时间和现有成果表为准，强调稳定、可解释和可回溯。',
    }


def apply_year_filter(
    queryset: QuerySet,
    year: int | None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> QuerySet:
    if year:
        return queryset.filter(date_acquired__year=year)

    if year_from:
        queryset = queryset.filter(date_acquired__year__gte=year_from)

    if year_to:
        queryset = queryset.filter(date_acquired__year__lte=year_to)

    return queryset


def build_scope_querysets(
    teacher_ids: list[int],
    year: int | None,
    achievement_type: str = 'all',
    year_from: int | None = None,
    year_to: int | None = None,
) -> dict:
    paper_queryset = apply_year_filter(
        Paper.objects.filter(teacher_id__in=teacher_ids, status=APPROVED_STATUS),
        year,
        year_from,
        year_to,
    )
    project_queryset = apply_year_filter(
        Project.objects.filter(teacher_id__in=teacher_ids, status=APPROVED_STATUS),
        year,
        year_from,
        year_to,
    )
    ip_queryset = apply_year_filter(
        IntellectualProperty.objects.filter(teacher_id__in=teacher_ids, status=APPROVED_STATUS),
        year,
        year_from,
        year_to,
    )
    teaching_queryset = apply_year_filter(
        TeachingAchievement.objects.filter(teacher_id__in=teacher_ids, status=APPROVED_STATUS),
        year,
        year_from,
        year_to,
    )
    service_queryset = apply_year_filter(
        AcademicService.objects.filter(teacher_id__in=teacher_ids, status=APPROVED_STATUS),
        year,
        year_from,
        year_to,
    )
    collaboration_queryset = CoAuthor.objects.filter(paper__teacher_id__in=teacher_ids, paper__status=APPROVED_STATUS)
    if year:
        collaboration_queryset = collaboration_queryset.filter(paper__date_acquired__year=year)
    if year_from:
        collaboration_queryset = collaboration_queryset.filter(paper__date_acquired__year__gte=year_from)
    if year_to:
        collaboration_queryset = collaboration_queryset.filter(paper__date_acquired__year__lte=year_to)

    if achievement_type != 'all':
        if achievement_type != 'paper':
            paper_queryset = Paper.objects.none()
            collaboration_queryset = CoAuthor.objects.none()
        if achievement_type != 'project':
            project_queryset = Project.objects.none()
        if achievement_type != 'ip':
            ip_queryset = IntellectualProperty.objects.none()
        if achievement_type != 'teaching':
            teaching_queryset = TeachingAchievement.objects.none()
        if achievement_type != 'service':
            service_queryset = AcademicService.objects.none()

    return {
        'paper': paper_queryset,
        'project': project_queryset,
        'ip': ip_queryset,
        'teaching': teaching_queryset,
        'service': service_queryset,
        'collaboration': collaboration_queryset,
    }


def _append_yearly_counter(yearly_counter: dict, queryset: QuerySet, key: str):
    for item in queryset.values_list('date_acquired', flat=True):
        if not item:
            continue
        year = item.year
        yearly_counter[year]['achievement_total'] += 1
        yearly_counter[year][key] += 1


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

    _append_yearly_counter(yearly_counter, querysets['paper'], 'paper')
    _append_yearly_counter(yearly_counter, querysets['project'], 'project')
    _append_yearly_counter(yearly_counter, querysets['ip'], 'ip')
    _append_yearly_counter(yearly_counter, querysets['teaching'], 'teaching')
    _append_yearly_counter(yearly_counter, querysets['service'], 'service')

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


def build_scope_comparison_trend(scope_querysets: dict, baseline_querysets: dict, limit: int = 5) -> list[dict]:
    scope_trend = {item['year']: item for item in build_yearly_trend(scope_querysets)}
    baseline_trend = {item['year']: item for item in build_yearly_trend(baseline_querysets)}
    years = sorted(set(scope_trend) | set(baseline_trend))
    if len(years) > limit:
        years = years[-limit:]

    records = []
    for year in years:
        scope_item = scope_trend.get(year, {})
        baseline_item = baseline_trend.get(year, {})
        records.append(
            {
                'year': year,
                'scope_achievement_total': scope_item.get('achievement_total', 0),
                'baseline_achievement_total': baseline_item.get('achievement_total', 0),
                'scope_paper_count': scope_item.get('paper_count', 0),
                'baseline_paper_count': baseline_item.get('paper_count', 0),
            }
        )
    return records


def build_department_distribution(teachers) -> list[dict]:
    distribution = teachers.values('department').annotate(count=Count('id')).order_by('-count', 'department')
    return [{'name': item['department'] or '未填写院系', 'value': item['count']} for item in distribution]


def build_comparison_department_distribution(primary_department: str, compare_department: str, teachers) -> list[dict]:
    target_departments = [item for item in [primary_department, compare_department] if item]
    if not target_departments:
        return []
    return build_department_distribution(teachers.filter(department__in=target_departments))


def build_department_breakdown(teachers, querysets: dict) -> list[dict]:
    teacher_counts = {item['department'] or '未填写院系': item['teacher_count'] for item in teachers.values('department').annotate(teacher_count=Count('id'))}
    paper_counts = {item['teacher__department'] or '未填写院系': item['count'] for item in querysets['paper'].values('teacher__department').annotate(count=Count('id'))}
    project_counts = {item['teacher__department'] or '未填写院系': item['count'] for item in querysets['project'].values('teacher__department').annotate(count=Count('id'))}
    ip_counts = {item['teacher__department'] or '未填写院系': item['count'] for item in querysets['ip'].values('teacher__department').annotate(count=Count('id'))}
    teaching_counts = {item['teacher__department'] or '未填写院系': item['count'] for item in querysets['teaching'].values('teacher__department').annotate(count=Count('id'))}
    service_counts = {item['teacher__department'] or '未填写院系': item['count'] for item in querysets['service'].values('teacher__department').annotate(count=Count('id'))}
    collaboration_counts = {item['paper__teacher__department'] or '未填写院系': item['count'] for item in querysets['collaboration'].values('paper__teacher__department').annotate(count=Count('id'))}
    citation_counts = {item['teacher__department'] or '未填写院系': item['total'] or 0 for item in querysets['paper'].values('teacher__department').annotate(total=Sum('citation_count'))}

    breakdown = []
    for department_name, teacher_count in teacher_counts.items():
        paper_count = paper_counts.get(department_name, 0)
        project_count = project_counts.get(department_name, 0)
        ip_count = ip_counts.get(department_name, 0)
        teaching_count = teaching_counts.get(department_name, 0)
        service_count = service_counts.get(department_name, 0)
        breakdown.append(
            {
                'department': department_name,
                'teacher_count': teacher_count,
                'achievement_total': paper_count + project_count + ip_count + teaching_count + service_count,
                'paper_count': paper_count,
                'project_count': project_count,
                'ip_count': ip_count,
                'teaching_count': teaching_count,
                'service_count': service_count,
                'collaboration_count': collaboration_counts.get(department_name, 0),
                'citation_total': citation_counts.get(department_name, 0),
            }
        )

    breakdown.sort(key=lambda item: (item['achievement_total'], item['citation_total'], item['department']), reverse=True)
    return breakdown[:12]


def build_teacher_rank(teachers, querysets: dict, rank_by: str = 'achievement_total') -> list[dict]:
    teacher_rank = []
    paper_stats = {
        item['teacher_id']: item
        for item in querysets['paper'].values('teacher_id').annotate(
            paper_count=Count('id'),
            citation_total=Sum('citation_count'),
            latest_active_year=Max('date_acquired__year'),
        )
    }
    project_stats = {item['teacher_id']: item for item in querysets['project'].values('teacher_id').annotate(project_count=Count('id'), latest_active_year=Max('date_acquired__year'))}
    ip_stats = {item['teacher_id']: item for item in querysets['ip'].values('teacher_id').annotate(ip_count=Count('id'), latest_active_year=Max('date_acquired__year'))}
    teaching_stats = {item['teacher_id']: item for item in querysets['teaching'].values('teacher_id').annotate(teaching_count=Count('id'), latest_active_year=Max('date_acquired__year'))}
    service_stats = {item['teacher_id']: item for item in querysets['service'].values('teacher_id').annotate(service_count=Count('id'), latest_active_year=Max('date_acquired__year'))}
    collaboration_stats = {item['paper__teacher_id']: item for item in querysets['collaboration'].values('paper__teacher_id').annotate(collaboration_count=Count('id'))}

    for teacher in teachers:
        paper_stat = paper_stats.get(teacher.id, {})
        project_stat = project_stats.get(teacher.id, {})
        ip_stat = ip_stats.get(teacher.id, {})
        teaching_stat = teaching_stats.get(teacher.id, {})
        service_stat = service_stats.get(teacher.id, {})
        collaboration_stat = collaboration_stats.get(teacher.id, {})

        achievement_total = (
            paper_stat.get('paper_count', 0)
            + project_stat.get('project_count', 0)
            + ip_stat.get('ip_count', 0)
            + teaching_stat.get('teaching_count', 0)
            + service_stat.get('service_count', 0)
        )
        latest_year_candidates = [
            paper_stat.get('latest_active_year'),
            project_stat.get('latest_active_year'),
            ip_stat.get('latest_active_year'),
            teaching_stat.get('latest_active_year'),
            service_stat.get('latest_active_year'),
        ]
        item = {
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
            'achievement_total': achievement_total,
            'latest_active_year': max((item for item in latest_year_candidates if item), default=None),
        }
        item['rank_value'] = item.get(rank_by, achievement_total)
        item['rank_label'] = RANKING_MODE_LABELS.get(rank_by, '总成果')
        teacher_rank.append(item)

    teacher_rank.sort(
        key=lambda item: (
            item['rank_value'],
            item['achievement_total'],
            item['paper_count'],
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


def build_comparison_summary(
    current_metrics: dict,
    baseline_metrics: dict,
    year: int | None,
    achievement_type: str = 'all',
    compare_department: str = '',
) -> dict:
    baseline_teacher_total = baseline_metrics['teacher_total'] or 1
    baseline_achievement_total = baseline_metrics['achievement_total'] or 1
    scope_label = '当前筛选范围'
    compare_label = compare_department or (f'{year} 年全校口径' if year else '全校口径')
    type_label = ACHIEVEMENT_TYPE_LABELS.get(achievement_type, '全部成果')
    return {
        'scope_label': scope_label,
        'compare_label': compare_label,
        'teacher_total': current_metrics['teacher_total'],
        'teacher_share': round(current_metrics['teacher_total'] / baseline_teacher_total * 100, 1),
        'achievement_total': current_metrics['achievement_total'],
        'achievement_share': round(current_metrics['achievement_total'] / baseline_achievement_total * 100, 1),
        'collaboration_total': current_metrics['collaboration_total'],
        'collaboration_density': round(current_metrics['collaboration_total'] / current_metrics['teacher_total'], 2)
        if current_metrics['teacher_total']
        else 0,
        'description': (
            f"当前筛选范围在“{type_label}”口径下覆盖 {current_metrics['teacher_total']} 位教师，"
            f"约占 {compare_label}教师规模的 {round(current_metrics['teacher_total'] / baseline_teacher_total * 100, 1)}%，"
            f"成果量占比 {round(current_metrics['achievement_total'] / baseline_achievement_total * 100, 1)}%。"
        ),
    }


def build_filter_options(teachers=None):
    if teachers is None:
        user_model = get_user_model()
        teachers = user_model.objects.filter(is_superuser=False)
    teachers = teachers.order_by('department', 'id')
    years = sorted(
        {
            item.year
            for item in list(Paper.objects.filter(status=APPROVED_STATUS).values_list('date_acquired', flat=True))
            + list(Project.objects.filter(status=APPROVED_STATUS).values_list('date_acquired', flat=True))
            + list(IntellectualProperty.objects.filter(status=APPROVED_STATUS).values_list('date_acquired', flat=True))
            + list(TeachingAchievement.objects.filter(status=APPROVED_STATUS).values_list('date_acquired', flat=True))
            + list(AcademicService.objects.filter(status=APPROVED_STATUS).values_list('date_acquired', flat=True))
            if item
        }
    )
    dynamic_titles = [item for item in teachers.values_list('title', flat=True) if item]
    teacher_titles = []
    for title in DEFAULT_TEACHER_TITLE_FILTERS + sorted(set(dynamic_titles)):
        if title and title not in teacher_titles:
            teacher_titles.append(title)

    return {
        'departments': sorted({item for item in teachers.values_list('department', flat=True) if item}),
        'teacher_titles': teacher_titles,
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
        'achievement_types': [{'value': key, 'label': value} for key, value in ACHIEVEMENT_TYPE_LABELS.items()],
        'ranking_modes': [{'value': key, 'label': value} for key, value in RANKING_MODE_LABELS.items()],
    }


def build_recent_achievement_records(teacher_ids: list[int], achievement_type: str = 'all', limit: int = 8) -> list[dict]:
    records = []
    if achievement_type in {'all', 'paper'}:
        for item in Paper.objects.filter(teacher_id__in=teacher_ids, status=APPROVED_STATUS).order_by('-date_acquired', '-created_at')[:limit]:
            records.append({
                'type': 'paper',
                'title': item.title,
                'teacher_name': item.teacher.real_name or item.teacher.username,
                'department': item.teacher.department or '未填写院系',
                'date_acquired': item.date_acquired.isoformat(),
                'detail': item.journal_name,
            })
    if achievement_type in {'all', 'project'}:
        for item in Project.objects.filter(teacher_id__in=teacher_ids, status=APPROVED_STATUS).order_by('-date_acquired', '-created_at')[:limit]:
            records.append({
                'type': 'project',
                'title': item.title,
                'teacher_name': item.teacher.real_name or item.teacher.username,
                'department': item.teacher.department or '未填写院系',
                'date_acquired': item.date_acquired.isoformat(),
                'detail': item.get_level_display(),
            })
    if achievement_type in {'all', 'ip'}:
        for item in IntellectualProperty.objects.filter(teacher_id__in=teacher_ids, status=APPROVED_STATUS).order_by('-date_acquired', '-created_at')[:limit]:
            records.append({
                'type': 'ip',
                'title': item.title,
                'teacher_name': item.teacher.real_name or item.teacher.username,
                'department': item.teacher.department or '未填写院系',
                'date_acquired': item.date_acquired.isoformat(),
                'detail': item.get_ip_type_display(),
            })
    if achievement_type in {'all', 'teaching'}:
        for item in TeachingAchievement.objects.filter(teacher_id__in=teacher_ids, status=APPROVED_STATUS).order_by('-date_acquired', '-created_at')[:limit]:
            records.append({
                'type': 'teaching',
                'title': item.title,
                'teacher_name': item.teacher.real_name or item.teacher.username,
                'department': item.teacher.department or '未填写院系',
                'date_acquired': item.date_acquired.isoformat(),
                'detail': item.level,
            })
    if achievement_type in {'all', 'service'}:
        for item in AcademicService.objects.filter(teacher_id__in=teacher_ids, status=APPROVED_STATUS).order_by('-date_acquired', '-created_at')[:limit]:
            records.append({
                'type': 'service',
                'title': item.title,
                'teacher_name': item.teacher.real_name or item.teacher.username,
                'department': item.teacher.department or '未填写院系',
                'date_acquired': item.date_acquired.isoformat(),
                'detail': item.organization,
            })

    return sorted(records, key=lambda item: item['date_acquired'], reverse=True)[:limit]


def build_teacher_drilldown(teacher, querysets: dict, achievement_type: str = 'all') -> dict:
    teacher_id = teacher.id
    paper_count = querysets['paper'].filter(teacher_id=teacher_id).count()
    project_count = querysets['project'].filter(teacher_id=teacher_id).count()
    ip_count = querysets['ip'].filter(teacher_id=teacher_id).count()
    teaching_count = querysets['teaching'].filter(teacher_id=teacher_id).count()
    service_count = querysets['service'].filter(teacher_id=teacher_id).count()
    citation_total = querysets['paper'].filter(teacher_id=teacher_id).aggregate(total=Sum('citation_count'))['total'] or 0
    collaboration_count = querysets['collaboration'].filter(paper__teacher_id=teacher_id).count()
    return {
        'selected_teacher_summary': {
            'user_id': teacher.id,
            'teacher_name': teacher.real_name or teacher.username,
            'department': teacher.department or '未填写院系',
            'title': getattr(teacher, 'title', '') or '未填写职称',
            'achievement_total': paper_count + project_count + ip_count + teaching_count + service_count,
            'paper_count': paper_count,
            'project_count': project_count,
            'ip_count': ip_count,
            'teaching_count': teaching_count,
            'service_count': service_count,
            'citation_total': citation_total,
            'collaboration_count': collaboration_count,
        },
        'teacher_recent_achievements': build_recent_achievement_records([teacher_id], achievement_type=achievement_type, limit=8),
    }


def build_department_drilldown(teachers, department_name: str, querysets: dict, rank_by: str = 'achievement_total') -> dict:
    department_teachers = teachers.filter(department=department_name)
    teacher_ids = list(department_teachers.values_list('id', flat=True))
    scoped_querysets = build_scope_querysets(teacher_ids, None, 'all')
    top_teachers = build_teacher_rank(department_teachers, scoped_querysets, rank_by=rank_by)[:6]
    recent_records = build_recent_achievement_records(teacher_ids, limit=8)
    return {
        'selected_department_summary': {
            'department': department_name,
            'teacher_count': department_teachers.count(),
            'top_teacher_count': len(top_teachers),
            'recent_record_count': len(recent_records),
        },
        'department_top_teachers': top_teachers,
        'department_recent_achievements': recent_records,
    }


def export_academy_csv(*, export_target: str, statistics: list[dict], yearly_trend: list[dict], comparison_trend: list[dict], department_breakdown: list[dict], top_active_teachers: list[dict], recent_records: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)

    if export_target == 'departments':
        writer.writerow(['院系', '教师数', '总成果', '论文', '项目', '知识产权', '教学成果', '学术服务', '合作关系', '总被引'])
        for item in department_breakdown:
            writer.writerow([
                item['department'],
                item['teacher_count'],
                item['achievement_total'],
                item['paper_count'],
                item['project_count'],
                item['ip_count'],
                item['teaching_count'],
                item['service_count'],
                item['collaboration_count'],
                item['citation_total'],
            ])
        return '\ufeff' + output.getvalue()

    if export_target == 'trend':
        writer.writerow(['年份', '当前范围总成果', '当前范围论文', '当前范围项目', '全校总成果', '全校论文'])
        comparison_map = {item['year']: item for item in comparison_trend}
        for item in yearly_trend:
            compare_item = comparison_map.get(item['year'], {})
            writer.writerow([
                item['year'],
                item['achievement_total'],
                item['paper_count'],
                item['project_count'],
                compare_item.get('baseline_achievement_total', 0),
                compare_item.get('baseline_paper_count', 0),
            ])
        return '\ufeff' + output.getvalue()

    if export_target == 'recent_records':
        writer.writerow(['成果类型', '标题', '教师', '院系', '日期', '说明'])
        for item in recent_records:
            writer.writerow([
                item['type'],
                item['title'],
                item['teacher_name'],
                item['department'],
                item['date_acquired'],
                item['detail'],
            ])
        return '\ufeff' + output.getvalue()

    writer.writerow(['指标', '数值', '说明'])
    for item in statistics:
        writer.writerow([item['title'], item['value'], item.get('helper', '')])
    writer.writerow([])
    writer.writerow(['教师', '院系', '职称', '排行指标', '排行值', '总成果', '论文', '项目', '总被引', '合作关系'])
    for item in top_active_teachers:
        writer.writerow([
            item['teacher_name'],
            item['department'],
            item['title'],
            item['rank_label'],
            item['rank_value'],
            item['achievement_total'],
            item['paper_count'],
            item['project_count'],
            item['citation_total'],
            item['collaboration_count'],
        ])
    return '\ufeff' + output.getvalue()
