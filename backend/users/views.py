from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponse
from django.utils import timezone
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
    ensure_teacher_user,
    is_college_admin_user,
    is_same_college_user,
    is_system_admin_user,
)
from .models import College, TeacherTitleChangeRequest, UserNotification
from .serializers import (
    CollegeSerializer,
    DEFAULT_TEACHER_PASSWORD,
    CurrentUserSerializer,
    CurrentUserUpdateSerializer,
    CurrentUserAvatarUploadSerializer,
    ForgotPasswordCodeSerializer,
    ForgotPasswordConfirmSerializer,
    PasswordChangeSerializer,
    TeacherAccountSerializer,
    TeacherBulkActionSerializer,
    TeacherCreateSerializer,
    TeacherTitleChangeRequestCreateSerializer,
    TeacherTitleChangeRequestRejectSerializer,
    TeacherTitleChangeRequestReviewSerializer,
    TeacherTitleChangeRequestSerializer,
    UserNotificationSerializer,
    TeacherManagementSummarySerializer,
    TeacherUpdateSerializer,
)
from .services import (
    build_teacher_management_summary,
    build_bulk_import_template_xlsx,
    bulk_create_user_notifications,
    create_user_notification,
    ensure_password_change_notification,
    get_user_security_notice,
    log_account_lifecycle_event,
    parse_bulk_account_import_file,
    set_user_active_status,
    set_user_password,
    store_user_avatar_upload,
)
from .title_catalog import get_teacher_professional_title_options


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CurrentUserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = CurrentUserUpdateSerializer(request.user, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(CurrentUserSerializer(request.user).data)


class CurrentUserTitleChangeRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_teacher_user(request.user)
        queryset = TeacherTitleChangeRequest.objects.filter(teacher=request.user).order_by("-created_at", "-id")
        serializer = TeacherTitleChangeRequestSerializer(queryset, many=True)
        return Response({"records": serializer.data})

    def post(self, request):
        ensure_teacher_user(request.user)
        serializer = TeacherTitleChangeRequestCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        request_record = serializer.save()

        college_admins = get_user_model().objects.filter(
            is_active=True,
            is_staff=True,
            is_superuser=False,
            department=request.user.department,
        ).order_by("id")
        requester_name = request.user.real_name or request.user.username
        bulk_create_user_notifications(
            recipients=college_admins,
            sender=request.user,
            category=UserNotification.CATEGORY_TITLE_CHANGE_REQUEST,
            title="收到教师职称变更申请",
            content_builder=lambda recipient: (
                f"教师 {requester_name}（工号 {request.user.username}）申请职称变更："
                f"{request_record.current_title or '未设置'} -> {request_record.requested_title}。"
            ),
            action_path="/teachers",
            action_query_builder=lambda recipient: {
                "source": "title_change_request",
                "focus": str(request.user.id),
            },
            payload_builder=lambda recipient: {
                "request_id": request_record.id,
                "teacher_id": request.user.id,
                "teacher_name": requester_name,
                "requested_title": request_record.requested_title,
            },
        )

        return Response(
            {
                "detail": "职称变更申请已提交，待学院管理员审核通过后生效。",
                "request": TeacherTitleChangeRequestSerializer(request_record).data,
            },
            status=status.HTTP_201_CREATED,
        )


class TeacherTitleChangeRequestListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_admin_user(request.user)
        status_filter = (request.query_params.get("status", "") or "").strip().upper()
        queryset = TeacherTitleChangeRequest.objects.select_related("teacher", "reviewer")

        if is_system_admin_user(request.user):
            queryset = queryset.filter(teacher__is_staff=False, teacher__is_superuser=False)
        else:
            queryset = queryset.filter(
                teacher__is_staff=False,
                teacher__is_superuser=False,
                teacher__department=request.user.department,
            )

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        serializer = TeacherTitleChangeRequestSerializer(queryset.order_by("-created_at", "-id"), many=True)
        return Response({"records": serializer.data})


class TeacherTitleChangeRequestApproveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id: int):
        ensure_admin_user(request.user)
        serializer = TeacherTitleChangeRequestReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_request = TeacherTitleChangeRequest.objects.select_related("teacher").filter(id=request_id).first()
        if target_request is None:
            return api_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="职称变更申请不存在。",
                code="title_change_request_not_found",
                request=request,
                next_step="请刷新申请列表后重试。",
            )

        if not is_system_admin_user(request.user):
            if not is_same_college_user(request.user, target_request.teacher):
                return api_error_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message="学院管理员仅可审核本学院教师的职称申请。",
                    code="title_change_request_scope_forbidden",
                    request=request,
                    next_step="请返回列表并选择本学院教师申请。",
                )

        if target_request.status != TeacherTitleChangeRequest.STATUS_PENDING:
            return api_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="该申请已处理，无法重复审核。",
                code="title_change_request_already_processed",
                request=request,
                next_step="请刷新申请列表后重试。",
            )

        with transaction.atomic():
            target_request.teacher.title = target_request.requested_title
            target_request.teacher.save(update_fields=["title"])
            target_request.status = TeacherTitleChangeRequest.STATUS_APPROVED
            target_request.reviewer = request.user
            target_request.review_comment = (serializer.validated_data.get("review_comment") or "").strip()
            target_request.reviewed_at = timezone.now()
            target_request.save(update_fields=["status", "reviewer", "review_comment", "reviewed_at"])

            profile = getattr(target_request.teacher, "profile", None)
            if profile is not None:
                profile.title = target_request.requested_title
                profile.save(update_fields=["title"])

        create_user_notification(
            recipient=target_request.teacher,
            sender=request.user,
            category=UserNotification.CATEGORY_TITLE_CHANGE_REQUEST,
            title="你的职称变更申请已通过",
            content=(
                f"学院管理员已通过你的职称变更申请："
                f"{target_request.current_title or '未设置'} -> {target_request.requested_title}。"
            ),
            action_path="/profile",
            action_query={"section": "public-profile"},
            payload={"request_id": target_request.id, "status": target_request.status},
        )

        return Response(
            {
                "detail": "职称变更申请已通过并生效。",
                "request": TeacherTitleChangeRequestSerializer(target_request).data,
            }
        )


class TeacherTitleChangeRequestRejectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, request_id: int):
        ensure_admin_user(request.user)
        serializer = TeacherTitleChangeRequestRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_request = TeacherTitleChangeRequest.objects.select_related("teacher").filter(id=request_id).first()
        if target_request is None:
            return api_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="职称变更申请不存在。",
                code="title_change_request_not_found",
                request=request,
                next_step="请刷新申请列表后重试。",
            )

        if not is_system_admin_user(request.user):
            if not is_same_college_user(request.user, target_request.teacher):
                return api_error_response(
                    status_code=status.HTTP_403_FORBIDDEN,
                    message="学院管理员仅可审核本学院教师的职称申请。",
                    code="title_change_request_scope_forbidden",
                    request=request,
                    next_step="请返回列表并选择本学院教师申请。",
                )

        if target_request.status != TeacherTitleChangeRequest.STATUS_PENDING:
            return api_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="该申请已处理，无法重复审核。",
                code="title_change_request_already_processed",
                request=request,
                next_step="请刷新申请列表后重试。",
            )

        target_request.status = TeacherTitleChangeRequest.STATUS_REJECTED
        target_request.reviewer = request.user
        target_request.review_comment = serializer.validated_data["review_comment"].strip()
        target_request.reviewed_at = timezone.now()
        target_request.save(update_fields=["status", "reviewer", "review_comment", "reviewed_at"])

        create_user_notification(
            recipient=target_request.teacher,
            sender=request.user,
            category=UserNotification.CATEGORY_TITLE_CHANGE_REQUEST,
            title="你的职称变更申请未通过",
            content=(
                f"学院管理员驳回了你的职称变更申请（目标：{target_request.requested_title}）。"
                f"驳回意见：{target_request.review_comment}"
            ),
            action_path="/profile",
            action_query={"section": "public-profile"},
            payload={"request_id": target_request.id, "status": target_request.status},
        )

        return Response(
            {
                "detail": "已驳回该职称变更申请。",
                "request": TeacherTitleChangeRequestSerializer(target_request).data,
            }
        )


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


class CollegeListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_admin_user(request.user)
        queryset = College.objects.filter(is_active=True).order_by("sort_order", "id")
        serializer = CollegeSerializer(queryset, many=True)
        return Response({"records": serializer.data})

    def post(self, request):
        if not is_system_admin_user(request.user):
            return api_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message="仅系统管理员可以新增学院。",
                code="college_manage_forbidden",
                request=request,
                next_step="请使用系统管理员账号进入学院管理页面。",
            )

        serializer = CollegeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sort_order = serializer.validated_data.get("sort_order")
        if not sort_order:
            sort_order = (College.objects.aggregate(max_order=Max("sort_order"))["max_order"] or 0) + 1
        college = serializer.save(sort_order=sort_order, is_active=True)
        return Response(CollegeSerializer(college).data, status=status.HTTP_201_CREATED)


class CollegeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, college_id: int):
        if not is_system_admin_user(request.user):
            return api_error_response(
                status_code=status.HTTP_403_FORBIDDEN,
                message="仅系统管理员可以删除学院。",
                code="college_manage_forbidden",
                request=request,
                next_step="请使用系统管理员账号进入学院管理页面。",
            )

        college = College.objects.filter(id=college_id).first()
        if college is None:
            return api_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="学院不存在。",
                code="college_not_found",
                request=request,
                next_step="请刷新学院管理列表后重试。",
            )

        user_model = get_user_model()
        account_count = user_model.objects.filter(department=college.name, is_superuser=False).count()
        if account_count:
            return api_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=f"该学院下已有 {account_count} 个账号，不能直接删除。",
                code="college_in_use",
                request=request,
                next_step="请先将该学院下的学院管理员和教师账号迁移到其他学院，或停用相关账号后再处理。",
            )

        college.delete()
        return Response({"detail": "学院已删除。"})


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


class TeacherTitleOptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"options": get_teacher_professional_title_options()})


class TeacherRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return api_error_response(
            status_code=status.HTTP_403_FORBIDDEN,
            message="系统已关闭自助注册，请联系学院管理员创建账号。",
            code="self_registration_disabled",
            request=request,
            next_step="请返回登录页，通过“忘记密码”提交重置申请，或联系学院管理员开通账号。",
        )


class ForgotPasswordCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.save()
        return Response(
            {
                "detail": "验证码已生成并输出到后端运行终端，请查看终端后输入验证码。",
                **payload,
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "detail": "密码已重置成功，请使用新密码登录。",
                "security_notice": get_user_security_notice(user),
            },
            status=status.HTTP_200_OK,
        )


class TeacherBulkImportView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        ensure_admin_user(request.user)

        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return api_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="请先上传导入文件。",
                code="bulk_import_file_required",
                request=request,
                next_step="请选择 .xlsx 或 .csv 文件后重试。",
            )

        try:
            rows = parse_bulk_account_import_file(uploaded_file)
        except ValueError as exc:
            return api_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=str(exc),
                code="bulk_import_file_invalid",
                request=request,
                next_step="请按模板整理后重新上传。",
            )

        if not rows:
            return api_error_response(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="未解析到可导入数据，请检查模板内容。",
                code="bulk_import_empty_rows",
                request=request,
                next_step="请至少提供一行工号与姓名后重试。",
            )

        created_items = []
        skipped_items = []

        for row in rows:
            employee_id = (row.get("employee_id") or "").strip()
            real_name = (row.get("real_name") or "").strip()
            department = (row.get("department") or "").strip()
            email = (row.get("email") or "").strip()
            contact_phone = (row.get("contact_phone") or "").strip()
            row_number = row.get("row_number")

            if not employee_id or not real_name:
                skipped_items.append(
                    {
                        "row_number": row_number,
                        "employee_id": employee_id,
                        "real_name": real_name,
                        "reason": "工号或姓名为空，已跳过。",
                    }
                )
                continue

            if is_system_admin_user(request.user):
                if not department:
                    skipped_items.append(
                        {
                            "row_number": row_number,
                            "employee_id": employee_id,
                            "real_name": real_name,
                            "reason": "创建学院管理员时必须填写所属学院。",
                        }
                    )
                    continue
                payload = {
                    "employee_id": employee_id,
                    "role_code": "college_admin",
                    "real_name": real_name,
                    "department": department,
                    "title": "学院管理员",
                }
            else:
                department = (request.user.department or "").strip()
                if not department:
                    skipped_items.append(
                        {
                            "row_number": row_number,
                            "employee_id": employee_id,
                            "real_name": real_name,
                            "reason": "当前学院管理员账号未配置所属学院，无法批量创建。",
                        }
                    )
                    continue
                payload = {
                    "employee_id": employee_id,
                    "role_code": "teacher",
                    "real_name": real_name,
                    "department": department,
                    "title": "讲师",
                }

            if payload.get("role_code") == "teacher":
                payload["email"] = email
                payload["contact_phone"] = contact_phone

            serializer = TeacherCreateSerializer(data=payload, context={"request": request})
            if not serializer.is_valid():
                first_error = next(iter(serializer.errors.values()), ["数据校验失败"])
                message = first_error[0] if isinstance(first_error, list) else str(first_error)
                skipped_items.append(
                    {
                        "row_number": row_number,
                        "employee_id": employee_id,
                        "real_name": real_name,
                        "reason": message,
                    }
                )
                continue

            user = serializer.save()
            created_items.append(
                {
                    "row_number": row_number,
                    "employee_id": user.id,
                    "username": user.username,
                    "real_name": user.real_name,
                    "department": user.department,
                    "title": user.title,
                    "role_code": "college_admin" if user.is_staff else "teacher",
                }
            )

        target_label = "学院管理员" if is_system_admin_user(request.user) else "教师"
        return Response(
            {
                "detail": f"批量创建{target_label}完成。",
                "created_count": len(created_items),
                "skipped_count": len(skipped_items),
                "temporary_password": DEFAULT_TEACHER_PASSWORD,
                "created_items": created_items,
                "skipped_items": skipped_items,
            },
            status=status.HTTP_200_OK,
        )


class TeacherBulkImportTemplateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        ensure_admin_user(request.user)
        is_system_admin = is_system_admin_user(request.user)
        filename, content = build_bulk_import_template_xlsx(
            is_system_admin=is_system_admin,
            college_name=request.user.department or "",
        )
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


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
        serializer = serializer_class(teacher, data=request.data, partial=True, context={"request": request})
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
        ensure_password_change_notification(
            teacher,
            temporary_password=DEFAULT_TEACHER_PASSWORD,
            created_by_admin=True,
        )
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
                ensure_password_change_notification(
                    teacher,
                    temporary_password=DEFAULT_TEACHER_PASSWORD,
                    created_by_admin=True,
                )
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


class UserNotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread_count = UserNotification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread_count": unread_count})


class UserNotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        unread_only_raw = (request.query_params.get("unread_only", "") or "").strip().lower()
        unread_only = unread_only_raw in {"1", "true", "yes"}
        limit_raw = (request.query_params.get("limit", "20") or "20").strip()
        try:
            limit = max(min(int(limit_raw), 100), 1)
        except (TypeError, ValueError):
            limit = 20

        queryset = UserNotification.objects.filter(recipient=request.user)
        total_count = queryset.count()
        unread_count = queryset.filter(is_read=False).count()
        if unread_only:
            queryset = queryset.filter(is_read=False)
        records = queryset.order_by("is_read", "-created_at", "-id")[:limit]
        serializer = UserNotificationSerializer(records, many=True)
        return Response(
            {
                "total_count": total_count,
                "unread_count": unread_count,
                "records": serializer.data,
            }
        )


class UserNotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, notification_id: int):
        notification = UserNotification.objects.filter(id=notification_id, recipient=request.user).first()
        if notification is None:
            return api_error_response(
                status_code=status.HTTP_404_NOT_FOUND,
                message="通知不存在。",
                code="notification_not_found",
                request=request,
                next_step="请刷新通知列表后重试。",
            )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save(update_fields=["is_read", "read_at", "updated_at"])

        unread_count = UserNotification.objects.filter(recipient=request.user, is_read=False).count()
        return Response(
            {
                "detail": "通知已标记为已读。",
                "unread_count": unread_count,
                "notification": UserNotificationSerializer(notification).data,
            }
        )


class UserNotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        unread_queryset = UserNotification.objects.filter(recipient=request.user, is_read=False)
        updated_count = unread_queryset.update(is_read=True, read_at=timezone.now())
        return Response(
            {
                "detail": f"已将 {updated_count} 条通知标记为已读。",
                "updated_count": updated_count,
                "unread_count": 0,
            }
        )
