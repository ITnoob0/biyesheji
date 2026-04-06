from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_assistant.utils import AcademicAI
from core.api_errors import api_error_response
from graph_engine.services import AcademicGraphSyncService
from users.access import (
    PROFILE_SCOPE_MESSAGE,
    can_access_teacher_scope,
    ensure_admin_user,
    is_admin_user,
    is_college_admin_user,
    ensure_self_or_admin_user,
    ensure_self_user,
)

ACHIEVEMENT_SELF_SERVICE_ONLY_MESSAGE = '当前成果仅支持账号本人维护，查看他人成果时为只读。'

from .bibtex_import import build_bibtex_preview_entries, decode_bibtex_bytes, revalidate_bibtex_entries
from .governance import (
    build_compare_payload,
    build_governance_overview,
    build_metadata_flag_codes,
    diff_paper_fields,
    export_papers_as_csv,
    log_paper_operation,
    metadata_alert_count_expression,
    normalize_selected_papers,
    snapshot_paper_fields,
)
from .import_serializers import (
    BibtexConfirmImportSerializer,
    BibtexPreviewRequestSerializer,
    BibtexRevalidateSerializer,
)
from .models import (
    AcademicService,
    AchievementOperationLog,
    IntellectualProperty,
    Paper,
    PaperKeyword,
    Project,
    ResearchKeyword,
    TeachingAchievement,
)
from .portrait_analysis import (
    build_dimension_trend,
    build_portrait_explanation,
    build_portrait_report,
    build_recent_structure,
    build_snapshot_boundary,
    build_stage_comparison,
    export_portrait_report_markdown,
)
from .scoring_engine import TeacherScoringEngine
from .serializers import (
    AcademicServiceSerializer,
    AchievementOperationLogSerializer,
    AchievementRejectSerializer,
    IntellectualPropertySerializer,
    PaperCleanupApplySerializer,
    PaperOperationLogSerializer,
    PaperRepresentativeBatchSerializer,
    PaperSerializer,
    ProjectSerializer,
    TeachingAchievementSerializer,
)
from .visibility import APPROVED_STATUS, approved_queryset


def parse_bool_query_param(value: str) -> bool | None:
    normalized = (value or '').strip().lower()
    if normalized in {'1', 'true', 'yes'}:
        return True
    if normalized in {'0', 'false', 'no'}:
        return False
    return None


def normalize_operation_value(value):
    if value is None:
        return ''
    if isinstance(value, bool):
        return '是' if value else '否'
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


def build_achievement_operation_snapshot(achievement_type: str, instance) -> tuple[dict, str]:
    if achievement_type == 'papers':
        payload = {
            '题目': instance.title,
            '类型': instance.get_paper_type_display(),
            '期刊/会议': instance.journal_name,
            '时间': normalize_operation_value(instance.date_acquired),
            'DOI': instance.doi,
            '引用次数': normalize_operation_value(instance.citation_count),
        }
        return payload, instance.journal_name

    if achievement_type == 'projects':
        payload = {
            '项目名称': instance.title,
            '项目级别': instance.get_level_display(),
            '角色': instance.get_role_display(),
            '经费金额': normalize_operation_value(instance.funding_amount),
            '项目状态': instance.project_status,
            '时间': normalize_operation_value(instance.date_acquired),
        }
        return payload, f"{instance.get_level_display()} / {instance.get_role_display()}"

    if achievement_type == 'intellectual-properties':
        payload = {
            '成果名称': instance.title,
            '知识产权类型': instance.get_ip_type_display(),
            '角色': instance.get_role_display(),
            '登记号': instance.registration_number,
            '是否转化': normalize_operation_value(instance.is_transformed),
            '时间': normalize_operation_value(instance.date_acquired),
        }
        return payload, f"{instance.get_ip_type_display()} / {instance.get_role_display()}"

    if achievement_type == 'teaching-achievements':
        payload = {
            '成果名称': instance.title,
            '教学成果类型': instance.get_achievement_type_display(),
            '角色': instance.get_role_display(),
            '级别': instance.level,
            '时间': normalize_operation_value(instance.date_acquired),
        }
        return payload, f"{instance.get_achievement_type_display()} / {instance.get_role_display()} / {instance.level}"

    if achievement_type == 'academic-services':
        payload = {
            '服务名称': instance.title,
            '服务类型': instance.get_service_type_display(),
            '服务机构': instance.organization,
            '时间': normalize_operation_value(instance.date_acquired),
        }
        return payload, instance.organization

    return {'标题': getattr(instance, 'title', '')}, ''


def diff_operation_snapshot(before: dict, after: dict) -> list[str]:
    field_names = []
    for key in set(before.keys()) | set(after.keys()):
        if normalize_operation_value(before.get(key)) != normalize_operation_value(after.get(key)):
            field_names.append(key)
    return field_names


