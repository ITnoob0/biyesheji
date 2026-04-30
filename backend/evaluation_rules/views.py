from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.access import ensure_system_admin_user, is_system_admin_user

from .models import EvaluationRuleCategory, EvaluationRuleItem, EvaluationRuleVersion, FilingWorkflowStep
from .serializers import (
    EvaluationRuleCategorySerializer,
    EvaluationRuleItemSerializer,
    EvaluationRuleVersionSerializer,
    FilingWorkflowStepSerializer,
)


def _resolve_active_version() -> EvaluationRuleVersion | None:
    version = EvaluationRuleVersion.objects.filter(status=EvaluationRuleVersion.STATUS_ACTIVE).order_by('-updated_at', '-id').first()
    if version:
        return version
    return EvaluationRuleVersion.objects.order_by('-updated_at', '-id').first()


class SystemAdminWriteGuardMixin:
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        ensure_system_admin_user(request.user)
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        ensure_system_admin_user(request.user)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        ensure_system_admin_user(request.user)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        ensure_system_admin_user(request.user)
        return super().destroy(request, *args, **kwargs)


class EvaluationRuleVersionViewSet(SystemAdminWriteGuardMixin, viewsets.ModelViewSet):
    serializer_class = EvaluationRuleVersionSerializer
    queryset = EvaluationRuleVersion.objects.all()

    def get_queryset(self):
        queryset = self.queryset.order_by('-updated_at', '-id')
        if is_system_admin_user(self.request.user):
            status_filter = (self.request.query_params.get('status') or '').strip()
            if status_filter in {item[0] for item in EvaluationRuleVersion.STATUS_CHOICES}:
                queryset = queryset.filter(status=status_filter)
            return queryset
        return queryset.filter(status=EvaluationRuleVersion.STATUS_ACTIVE)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class EvaluationRuleCategoryViewSet(SystemAdminWriteGuardMixin, viewsets.ModelViewSet):
    serializer_class = EvaluationRuleCategorySerializer
    queryset = EvaluationRuleCategory.objects.select_related('version').all()

    def get_queryset(self):
        queryset = self.queryset.order_by('sort_order', 'id')
        version_id = (self.request.query_params.get('version') or '').strip()
        active_only = (self.request.query_params.get('active_only') or '').strip().lower() in {'1', 'true', 'yes'}

        if not is_system_admin_user(self.request.user) or active_only:
            queryset = queryset.filter(version__status=EvaluationRuleVersion.STATUS_ACTIVE, is_active=True)

        if version_id:
            queryset = queryset.filter(version_id=version_id)
        return queryset


class EvaluationRuleItemViewSet(SystemAdminWriteGuardMixin, viewsets.ModelViewSet):
    serializer_class = EvaluationRuleItemSerializer
    queryset = EvaluationRuleItem.objects.select_related('version', 'category_ref').all()

    def get_queryset(self):
        queryset = self.queryset.order_by('sort_order', 'id')
        version_id = (self.request.query_params.get('version') or '').strip()
        category_id = (self.request.query_params.get('category_id') or '').strip()
        discipline = (self.request.query_params.get('discipline') or '').strip()
        entry_policy = (self.request.query_params.get('entry_policy') or '').strip()
        search = (self.request.query_params.get('search') or '').strip()
        active_only = (self.request.query_params.get('active_only') or '').strip().lower() in {'1', 'true', 'yes'}

        if not is_system_admin_user(self.request.user) or active_only:
            queryset = queryset.filter(version__status=EvaluationRuleVersion.STATUS_ACTIVE, is_active=True)

        if version_id:
            queryset = queryset.filter(version_id=version_id)
        if category_id:
            queryset = queryset.filter(category_ref_id=category_id)
        if discipline in {item[0] for item in EvaluationRuleItem.DISCIPLINE_CHOICES}:
            queryset = queryset.filter(discipline=discipline)
        if entry_policy in {item[0] for item in EvaluationRuleItem.ENTRY_POLICY_CHOICES}:
            queryset = queryset.filter(entry_policy=entry_policy)
        if search:
            queryset = queryset.filter(title__icontains=search)
        return queryset


class FilingWorkflowStepViewSet(SystemAdminWriteGuardMixin, viewsets.ModelViewSet):
    serializer_class = FilingWorkflowStepSerializer
    queryset = FilingWorkflowStep.objects.select_related('version').all()

    def get_queryset(self):
        queryset = self.queryset.order_by('step_order', 'id')
        version_id = (self.request.query_params.get('version') or '').strip()
        if not is_system_admin_user(self.request.user):
            queryset = queryset.filter(version__status=EvaluationRuleVersion.STATUS_ACTIVE, is_active=True)
        if version_id:
            queryset = queryset.filter(version_id=version_id)
        return queryset


class EvaluationRuleDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        version = _resolve_active_version()
        if version is None:
            raise ValidationError({'detail': '当前尚未配置评价规则版本。'})

        category_queryset = EvaluationRuleCategory.objects.filter(version=version).order_by('sort_order', 'id')
        item_queryset = EvaluationRuleItem.objects.filter(version=version).select_related('category_ref').order_by('sort_order', 'id')
        workflow_queryset = FilingWorkflowStep.objects.filter(version=version).order_by('step_order', 'id')
        available_versions = EvaluationRuleVersion.objects.order_by('-updated_at', '-id')

        if not is_system_admin_user(request.user):
            category_queryset = category_queryset.filter(is_active=True)
            item_queryset = item_queryset.filter(is_active=True)
            workflow_queryset = workflow_queryset.filter(is_active=True)
            available_versions = available_versions.filter(status=EvaluationRuleVersion.STATUS_ACTIVE)

        grouped_rules = []
        for category in category_queryset:
            category_items = item_queryset.filter(category_ref=category)
            if not category_items.exists():
                continue
            grouped_rules.append(
                {
                    'id': category.id,
                    'key': category.code,
                    'label': category.name,
                    'dimension_key': category.dimension_key,
                    'dimension_label': category.dimension_label,
                    'entry_enabled': category.entry_enabled,
                    'include_in_total': category.include_in_total,
                    'include_in_radar': category.include_in_radar,
                    'items': EvaluationRuleItemSerializer(category_items, many=True).data,
                }
            )

        return Response(
            {
                'active_version': EvaluationRuleVersionSerializer(version).data,
                'available_versions': EvaluationRuleVersionSerializer(available_versions, many=True).data,
                'summary': {
                    'rule_count': item_queryset.count(),
                    'included_count': item_queryset.filter(entry_policy=EvaluationRuleItem.ENTRY_REQUIRED).count(),
                    'category_count': category_queryset.count(),
                    'workflow_step_count': workflow_queryset.count(),
                },
                'categories': EvaluationRuleCategorySerializer(category_queryset, many=True).data,
                'grouped_rules': grouped_rules,
                'workflow_steps': FilingWorkflowStepSerializer(workflow_queryset, many=True).data,
                'permissions': {
                    'can_edit': is_system_admin_user(request.user),
                    'read_mode': 'editable' if is_system_admin_user(request.user) else 'readonly',
                },
            }
        )
