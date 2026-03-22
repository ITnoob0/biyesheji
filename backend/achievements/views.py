from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db import transaction
from django.db.models.functions import ExtractYear
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_assistant.utils import AcademicAI
from core.api_errors import api_error_response
from graph_engine.services import AcademicGraphSyncService
from users.access import (
    PROFILE_SCOPE_MESSAGE,
    TEACHER_SELF_SERVICE_ONLY_MESSAGE,
    ensure_self_or_admin_user,
    ensure_self_user,
    ensure_teacher_user,
)

from .bibtex_import import build_bibtex_preview_entries, decode_bibtex_bytes
from .import_serializers import BibtexConfirmImportSerializer, BibtexPreviewRequestSerializer
from .models import AcademicService, IntellectualProperty, Paper, PaperKeyword, Project, ResearchKeyword, TeachingAchievement
from .portrait_analysis import build_dimension_trend, build_portrait_explanation, build_recent_structure
from .scoring_engine import TeacherScoringEngine
from .serializers import (
    AcademicServiceSerializer,
    IntellectualPropertySerializer,
    PaperSerializer,
    ProjectSerializer,
    TeachingAchievementSerializer,
)


def parse_bool_query_param(value: str) -> bool | None:
    normalized = (value or '').strip().lower()
    if normalized in {'1', 'true', 'yes'}:
        return True
    if normalized in {'0', 'false', 'no'}:
        return False
    return None


def get_requested_teacher(request, user_id: int | None = None):
    target_user_id = user_id or request.query_params.get('user_id', '').strip()

    if target_user_id:
        try:
            normalized_user_id = int(target_user_id)
        except (TypeError, ValueError):
            return None

        user_model = get_user_model()
        try:
            target_user = user_model.objects.get(id=normalized_user_id)
        except user_model.DoesNotExist:
            return None

        ensure_self_or_admin_user(request.user, target_user, PROFILE_SCOPE_MESSAGE)
        return target_user

    return request.user


def get_portrait_data_meta(user):
    created_candidates = []

    for model in (Paper, Project, IntellectualProperty, TeachingAchievement, AcademicService):
        latest = model.objects.filter(teacher=user).order_by('-created_at').values_list('created_at', flat=True).first()
        if latest:
            created_candidates.append(latest)

    latest_created_at = max(created_candidates) if created_candidates else None

    return {
        'updated_at': latest_created_at.isoformat() if latest_created_at else None,
        'source_note': '教师基础档案与论文、项目、知识产权、教学成果、学术服务实时聚合；关键词与合作画像仍主要基于论文数据；近年趋势按成果年份回溯估算，不等同于历史快照；拓扑图支持 Neo4j 失败时回退到 MySQL 关系数据。',
        'acceptance_scope': '本能力纳入当前阶段验收。',
    }


def build_recent_achievements(user, limit: int = 6):
    recent_records = []

    for paper in Paper.objects.filter(teacher=user).order_by('-date_acquired', '-created_at')[:limit]:
        recent_records.append(
            {
                'id': paper.id,
                'type': 'paper',
                'type_label': '论文成果',
                'title': paper.title,
                'date_acquired': paper.date_acquired.isoformat(),
                'detail': f'{paper.get_paper_type_display()} · {paper.journal_name}',
                'highlight': '代表作' if paper.is_representative else f'引用 {paper.citation_count} 次',
            }
        )

    for project in Project.objects.filter(teacher=user).order_by('-date_acquired', '-created_at')[:limit]:
        recent_records.append(
            {
                'id': project.id,
                'type': 'project',
                'type_label': '科研项目',
                'title': project.title,
                'date_acquired': project.date_acquired.isoformat(),
                'detail': f'{project.get_level_display()} · {project.get_role_display()}',
                'highlight': f'经费 {project.funding_amount} 万元',
            }
        )

    for item in IntellectualProperty.objects.filter(teacher=user).order_by('-date_acquired', '-created_at')[:limit]:
        recent_records.append(
            {
                'id': item.id,
                'type': 'intellectual_property',
                'type_label': '知识产权',
                'title': item.title,
                'date_acquired': item.date_acquired.isoformat(),
                'detail': f'{item.get_ip_type_display()} · 登记号 {item.registration_number}',
                'highlight': '已转化' if item.is_transformed else '未转化',
            }
        )

    for item in TeachingAchievement.objects.filter(teacher=user).order_by('-date_acquired', '-created_at')[:limit]:
        recent_records.append(
            {
                'id': item.id,
                'type': 'teaching_achievement',
                'type_label': '教学成果',
                'title': item.title,
                'date_acquired': item.date_acquired.isoformat(),
                'detail': f'{item.get_achievement_type_display()} · {item.level}',
                'highlight': '育人成果',
            }
        )

    for item in AcademicService.objects.filter(teacher=user).order_by('-date_acquired', '-created_at')[:limit]:
        recent_records.append(
            {
                'id': item.id,
                'type': 'academic_service',
                'type_label': '学术服务',
                'title': item.title,
                'date_acquired': item.date_acquired.isoformat(),
                'detail': f'{item.get_service_type_display()} · {item.organization}',
                'highlight': '学术共同体贡献',
            }
        )

    return sorted(
        recent_records,
        key=lambda item: (item['date_acquired'], item['id']),
        reverse=True,
    )[:limit]


class TeacherRadarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id: int) -> Response:
        user = get_requested_teacher(request, user_id=user_id)
        if user is None:
            return api_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message='教师账户不存在。',
                code='teacher_not_found',
                request=request,
                next_step='请确认教师账号是否存在，或返回教师列表后重新选择。',
            )

        radar_result = TeacherScoringEngine.get_comprehensive_radar_data(user)
        return Response(
            {
                'radar_dimensions': radar_result['radar_dimensions'],
                'dimension_sources': radar_result['dimension_sources'],
                'dimension_insights': radar_result['dimension_insights'],
                'data_meta': get_portrait_data_meta(user),
            }
        )


class TeacherOwnedAchievementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields: tuple[str, ...] = ()

    def get_queryset(self):
        queryset = self.queryset
        teacher_id = self.request.query_params.get('teacher_id', '').strip()

        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(teacher=self.request.user)
        elif teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)

        search = self.request.query_params.get('search', '').strip()
        if search and self.search_fields:
            q_object = Q()
            for field in self.search_fields:
                q_object |= Q(**{f'{field}__icontains': search})
            queryset = queryset.filter(q_object)

        return queryset

    def perform_create(self, serializer):
        ensure_teacher_user(self.request.user, TEACHER_SELF_SERVICE_ONLY_MESSAGE)
        instance = serializer.save(teacher=self.request.user)
        self.sync_graph(instance)

    def perform_update(self, serializer):
        ensure_teacher_user(self.request.user, TEACHER_SELF_SERVICE_ONLY_MESSAGE)
        ensure_self_user(self.request.user, serializer.instance.teacher, TEACHER_SELF_SERVICE_ONLY_MESSAGE)
        instance = serializer.save()
        self.sync_graph(instance)

    def perform_destroy(self, instance):
        ensure_teacher_user(self.request.user, TEACHER_SELF_SERVICE_ONLY_MESSAGE)
        ensure_self_user(self.request.user, instance.teacher, TEACHER_SELF_SERVICE_ONLY_MESSAGE)
        identifier = instance.id
        instance.delete()
        self.delete_graph_snapshot(identifier)

    def teacher_payload(self, instance):
        return {
            'user_id': instance.teacher_id,
            'name': instance.teacher.real_name or instance.teacher.username,
        }

    def sync_graph(self, instance):
        return None

    def delete_graph_snapshot(self, identifier):
        return None


