from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.api_errors import api_error_response
from evaluation_rules.models import EvaluationRuleCategory, EvaluationRuleItem, EvaluationRuleVersion
from users.access import (
    PROFILE_SCOPE_MESSAGE,
    can_access_teacher_scope,
    ensure_admin_user,
    ensure_self_or_admin_user,
    ensure_self_user,
    is_admin_user,
    is_college_admin_user,
)

from .models import AchievementOperationLog, RuleBasedAchievement
from .portrait_analysis import invalidate_benchmark_score_cache
from .rule_entry_schema import build_rule_entry_form_schema
from .rule_scoring import apply_rule_snapshots, build_score_preview, resolve_rule_item_scoring, validate_team_rule_constraints
from .serializers import AchievementRejectSerializer, RuleBasedAchievementSerializer


def _resolve_active_version() -> EvaluationRuleVersion | None:
    version = EvaluationRuleVersion.objects.filter(status=EvaluationRuleVersion.STATUS_ACTIVE).order_by('-updated_at', '-id').first()
    if version:
        return version
    return EvaluationRuleVersion.objects.order_by('-updated_at', '-id').first()


def _is_frozen_rule_version_record(instance: RuleBasedAchievement) -> bool:
    active_version = _resolve_active_version()
    return (
        instance.status == 'APPROVED'
        and active_version is not None
        and instance.version_id != active_version.id
    )


def _rule_version_frozen_response(request):
    return api_error_response(
        status_code=status.HTTP_409_CONFLICT,
        message='该成果属于历史规则版本且已审核通过，积分已冻结，不允许继续编辑或删除。',
        code='rule_achievement_version_frozen',
        request=request,
        next_step='如需修正，请按当前启用规则重新申报新成果，旧版本积分保留为历史认可结果。',
    )


