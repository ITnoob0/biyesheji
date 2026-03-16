from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_assistant.utils import AcademicAI
from graph_engine.utils import Neo4jEngine

from .models import Paper, PaperKeyword, Project, ResearchKeyword
from .scoring_engine import TeacherScoringEngine
from .serializers import PaperSerializer


class TeacherRadarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id: int) -> Response:
        if request.user.id != user_id and not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied('You do not have permission to view this teacher profile.')

        user_model = get_user_model()
        try:
            user = user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            return Response({'error': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

        papers_count = Paper.objects.filter(teacher=user).count()
        academic_output = min(papers_count * 10, 100)

        projects_count = Project.objects.filter(teacher=user).count()
        funding = min(projects_count * 20, 100)

        ip_patents = min(Paper.objects.filter(teacher=user, doi__isnull=False).count() * 25, 100)
        talent = min(papers_count * 8, 100)
        reputation = min(papers_count * 5, 100)
        keywords_count = PaperKeyword.objects.filter(paper__teacher=user).count()
        interdisciplinary = min(keywords_count * 4, 100)

        radar_dimensions = [
            {'name': '基础学术产出', 'value': academic_output},
            {'name': '经费吸附与攻坚', 'value': funding},
            {'name': '硬核知识产权', 'value': ip_patents},
            {'name': '人才培养成效', 'value': talent},
            {'name': '学术活跃与声誉', 'value': reputation},
            {'name': '跨学科融合度', 'value': interdisciplinary},
        ]
        return Response({'radar_dimensions': radar_dimensions})


class PaperViewSet(viewsets.ModelViewSet):
    queryset = (
        Paper.objects.select_related('teacher')
        .prefetch_related('coauthors', 'paperkeyword_set__keyword')
        .all()
        .order_by('-date_acquired', '-created_at')
    )
    serializer_class = PaperSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = self.queryset

        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(teacher=self.request.user)

        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(journal_name__icontains=search) | Q(doi__icontains=search)
            )

        paper_type = self.request.query_params.get('paper_type', '').strip()
        if paper_type:
            queryset = queryset.filter(paper_type=paper_type)

        return queryset

    def perform_create(self, serializer):
        instance = serializer.save(teacher=self.request.user)
        self._run_post_submit_pipeline(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        self._run_post_submit_pipeline(instance)

    def perform_destroy(self, instance):
        paper_id = instance.id
        instance.delete()
        self._delete_graph_snapshot(paper_id)

    def _run_post_submit_pipeline(self, instance):
        keywords = self._extract_keywords(instance)
        self._sync_graph(instance, keywords)

    def _extract_keywords(self, instance):
        PaperKeyword.objects.filter(paper=instance).delete()

        if not instance.abstract or len(instance.abstract.strip()) < 10:
            return []

        ai = AcademicAI()
        keywords = ai.extract_tags(instance.title, instance.abstract)

        for keyword_name in keywords:
            keyword_obj, _ = ResearchKeyword.objects.get_or_create(name=keyword_name)
            PaperKeyword.objects.get_or_create(paper=instance, keyword=keyword_obj)

        return keywords

    def _sync_graph(self, instance, keywords):
        graph = None
        try:
            graph = Neo4jEngine()
            graph.sync_paper_to_graph(
                paper_id=instance.id,
                title=instance.title,
                teacher={
                    'user_id': instance.teacher_id,
                    'name': instance.teacher.real_name or instance.teacher.username,
                },
                coauthors=[coauthor.name for coauthor in instance.coauthors.all()],
                keywords=keywords,
            )
        except Exception as exc:
            print(f'Failed to sync paper to graph database: {exc}')
        finally:
            if graph is not None:
                graph.close()

    def _delete_graph_snapshot(self, paper_id):
        graph = None
        try:
            graph = Neo4jEngine()
            graph.delete_paper_from_graph(paper_id)
        except Exception as exc:
            print(f'Failed to delete paper from graph database: {exc}')
        finally:
            if graph is not None:
                graph.close()


class TeacherDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        radar_result = TeacherScoringEngine.get_comprehensive_radar_data(user)
        total_papers = Paper.objects.filter(teacher=user).count()
        total_citations = (
            Paper.objects.filter(teacher=user).aggregate(Sum('citation_count'))['citation_count__sum'] or 0
        )
        total_projects = Project.objects.filter(teacher=user).count()

        return Response(
            {
                'statistics': [
                    {
                        'title': '总发文量',
                        'value': total_papers,
                        'suffix': '篇',
                        'icon': 'Document',
                        'iconClass': 'icon-blue',
                        'trend': 12.5,
                    },
                    {
                        'title': '总被引频次',
                        'value': total_citations,
                        'suffix': '次',
                        'icon': 'Star',
                        'iconClass': 'icon-orange',
                        'trend': 8.2,
                    },
                    {
                        'title': '综合科研评分',
                        'value': radar_result['total_score'],
                        'suffix': '分',
                        'icon': 'Trophy',
                        'iconClass': 'icon-red',
                        'trend': 5.0,
                    },
                    {
                        'title': '主持/参与项目',
                        'value': total_projects,
                        'suffix': '项',
                        'icon': 'Reading',
                        'iconClass': 'icon-green',
                        'trend': 0.0,
                    },
                ],
                'radar_data': radar_result['radar_dimensions'],
            }
        )
