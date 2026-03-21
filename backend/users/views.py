from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import ensure_admin_user, ensure_manageable_teacher, ensure_self_or_admin_user
from .serializers import (
    DEFAULT_TEACHER_PASSWORD,
    CurrentUserSerializer,
    CurrentUserUpdateSerializer,
    ForgotPasswordResetSerializer,
    PasswordChangeSerializer,
    TeacherAccountSerializer,
    TeacherCreateSerializer,
    TeacherUpdateSerializer,
)
from .services import get_user_security_notice, set_user_password


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


class TeacherListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_model = get_user_model()
        queryset = user_model.objects.all().order_by("id")

        if request.user.is_staff or request.user.is_superuser:
            queryset = queryset.filter(is_staff=False, is_superuser=False)
        else:
            queryset = queryset.filter(id=request.user.id)

        serializer = TeacherAccountSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        ensure_admin_user(request.user, "只有管理员可以创建教师账户。")

        serializer = TeacherCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


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
        return teacher

    def get(self, request, user_id):
        teacher = self.get_object(request, user_id)
        if teacher is None:
            return Response({"detail": "教师账户不存在。"}, status=status.HTTP_404_NOT_FOUND)
        return Response(TeacherAccountSerializer(teacher).data)

    def patch(self, request, user_id):
        teacher = self.get_object(request, user_id)
        if teacher is None:
            return Response({"detail": "教师账户不存在。"}, status=status.HTTP_404_NOT_FOUND)

        serializer_class = (
            TeacherUpdateSerializer if (request.user.is_staff or request.user.is_superuser) else CurrentUserUpdateSerializer
        )
        serializer = serializer_class(teacher, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TeacherAccountSerializer(teacher).data)


class TeacherResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        ensure_admin_user(request.user, "只有管理员可以重置教师密码。")

        user_model = get_user_model()
        try:
            teacher = user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            return Response({"detail": "教师账户不存在。"}, status=status.HTTP_404_NOT_FOUND)

        ensure_manageable_teacher(teacher, "管理员账户不支持通过教师管理入口重置密码。")
        set_user_password(teacher, DEFAULT_TEACHER_PASSWORD, require_password_change=True)

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
