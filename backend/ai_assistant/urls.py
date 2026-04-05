from django.urls import path

from .views import AssistantChatView, DifyAssistantChatView, PortraitAssistantView


urlpatterns = [
    path('portrait-qa/', PortraitAssistantView.as_view(), name='portrait_assistant'),
    path('chat/', AssistantChatView.as_view(), name='assistant_chat'),
    path('dify-chat/', DifyAssistantChatView.as_view(), name='dify_assistant_chat'),
]
