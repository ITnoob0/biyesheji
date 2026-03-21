from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import PermissionDenied


ADMIN_ONLY_MESSAGE = "当前账号没有管理员权限。"
TEACHER_MANAGEMENT_ONLY_MESSAGE = "当前账号不能执行教师账户管理操作。"
SELF_OR_ADMIN_MESSAGE = "当前账号只能访问自己的账户信息。"
MANAGEABLE_TEACHER_ONLY_MESSAGE = "管理员账户不属于教师账户管理范围。"


def is_authenticated_user(user) -> bool:
    return bool(user and not isinstance(user, AnonymousUser) and user.is_authenticated)


def is_admin_user(user) -> bool:
    return bool(is_authenticated_user(user) and (user.is_staff or user.is_superuser))


def is_manageable_teacher(user) -> bool:
    return bool(user and not is_admin_user(user))


def ensure_admin_user(user, message: str = ADMIN_ONLY_MESSAGE) -> None:
    if not is_admin_user(user):
        raise PermissionDenied(message)


def ensure_self_or_admin_user(request_user, target_user, message: str = SELF_OR_ADMIN_MESSAGE) -> None:
    if request_user.id == target_user.id or is_admin_user(request_user):
        return
    raise PermissionDenied(message)


def ensure_manageable_teacher(target_user, message: str = MANAGEABLE_TEACHER_ONLY_MESSAGE) -> None:
    if is_manageable_teacher(target_user):
        return
    raise PermissionDenied(message)
