from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ProjectGuideRecommendationView, ProjectGuideViewSet


router = DefaultRouter()
router.register(r'', ProjectGuideViewSet, basename='project-guide')

urlpatterns = [
    path('recommendations/', ProjectGuideRecommendationView.as_view(), name='project-guide-recommendations'),
    path('', include(router.urls)),
]
