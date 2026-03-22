from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import PermissionDenied


ADMIN_ONLY_MESSAGE = "当前账号没有管理员权限。"
TEACHER_MANAGEMENT_ONLY_MESSAGE = "当前账号不能执行教师账户管理操作。"
SELF_OR_ADMIN_MESSAGE = "当前账号只能访问自己的账户信息。"
MANAGEABLE_TEACHER_ONLY_MESSAGE = "管理员账户不属于教师账户管理范围。"
TEACHER_ONLY_MESSAGE = "当前入口仅支持教师本人操作。"
TEACHER_SELF_SERVICE_ONLY_MESSAGE = "成果录入和维护仅限教师本人操作，管理员当前仅可查看与验证。"
PROFILE_SCOPE_MESSAGE = "教师账号只能查看本人的画像与账户信息。"
RECOMMENDATION_SCOPE_MESSAGE = "教师账号只能查看本人的推荐结果。"
ASSISTANT_SCOPE_MESSAGE = "教师账号只能查看本人的问答结果。"
GRAPH_SCOPE_MESSAGE = "教师账号只能查看本人的学术图谱。"
COMPARE_SCOPE_MESSAGE = "当前账号无权使用教师对比能力。"
ACADEMY_SCOPE_MESSAGE = "当前账号无权查看学院级统计结果。"
TEACHER_MANAGEMENT_SCOPE_MESSAGE = "教师管理入口仅支持教师账户，不包含管理员账户。"


def is_authenticated_user(user) -> bool:
    return bool(user and not isinstance(user, AnonymousUser) and user.is_authenticated)


def is_admin_user(user) -> bool:
    return bool(is_authenticated_user(user) and (user.is_staff or user.is_superuser))


def is_teacher_user(user) -> bool:
    return bool(is_authenticated_user(user) and not is_admin_user(user))


def is_manageable_teacher(user) -> bool:
    return bool(user and not is_admin_user(user))


def ensure_admin_user(user, message: str = ADMIN_ONLY_MESSAGE) -> None:
    if not is_admin_user(user):
        raise PermissionDenied(message)


def ensure_teacher_user(user, message: str = TEACHER_ONLY_MESSAGE) -> None:
    if not is_teacher_user(user):
        raise PermissionDenied(message)


def ensure_self_user(request_user, target_user, message: str = TEACHER_SELF_SERVICE_ONLY_MESSAGE) -> None:
    if request_user.id == target_user.id:
        return
    raise PermissionDenied(message)


def ensure_self_or_admin_user(request_user, target_user, message: str = SELF_OR_ADMIN_MESSAGE) -> None:
    if request_user.id == target_user.id or is_admin_user(request_user):
        return
    raise PermissionDenied(message)


def ensure_manageable_teacher(target_user, message: str = MANAGEABLE_TEACHER_ONLY_MESSAGE) -> None:
    if is_manageable_teacher(target_user):
        return
    raise PermissionDenied(message)
