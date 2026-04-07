from django.urls import path

from .views import (
    CurrentUserAvatarUploadView,
    UserNotificationListView,
    UserNotificationMarkAllReadView,
    UserNotificationMarkReadView,
    UserNotificationUnreadCountView,
    TeacherBulkActionView,
    TeacherBulkImportView,
    TeacherBulkImportTemplateView,
    CurrentUserPasswordChangeView,
    CurrentUserView,
    ForgotPasswordResetView,
    TeacherDetailView,
    TeacherListCreateView,
    TeacherManagementSummaryView,
    TeacherRegistrationView,
    TeacherResetPasswordView,
)


urlpatterns = [
    path("me/", CurrentUserView.as_view(), name="current_user"),
    path("me/change-password/", CurrentUserPasswordChangeView.as_view(), name="current_user_change_password"),
    path("me/avatar/", CurrentUserAvatarUploadView.as_view(), name="current_user_avatar_upload"),
    path("register/", TeacherRegistrationView.as_view(), name="teacher_register"),
    path("forgot-password/", ForgotPasswordResetView.as_view(), name="forgot_password_reset"),
    path("teachers/", TeacherListCreateView.as_view(), name="teacher_list_create"),
    path("teachers/summary/", TeacherManagementSummaryView.as_view(), name="teacher_management_summary"),
    path("teachers/bulk-actions/", TeacherBulkActionView.as_view(), name="teacher_bulk_action"),
    path("teachers/bulk-import/", TeacherBulkImportView.as_view(), name="teacher_bulk_import"),
    path("teachers/bulk-import-template/", TeacherBulkImportTemplateView.as_view(), name="teacher_bulk_import_template"),
    path("teachers/<int:user_id>/", TeacherDetailView.as_view(), name="teacher_detail"),
    path("teachers/<int:user_id>/reset-password/", TeacherResetPasswordView.as_view(), name="teacher_reset_password"),
    path("notifications/unread-count/", UserNotificationUnreadCountView.as_view(), name="user_notification_unread_count"),
    path("notifications/", UserNotificationListView.as_view(), name="user_notification_list"),
    path("notifications/read-all/", UserNotificationMarkAllReadView.as_view(), name="user_notification_read_all"),
    path("notifications/<int:notification_id>/read/", UserNotificationMarkReadView.as_view(), name="user_notification_read"),
]
