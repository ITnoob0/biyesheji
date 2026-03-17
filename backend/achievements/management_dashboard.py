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


class AcademyOverviewDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_admin(request.user)

        user_model = get_user_model()
        teachers = user_model.objects.filter(is_superuser=False)

        teacher_total = teachers.count()
        paper_total = Paper.objects.count()
        project_total = Project.objects.count()
        ip_total = IntellectualProperty.objects.count()
        teaching_total = TeachingAchievement.objects.count()
        service_total = AcademicService.objects.count()
        achievement_total = paper_total + project_total + ip_total + teaching_total + service_total
        collaboration_total = CoAuthor.objects.count()

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
            ('paper', Paper.objects.all()),
            ('project', Project.objects.all()),
            ('ip', IntellectualProperty.objects.all()),
            ('teaching', TeachingAchievement.objects.all()),
            ('service', AcademicService.objects.all()),
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
            teacher_rank.append(
                {
                    'user_id': teacher.id,
                    'teacher_name': teacher.real_name or teacher.username,
                    'department': teacher.department or '未填写院系',
                    'paper_count': Paper.objects.filter(teacher=teacher).count(),
                    'project_count': Project.objects.filter(teacher=teacher).count(),
                    'achievement_total': (
                        Paper.objects.filter(teacher=teacher).count()
                        + Project.objects.filter(teacher=teacher).count()
                        + IntellectualProperty.objects.filter(teacher=teacher).count()
                        + TeachingAchievement.objects.filter(teacher=teacher).count()
                        + AcademicService.objects.filter(teacher=teacher).count()
                    ),
                }
            )

        teacher_rank.sort(
            key=lambda item: (item['achievement_total'], item['paper_count'], item['project_count']),
            reverse=True,
        )

        teachers_with_collaboration = Paper.objects.filter(coauthors__isnull=False).values('teacher').distinct().count()
        collaboration_overview = {
            'coauthor_relation_total': collaboration_total,
            'teachers_with_collaboration': teachers_with_collaboration,
            'paper_with_collaboration': Paper.objects.filter(coauthors__isnull=False).distinct().count(),
            'average_coauthors_per_paper': round(collaboration_total / paper_total, 2) if paper_total else 0,
        }

        return Response(
            {
                'statistics': statistics,
                'yearly_trend': yearly_trend,
                'department_distribution': department_distribution,
                'top_active_teachers': teacher_rank[:8],
                'collaboration_overview': collaboration_overview,
                'data_meta': build_management_data_meta(),
            },
            status=status.HTTP_200_OK,
        )
