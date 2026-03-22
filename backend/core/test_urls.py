from django.http import HttpResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from users.auth_views import EmployeeTokenObtainPairView


def crashing_api_view(request):
    raise RuntimeError("simulated api failure")


def ok_view(request):
    return HttpResponse("ok")


urlpatterns = [
    path("healthz/", ok_view),
    path("api/test-error/", crashing_api_view),
    path("api/token/", EmployeeTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/users/", include("users.urls")),
    path("api/achievements/", include("achievements.urls")),
    path("api/project-guides/", include("project_guides.urls")),
    path("api/graph/", include("graph_engine.urls")),
    path("api/ai-assistant/", include("ai_assistant.urls")),
]