def _parse_preview_boolean(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {'1', 'true', 'yes', 'on'}


def _parse_preview_payload(raw_payload) -> dict:
    if raw_payload is None or raw_payload == '' or raw_payload == []:
        return {}
    if isinstance(raw_payload, dict):
        return raw_payload
    if isinstance(raw_payload, str):
        try:
            parsed = json.loads(raw_payload)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _parse_preview_name_list(raw_value) -> list[str]:
    if raw_value is None or raw_value == '' or raw_value == []:
        return []
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    if isinstance(raw_value, str):
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
        return [item.strip() for item in raw_value.replace('\n', '，').split('，') if item.strip()]
    return []


def _build_preview_instance(rule_item: EvaluationRuleItem, request_data) -> RuleBasedAchievement:
    return RuleBasedAchievement(
        version=rule_item.version,
        category=rule_item.category_ref,
        rule_item=rule_item,
        title=str(request_data.get('title') or '').strip(),
        external_reference=str(request_data.get('external_reference') or '').strip(),
        date_acquired=request_data.get('date_acquired') or None,
        issuing_organization=str(request_data.get('issuing_organization') or '').strip(),
        publication_name=str(request_data.get('publication_name') or '').strip(),
        role_text=str(request_data.get('role_text') or '').strip(),
        author_rank=request_data.get('author_rank') or None,
        is_corresponding_author=_parse_preview_boolean(request_data.get('is_corresponding_author')),
        is_representative=_parse_preview_boolean(request_data.get('is_representative')),
        school_unit_order=str(request_data.get('school_unit_order') or '').strip(),
        amount_value=request_data.get('amount_value') or None,
        keywords_text=str(request_data.get('keywords_text') or '').strip(),
        coauthor_names=_parse_preview_name_list(request_data.get('coauthor_names')),
        team_identifier=str(request_data.get('team_identifier') or '').strip(),
        team_total_members=request_data.get('team_total_members') or None,
        team_allocated_score=request_data.get('team_allocated_score') or None,
        team_contribution_note=str(request_data.get('team_contribution_note') or '').strip(),
        evidence_note=str(request_data.get('evidence_note') or '').strip(),
        factual_payload=_parse_preview_payload(request_data.get('factual_payload')),
    )


def _parse_final_score(raw_value) -> Decimal:
    if raw_value in (None, ''):
        raise ValueError('审核通过前必须填写最终分数。')
    try:
        parsed = Decimal(str(raw_value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError('最终分数必须是合法数字。')
    if parsed < 0:
        raise ValueError('最终分数不能为负数。')
    return parsed.quantize(Decimal('0.01'))


def _build_rule_achievement_snapshot(instance: RuleBasedAchievement) -> tuple[dict, str]:
    payload = {
        '成果名称': instance.title,
        '规则分类': instance.category_name_snapshot or instance.category.name,
        '规则条目': instance.rule_title_snapshot or instance.rule_item.title,
        '规则编码': instance.rule_code_snapshot or instance.rule_item.rule_code,
        '成果时间': instance.date_acquired.isoformat() if instance.date_acquired else '',
        '预估积分': str(instance.provisional_score),
        '生效积分': str(instance.final_score),
        '团队标识': instance.team_identifier,
    }
    detail = f"{instance.category_name_snapshot or instance.category.name} / {instance.rule_title_snapshot or instance.rule_item.title}"
    return payload, detail


def _log_rule_achievement_operation(
    *,
    instance: RuleBasedAchievement,
    action: str,
    source: str,
    summary: str,
    changed_fields: list[str] | None = None,
    operator=None,
    review_comment: str = '',
):
    payload, detail = _build_rule_achievement_snapshot(instance)
    return AchievementOperationLog.objects.create(
        teacher=instance.teacher,
        operator=operator,
        achievement_type='rule-achievements',
        achievement_id=instance.id,
        action=action,
        source=source,
        summary=summary,
        changed_fields=changed_fields or [],
        title_snapshot=instance.title,
        detail_snapshot=detail,
        snapshot_payload=payload,
        review_comment=review_comment,
    )


class RuleBasedAchievementViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = RuleBasedAchievementSerializer
    queryset = RuleBasedAchievement.objects.select_related('teacher', 'version', 'category', 'rule_item').prefetch_related('attachments').all()

    def get_queryset(self):
        queryset = self.queryset.order_by('-date_acquired', '-created_at')
        teacher_id = (self.request.query_params.get('teacher_id') or '').strip()
        status_filter = (self.request.query_params.get('status') or '').strip()
        rule_version_id = (self.request.query_params.get('rule_version') or '').strip()

        if not is_admin_user(self.request.user):
            queryset = queryset.filter(teacher=self.request.user)
        elif teacher_id:
            user_model = get_user_model()
            target_teacher = user_model.objects.filter(id=teacher_id).first()
            if target_teacher is None or not can_access_teacher_scope(self.request.user, target_teacher):
                queryset = queryset.none()
            else:
                queryset = queryset.filter(teacher_id=teacher_id)
        else:
            queryset = queryset.filter(teacher__is_staff=False, teacher__is_superuser=False)
            if is_college_admin_user(self.request.user):
                queryset = queryset.filter(teacher__department=self.request.user.department)

        if status_filter in {'DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED'}:
            queryset = queryset.filter(status=status_filter)
        if rule_version_id and rule_version_id.lower() not in {'all', 'current'}:
            try:
                queryset = queryset.filter(version_id=int(rule_version_id))
            except (TypeError, ValueError):
                queryset = queryset.none()
        return queryset

    def create(self, request, *args, **kwargs):
        if is_admin_user(request.user):
            return api_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message='成果录入仅限教师本人操作。',
                code='rule_achievement_self_service_only',
                request=request,
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if is_admin_user(request.user):
            return api_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message='管理员不可通过教师自助入口编辑成果。',
                code='rule_achievement_self_service_only',
                request=request,
            )
        instance = self.get_object()
        if _is_frozen_rule_version_record(instance):
            return _rule_version_frozen_response(request)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if is_admin_user(request.user):
            return api_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message='管理员不可以通过教师自助入口编辑成果。',
                code='rule_achievement_self_service_only',
                request=request,
            )
        instance = self.get_object()
        if _is_frozen_rule_version_record(instance):
            return _rule_version_frozen_response(request)
        kwargs['partial'] = True
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        ensure_self_user(request.user, instance.teacher, '成果录入和维护仅限教师本人操作。')
        if _is_frozen_rule_version_record(instance):
            return _rule_version_frozen_response(request)
        _log_rule_achievement_operation(
            instance=instance,
            action='DELETE',
            source='manual',
            summary=f'删除规则化成果：{instance.title}',
        )
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        instance = serializer.save()
        _log_rule_achievement_operation(
            instance=instance,
            action='CREATE',
            source='manual',
            summary=f'新增规则化成果：{instance.title}',
            changed_fields=['规则分类', '规则条目', '预估积分'],
        )
        _log_rule_achievement_operation(
            instance=instance,
            action='SUBMIT_REVIEW',
            source='manual',
            summary=f'提交审核：{instance.title}',
            changed_fields=['审核状态'],
        )

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        instance = serializer.save()
        _log_rule_achievement_operation(
            instance=instance,
            action='UPDATE',
            source='manual',
            summary=f'更新规则化成果：{instance.title}',
            changed_fields=['规则分类', '规则条目', '预估积分'],
        )
        if instance.status == 'PENDING_REVIEW' and previous_status != 'PENDING_REVIEW':
            _log_rule_achievement_operation(
                instance=instance,
                action='SUBMIT_REVIEW',
                source='manual',
                summary=f'重新提交审核：{instance.title}',
                changed_fields=['审核状态'],
            )

    @action(detail=False, methods=['get'], url_path='entry-config')
    def entry_config(self, request):
        version = _resolve_active_version()
        if version is None:
            return Response({'detail': '当前尚未配置可用规则版本。'}, status=status.HTTP_404_NOT_FOUND)

        categories = EvaluationRuleCategory.objects.filter(
            version=version,
            is_active=True,
            entry_enabled=True,
        ).order_by('sort_order', 'id')
        items = (
            EvaluationRuleItem.objects.filter(
                version=version,
                is_active=True,
                entry_policy=EvaluationRuleItem.ENTRY_REQUIRED,
                category_ref__in=categories,
            )
            .select_related('category_ref')
            .order_by('sort_order', 'id')
        )
        return Response(
            {
                'active_version': {
                    'id': version.id,
                    'code': version.code,
                    'name': version.name,
                },
                'categories': [
                    {
                        'id': category.id,
                        'code': category.code,
                        'name': category.name,
                        'description': category.description,
                        'dimension_key': category.dimension_key,
                        'dimension_label': category.dimension_label,
                        'include_in_total': category.include_in_total,
                        'include_in_radar': category.include_in_radar,
                    }
                    for category in categories
                ],
                'items': [
                    {
                        'id': item.id,
                        'category_id': item.category_ref_id,
                        'rule_code': item.rule_code,
                        'title': item.title,
                        'score_text': item.score_text,
                        'score_mode': resolve_rule_item_scoring(item)['score_mode'],
                        'base_score': str(resolve_rule_item_scoring(item)['base_score'] or ''),
                        'score_per_unit': str(resolve_rule_item_scoring(item)['score_per_unit'] or ''),
                        'score_unit_label': resolve_rule_item_scoring(item)['score_unit_label'],
                        'requires_amount_input': resolve_rule_item_scoring(item)['requires_amount_input'],
                        'is_team_rule': item.is_team_rule,
                        'team_distribution_note': item.team_distribution_note,
                        'team_max_member_ratio': str(item.team_max_member_ratio),
                        'description': item.description,
                        'note': item.note,
                        'evidence_requirements': item.evidence_requirements,
                        'include_in_total': item.include_in_total,
                        'include_in_radar': item.include_in_radar,
                        'entry_form_schema': item.entry_form_schema,
                        'resolved_entry_form_schema': build_rule_entry_form_schema(item),
                    }
                    for item in items
                ],
            }
        )

    @action(detail=False, methods=['post'], url_path='preview-score')
    def preview_score(self, request):
        rule_item_id = request.data.get('rule_item')
        if not rule_item_id:
            return Response({'detail': '请选择加分项。'}, status=status.HTTP_400_BAD_REQUEST)
        rule_item = EvaluationRuleItem.objects.select_related('category_ref').filter(id=rule_item_id, is_active=True).first()
        if rule_item is None:
            return Response({'detail': '规则条目不存在。'}, status=status.HTTP_404_NOT_FOUND)

        preview_instance = _build_preview_instance(rule_item, request.data)
        preview = build_score_preview(
            rule_item=rule_item,
            amount_value=preview_instance.amount_value,
            team_allocated_score=preview_instance.team_allocated_score,
            instance=preview_instance,
        )
        return Response(preview)

    @action(detail=False, methods=['get'], url_path='pending-review')
    def pending_review(self, request):
        ensure_admin_user(request.user)
        queryset = self.get_queryset().filter(status='PENDING_REVIEW')
        serializer = self.get_serializer(queryset[:100], many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='approve')
    def approve(self, request, pk=None):
        instance = self.get_object()
        ensure_admin_user(request.user)
        if not can_access_teacher_scope(request.user, instance.teacher):
            return api_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message='当前账号无权审核该教师成果。',
                code='rule_achievement_review_forbidden',
                request=request,
                next_step=PROFILE_SCOPE_MESSAGE,
            )

        errors = validate_team_rule_constraints(instance, approval_phase=True)
        if errors:
            return Response({'detail': errors[0], 'errors': errors}, status=status.HTTP_400_BAD_REQUEST)

        apply_rule_snapshots(instance)
        try:
            final_score = _parse_final_score(request.data.get('final_score'))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        instance.status = 'APPROVED'
        instance.final_score = final_score
        instance.review_comment = ''
        instance.reviewed_by = request.user
        instance.reviewed_at = timezone.now()
        instance.save()
        invalidate_benchmark_score_cache()
        _log_rule_achievement_operation(
            instance=instance,
            action='APPROVE',
            source='manual',
            summary=f'审核通过：{instance.title}',
            changed_fields=['审核状态', '生效积分'],
            operator=request.user,
        )
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=['post'], url_path='reject')
    def reject(self, request, pk=None):
        instance = self.get_object()
        ensure_admin_user(request.user)
        if not can_access_teacher_scope(request.user, instance.teacher):
            return api_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message='当前账号无权审核该教师成果。',
                code='rule_achievement_review_forbidden',
                request=request,
                next_step=PROFILE_SCOPE_MESSAGE,
            )

        serializer = AchievementRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('reason', '').strip()

        instance.status = 'REJECTED'
        instance.review_comment = reason
        instance.reviewed_by = request.user
        instance.reviewed_at = timezone.now()
        instance.final_score = 0
        instance.save(update_fields=['status', 'review_comment', 'reviewed_by', 'reviewed_at', 'final_score', 'updated_at'])
        _log_rule_achievement_operation(
            instance=instance,
            action='REJECT',
            source='manual',
            summary=f'审核驳回：{instance.title}',
            changed_fields=['审核状态'],
            operator=request.user,
            review_comment=reason,
        )
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=['get'], url_path='workflow-logs')
    def workflow_logs(self, request, pk=None):
        instance = self.get_object()
        ensure_self_or_admin_user(request.user, instance.teacher, '仅可查看本人或管理范围内教师的成果记录。')
        queryset = AchievementOperationLog.objects.filter(
            teacher_id=instance.teacher_id,
            achievement_type='rule-achievements',
            achievement_id=instance.id,
        ).order_by('-created_at', '-id')[:50]
        records = [
            {
                'id': item.id,
                'action': item.action,
                'action_label': item.get_action_display(),
                'source': item.source,
                'source_label': item.get_source_display(),
                'summary': item.summary,
                'changed_fields': item.changed_fields,
                'snapshot_payload': item.snapshot_payload,
                'review_comment': item.review_comment,
                'created_at': item.created_at,
                'operator_name': (item.operator.real_name or item.operator.username) if item.operator_id else '',
            }
            for item in queryset
        ]
        return Response({'history': records})