class PaperViewSet(TeacherOwnedAchievementViewSet):
    queryset = (
        Paper.objects.select_related('teacher')
        .prefetch_related('coauthors', 'paperkeyword_set__keyword')
        .all()
        .order_by('-date_acquired', '-created_at')
    )
    serializer_class = PaperSerializer
    search_fields = ('title', 'journal_name', 'doi')

    def get_queryset(self):
        queryset = super().get_queryset()
        paper_type = self.request.query_params.get('paper_type', '').strip()
        if paper_type:
            queryset = queryset.filter(paper_type=paper_type)
        year = self.request.query_params.get('year', '').strip()
        if year.isdigit():
            queryset = queryset.filter(date_acquired__year=int(year))
        year_from = self.request.query_params.get('year_from', '').strip()
        if year_from.isdigit():
            queryset = queryset.filter(date_acquired__year__gte=int(year_from))
        year_to = self.request.query_params.get('year_to', '').strip()
        if year_to.isdigit():
            queryset = queryset.filter(date_acquired__year__lte=int(year_to))
        is_representative = parse_bool_query_param(self.request.query_params.get('is_representative', ''))
        if is_representative is not None:
            queryset = queryset.filter(is_representative=is_representative)

        ordering_map = {
            'date_desc': ('-date_acquired', '-created_at'),
            'date_asc': ('date_acquired', 'created_at'),
            'citation_desc': ('-citation_count', '-date_acquired', '-created_at'),
            'citation_asc': ('citation_count', '-date_acquired', '-created_at'),
            'title_asc': ('title', '-date_acquired', '-created_at'),
            'title_desc': ('-title', '-date_acquired', '-created_at'),
            'created_desc': ('-created_at',),
            'created_asc': ('created_at',),
        }
        sort_by = self.request.query_params.get('sort_by', '').strip()
        if sort_by in ordering_map:
            queryset = queryset.order_by(*ordering_map[sort_by])
        return queryset

    @action(
        detail=False,
        methods=['post'],
        url_path='import/bibtex-preview',
        parser_classes=[MultiPartParser, FormParser, JSONParser],
    )
    def bibtex_preview(self, request):
        serializer = BibtexPreviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if serializer.validated_data.get('file'):
            raw_content = decode_bibtex_bytes(serializer.validated_data['file'].read())
        else:
            raw_content = serializer.validated_data['content']

        try:
            preview_data = build_bibtex_preview_entries(raw_content, request.user)
        except ValueError as exc:
            return api_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=str(exc),
                code='bibtex_preview_invalid',
                request=request,
                next_step='请检查 BibTeX 内容编码、条目格式和必填字段后重新预览。',
            )

        return Response(
            {
                **preview_data,
                'parser': 'bibtex',
                'pdf_import_note': 'PDF 元数据解析暂未纳入当前阶段验收，已为后续版本预留。',
                'acceptance_scope': '本能力纳入当前阶段验收。',
            }
        )

    @action(detail=False, methods=['post'], url_path='import/bibtex-confirm')
    def bibtex_confirm(self, request):
        serializer = BibtexConfirmImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        imported_records = []
        skipped_entries = []
        failed_entries = []

        for entry in serializer.validated_data['entries']:
            payload = {
                'title': entry['title'],
                'abstract': entry.get('abstract', ''),
                'date_acquired': entry['date_acquired'],
                'paper_type': entry['paper_type'],
                'journal_name': entry['journal_name'],
                'journal_level': entry.get('journal_level', ''),
                'published_volume': entry.get('published_volume', ''),
                'published_issue': entry.get('published_issue', ''),
                'pages': entry.get('pages', ''),
                'source_url': entry.get('source_url', ''),
                'citation_count': entry.get('citation_count', 0),
                'is_first_author': entry.get('is_first_author', True),
                'is_representative': entry.get('is_representative', False),
                'doi': entry.get('doi', ''),
                'coauthors': entry.get('coauthors', []),
            }

            paper_serializer = self.get_serializer(data=payload, context={'request': request})
            if not paper_serializer.is_valid():
                target_collection = skipped_entries if 'doi' in paper_serializer.errors else failed_entries
                target_collection.append(
                    {
                        'source_index': entry.get('source_index'),
                        'title': entry.get('title', ''),
                        'doi': entry.get('doi', ''),
                        'issue_summary': '重复记录已跳过，请先核对当前账号下的现有论文。'
                        if 'doi' in paper_serializer.errors
                        else '字段校验未通过，请根据错误提示修正后重试。',
                        'errors': paper_serializer.errors,
                    }
                )
                continue

            try:
                with transaction.atomic():
                    paper = paper_serializer.save(teacher=request.user)
                    self.sync_graph(paper)
            except Exception as exc:
                failed_entries.append(
                    {
                        'source_index': entry.get('source_index'),
                        'title': entry.get('title', ''),
                        'doi': entry.get('doi', ''),
                        'issue_summary': '写入论文数据失败，请稍后重试或联系管理员检查日志。',
                        'errors': {'detail': [str(exc)]},
                    }
                )
                continue

            imported_records.append(
                {
                    'id': paper.id,
                    'title': paper.title,
                    'doi': paper.doi,
                }
            )

        return Response(
            {
                'imported_count': len(imported_records),
                'skipped_count': len(skipped_entries),
                'failed_count': len(failed_entries),
                'imported_records': imported_records,
                'skipped_entries': skipped_entries,
                'failed_entries': failed_entries,
            }
        )

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        queryset = self.get_queryset()
        yearly_distribution = list(
            queryset.annotate(year=ExtractYear('date_acquired'))
            .values('year')
            .annotate(count=Count('id'))
            .order_by('-year')
        )
        type_distribution = list(
            queryset.values('paper_type')
            .annotate(count=Count('id'))
            .order_by('-count', 'paper_type')
        )
        latest_records = queryset.order_by('-date_acquired', '-created_at')[:5]

        duplicate_doi_groups = list(
            queryset.exclude(doi='')
            .values('doi')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
            .order_by('-count', 'doi')
        )

        return Response(
            {
                'total_count': queryset.count(),
                'representative_count': queryset.filter(is_representative=True).count(),
                'recent_count': queryset.filter(date_acquired__year__gte=timezone.now().year - 2).count(),
                'missing_doi_count': queryset.filter(doi='').count(),
                'missing_source_url_count': queryset.filter(source_url='').count(),
                'incomplete_metadata_count': queryset.filter(
                    Q(pages='') | Q(source_url='') | Q(journal_level='')
                ).count(),
                'duplicate_doi_count': len(duplicate_doi_groups),
                'yearly_distribution': [
                    {'year': item['year'], 'count': item['count']}
                    for item in yearly_distribution
                    if item['year'] is not None
                ],
                'type_distribution': [
                    {
                        'paper_type': item['paper_type'],
                        'label': dict(Paper.PAPER_TYPES).get(item['paper_type'], item['paper_type']),
                        'count': item['count'],
                    }
                    for item in type_distribution
                ],
                'recent_records': [
                    {
                        'id': paper.id,
                        'title': paper.title,
                        'date_acquired': paper.date_acquired.isoformat(),
                        'paper_type': paper.paper_type,
                        'paper_type_display': paper.get_paper_type_display(),
                        'journal_name': paper.journal_name,
                        'citation_count': paper.citation_count,
                        'is_representative': paper.is_representative,
                        'metadata_alerts': PaperSerializer(paper, context={'request': request}).data.get('metadata_alerts', []),
                    }
                    for paper in latest_records
                ],
            }
        )

    def sync_graph(self, instance):
        keywords = self._extract_keywords(instance)
        AcademicGraphSyncService.sync_paper(
            paper_id=instance.id,
            title=instance.title,
            teacher=self.teacher_payload(instance),
            coauthors=[coauthor.name for coauthor in instance.coauthors.all()],
            keywords=keywords,
        )

    def delete_graph_snapshot(self, identifier):
        AcademicGraphSyncService.delete_paper(identifier)

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


