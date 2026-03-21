from __future__ import annotations

from django.utils import timezone

from achievements.models import TeacherProfile

from .access import is_admin_user


DEFAULT_PASSWORD_SECURITY_NOTICE = "请妥善保管工号与密码，建议使用高强度密码并定期更新。"
TEMPORARY_PASSWORD_SECURITY_NOTICE = "当前密码为管理员初始化或重置后的临时密码，请登录后尽快修改。"
INACTIVE_ACCOUNT_SECURITY_NOTICE = "当前账户已停用，请联系管理员恢复后再继续使用。"


def get_teacher_profile(user):
    try:
        return user.profile
    except TeacherProfile.DoesNotExist:
        return None


def sync_teacher_profile(user, profile_data):
    TeacherProfile.objects.update_or_create(
        user=user,
        defaults={
            "department": profile_data.get("department", user.department or ""),
            "title": profile_data.get("title", user.title or ""),
            "discipline": profile_data.get("discipline", ""),
            "research_interests": profile_data.get("research_interests", ""),
            "h_index": profile_data.get("h_index", 0),
        },
    )


def update_teacher_account_and_profile(user, user_data, profile_data):
    for attr, value in user_data.items():
        setattr(user, attr, value)
    user.save()

    sync_teacher_profile(
        user,
        {
            "department": user.department or "",
            "title": user.title or "",
            "discipline": profile_data.get("discipline", ""),
            "research_interests": profile_data.get("research_interests", ""),
            "h_index": profile_data.get("h_index", 0),
        },
    )

    return user


def set_user_password(user, raw_password: str, *, require_password_change: bool) -> None:
    user.set_password(raw_password)
    user.password_reset_required = require_password_change
    user.password_updated_at = timezone.now()
    user.save(update_fields=["password", "password_reset_required", "password_updated_at"])


def get_user_role_code(user) -> str:
    return "admin" if is_admin_user(user) else "teacher"


def get_user_role_label(user) -> str:
    return "系统管理员" if is_admin_user(user) else "教师账户"


def get_user_security_notice(user) -> str:
    if not user.is_active:
        return INACTIVE_ACCOUNT_SECURITY_NOTICE
    if getattr(user, "password_reset_required", False):
        return TEMPORARY_PASSWORD_SECURITY_NOTICE
    return DEFAULT_PASSWORD_SECURITY_NOTICE
