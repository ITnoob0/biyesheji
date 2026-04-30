from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.access import ACADEMY_SCOPE_MESSAGE, ensure_admin_user, is_college_admin_user

from .academy_dashboard_analysis import (
    build_collaboration_overview,
    build_comparison_department_distribution,
    build_comparison_summary,
    build_department_breakdown,
    build_department_distribution,
    build_department_drilldown,
    build_filter_options,
    build_management_data_meta,
    build_recent_achievement_records,
    build_scope_comparison_trend,
    build_scope_querysets,
    build_teacher_drilldown,
    build_teacher_rank,
    build_trend_summary,
    build_yearly_trend,
    export_academy_csv,
    normalize_year,
    parse_bool_query_param,
)


def filter_teachers_queryset(*, all_teachers, department: str, teacher_id: str, teacher_title: str, has_collaboration: bool | None):
    teachers = all_teachers
    if department:
        teachers = teachers.filter(department=department)
    if teacher_title:
        teachers = teachers.filter(title=teacher_title)
    if teacher_id:
        teachers = teachers.filter(id=teacher_id)
    if has_collaboration is not None:
        if has_collaboration:
            teachers = teachers.filter(papers__status='APPROVED', papers__coauthors__isnull=False).distinct()
        else:
            teachers = teachers.exclude(papers__status='APPROVED', papers__coauthors__isnull=False).distinct()
    return teachers


def _count_scope_totals(querysets: dict) -> dict:
    legacy_scope = querysets['legacy']
    rule_unique_records = querysets['rule']['unique_records']

    paper_total = len(legacy_scope['paper']) + sum(1 for item in rule_unique_records if (item.category_code_snapshot or item.category.code) == 'PAPER_BOOK')
    project_total = len(legacy_scope['project']) + sum(1 for item in rule_unique_records if (item.category_code_snapshot or item.category.code) == 'PROJECT')
    ip_total = len(legacy_scope['ip']) + sum(
        1
        for item in rule_unique_records
        if (item.category_code_snapshot or item.category.code) in {'AWARD', 'TRANSFORMATION', 'THINK_TANK'}
    )
    service_total = len(legacy_scope['service']) + sum(
        1
        for item in rule_unique_records
        if (item.category_code_snapshot or item.category.code) in {'PLATFORM_TEAM', 'SCI_POP_AWARD'}
    )
    achievement_total = len(querysets['combined_unique_records'])

    return {
        'paper_total': paper_total,
        'project_total': project_total,
        'ip_total': ip_total,
        'service_total': service_total,
        'achievement_total': achievement_total,
    }


def _score_totals(querysets: dict) -> dict:
    metrics_by_teacher = querysets['rule']['metrics_by_teacher']
    return {
        'paper_book_score': round(sum(item['paper_book_score'] for item in metrics_by_teacher.values()), 1),
        'project_score': round(sum(item['project_score'] for item in metrics_by_teacher.values()), 1),
        'award_transform_score': round(
            sum(item['award_score'] + item['transformation_score'] + item['think_tank_score'] for item in metrics_by_teacher.values()),
            1,
        ),
        'platform_pop_score': round(
            sum(item['platform_team_score'] + item['science_pop_score'] for item in metrics_by_teacher.values()),
            1,
        ),
        'total_score': round(sum(item['total_rule_score'] for item in metrics_by_teacher.values()), 1),
    }