class ProjectViewSet(TeacherOwnedAchievementViewSet):
    queryset = Project.objects.select_related('teacher').all().order_by('-date_acquired', '-created_at')
    serializer_class = ProjectSerializer
    search_fields = ('title', 'status')

    def sync_graph(self, instance):
        AcademicGraphSyncService.sync_project(
            project_id=instance.id,
            title=instance.title,
            teacher=self.teacher_payload(instance),
            level=instance.level,
            role=instance.role,
            status=instance.status,
        )

    def delete_graph_snapshot(self, identifier):
        AcademicGraphSyncService.delete_project(identifier)


class IntellectualPropertyViewSet(TeacherOwnedAchievementViewSet):
    queryset = IntellectualProperty.objects.select_related('teacher').all().order_by('-date_acquired', '-created_at')
    serializer_class = IntellectualPropertySerializer
    search_fields = ('title', 'registration_number')

    def sync_graph(self, instance):
        AcademicGraphSyncService.sync_intellectual_property(
            ip_id=instance.id,
            title=instance.title,
            teacher=self.teacher_payload(instance),
            ip_type=instance.ip_type,
            registration_number=instance.registration_number,
        )

    def delete_graph_snapshot(self, identifier):
        AcademicGraphSyncService.delete_intellectual_property(identifier)


