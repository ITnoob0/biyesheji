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
    build_comparison_summary,
    build_comparison_department_distribution,
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
            teachers = teachers.filter(papers__coauthors__isnull=False).distinct()
        else:
            teachers = teachers.exclude(papers__coauthors__isnull=False).distinct()
    return teachers


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
    comparison_scope_querysets = build_scope_querysets(teacher_ids, None, achievement_type)
    comparison_baseline_teachers = (
        all_teachers.filter(department=compare_department) if compare_department else all_teachers
    )
    comparison_baseline_teacher_ids = list(comparison_baseline_teachers.values_list('id', flat=True))
    comparison_baseline_querysets = build_scope_querysets(comparison_baseline_teacher_ids, None, achievement_type)

    teacher_total = teachers.count()
    paper_total = current_querysets['paper'].count()
    project_total = current_querysets['project'].count()
    ip_total = current_querysets['ip'].count()
    teaching_total = current_querysets['teaching'].count()
    service_total = current_querysets['service'].count()
    achievement_total = paper_total + project_total + ip_total + teaching_total + service_total
    collaboration_total = current_querysets['collaboration'].count()

    statistics = [
        {
            'title': '教师总数',
            'value': teacher_total,
            'suffix': '人',
            'icon': 'User',
            'iconClass': 'icon-blue',
            'helper': '当前筛选范围内纳入分析的教师账号数量',
        },
        {
            'title': '论文总数',
            'value': paper_total,
            'suffix': '篇',
            'icon': 'Document',
            'iconClass': 'icon-blue',
            'helper': '当前筛选范围内已录入论文成果',
        },
        {
            'title': '总成果数',
            'value': achievement_total,
            'suffix': '项',
            'icon': 'CollectionTag',
            'iconClass': 'icon-green',
            'helper': '论文、项目、知识产权、教学成果、学术服务合计',
        },
        {
            'title': '合作关系数',
            'value': collaboration_total,
            'suffix': '条',
            'icon': 'Share',
            'iconClass': 'icon-orange',
            'helper': '当前筛选范围内论文合作作者关系累计条目',
        },
        {
            'title': '项目与知产',
            'value': project_total + ip_total,
            'suffix': '项',
            'icon': 'Reading',
            'iconClass': 'icon-red',
            'helper': f'项目 {project_total} 项 / 知识产权 {ip_total} 项',
        },
    ]

    yearly_trend = build_yearly_trend(current_querysets)
    comparison_trend = build_scope_comparison_trend(comparison_scope_querysets, comparison_baseline_querysets)
    teacher_rank = build_teacher_rank(teachers, current_querysets, rank_by=rank_by)

    current_metrics = {
        'teacher_total': teacher_total,
        'achievement_total': achievement_total,
        'collaboration_total': collaboration_total,
    }
    baseline_metrics = {
        'teacher_total': all_teachers.count(),
        'achievement_total': (
            baseline_querysets['paper'].count()
            + baseline_querysets['project'].count()
            + baseline_querysets['ip'].count()
            + baseline_querysets['teaching'].count()
            + baseline_querysets['service'].count()
        ),
        'collaboration_total': baseline_querysets['collaboration'].count(),
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
        'top_active_teachers': teacher_rank[:12],
        'collaboration_overview': build_collaboration_overview(
            current_querysets['paper'],
            current_querysets['collaboration'],
            paper_total,
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
        all_teachers = user_model.objects.filter(is_superuser=False)
        if is_college_admin_user(request.user):
            all_teachers = all_teachers.filter(is_staff=False, department=request.user.department)

        department = request.query_params.get('department', '').strip()
        compare_department = request.query_params.get('compare_department', '').strip()
        teacher_id = request.query_params.get('teacher_id', '').strip()
        teacher_title = request.query_params.get('teacher_title', '').strip()
        achievement_type = request.query_params.get('achievement_type', 'all').strip() or 'all'
        rank_by = request.query_params.get('rank_by', 'achievement_total').strip() or 'achievement_total'
        year = normalize_year(request.query_params.get('year'))
        year_from = normalize_year(request.query_params.get('year_from'))
        year_to = normalize_year(request.query_params.get('year_to'))
        has_collaboration = parse_bool_query_param(request.query_params.get('has_collaboration'))

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
        all_teachers = user_model.objects.filter(is_superuser=False)
        if is_college_admin_user(request.user):
            all_teachers = all_teachers.filter(is_staff=False, department=request.user.department)

        department = request.query_params.get('department', '').strip()
        teacher_id = request.query_params.get('teacher_id', '').strip()
        teacher_title = request.query_params.get('teacher_title', '').strip()
        achievement_type = request.query_params.get('achievement_type', 'all').strip() or 'all'
        rank_by = request.query_params.get('rank_by', 'achievement_total').strip() or 'achievement_total'
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
            statistics=payload['statistics'],
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
