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


def get_user_permission_scope(user) -> dict:
    admin = is_admin_user(user)

    if admin:
        return {
            "entry_role": "admin",
            "scope_summary": "管理员可管理教师账户、项目指南和学院看板，并可查看指定教师的画像、图谱、推荐与问答结果。",
            "allowed_actions": [
                "管理教师账户",
                "重置教师密码",
                "维护项目指南",
                "查看学院级统计看板",
                "查看指定教师画像、图谱、推荐与问答结果",
            ],
            "restricted_actions": [
                "不通过教师成果入口直接代教师新增、修改或删除成果",
            ],
            "future_extension_hint": "后续如扩展多角色，应继续优先在统一权限入口中集中扩展，而不是在页面和接口中散落判断。",
        }

    return {
        "entry_role": "teacher",
        "scope_summary": "教师可维护本人资料与成果，并查看本人的画像、图谱、推荐与问答结果，不能访问管理员入口或其他教师数据。",
        "allowed_actions": [
            "维护本人资料",
            "修改本人密码",
            "录入、编辑和删除本人成果",
            "查看本人的画像、图谱、推荐与问答结果",
        ],
        "restricted_actions": [
            "不能访问管理员入口",
            "不能管理教师账户",
            "不能查看其他教师的数据",
            "不能使用学院级统计和教师对比能力",
        ],
        "future_extension_hint": "后续如扩展多角色，应继续优先在统一权限入口中集中扩展，而不是在页面和接口中散落判断。",
    }


def get_user_security_notice(user) -> str:
    if not user.is_active:
        return INACTIVE_ACCOUNT_SECURITY_NOTICE
    if getattr(user, "password_reset_required", False):
        return TEMPORARY_PASSWORD_SECURITY_NOTICE
    return DEFAULT_PASSWORD_SECURITY_NOTICE
