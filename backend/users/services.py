from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

from achievements.models import TeacherProfile

from .access import is_admin_user


DEFAULT_PASSWORD_SECURITY_NOTICE = "请妥善保管工号与密码，建议使用高强度密码并定期更新。"
TEMPORARY_PASSWORD_SECURITY_NOTICE = "当前密码为管理员初始化或重置后的临时密码，请登录后尽快修改。"
INACTIVE_ACCOUNT_SECURITY_NOTICE = "当前账户已停用，请联系管理员恢复后再继续使用。"
logger = logging.getLogger(__name__)
CONTACT_VISIBILITY_LABELS = {
    "email_only": "仅公开邮箱",
    "phone_only": "仅公开电话",
    "both": "公开邮箱和电话",
    "internal_only": "联系方式仅内部可见",
}


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


def set_user_active_status(user, *, is_active: bool) -> None:
    user.is_active = is_active
    user.save(update_fields=["is_active"])


def get_user_role_code(user) -> str:
    return "admin" if is_admin_user(user) else "teacher"


def get_user_role_label(user) -> str:
    return "系统管理员" if is_admin_user(user) else "教师账户"


def get_user_account_status_label(user) -> str:
    return "账户可用" if getattr(user, "is_active", False) else "账户停用"


def get_user_password_status_label(user) -> str:
    return "待修改密码" if getattr(user, "password_reset_required", False) else "状态正常"


def get_user_contact_visibility_label(user) -> str:
    return CONTACT_VISIBILITY_LABELS.get(getattr(user, "contact_visibility", "email_only"), "仅公开邮箱")


def get_user_next_action_hint(user) -> str:
    if not getattr(user, "is_active", True):
        return "当前账户已停用，需由管理员恢复启用后才能继续登录和修改密码。"
    if getattr(user, "password_reset_required", False):
        return "当前密码为初始化或重置后的临时密码，请登录后尽快前往个人中心修改密码。"
    return "当前账户状态正常，可继续维护资料、成果和密码。"


def build_public_contact_channels(user) -> list[dict]:
    channels = []
    visibility = getattr(user, "contact_visibility", "email_only")
    email = (getattr(user, "email", "") or "").strip()
    phone = (getattr(user, "contact_phone", "") or "").strip()

    if visibility in {"email_only", "both"} and email:
        channels.append({"key": "email", "label": "联系邮箱", "value": email})
    if visibility in {"phone_only", "both"} and phone:
        channels.append({"key": "phone", "label": "联系电话", "value": phone})

    return channels


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


def store_user_avatar_upload(*, user, uploaded_file, request) -> str:
    avatar_dir = Path("avatars")
    extension = Path(uploaded_file.name).suffix.lower() or ".bin"
    generated_name = avatar_dir / f"user_{user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}{extension}"

    old_avatar_url = getattr(user, "avatar_url", "") or ""
    parsed_url = urlparse(old_avatar_url)
    if parsed_url.path.startswith(settings.MEDIA_URL):
        old_relative_path = parsed_url.path.removeprefix(settings.MEDIA_URL)
        old_storage_path = str(Path(old_relative_path))
        if old_storage_path and default_storage.exists(old_storage_path):
            default_storage.delete(old_storage_path)

    stored_path = default_storage.save(str(generated_name), uploaded_file)
    return request.build_absolute_uri(f"{settings.MEDIA_URL}{stored_path}")


def build_teacher_management_summary(queryset) -> dict:
    total_count = queryset.count()
    active_count = queryset.filter(is_active=True).count()
    inactive_count = queryset.filter(is_active=False).count()
    password_reset_required_count = queryset.filter(password_reset_required=True).count()
    stable_password_count = max(total_count - password_reset_required_count, 0)

    return {
        "total_count": total_count,
        "active_count": active_count,
        "inactive_count": inactive_count,
        "password_reset_required_count": password_reset_required_count,
        "stable_password_count": stable_password_count,
        "recovery_guidance": "账户停用后，教师将无法继续登录或修改密码；恢复启用后可继续使用原密码登录。若管理员执行了密码重置，教师登录后需尽快修改临时密码。",
        "future_extension_hint": "后续如扩展多角色，应继续在统一权限入口和账户生命周期摘要中集中扩展，不应散落到各个页面自行判断。",
    }


def log_account_lifecycle_event(*, actor, target, action: str, detail: str = "") -> None:
    actor_name = getattr(actor, "username", "unknown")
    target_name = getattr(target, "username", "unknown")
    logger.info(
        "account_lifecycle action=%s actor=%s target=%s detail=%s",
        action,
        actor_name,
        target_name,
        detail or "-",
    )
