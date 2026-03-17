from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .management_dashboard import AcademyOverviewDashboardView
from .views import (
    AcademicServiceViewSet,
    IntellectualPropertyViewSet,
    PaperViewSet,
    ProjectViewSet,
    TeacherDashboardStatsView,
    TeacherRadarView,
    TeachingAchievementViewSet,
)

router = DefaultRouter()
router.register(r'papers', PaperViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'intellectual-properties', IntellectualPropertyViewSet)
router.register(r'teaching-achievements', TeachingAchievementViewSet)
router.register(r'academic-services', AcademicServiceViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard-stats/', TeacherDashboardStatsView.as_view(), name='dashboard_stats'),
    path('radar/<int:user_id>/', TeacherRadarView.as_view(), name='teacher_radar'),
    path('academy-overview/', AcademyOverviewDashboardView.as_view(), name='academy_overview_dashboard'),
]
