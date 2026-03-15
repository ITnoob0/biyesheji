from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaperViewSet, TeacherDashboardStatsView, TeacherRadarView

router = DefaultRouter()
router.register(r'papers', PaperViewSet)

urlpatterns = [
    path('', include(router.urls)),
    # 新增的打分概览数据接口
    path('dashboard-stats/', TeacherDashboardStatsView.as_view(), name='dashboard_stats'),
    path('radar/<int:user_id>/', TeacherRadarView.as_view(), name='teacher_radar'),
]