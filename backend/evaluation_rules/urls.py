from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    EvaluationRuleCategoryViewSet,
    EvaluationRuleDashboardView,
    EvaluationRuleItemViewSet,
    EvaluationRuleVersionViewSet,
    FilingWorkflowStepViewSet,
)


router = DefaultRouter()
router.register(r'versions', EvaluationRuleVersionViewSet, basename='evaluation-rule-version')
router.register(r'categories', EvaluationRuleCategoryViewSet, basename='evaluation-rule-category')
router.register(r'items', EvaluationRuleItemViewSet, basename='evaluation-rule-item')
router.register(r'workflow-steps', FilingWorkflowStepViewSet, basename='filing-workflow-step')

urlpatterns = [
    path('dashboard/', EvaluationRuleDashboardView.as_view(), name='evaluation-rule-dashboard'),
    path('', include(router.urls)),
]
