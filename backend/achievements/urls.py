from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaperViewSet

# 使用 DRF 的路由器自动生成标准的 RESTful 网址
router = DefaultRouter()
router.register(r'papers', PaperViewSet)

urlpatterns = [
    path('', include(router.urls)),
]