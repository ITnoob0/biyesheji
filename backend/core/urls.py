from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from achievements.views import (
    AchievementClaimAcceptView,
    AchievementClaimPendingCountView,
    AchievementClaimPendingListView,
    AchievementClaimRejectView,
)
from users.auth_views import EmployeeTokenObtainPairView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/token/", EmployeeTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/users/", include("users.urls")),
    path("api/achievements/", include("achievements.urls")),
    path("api/project-guides/", include("project_guides.urls")),
    path("api/graph/", include("graph_engine.urls")),
    path("api/ai-assistant/", include("ai_assistant.urls")),
    path("api/claims/pending-count/", AchievementClaimPendingCountView.as_view(), name="claim_pending_count_alias"),
    path("api/claims/pending/", AchievementClaimPendingListView.as_view(), name="claim_pending_list_alias"),
    path("api/claims/<int:claim_id>/accept/", AchievementClaimAcceptView.as_view(), name="claim_accept_alias"),
    path("api/claims/<int:claim_id>/reject/", AchievementClaimRejectView.as_view(), name="claim_reject_alias"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