def log_achievement_operation(
    *,
    teacher,
    achievement_type: str,
    action: str,
    source: str,
    summary: str,
    instance=None,
    changed_fields: list[str] | None = None,
    title_snapshot: str = '',
    detail_snapshot: str = '',
    snapshot_payload: dict | None = None,
    achievement_id: int | None = None,
):
    payload = snapshot_payload or {}
    if instance is not None and not payload:
        payload, detail = build_achievement_operation_snapshot(achievement_type, instance)
        detail_snapshot = detail_snapshot or detail
        achievement_id = achievement_id or instance.id
        title_snapshot = title_snapshot or instance.title

    return AchievementOperationLog.objects.create(
        teacher=teacher,
        achievement_type=achievement_type,
        achievement_id=achievement_id,
        action=action,
        source=source,
        summary=summary,
        changed_fields=changed_fields or [],
        title_snapshot=title_snapshot,
        detail_snapshot=detail_snapshot,
        snapshot_payload=payload,
    )


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
        latest = (
            approved_queryset(model.objects.filter(teacher=user))
            .order_by('-created_at')
            .values_list('created_at', flat=True)
            .first()
        )
        if latest:
            created_candidates.append(latest)

    latest_created_at = max(created_candidates) if created_candidates else None
    return {
        'updated_at': latest_created_at.isoformat() if latest_created_at else None,
        'source_note': '教师基础档案与论文、项目、知识产权、教学成果、学术服务实时聚合；关键词与合作画像仍主要基于论文数据；图谱分析继续保留 Neo4j 可选、MySQL 回退链路。',
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
                'detail': f'{paper.get_paper_type_display()} / {paper.journal_name}',
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
                'detail': f'{project.get_level_display()} / {project.get_role_display()}',
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
                'detail': f'{item.get_ip_type_display()} / 登记号 {item.registration_number}',
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
                'detail': f'{item.get_achievement_type_display()} / {item.level}',
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
                'detail': f'{item.get_service_type_display()} / {item.organization}',
                'highlight': '学术共同体贡献',
            }
        )

    return sorted(recent_records, key=lambda item: (item['date_acquired'], item['id']), reverse=True)[:limit]


def build_all_achievements(user):
    achievement_records = []

    for paper in approved_queryset(Paper.objects.filter(teacher=user)).order_by('-date_acquired', '-created_at'):
        is_representative = bool(paper.is_representative)
        achievement_records.append(
            {
                'id': paper.id,
                'type': 'paper',
                'type_label': '论文成果',
                'title': paper.title,
                'date_acquired': paper.date_acquired.isoformat(),
                'detail': f'{paper.get_paper_type_display()} / {paper.journal_name}',
                'highlight': '代表作' if is_representative else f'引用 {paper.citation_count} 次',
                'is_representative': is_representative,
                'author_rank_category': 'lead' if paper.is_first_author else 'participating',
                'author_rank_label': '第一作者/通讯作者' if paper.is_first_author else '合作作者',
            }
        )

    for project in approved_queryset(Project.objects.filter(teacher=user)).order_by('-date_acquired', '-created_at'):
        achievement_records.append(
            {
                'id': project.id,
                'type': 'project',
                'type_label': '科研项目',
                'title': project.title,
                'date_acquired': project.date_acquired.isoformat(),
                'detail': f'{project.get_level_display()} / {project.get_role_display()}',
                'highlight': f'经费 {project.funding_amount} 万元',
                'is_representative': False,
                'author_rank_category': 'lead' if project.role == 'PI' else 'participating',
                'author_rank_label': project.get_role_display(),
            }
        )

    for item in approved_queryset(IntellectualProperty.objects.filter(teacher=user)).order_by('-date_acquired', '-created_at'):
        achievement_records.append(
            {
                'id': item.id,
                'type': 'intellectual_property',
                'type_label': '知识产权',
                'title': item.title,
                'date_acquired': item.date_acquired.isoformat(),
                'detail': f'{item.get_ip_type_display()} / {item.get_role_display()} / 登记号 {item.registration_number}',
                'highlight': '已转化' if item.is_transformed else '未转化',
                'is_representative': False,
                'author_rank_category': 'lead' if item.role == 'PI' else 'participating',
                'author_rank_label': item.get_role_display(),
            }
        )

    for item in approved_queryset(TeachingAchievement.objects.filter(teacher=user)).order_by('-date_acquired', '-created_at'):
        teaching_role_label = '指导教师' if item.achievement_type in {'COMPETITION', 'THESIS'} else item.get_role_display()
        achievement_records.append(
            {
                'id': item.id,
                'type': 'teaching_achievement',
                'type_label': '教学成果',
                'title': item.title,
                'date_acquired': item.date_acquired.isoformat(),
                'detail': f'{item.get_achievement_type_display()} / {teaching_role_label} / {item.level}',
                'highlight': '育人成果',
                'is_representative': False,
                'author_rank_category': 'lead' if item.role == 'PI' else 'participating',
                'author_rank_label': teaching_role_label,
            }
        )

    for item in approved_queryset(AcademicService.objects.filter(teacher=user)).order_by('-date_acquired', '-created_at'):
        achievement_records.append(
            {
                'id': item.id,
                'type': 'academic_service',
                'type_label': '学术服务',
                'title': item.title,
                'date_acquired': item.date_acquired.isoformat(),
                'detail': f'{item.get_service_type_display()} / {item.organization}',
                'highlight': '学术共同体贡献',
                'is_representative': False,
                'author_rank_category': 'unspecified',
                'author_rank_label': '未区分排名',
            }
        )

    return sorted(
        achievement_records,
        key=lambda item: (1 if item['is_representative'] else 0, item['date_acquired'], item['id']),
        reverse=True,
    )