def build_overview_payload(
    *,
    teachers,
    all_teachers,
    year: int | None,
    year_from: int | None,
    year_to: int | None,
    achievement_type: str,
    rank_by: str,
    selected_department: str,
    selected_teacher_id: str,
    compare_department: str = '',
    teacher_rank_limit: int | None = 12,
):
    teacher_ids = list(teachers.values_list('id', flat=True))
    current_querysets = build_scope_querysets(teacher_ids, year, achievement_type, year_from=year_from, year_to=year_to)
    baseline_teacher_ids = list(all_teachers.values_list('id', flat=True))
    baseline_querysets = build_scope_querysets(
        baseline_teacher_ids,
        year,
        achievement_type,
        year_from=year_from,
        year_to=year_to,
    )
    comparison_scope_querysets = current_querysets
    comparison_baseline_teachers = all_teachers.filter(department=compare_department) if compare_department else all_teachers
    comparison_baseline_teacher_ids = list(comparison_baseline_teachers.values_list('id', flat=True))
    comparison_baseline_querysets = build_scope_querysets(
        comparison_baseline_teacher_ids,
        year,
        achievement_type,
        year_from=year_from,
        year_to=year_to,
    )

    teacher_total = teachers.count()
    current_counts = _count_scope_totals(current_querysets)
    current_scores = _score_totals(current_querysets)
    baseline_counts = _count_scope_totals(baseline_querysets)
    baseline_scores = _score_totals(baseline_querysets)
    collaboration_total = current_querysets['legacy']['collaboration_total'] + current_querysets['rule']['collaboration_total']

    statistics = [
        {
            'title': '教师总数',
            'value': teacher_total,
            'suffix': '人',
            'icon': 'User',
            'iconClass': 'icon-blue',
            'helper': '当前筛选范围内纳入统计的教师账号数量。',
        },
        {
            'title': '学术产出数量',
            'value': current_counts['paper_total'],
            'suffix': '项',
            'icon': 'Document',
            'iconClass': 'icon-blue',
            'helper': '论文、著作等学术产出数量，兼容已审核历史成果与新规则成果。',
        },
        {
            'title': '唯一成果数量',
            'value': current_counts['achievement_total'],
            'suffix': '项',
            'icon': 'CollectionTag',
            'iconClass': 'icon-green',
            'helper': '数量口径默认去重，避免同一成果被多位教师录入后重复累计。',
        },
        {
            'title': '合作关系数',
            'value': collaboration_total,
            'suffix': '条',
            'icon': 'Share',
            'iconClass': 'icon-orange',
            'helper': '基于历史论文合作者与新规则成果中的合作作者字段聚合统计。',
        },
        {
            'title': '项目与扩展成果',
            'value': current_counts['project_total'] + current_counts['ip_total'] + current_counts['service_total'],
            'suffix': '项',
            'icon': 'Reading',
            'iconClass': 'icon-red',
            'helper': (
                f"项目 {current_counts['project_total']} 项 / 奖励转化 {current_counts['ip_total']} 项 / "
                f"平台科普 {current_counts['service_total']} 项"
            ),
        },
    ]

    score_statistics = [
        {
            'title': '核心科研积分',
            'value': current_scores['total_score'],
            'suffix': '分',
            'icon': 'CollectionTag',
            'iconClass': 'icon-blue',
            'helper': (
                f"纳入教师 {teacher_total} 人 / 唯一成果 {current_counts['achievement_total']} 项 / "
                f"当前待审核 {current_querysets['rule']['pending_count']} 项。"
            ),
        },
        {
            'title': '学术产出积分',
            'value': current_scores['paper_book_score'],
            'suffix': '分',
            'icon': 'Document',
            'iconClass': 'icon-blue',
            'helper': f"{current_counts['paper_total']} 项。",
        },
        {
            'title': '项目竞争积分',
            'value': current_scores['project_score'],
            'suffix': '分',
            'icon': 'Reading',
            'iconClass': 'icon-green',
            'helper': f"{current_counts['project_total']} 项。",
        },
        {
            'title': '奖励转化积分',
            'value': current_scores['award_transform_score'],
            'suffix': '分',
            'icon': 'Trophy',
            'iconClass': 'icon-orange',
            'helper': f"{current_counts['ip_total']} 项。",
        },
        {
            'title': '平台科普积分',
            'value': current_scores['platform_pop_score'],
            'suffix': '分',
            'icon': 'Star',
            'iconClass': 'icon-red',
            'helper': f"{current_counts['service_total']} 项。",
        },
    ]

    yearly_trend = build_yearly_trend(current_querysets)
    comparison_trend = build_scope_comparison_trend(comparison_scope_querysets, comparison_baseline_querysets)
    teacher_rank = build_teacher_rank(teachers, current_querysets, rank_by=rank_by)

    current_metrics = {
        'teacher_total': teacher_total,
        'achievement_total': current_counts['achievement_total'],
        'collaboration_total': collaboration_total,
        'score_total': current_scores['total_score'],
    }
    baseline_metrics = {
        'teacher_total': all_teachers.count(),
        'achievement_total': baseline_counts['achievement_total'],
        'collaboration_total': baseline_querysets['legacy']['collaboration_total'] + baseline_querysets['rule']['collaboration_total'],
        'score_total': baseline_scores['total_score'],
    }

    drilldown = {
        'selected_department_summary': None,
        'department_top_teachers': [],
        'department_recent_achievements': [],
        'selected_teacher_summary': None,
        'teacher_recent_achievements': [],
    }
    if selected_department:
        drilldown.update(build_department_drilldown(teachers, selected_department, current_querysets, rank_by=rank_by))
    if selected_teacher_id:
        teacher = teachers.filter(id=selected_teacher_id).first()
        if teacher is not None:
            drilldown.update(build_teacher_drilldown(teacher, current_querysets, achievement_type=achievement_type))

    return {
        'statistics': statistics,
        'score_statistics': score_statistics,
        'yearly_trend': yearly_trend,
        'comparison_trend': comparison_trend,
        'trend_summary': build_trend_summary(yearly_trend),
        'comparison_summary': build_comparison_summary(
            current_metrics,
            baseline_metrics,
            year,
            achievement_type=achievement_type,
            compare_department=compare_department,
        ),
        'department_distribution': build_department_distribution(teachers),
        'comparison_department_distribution': build_comparison_department_distribution(
            selected_department,
            compare_department,
            all_teachers,
        ),
        'department_breakdown': build_department_breakdown(teachers, current_querysets),
        'top_active_teachers': teacher_rank if teacher_rank_limit is None else teacher_rank[:teacher_rank_limit],
        'collaboration_overview': build_collaboration_overview(
            None,
            None,
            current_counts['paper_total'],
            querysets=current_querysets,
        ),
        'drilldown': drilldown,
        'recent_scope_records': build_recent_achievement_records(teacher_ids, achievement_type=achievement_type, limit=10),
        'ranking_meta': {
            'current_rank_by': rank_by,
            'current_rank_label': teacher_rank[0]['rank_label'] if teacher_rank else '',
        },
        'data_meta': build_management_data_meta(),
    }


class AcademyOverviewDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_admin_user(request.user, ACADEMY_SCOPE_MESSAGE)

        user_model = get_user_model()
        all_teachers = user_model.objects.filter(is_superuser=False, is_staff=False)
        if is_college_admin_user(request.user):
            all_teachers = all_teachers.filter(department=request.user.department)

        department = request.query_params.get('department', '').strip()
        compare_department = request.query_params.get('compare_department', '').strip()
        teacher_id = request.query_params.get('teacher_id', '').strip()
        teacher_title = request.query_params.get('teacher_title', '').strip()
        achievement_type = request.query_params.get('achievement_type', 'all').strip() or 'all'
        rank_by = request.query_params.get('rank_by', 'total_score').strip() or 'total_score'
        year = normalize_year(request.query_params.get('year'))
        year_from = normalize_year(request.query_params.get('year_from'))
        year_to = normalize_year(request.query_params.get('year_to'))
        has_collaboration = parse_bool_query_param(request.query_params.get('has_collaboration'))
        rank_limit = request.query_params.get('rank_limit', '').strip().lower()
        teacher_rank_limit = None if rank_limit == 'all' else 12

        if is_college_admin_user(request.user):
            department = request.user.department or ''
            compare_department = ''

        teachers = filter_teachers_queryset(
            all_teachers=all_teachers,
            department=department,
            teacher_id=teacher_id,
            teacher_title=teacher_title,
            has_collaboration=has_collaboration,
        )

        payload = build_overview_payload(
            teachers=teachers,
            all_teachers=all_teachers,
            year=year,
            year_from=year_from,
            year_to=year_to,
            achievement_type=achievement_type,
            rank_by=rank_by,
            selected_department=department,
            selected_teacher_id=teacher_id,
            compare_department=compare_department,
            teacher_rank_limit=teacher_rank_limit,
        )
        payload['active_filters'] = {
            'department': department,
            'compare_department': compare_department,
            'teacher_id': int(teacher_id) if teacher_id else None,
            'teacher_title': teacher_title,
            'year': year,
            'year_from': year_from,
            'year_to': year_to,
            'has_collaboration': has_collaboration,
            'achievement_type': achievement_type,
            'rank_by': rank_by,
        }
        payload['filter_options'] = build_filter_options(all_teachers)
        return Response(payload, status=status.HTTP_200_OK)


class AcademyOverviewExportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_admin_user(request.user, ACADEMY_SCOPE_MESSAGE)

        user_model = get_user_model()
        all_teachers = user_model.objects.filter(is_superuser=False, is_staff=False)
        if is_college_admin_user(request.user):
            all_teachers = all_teachers.filter(department=request.user.department)

        department = request.query_params.get('department', '').strip()
        teacher_id = request.query_params.get('teacher_id', '').strip()
        teacher_title = request.query_params.get('teacher_title', '').strip()
        achievement_type = request.query_params.get('achievement_type', 'all').strip() or 'all'
        rank_by = request.query_params.get('rank_by', 'total_score').strip() or 'total_score'
        export_target = request.query_params.get('export_target', 'teachers').strip() or 'teachers'
        year = normalize_year(request.query_params.get('year'))
        year_from = normalize_year(request.query_params.get('year_from'))
        year_to = normalize_year(request.query_params.get('year_to'))
        has_collaboration = parse_bool_query_param(request.query_params.get('has_collaboration'))

        if is_college_admin_user(request.user):
            department = request.user.department or ''

        teachers = filter_teachers_queryset(
            all_teachers=all_teachers,
            department=department,
            teacher_id=teacher_id,
            teacher_title=teacher_title,
            has_collaboration=has_collaboration,
        )
        payload = build_overview_payload(
            teachers=teachers,
            all_teachers=all_teachers,
            year=year,
            year_from=year_from,
            year_to=year_to,
            achievement_type=achievement_type,
            rank_by=rank_by,
            selected_department=department,
            selected_teacher_id=teacher_id,
        )

        content = export_academy_csv(
            export_target=export_target,
            statistics=payload.get('score_statistics') or payload['statistics'],
            yearly_trend=payload['yearly_trend'],
            comparison_trend=payload['comparison_trend'],
            department_breakdown=payload['department_breakdown'],
            top_active_teachers=payload['top_active_teachers'],
            recent_records=payload['recent_scope_records'],
        )
        response = HttpResponse(content, content_type='text/csv; charset=utf-8')
        filename = f'academy-dashboard-{export_target}-{timezone.now().strftime("%Y%m%d-%H%M%S")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
