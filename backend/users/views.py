from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api_errors import api_error_response

from .access import (
    ensure_admin_user,
    ensure_manageable_teacher,
    ensure_self_or_admin_user,
    is_college_admin_user,
    is_system_admin_user,
)
from .serializers import (
    DEFAULT_TEACHER_PASSWORD,
    CurrentUserSerializer,
    CurrentUserUpdateSerializer,
    CurrentUserAvatarUploadSerializer,
    ForgotPasswordResetSerializer,
    PasswordChangeSerializer,
    TeacherAccountSerializer,
    TeacherBulkActionSerializer,
    TeacherCreateSerializer,
    TeacherManagementSummarySerializer,
    TeacherUpdateSerializer,
)
from .services import (
    build_teacher_management_summary,
    get_user_security_notice,
    log_account_lifecycle_event,
    set_user_active_status,
    set_user_password,
    store_user_avatar_upload,
)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = CurrentUserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CurrentUserSerializer(request.user).data)


class CurrentUserPasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "detail": "密码修改成功，请使用新密码继续登录。",
                "security_notice": get_user_security_notice(user),
                "user": CurrentUserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class CurrentUserAvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = CurrentUserAvatarUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        avatar_url = store_user_avatar_upload(
            user=request.user,
            uploaded_file=serializer.validated_data["avatar"],
            request=request,
        )
        request.user.avatar_url = avatar_url
        request.user.save(update_fields=["avatar_url"])

        return Response(
            {
                "detail": "头像上传成功，个人中心已更新头像展示。",
                "avatar_url": avatar_url,
                "user": CurrentUserSerializer(request.user).data,
            },
            status=status.HTTP_200_OK,
        )


class TeacherListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_model = get_user_model()
        queryset = user_model.objects.all().order_by("id")

        if is_system_admin_user(request.user):
            queryset = queryset.filter(is_superuser=False)
        elif is_college_admin_user(request.user):
            queryset = queryset.filter(
                is_staff=False,
                is_superuser=False,
                department=request.user.department,
            )
        else:
            queryset = queryset.filter(id=request.user.id)

        serializer = TeacherAccountSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        ensure_admin_user(request.user)

        serializer = TeacherCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TeacherManagementSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_admin_user(request.user)

        user_model = get_user_model()
        if is_system_admin_user(request.user):
            queryset = user_model.objects.filter(is_superuser=False).order_by("id")
        else:
            queryset = user_model.objects.filter(
                is_staff=False,
                is_superuser=False,
                department=request.user.department,
            ).order_by("id")
        serializer = TeacherManagementSummarySerializer(build_teacher_management_summary(queryset))
        return Response(serializer.data)


class TeacherRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TeacherCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ForgotPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "detail": "密码已重置，请使用工号和新密码重新登录。",
                "security_notice": get_user_security_notice(user),
            },
            status=status.HTTP_200_OK,
        )


class TeacherDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, user_id):
        user_model = get_user_model()
        try:
            teacher = user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            return None

        ensure_self_or_admin_user(request.user, teacher, "当前账号只能查看自己的账户信息。")
        if is_system_admin_user(request.user):
            if teacher.is_superuser:
                ensure_manageable_teacher(teacher, "教师管理入口不支持系统管理员账户。")
        elif is_college_admin_user(request.user):
            ensure_manageable_teacher(teacher, "学院管理员当前仅可管理本学院教师账户。")
            if teacher.department != request.user.department:
                return None
        elif request.user.is_staff or request.user.is_superuser:
            ensure_manageable_teacher(teacher, "教师管理入口仅支持教师账户，不包含管理员账户。")
        return teacher

    def get(self, request, user_id):
        teacher = self.get_object(request, user_id)
        if teacher is None:
            return api_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="教师账户不存在。",
                code="teacher_not_found",
                request=request,
                next_step="请确认教师账号是否存在，或刷新教师列表后再试。",
            )
        return Response(TeacherAccountSerializer(teacher).data)

    def patch(self, request, user_id):
        teacher = self.get_object(request, user_id)
        if teacher is None:
            return api_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="教师账户不存在。",
                code="teacher_not_found",
                request=request,
                next_step="请确认教师账号是否存在，或刷新教师列表后再试。",
            )

        serializer_class = (
            TeacherUpdateSerializer if (request.user.is_staff or request.user.is_superuser) else CurrentUserUpdateSerializer
        )
        serializer = serializer_class(teacher, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        original_is_active = teacher.is_active
        serializer.save()

        if (request.user.is_staff or request.user.is_superuser) and "is_active" in serializer.validated_data:
            updated_is_active = serializer.validated_data["is_active"]
            if updated_is_active != original_is_active:
                log_account_lifecycle_event(
                    actor=request.user,
                    target=teacher,
                    action="activate" if updated_is_active else "deactivate",
                    detail="管理员通过教师详情页更新账户状态。",
                )

        return Response(TeacherAccountSerializer(teacher).data)


class TeacherResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        ensure_admin_user(request.user)

        user_model = get_user_model()
        try:
            teacher = user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            return api_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="教师账户不存在。",
                code="teacher_not_found",
                request=request,
                next_step="请确认教师账号是否存在，或刷新教师列表后再试。",
            )

        if is_system_admin_user(request.user):
            if teacher.is_superuser:
                return api_error_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message="系统管理员账户不支持通过教师管理入口重置密码。",
                    code="teacher_scope_forbidden",
                    request=request,
                    next_step="请返回教师管理列表并选择教师或学院管理员账户。",
                )
        else:
            ensure_manageable_teacher(teacher, "管理员账户不支持通过教师管理入口重置密码。")
            if teacher.department != request.user.department:
                return api_error_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message="学院管理员当前仅可重置本学院教师账户密码。",
                    code="teacher_scope_forbidden",
                    request=request,
                    next_step="请返回教师管理列表并选择本学院教师账户。",
                )
        set_user_password(teacher, DEFAULT_TEACHER_PASSWORD, require_password_change=True)
        log_account_lifecycle_event(
            actor=request.user,
            target=teacher,
            action="reset_password",
            detail="管理员通过教师管理入口重置教师密码。",
        )

        return Response(
            {
                "detail": "教师账户密码已重置。",
                "temporary_password": DEFAULT_TEACHER_PASSWORD,
                "password": DEFAULT_TEACHER_PASSWORD,
                "role_label": TeacherAccountSerializer(teacher).data["role_label"],
                "password_reset_required": teacher.password_reset_required,
                "security_notice": get_user_security_notice(teacher),
            },
            status=status.HTTP_200_OK,
        )


class TeacherBulkActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ensure_admin_user(request.user)

        serializer = TeacherBulkActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]
        requested_ids = serializer.validated_data["user_ids"]
        user_model = get_user_model()

        if is_system_admin_user(request.user):
            base_queryset = user_model.objects.filter(id__in=requested_ids, is_superuser=False)
        else:
            base_queryset = user_model.objects.filter(
                id__in=requested_ids,
                is_staff=False,
                is_superuser=False,
                department=request.user.department,
            )

        teachers_by_id = {
            teacher.id: teacher
            for teacher in base_queryset.order_by("id")
        }

        processed_items = []
        skipped_items = []

        for teacher_id in requested_ids:
            teacher = teachers_by_id.get(teacher_id)
            if not teacher:
                skipped_items.append(
                    {
                        "user_id": teacher_id,
                        "reason": "教师账户不存在，或该账号不属于教师账户管理范围。",
                    }
                )
                continue

            if action == "activate":
                set_user_active_status(teacher, is_active=True)
                log_account_lifecycle_event(
                    actor=request.user,
                    target=teacher,
                    action="activate",
                    detail="管理员批量恢复教师账户。",
                )
            elif action == "deactivate":
                set_user_active_status(teacher, is_active=False)
                log_account_lifecycle_event(
                    actor=request.user,
                    target=teacher,
                    action="deactivate",
                    detail="管理员批量停用教师账户。",
                )
            elif action == "reset_password":
                set_user_password(teacher, DEFAULT_TEACHER_PASSWORD, require_password_change=True)
                log_account_lifecycle_event(
                    actor=request.user,
                    target=teacher,
                    action="reset_password",
                    detail="管理员批量重置教师密码。",
                )

            processed_items.append(
                {
                    "user_id": teacher.id,
                    "username": teacher.username,
                    "real_name": teacher.real_name,
                    "account_status_label": TeacherAccountSerializer(teacher).data["account_status_label"],
                    "password_status_label": TeacherAccountSerializer(teacher).data["password_status_label"],
                }
            )

        detail_map = {
            "activate": "教师账户已批量恢复启用。",
            "deactivate": "教师账户已批量停用。",
            "reset_password": "教师账户密码已批量重置。",
        }

        return Response(
            {
                "detail": detail_map[action],
                "action": action,
                "processed_count": len(processed_items),
                "skipped_count": len(skipped_items),
                "processed_items": processed_items,
                "skipped_items": skipped_items,
                "temporary_password": DEFAULT_TEACHER_PASSWORD if action == "reset_password" else "",
                "management_summary": build_teacher_management_summary(
                    (
                        user_model.objects.filter(is_superuser=False)
                        if is_system_admin_user(request.user)
                        else user_model.objects.filter(
                            is_staff=False,
                            is_superuser=False,
                            department=request.user.department,
                        )
                    )
                ),
                "recovery_notice": "账户停用后将无法继续登录；恢复启用后可继续使用原密码登录。若执行了密码重置，教师需登录后尽快修改临时密码。",
            },
            status=status.HTTP_200_OK,
        )
