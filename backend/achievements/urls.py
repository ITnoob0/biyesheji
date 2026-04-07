from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .management_dashboard import AcademyOverviewDashboardView, AcademyOverviewExportView
from .views import (
    AcademicServiceViewSet,
    AchievementClaimAcceptView,
    AchievementClaimAuthorCandidateView,
    AchievementClaimPendingCountView,
    AchievementClaimPendingListView,
    AchievementClaimRejectView,
    CollegeUnclaimedClaimRemindView,
    CollegeUnclaimedClaimView,
    IntellectualPropertyViewSet,
    PaperViewSet,
    ProjectViewSet,
    TeacherAllAchievementsView,
    TeacherPortraitAnalysisView,
    TeacherDashboardStatsView,
    TeacherPortraitReportView,
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
    path('portrait/analysis/', TeacherPortraitAnalysisView.as_view(), name='teacher_portrait_analysis'),
    path('all-achievements/<int:user_id>/', TeacherAllAchievementsView.as_view(), name='teacher_all_achievements'),
    path('radar/<int:user_id>/', TeacherRadarView.as_view(), name='teacher_radar'),
    path('portrait-report/<int:user_id>/', TeacherPortraitReportView.as_view(), name='teacher_portrait_report'),
    path('academy-overview/', AcademyOverviewDashboardView.as_view(), name='academy_overview_dashboard'),
    path('academy-overview/export/', AcademyOverviewExportView.as_view(), name='academy_overview_export'),
    path('claims/pending-count/', AchievementClaimPendingCountView.as_view(), name='achievement_claim_pending_count'),
    path('claims/pending/', AchievementClaimPendingListView.as_view(), name='achievement_claim_pending_list'),
    path('claims/author-candidates/', AchievementClaimAuthorCandidateView.as_view(), name='achievement_claim_author_candidates'),
    path('claims/<int:claim_id>/accept/', AchievementClaimAcceptView.as_view(), name='achievement_claim_accept'),
    path('claims/<int:claim_id>/reject/', AchievementClaimRejectView.as_view(), name='achievement_claim_reject'),
    path('claims/college-unclaimed/', CollegeUnclaimedClaimView.as_view(), name='college_unclaimed_claims'),
    path('claims/college-unclaimed/remind/', CollegeUnclaimedClaimRemindView.as_view(), name='college_unclaimed_claims_remind'),
]