class TeachingAchievementViewSet(TeacherOwnedAchievementViewSet):
    queryset = TeachingAchievement.objects.select_related('teacher').all().order_by('-date_acquired', '-created_at')
    serializer_class = TeachingAchievementSerializer
    search_fields = ('title', 'level')

    def sync_graph(self, instance):
        AcademicGraphSyncService.sync_teaching_achievement(
            teaching_id=instance.id,
            title=instance.title,
            teacher=self.teacher_payload(instance),
            achievement_type=instance.achievement_type,
            level=instance.level,
        )

    def delete_graph_snapshot(self, identifier):
        AcademicGraphSyncService.delete_teaching_achievement(identifier)


class AcademicServiceViewSet(TeacherOwnedAchievementViewSet):
    queryset = AcademicService.objects.select_related('teacher').all().order_by('-date_acquired', '-created_at')
    serializer_class = AcademicServiceSerializer
    search_fields = ('title', 'organization')

    def sync_graph(self, instance):
        AcademicGraphSyncService.sync_academic_service(
            service_id=instance.id,
            title=instance.title,
            teacher=self.teacher_payload(instance),
            service_type=instance.service_type,
            organization=instance.organization,
        )

    def delete_graph_snapshot(self, identifier):
        AcademicGraphSyncService.delete_academic_service(identifier)


class TeacherDashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = get_requested_teacher(request)
        if user is None:
            return api_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message='教师账户不存在。',
                code='teacher_not_found',
                request=request,
                next_step='请确认教师账号是否存在，或返回教师列表后重新选择。',
            )

        radar_result = TeacherScoringEngine.get_comprehensive_radar_data(user)
        metrics = radar_result['metrics']

        statistics = [
            {
                'title': '总成果数',
                'value': metrics['total_achievements'],
                'suffix': '项',
                'icon': 'CollectionTag',
                'iconClass': 'icon-blue',
                'trend': None,
                'helper': '论文、项目、知识产权、教学成果、学术服务总和',
            },
            {
                'title': '论文成果',
                'value': metrics['paper_count'],
                'suffix': '篇',
                'icon': 'Document',
                'iconClass': 'icon-blue',
                'trend': None,
                'helper': f"总被引 {metrics['citation_total']} 次",
            },
            {
                'title': '项目与知识产权',
                'value': metrics['project_count'] + metrics['ip_count'],
                'suffix': '项',
                'icon': 'Reading',
                'iconClass': 'icon-green',
                'trend': None,
                'helper': f"项目 {metrics['project_count']} 项 / 知识产权 {metrics['ip_count']} 项",
            },
            {
                'title': '教学与学术服务',
                'value': metrics['teaching_count'] + metrics['service_count'],
                'suffix': '项',
                'icon': 'User',
                'iconClass': 'icon-orange',
                'trend': None,
                'helper': f"教学成果 {metrics['teaching_count']} 项 / 学术服务 {metrics['service_count']} 项",
            },
            {
                'title': '综合画像评分',
                'value': radar_result['total_score'],
                'suffix': '分',
                'icon': 'Trophy',
                'iconClass': 'icon-red',
                'trend': None,
                'helper': '依据多成果类型实时聚合计算',
            },
        ]

        return Response(
            {
                'statistics': statistics,
                'radar_data': radar_result['radar_dimensions'],
                'dimension_insights': radar_result['dimension_insights'],
                'achievement_overview': {
                    'paper_count': metrics['paper_count'],
                    'project_count': metrics['project_count'],
                    'intellectual_property_count': metrics['ip_count'],
                    'teaching_achievement_count': metrics['teaching_count'],
                    'academic_service_count': metrics['service_count'],
                    'total_citations': metrics['citation_total'],
                    'total_achievements': metrics['total_achievements'],
                },
                'recent_achievements': build_recent_achievements(user),
                'dimension_trend': build_dimension_trend(user),
                'recent_structure': build_recent_structure(user),
                'portrait_explanation': build_portrait_explanation(),
                'data_meta': get_portrait_data_meta(user),
            }
        )
