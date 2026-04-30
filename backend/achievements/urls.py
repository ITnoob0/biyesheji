from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .management_dashboard import AcademyOverviewDashboardView, AcademyOverviewExportView
from .views import (
    AcademicServiceViewSet,
    IntellectualPropertyViewSet,
    PaperViewSet,
    ProjectViewSet,
    TeacherAllAchievementsView,
    TeacherPortraitAnalysisView,
    TeacherDashboardStatsView,
    TeacherPortraitReportView,
    TeacherRadarView,
)
from .rule_views import RuleBasedAchievementViewSet

router = DefaultRouter()
router.register(r'papers', PaperViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'intellectual-properties', IntellectualPropertyViewSet)
router.register(r'academic-services', AcademicServiceViewSet)
router.register(r'rule-achievements', RuleBasedAchievementViewSet, basename='rule-achievement')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard-stats/', TeacherDashboardStatsView.as_view(), name='dashboard_stats'),
    path('portrait/analysis/', TeacherPortraitAnalysisView.as_view(), name='teacher_portrait_analysis'),
    path('all-achievements/<int:user_id>/', TeacherAllAchievementsView.as_view(), name='teacher_all_achievements'),
    path('radar/<int:user_id>/', TeacherRadarView.as_view(), name='teacher_radar'),
    path('portrait-report/<int:user_id>/', TeacherPortraitReportView.as_view(), name='teacher_portrait_report'),
    path('academy-overview/', AcademyOverviewDashboardView.as_view(), name='academy_overview_dashboard'),
    path('academy-overview/export/', AcademyOverviewExportView.as_view(), name='academy_overview_export'),
]
