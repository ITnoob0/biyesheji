from django.urls import path

from .views import PortraitAssistantView


urlpatterns = [
    path('portrait-qa/', PortraitAssistantView.as_view(), name='portrait_assistant'),
]
