from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .academy_dashboard_analysis import (
    build_collaboration_overview,
    build_comparison_summary,
    build_department_breakdown,
    build_department_distribution,
    build_filter_options,
    build_management_data_meta,
    build_scope_querysets,
    build_teacher_rank,
    build_trend_summary,
    build_yearly_trend,
    normalize_year,
    parse_bool_query_param,
)


def ensure_admin(user):
    if not (user.is_staff or user.is_superuser):
        raise PermissionDenied('Only administrators can access the academy dashboard.')


class AcademyOverviewDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_admin(request.user)

        user_model = get_user_model()
        all_teachers = user_model.objects.filter(is_superuser=False)

        department = request.query_params.get('department', '').strip()
        teacher_id = request.query_params.get('teacher_id', '').strip()
        teacher_title = request.query_params.get('teacher_title', '').strip()
        year = normalize_year(request.query_params.get('year'))
        has_collaboration = parse_bool_query_param(request.query_params.get('has_collaboration'))

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

        teacher_ids = list(teachers.values_list('id', flat=True))
        current_querysets = build_scope_querysets(teacher_ids, year)
        baseline_teacher_ids = list(all_teachers.values_list('id', flat=True))
        baseline_querysets = build_scope_querysets(baseline_teacher_ids, year)

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
        teacher_rank = build_teacher_rank(teachers, current_querysets)

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

        return Response(
            {
                'statistics': statistics,
                'yearly_trend': yearly_trend,
                'trend_summary': build_trend_summary(yearly_trend),
                'comparison_summary': build_comparison_summary(current_metrics, baseline_metrics, year),
                'department_distribution': build_department_distribution(teachers),
                'department_breakdown': build_department_breakdown(teachers, current_querysets),
                'top_active_teachers': teacher_rank[:12],
                'collaboration_overview': build_collaboration_overview(
                    current_querysets['paper'],
                    current_querysets['collaboration'],
                    paper_total,
                ),
                'data_meta': build_management_data_meta(),
                'active_filters': {
                    'department': department,
                    'teacher_id': int(teacher_id) if teacher_id else None,
                    'teacher_title': teacher_title,
                    'year': year,
                    'has_collaboration': has_collaboration,
                },
                'filter_options': build_filter_options(),
            },
            status=status.HTTP_200_OK,
        )
