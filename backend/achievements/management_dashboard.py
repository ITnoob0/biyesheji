from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db.models import Count
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AcademicService, CoAuthor, IntellectualProperty, Paper, Project, TeachingAchievement


def ensure_admin(user):
    if not (user.is_staff or user.is_superuser):
        raise PermissionDenied('Only administrators can access the academy dashboard.')


def build_management_data_meta():
    return {
        'source_note': '学院级看板当前基于 MySQL 业务数据实时聚合，聚焦教师、论文、项目、知识产权、教学成果、学术服务与合作网络的基础统计。',
        'acceptance_scope': '本能力属于当前阶段扩展方向，以克制版管理统计看板交付。',
        'future_extension_hint': '后续可在当前聚合接口基础上继续扩展学院级钻取、筛选和更复杂的 BI 分析。',
    }


def normalize_year(raw_value):
    if raw_value in (None, ''):
        return None

    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


class AcademyOverviewDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_admin(request.user)

        user_model = get_user_model()
        teachers = user_model.objects.filter(is_superuser=False)
        department = request.query_params.get('department', '').strip()
        teacher_id = request.query_params.get('teacher_id', '').strip()
        year = normalize_year(request.query_params.get('year'))

        if department:
            teachers = teachers.filter(department=department)

        if teacher_id:
            teachers = teachers.filter(id=teacher_id)

        teacher_ids = list(teachers.values_list('id', flat=True))

        paper_queryset = Paper.objects.filter(teacher_id__in=teacher_ids)
        project_queryset = Project.objects.filter(teacher_id__in=teacher_ids)
        ip_queryset = IntellectualProperty.objects.filter(teacher_id__in=teacher_ids)
        teaching_queryset = TeachingAchievement.objects.filter(teacher_id__in=teacher_ids)
        service_queryset = AcademicService.objects.filter(teacher_id__in=teacher_ids)
        collaboration_queryset = CoAuthor.objects.filter(paper__teacher_id__in=teacher_ids)

        if year:
            paper_queryset = paper_queryset.filter(date_acquired__year=year)
            project_queryset = project_queryset.filter(date_acquired__year=year)
            ip_queryset = ip_queryset.filter(date_acquired__year=year)
            teaching_queryset = teaching_queryset.filter(date_acquired__year=year)
            service_queryset = service_queryset.filter(date_acquired__year=year)
            collaboration_queryset = collaboration_queryset.filter(paper__date_acquired__year=year)

        teacher_total = teachers.count()
        paper_total = paper_queryset.count()
        project_total = project_queryset.count()
        ip_total = ip_queryset.count()
        teaching_total = teaching_queryset.count()
        service_total = service_queryset.count()
        achievement_total = paper_total + project_total + ip_total + teaching_total + service_total
        collaboration_total = collaboration_queryset.count()

        statistics = [
            {
                'title': '教师总数',
                'value': teacher_total,
                'suffix': '人',
                'icon': 'User',
                'iconClass': 'icon-blue',
                'helper': '已纳入系统的教师账号数量',
            },
            {
                'title': '论文总数',
                'value': paper_total,
                'suffix': '篇',
                'icon': 'Document',
                'iconClass': 'icon-blue',
                'helper': '当前系统中已录入论文成果',
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
                'helper': '论文合作作者关系累计条目',
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

        yearly_counter = defaultdict(lambda: {'paper': 0, 'project': 0, 'achievement_total': 0})
        for model_name, queryset in (
            ('paper', paper_queryset),
            ('project', project_queryset),
            ('ip', ip_queryset),
            ('teaching', teaching_queryset),
            ('service', service_queryset),
        ):
            for item in queryset.values_list('date_acquired', flat=True):
                if not item:
                    continue
                year = item.year
                yearly_counter[year]['achievement_total'] += 1
                if model_name == 'paper':
                    yearly_counter[year]['paper'] += 1
                if model_name == 'project':
                    yearly_counter[year]['project'] += 1

        yearly_trend = [
            {
                'year': year,
                'paper_count': payload['paper'],
                'project_count': payload['project'],
                'achievement_total': payload['achievement_total'],
            }
            for year, payload in sorted(yearly_counter.items())
        ]

        department_distribution = list(
            teachers.values('department')
            .annotate(count=Count('id'))
            .order_by('-count', 'department')
        )
        department_distribution = [
            {
                'name': item['department'] or '未填写院系',
                'value': item['count'],
            }
            for item in department_distribution
        ]

        teacher_rank = []
        for teacher in teachers:
            teacher_papers = paper_queryset.filter(teacher=teacher)
            teacher_projects = project_queryset.filter(teacher=teacher)
            teacher_ips = ip_queryset.filter(teacher=teacher)
            teacher_teaching = teaching_queryset.filter(teacher=teacher)
            teacher_services = service_queryset.filter(teacher=teacher)
            teacher_rank.append(
                {
                    'user_id': teacher.id,
                    'teacher_name': teacher.real_name or teacher.username,
                    'department': teacher.department or '未填写院系',
                    'paper_count': teacher_papers.count(),
                    'project_count': teacher_projects.count(),
                    'achievement_total': (
                        teacher_papers.count()
                        + teacher_projects.count()
                        + teacher_ips.count()
                        + teacher_teaching.count()
                        + teacher_services.count()
                    ),
                }
            )

        teacher_rank.sort(
            key=lambda item: (item['achievement_total'], item['paper_count'], item['project_count']),
            reverse=True,
        )

        teachers_with_collaboration = paper_queryset.filter(coauthors__isnull=False).values('teacher').distinct().count()
        collaboration_overview = {
            'coauthor_relation_total': collaboration_total,
            'teachers_with_collaboration': teachers_with_collaboration,
            'paper_with_collaboration': paper_queryset.filter(coauthors__isnull=False).distinct().count(),
            'average_coauthors_per_paper': round(collaboration_total / paper_total, 2) if paper_total else 0,
        }

        filter_options = {
            'departments': sorted(
                {
                    item
                    for item in user_model.objects.filter(is_superuser=False).values_list('department', flat=True)
                    if item
                }
            ),
            'teachers': [
                {
                    'user_id': teacher.id,
                    'teacher_name': teacher.real_name or teacher.username,
                    'department': teacher.department or '未填写院系',
                }
                for teacher in user_model.objects.filter(is_superuser=False).order_by('department', 'id')
            ],
            'years': sorted(
                {
                    item.year
                    for item in list(Paper.objects.values_list('date_acquired', flat=True))
                    + list(Project.objects.values_list('date_acquired', flat=True))
                    + list(IntellectualProperty.objects.values_list('date_acquired', flat=True))
                    + list(TeachingAchievement.objects.values_list('date_acquired', flat=True))
                    + list(AcademicService.objects.values_list('date_acquired', flat=True))
                    if item
                }
            ),
        }

        return Response(
            {
                'statistics': statistics,
                'yearly_trend': yearly_trend,
                'department_distribution': department_distribution,
                'top_active_teachers': teacher_rank[:8],
                'collaboration_overview': collaboration_overview,
                'data_meta': build_management_data_meta(),
                'active_filters': {
                    'department': department,
                    'teacher_id': int(teacher_id) if teacher_id else None,
                    'year': year,
                },
                'filter_options': filter_options,
            },
            status=status.HTTP_200_OK,
        )