def build_recent_achievements(user, limit: int = 6):
    return sorted(build_all_achievements(user), key=lambda item: (item['date_acquired'], item['id']), reverse=True)[:limit]


def classify_import_errors(errors: dict) -> dict:
    flattened = {key: ' '.join(str(item) for item in value) if isinstance(value, list) else str(value) for key, value in errors.items()}
    if 'doi' in flattened and '相同 DOI' in flattened['doi']:
        return {
            'reason_code': 'duplicate_existing_doi',
            'reason_label': '重复 DOI',
            'reason_category': 'duplicate_existing',
            'issue_summary': '当前账号下已存在相同 DOI 的论文，已跳过导入。',
        }
    if any(field in flattened for field in ('title', 'journal_name', 'date_acquired')):
        return {
            'reason_code': 'missing_required_fields',
            'reason_label': '缺少必填字段',
            'reason_category': 'missing_required',
            'issue_summary': '关键字段校验未通过，请补全题目、期刊/会议和时间后重试。',
        }
    return {
        'reason_code': 'validation_error',
        'reason_label': '字段校验失败',
        'reason_category': 'invalid_value',
        'issue_summary': '字段校验未通过，请根据错误提示修正后重试。',
    }


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
                'weight_spec': radar_result['weight_spec'],
                'calculation_summary': radar_result['calculation_summary'],
                'data_meta': get_portrait_data_meta(user),
            }
        )


class TeacherOwnedAchievementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields: tuple[str, ...] = ()
    operation_log_type: str = ''

    def create(self, request, *args, **kwargs):
        if is_admin_user(request.user):
            return api_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message='成果录入和维护仅限教师本人操作，管理员当前仅可查看与验证。',
                code='achievement_self_service_forbidden',
                request=request,
            )
        return super().create(request, *args, **kwargs)


    def update(self, request, *args, **kwargs):
        if is_admin_user(request.user):
            return api_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message='管理员不可通过教师自助入口编辑成果。',
                code='achievement_self_service_forbidden',
                request=request,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if is_admin_user(request.user):
            return api_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message='管理员不可通过教师自助入口编辑成果。',
                code='achievement_self_service_forbidden',
                request=request,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if is_admin_user(request.user):
            return api_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message='管理员不可通过教师自助入口删除成果。',
                code='achievement_self_service_forbidden',
                request=request,
            )
        return super().destroy(request, *args, **kwargs)
    def get_queryset(self):
        queryset = self.queryset
        teacher_id = self.request.query_params.get('teacher_id', '').strip()

        if not (self.request.user.is_staff or self.request.user.is_superuser):
            queryset = queryset.filter(teacher=self.request.user)
        elif teacher_id:
            user_model = get_user_model()
            target_teacher = user_model.objects.filter(id=teacher_id).first()
            if target_teacher is None or not can_access_teacher_scope(self.request.user, target_teacher):
                queryset = queryset.none()
            else:
                queryset = queryset.filter(teacher_id=teacher_id)
        else:
            queryset = queryset.filter(teacher__is_superuser=False, teacher__is_staff=False)
            if is_college_admin_user(self.request.user):
                queryset = queryset.filter(teacher__department=self.request.user.department)

        search = self.request.query_params.get('search', '').strip()
        if search and self.search_fields:
            q_object = Q()
            for field in self.search_fields:
                q_object |= Q(**{f'{field}__icontains': search})
            queryset = queryset.filter(q_object)

        return queryset

    def perform_create(self, serializer):
        instance = serializer.save(teacher=self.request.user, status='PENDING_REVIEW')
        self.log_operation(
            instance=instance,
            action='CREATE',
            source='manual',
            summary=f'新增{instance.title}',
            changed_fields=list(build_achievement_operation_snapshot(self.operation_log_type, instance)[0].keys()),
        )
        self.sync_graph_by_status(instance)

    def perform_update(self, serializer):
        before_snapshot, _ = build_achievement_operation_snapshot(self.operation_log_type, serializer.instance)
        ensure_self_user(self.request.user, serializer.instance.teacher, ACHIEVEMENT_SELF_SERVICE_ONLY_MESSAGE)
        instance = serializer.save()
        if instance.status != 'PENDING_REVIEW':
            instance.status = 'PENDING_REVIEW'
            instance.save(update_fields=['status'])
        after_snapshot, _ = build_achievement_operation_snapshot(self.operation_log_type, instance)
        self.log_operation(
            instance=instance,
            action='UPDATE',
            source='manual',
            summary=f'更新{instance.title}',
            changed_fields=diff_operation_snapshot(before_snapshot, after_snapshot),
            snapshot_payload=after_snapshot,
        )
        self.sync_graph_by_status(instance)

    def perform_destroy(self, instance):
        ensure_self_user(self.request.user, instance.teacher, ACHIEVEMENT_SELF_SERVICE_ONLY_MESSAGE)
        identifier = instance.id
        snapshot_payload, detail_snapshot = build_achievement_operation_snapshot(self.operation_log_type, instance)
        self.log_operation(
            action='DELETE',
            source='manual',
            summary=f'删除{instance.title}',
            title_snapshot=instance.title,
            detail_snapshot=detail_snapshot,
            snapshot_payload=snapshot_payload,
            achievement_id=instance.id,
        )
        instance.delete()
        self.delete_graph_snapshot(identifier)

    def log_operation(
        self,
        *,
        instance=None,
        action: str,
        source: str,
        summary: str,
        changed_fields: list[str] | None = None,
        title_snapshot: str = '',
        detail_snapshot: str = '',
        snapshot_payload: dict | None = None,
        achievement_id: int | None = None,
    ):
        if not self.operation_log_type:
            return None
        teacher_for_log = instance.teacher if instance is not None else self.request.user
        return log_achievement_operation(
            teacher=teacher_for_log,
            achievement_type=self.operation_log_type,
            instance=instance,
            action=action,
            source=source,
            summary=summary,
            changed_fields=changed_fields,
            title_snapshot=title_snapshot,
            detail_snapshot=detail_snapshot,
            snapshot_payload=snapshot_payload,
            achievement_id=achievement_id,
        )

    @action(detail=False, methods=['get'], url_path='operations')
    def operations(self, request):
        target_teacher_id = request.user.id
        scoped_teacher_id = request.query_params.get('teacher_id', '').strip()
        if request.user.is_staff or request.user.is_superuser:
            if scoped_teacher_id.isdigit():
                target_teacher_id = int(scoped_teacher_id)
        queryset = AchievementOperationLog.objects.filter(
            teacher_id=target_teacher_id,
            achievement_type=self.operation_log_type,
        )
        achievement_id = request.query_params.get('achievement_id', '').strip()
        if achievement_id.isdigit():
            queryset = queryset.filter(achievement_id=int(achievement_id))
        serializer = AchievementOperationLogSerializer(queryset[:30], many=True)
        return Response({'history': serializer.data})

    def teacher_payload(self, instance):
        return {
            'user_id': instance.teacher_id,
            'name': instance.teacher.real_name or instance.teacher.username,
        }

    def sync_graph(self, instance):
        return None

    def delete_graph_snapshot(self, identifier):
        return None
    def sync_graph_by_status(self, instance):
        if instance.status == APPROVED_STATUS:
            self.sync_graph(instance)
            return
        self.delete_graph_snapshot(instance.id)

    def _ensure_can_review(self, target_teacher):
        ensure_admin_user(self.request.user)
        if not can_access_teacher_scope(self.request.user, target_teacher):
            return api_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message='当前账号无权审核该教师成果。',
                code='achievement_review_forbidden',
                request=self.request,
                next_step='请确认审核账号权限或切换到目标教师所属管理范围。',
            )
        return None

    @action(detail=True, methods=['post'], url_path='submit-review')
    def submit_review(self, request, pk=None):
        instance = self.get_object()
        ensure_self_user(request.user, instance.teacher, ACHIEVEMENT_SELF_SERVICE_ONLY_MESSAGE)

        if instance.status != 'PENDING_REVIEW':
            instance.status = 'PENDING_REVIEW'
            instance.save(update_fields=['status'])
            self.log_operation(
                instance=instance,
                action='SUBMIT_REVIEW',
                source='manual',
                summary=f'提交审核：{instance.title}',
                changed_fields=['审批状态'],
            )
            self.sync_graph_by_status(instance)

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='pending-review')
    def pending_review(self, request):
        ensure_admin_user(request.user)
        queryset = self.queryset.filter(status__in=['PENDING_REVIEW', 'DRAFT'])
        if is_college_admin_user(request.user):
            queryset = queryset.filter(teacher__department=request.user.department)
        serializer = self.get_serializer(queryset.order_by('-date_acquired', '-created_at')[:100], many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        instance = self.queryset.filter(pk=pk).select_related('teacher').first()
        if instance is None:
            return api_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message='成果记录不存在。',
                code='achievement_not_found',
                request=request,
            )
        denied = self._ensure_can_review(instance.teacher)
        if denied is not None:
            return denied

        instance.status = APPROVED_STATUS
        instance.save(update_fields=['status'])
        self.log_operation(
            instance=instance,
            action='APPROVE',
            source='manual',
            summary=f'审核通过：{instance.title}',
            changed_fields=['审批状态'],
        )
        AchievementOperationLog.objects.filter(
            teacher_id=instance.teacher_id,
            achievement_type=self.operation_log_type,
            achievement_id=instance.id,
            action='APPROVE',
        ).order_by('-id').update(operator=request.user)
        self.sync_graph_by_status(instance)
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        instance = self.queryset.filter(pk=pk).select_related('teacher').first()
        if instance is None:
            return api_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message='成果记录不存在。',
                code='achievement_not_found',
                request=request,
            )
        denied = self._ensure_can_review(instance.teacher)
        if denied is not None:
            return denied

        serializer = AchievementRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('reason', '')

        instance.status = 'REJECTED'
        instance.save(update_fields=['status'])
        self.log_operation(
            instance=instance,
            action='REJECT',
            source='manual',
            summary=f'审核驳回：{instance.title}',
            changed_fields=['审批状态'],
            snapshot_payload={
                **build_achievement_operation_snapshot(self.operation_log_type, instance)[0],
                '审核意见': reason,
            },
        )
        AchievementOperationLog.objects.filter(
            teacher_id=instance.teacher_id,
            achievement_type=self.operation_log_type,
            achievement_id=instance.id,
            action='REJECT',
        ).order_by('-id').update(operator=request.user, review_comment=reason)
        self.sync_graph_by_status(instance)
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=['get'], url_path='workflow-logs')
    def workflow_logs(self, request, pk=None):
        instance = self.get_object()
        ensure_self_or_admin_user(request.user, instance.teacher, ACHIEVEMENT_SELF_SERVICE_ONLY_MESSAGE)
        queryset = AchievementOperationLog.objects.filter(
            teacher_id=instance.teacher_id,
            achievement_type=self.operation_log_type,
            achievement_id=instance.id,
        ).order_by('-created_at', '-id')[:50]
        serializer = AchievementOperationLogSerializer(queryset, many=True)
        return Response({'history': serializer.data})


