from django.contrib import admin
from django.urls import path, include  # 确保这里有 include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # JWT 登录鉴权接口
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # 业务模块 API 路由
    path('api/achievements/', include('achievements.urls')), # <--- 加上这一行
    path('api/graph/', include('graph_engine.urls')), # 新增图谱API路由
]