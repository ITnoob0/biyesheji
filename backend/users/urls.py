from django.urls import path

from .views import (
    CurrentUserView,
    ForgotPasswordResetView,
    TeacherDetailView,
    TeacherListCreateView,
    TeacherRegistrationView,
    TeacherResetPasswordView,
)


urlpatterns = [
    path('me/', CurrentUserView.as_view(), name='current_user'),
    path('register/', TeacherRegistrationView.as_view(), name='teacher_register'),
    path('forgot-password/', ForgotPasswordResetView.as_view(), name='forgot_password_reset'),
    path('teachers/', TeacherListCreateView.as_view(), name='teacher_list_create'),
    path('teachers/<int:user_id>/', TeacherDetailView.as_view(), name='teacher_detail'),
    path('teachers/<int:user_id>/reset-password/', TeacherResetPasswordView.as_view(), name='teacher_reset_password'),
]