class PaperViewSet(TeacherOwnedAchievementViewSet):
    operation_log_type = 'papers'
    queryset = (
        Paper.objects.select_related('teacher')
        .prefetch_related('coauthors', 'paperkeyword_set__keyword', 'operation_logs')
        .all()
        .order_by('-date_acquired', '-created_at')
    )
    serializer_class = PaperSerializer
    search_fields = ('title', 'journal_name', 'doi')

    def get_queryset(self):
        queryset = super().get_queryset().annotate(metadata_alert_count=metadata_alert_count_expression())

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

        has_metadata_alerts = parse_bool_query_param(self.request.query_params.get('has_metadata_alerts', ''))
        if has_metadata_alerts is True:
            queryset = queryset.filter(metadata_alert_count__gt=0)
        elif has_metadata_alerts is False:
            queryset = queryset.filter(metadata_alert_count=0)

        missing_field = self.request.query_params.get('missing_field', '').strip()
        if missing_field in {'doi', 'pages', 'source_url', 'journal_level'}:
            queryset = queryset.filter(**{missing_field: ''})

        citation_min = self.request.query_params.get('citation_min', '').strip()
        if citation_min.isdigit():
            queryset = queryset.filter(citation_count__gte=int(citation_min))

        citation_max = self.request.query_params.get('citation_max', '').strip()
        if citation_max.isdigit():
            queryset = queryset.filter(citation_count__lte=int(citation_max))

        ordering_map = {
            'date_desc': ('-date_acquired', '-created_at'),
            'date_asc': ('date_acquired', 'created_at'),
            'citation_desc': ('-citation_count', '-date_acquired', '-created_at'),
            'citation_asc': ('citation_count', '-date_acquired', '-created_at'),
            'title_asc': ('title', '-date_acquired', '-created_at'),
            'title_desc': ('-title', '-date_acquired', '-created_at'),
            'created_desc': ('-created_at',),
            'created_asc': ('created_at',),
            'representative_desc': ('-is_representative', '-citation_count', '-date_acquired', '-created_at'),
            'metadata_alerts_desc': ('-metadata_alert_count', '-date_acquired', '-created_at'),
        }
        sort_by = self.request.query_params.get('sort_by', '').strip()
        if sort_by in ordering_map:
            queryset = queryset.order_by(*ordering_map[sort_by])
        return queryset

    def perform_create(self, serializer):
        paper = serializer.save(teacher=self.request.user, status='PENDING_REVIEW')
        self._extract_keywords(paper)
        log_paper_operation(
            paper=paper,
            teacher=self.request.user,
            action='CREATE',
            source='manual',
            summary='新增论文记录',
            changed_fields=[
                'title',
                'abstract',
                'date_acquired',
                'paper_type',
                'journal_name',
                'journal_level',
                'published_volume',
                'published_issue',
                'pages',
                'source_url',
                'citation_count',
                'is_first_author',
                'is_representative',
                'doi',
                'coauthors',
            ],
            metadata_flags=build_metadata_flag_codes(paper),
        )
        self.log_operation(
            instance=paper,
            action='CREATE',
            source='manual',
            summary=f'新增{paper.title}',
            changed_fields=list(build_achievement_operation_snapshot(self.operation_log_type, paper)[0].keys()),
        )
        self.sync_graph_by_status(paper)

    def perform_update(self, serializer):
        ensure_self_user(self.request.user, serializer.instance.teacher, ACHIEVEMENT_SELF_SERVICE_ONLY_MESSAGE)
        before = snapshot_paper_fields(serializer.instance)
        generic_before_snapshot, _ = build_achievement_operation_snapshot(self.operation_log_type, serializer.instance)
        paper = serializer.save()
        self._extract_keywords(paper)
        if paper.status != 'PENDING_REVIEW':
            paper.status = 'PENDING_REVIEW'
            paper.save(update_fields=['status'])
        changed_fields = diff_paper_fields(before, paper)
        log_paper_operation(
            paper=paper,
            teacher=self.request.user,
            action='UPDATE',
            source='manual',
            summary='更新论文信息',
            changed_fields=changed_fields,
            metadata_flags=build_metadata_flag_codes(paper),
        )
        generic_after_snapshot, _ = build_achievement_operation_snapshot(self.operation_log_type, paper)
        self.log_operation(
            instance=paper,
            action='UPDATE',
            source='manual',
            summary=f'更新{paper.title}',
            changed_fields=diff_operation_snapshot(generic_before_snapshot, generic_after_snapshot),
            snapshot_payload=generic_after_snapshot,
        )
        self.sync_graph_by_status(paper)

    def perform_destroy(self, instance):
        ensure_self_user(self.request.user, instance.teacher, ACHIEVEMENT_SELF_SERVICE_ONLY_MESSAGE)
        identifier = instance.id
        log_paper_operation(
            paper=instance,
            teacher=self.request.user,
            action='DELETE',
            source='manual',
            summary='删除论文记录',
            changed_fields=[],
            metadata_flags=build_metadata_flag_codes(instance),
            title_snapshot=instance.title,
            doi_snapshot=instance.doi,
        )
        snapshot_payload, detail_snapshot = build_achievement_operation_snapshot(self.operation_log_type, instance)
        self.log_operation(
            action='DELETE',
            source='manual',
            summary=f'删除{instance.title}',
            title_snapshot=instance.title,
            detail_snapshot=detail_snapshot,
            snapshot_payload=snapshot_payload,
            achievement_id=instance.id,
        )
        instance.delete()
        self.delete_graph_snapshot(identifier)

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
                'pdf_import_note': 'PDF 元数据解析仍为预留能力，当前治理增强只覆盖 BibTeX 主链路。',
                'acceptance_scope': '当前已覆盖 BibTeX 预览、修订、确认导入与导入后治理。',
            }
        )

    @action(detail=False, methods=['post'], url_path='import/bibtex-revalidate')
    def bibtex_revalidate(self, request):
        serializer = BibtexRevalidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        preview_data = revalidate_bibtex_entries(serializer.validated_data['entries'], request.user)
        return Response(preview_data)

    @action(detail=False, methods=['post'], url_path='import/bibtex-confirm')
    def bibtex_confirm(self, request):
        serializer = BibtexConfirmImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        imported_records = []
        skipped_entries = []
        failed_entries = []
        classified_counts: dict[str, int] = {}

        for entry in serializer.validated_data['entries']:
            if entry.get('preview_status') == 'duplicate':
                payload = {
                    'source_index': entry.get('source_index'),
                    'title': entry.get('title', ''),
                    'doi': entry.get('doi', ''),
                    'reason_code': 'duplicate_preview',
                    'reason_label': '预览阶段判定重复',
                    'reason_category': 'duplicate_existing',
                    'issue_summary': '重复记录已跳过：该条目在预览阶段已判定为重复记录。',
                    'errors': {'preview_status': ['duplicate']},
                }
                skipped_entries.append(payload)
                classified_counts[payload['reason_code']] = classified_counts.get(payload['reason_code'], 0) + 1
                continue

            paper_payload = {
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

            paper_serializer = self.get_serializer(data=paper_payload, context={'request': request})
            if not paper_serializer.is_valid():
                classification = classify_import_errors(paper_serializer.errors)
                target_collection = skipped_entries if classification['reason_category'].startswith('duplicate') else failed_entries
                target_collection.append(
                    {
                        'source_index': entry.get('source_index'),
                        'title': entry.get('title', ''),
                        'doi': entry.get('doi', ''),
                        **classification,
                        'errors': paper_serializer.errors,
                    }
                )
                classified_counts[classification['reason_code']] = classified_counts.get(classification['reason_code'], 0) + 1
                continue

            try:
                with transaction.atomic():
                    paper = paper_serializer.save(teacher=request.user, status='PENDING_REVIEW')
                    self._extract_keywords(paper)
                    log_paper_operation(
                        paper=paper,
                        teacher=request.user,
                        action='IMPORT',
                        source='bibtex',
                        summary='通过 BibTeX 导入论文',
                        changed_fields=[
                            'title',
                            'abstract',
                            'date_acquired',
                            'paper_type',
                            'journal_name',
                            'journal_level',
                            'published_volume',
                            'published_issue',
                            'pages',
                            'source_url',
                            'citation_count',
                            'is_first_author',
                            'is_representative',
                            'doi',
                            'coauthors',
                        ],
                        metadata_flags=build_metadata_flag_codes(paper),
                    )
                    log_achievement_operation(
                        teacher=request.user,
                        achievement_type='papers',
                        instance=paper,
                        action='IMPORT',
                        source='bibtex',
                        summary=f'通过 BibTeX 导入{paper.title}',
                        changed_fields=list(build_achievement_operation_snapshot('papers', paper)[0].keys()),
                    )
                    self.sync_graph_by_status(paper)
            except Exception as exc:
                classification = {
                    'reason_code': 'storage_failure',
                    'reason_label': '写入失败',
                    'reason_category': 'storage_failure',
                    'issue_summary': '论文写入失败，请稍后重试或联系管理员检查日志。',
                }
                failed_entries.append(
                    {
                        'source_index': entry.get('source_index'),
                        'title': entry.get('title', ''),
                        'doi': entry.get('doi', ''),
                        **classification,
                        'errors': {'detail': [str(exc)]},
                    }
                )
                classified_counts[classification['reason_code']] = classified_counts.get(classification['reason_code'], 0) + 1
                continue

            imported_records.append({'id': paper.id, 'title': paper.title, 'doi': paper.doi})
            classified_counts['imported'] = classified_counts.get('imported', 0) + 1

        return Response(
            {
                'imported_count': len(imported_records),
                'skipped_count': len(skipped_entries),
                'failed_count': len(failed_entries),
                'classified_counts': classified_counts,
                'imported_records': imported_records,
                'skipped_entries': skipped_entries,
                'failed_entries': failed_entries,
            }
        )

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        return Response(build_governance_overview(self.get_queryset(), request.user)['summary'])

    @action(detail=False, methods=['get'], url_path='governance')
    def governance(self, request):
        return Response(build_governance_overview(self.get_queryset(), request.user))

    @action(detail=False, methods=['get'], url_path='export')
    def export(self, request):
        content = export_papers_as_csv(self.get_queryset())
        response = HttpResponse(content, content_type='text/csv; charset=utf-8')
        filename = f'papers-governance-{timezone.now().strftime("%Y%m%d-%H%M%S")}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['get'], url_path='compare')
    def compare(self, request):
        left_id = request.query_params.get('left_id', '').strip()
        right_id = request.query_params.get('right_id', '').strip()
        if not (left_id.isdigit() and right_id.isdigit()):
            return api_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message='请提供两个可比较的论文 ID。',
                code='paper_compare_invalid',
                request=request,
                next_step='请在成果治理面板中重新选择两篇论文后再发起对比。',
            )

        queryset = self.get_queryset()
        papers = {paper.id: paper for paper in queryset.filter(id__in=[int(left_id), int(right_id)])}
        if len(papers) != 2:
            return api_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message='待对比论文不存在或无访问权限。',
                code='paper_compare_not_found',
                request=request,
                next_step='请确认两篇论文都属于当前可访问范围。',
            )

        return Response(build_compare_payload(papers[int(left_id)], papers[int(right_id)]))

    @action(detail=False, methods=['post'], url_path='representative/batch-update')
    def batch_update_representative(self, request):
        serializer = PaperRepresentativeBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        queryset = self.get_queryset().filter(id__in=serializer.validated_data['paper_ids'])
        updated_ids = list(queryset.values_list('id', flat=True))
        if not updated_ids:
            return Response({'updated_count': 0, 'updated_ids': []})

        queryset.update(is_representative=serializer.validated_data['is_representative'])
        updated_papers = list(Paper.objects.filter(id__in=updated_ids))
        for paper in updated_papers:
            log_paper_operation(
                paper=paper,
                teacher=request.user,
                action='UPDATE',
                source='manual',
                summary='批量调整代表作标记',
                changed_fields=['is_representative'],
                metadata_flags=build_metadata_flag_codes(paper),
            )
            log_achievement_operation(
                teacher=request.user,
                achievement_type='papers',
                instance=paper,
                action='UPDATE',
                source='manual',
                summary=f'调整代表作标记：{paper.title}',
                changed_fields=['代表作'],
            )
        return Response(
            {
                'updated_count': len(updated_ids),
                'updated_ids': updated_ids,
                'is_representative': serializer.validated_data['is_representative'],
            }
        )

    @action(detail=False, methods=['post'], url_path='cleanup-apply')
    def cleanup_apply(self, request):
        serializer = PaperCleanupApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        queryset = list(self.get_queryset().filter(id__in=serializer.validated_data['paper_ids']))
        if serializer.validated_data['action'] != 'normalize_text_fields':
            return Response({'updated_count': 0, 'updated_ids': []})

        updated_papers = normalize_selected_papers(queryset)
        for paper in updated_papers:
            log_paper_operation(
                paper=paper,
                teacher=request.user,
                action='UPDATE',
                source='system',
                summary='执行批量文本标准化清洗',
                changed_fields=['doi', 'source_url', 'pages', 'journal_level', 'published_volume', 'published_issue'],
                metadata_flags=build_metadata_flag_codes(paper),
            )
            log_achievement_operation(
                teacher=request.user,
                achievement_type='papers',
                instance=paper,
                action='UPDATE',
                source='system',
                summary=f'执行文本标准化：{paper.title}',
                changed_fields=['DOI', '来源链接', '页码', '期刊等级', '卷号', '期号'],
            )
        return Response(
            {
                'updated_count': len(updated_papers),
                'updated_ids': [paper.id for paper in updated_papers],
                'action': serializer.validated_data['action'],
            }
        )

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        paper = self.get_object()
        serializer = PaperOperationLogSerializer(paper.operation_logs.all()[:20], many=True)
        return Response({'paper_id': paper.id, 'history': serializer.data})

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
    operation_log_type = 'projects'
    queryset = Project.objects.select_related('teacher').all().order_by('-date_acquired', '-created_at')
    serializer_class = ProjectSerializer
    search_fields = ('title', 'project_status', 'status')

    def sync_graph(self, instance):
        AcademicGraphSyncService.sync_project(
            project_id=instance.id,
            title=instance.title,
            teacher=self.teacher_payload(instance),
            level=instance.level,
            role=instance.role,
            status=instance.project_status,
        )

    def delete_graph_snapshot(self, identifier):
        AcademicGraphSyncService.delete_project(identifier)


class IntellectualPropertyViewSet(TeacherOwnedAchievementViewSet):
    operation_log_type = 'intellectual-properties'
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
    operation_log_type = 'teaching-achievements'
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
    operation_log_type = 'academic-services'
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
                'helper': f'总被引 {metrics["citation_total"]} 次',
            },
            {
                'title': '项目与知识产权',
                'value': metrics['project_count'] + metrics['ip_count'],
                'suffix': '项',
                'icon': 'Reading',
                'iconClass': 'icon-green',
                'trend': None,
                'helper': f'项目 {metrics["project_count"]} 项 / 知识产权 {metrics["ip_count"]} 项',
            },
            {
                'title': '教学与学术服务',
                'value': metrics['teaching_count'] + metrics['service_count'],
                'suffix': '项',
                'icon': 'User',
                'iconClass': 'icon-orange',
                'trend': None,
                'helper': f'教学成果 {metrics["teaching_count"]} 项 / 学术服务 {metrics["service_count"]} 项',
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
                'weight_spec': radar_result['weight_spec'],
                'calculation_summary': radar_result['calculation_summary'],
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
                'stage_comparison': build_stage_comparison(user),
                'snapshot_boundary': build_snapshot_boundary(user),
                'portrait_explanation': build_portrait_explanation(),
                'data_meta': get_portrait_data_meta(user),
            }
        )


class TeacherAllAchievementsView(APIView):
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

        records = build_all_achievements(user)
        return Response(
            {
                'teacher_id': user.id,
                'teacher_name': getattr(user, 'real_name', '') or user.username,
                'achievement_total': len(records),
                'records': records,
            }
        )


class TeacherPortraitReportView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id: int) -> Response | HttpResponse:
        user = get_requested_teacher(request, user_id=user_id)
        if user is None:
            return api_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message='教师账户不存在。',
                code='teacher_not_found',
                request=request,
                next_step='请确认教师账号是否存在，或返回教师列表后重新选择。',
            )

        export_format = request.query_params.get('export', '').strip().lower()
        if export_format == 'markdown':
            content = export_portrait_report_markdown(user)
            response = HttpResponse(content, content_type='text/markdown; charset=utf-8')
            filename = f'teacher-portrait-report-{user.id}-{timezone.now().strftime("%Y%m%d-%H%M%S")}.md'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response

        report_payload = build_portrait_report(user)
        report_payload['data_meta'] = get_portrait_data_meta(user)
        return Response(report_payload)


