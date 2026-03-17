from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    DEFAULT_TEACHER_PASSWORD,
    CurrentUserSerializer,
    CurrentUserUpdateSerializer,
    ForgotPasswordResetSerializer,
    TeacherAccountSerializer,
    TeacherCreateSerializer,
    TeacherUpdateSerializer,
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


class TeacherListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_model = get_user_model()
        queryset = user_model.objects.all().order_by('id')

        if not (request.user.is_staff or request.user.is_superuser):
            queryset = queryset.filter(id=request.user.id)
        else:
            queryset = queryset.filter(is_superuser=False)

        serializer = TeacherAccountSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied('Only administrators can create teacher accounts.')

        serializer = TeacherCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class TeacherRegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TeacherCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ForgotPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'detail': 'Password reset successfully.'}, status=status.HTTP_200_OK)


class TeacherDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, user_id):
        user_model = get_user_model()
        try:
            teacher = user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            return None

        if request.user.id != teacher.id and not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied('You do not have permission to access this teacher.')

        return teacher

    def get(self, request, user_id):
        teacher = self.get_object(request, user_id)
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(TeacherAccountSerializer(teacher).data)

    def patch(self, request, user_id):
        teacher = self.get_object(request, user_id)
        if teacher is None:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer_class = TeacherUpdateSerializer if request.user.is_staff or request.user.is_superuser else CurrentUserUpdateSerializer
        serializer = serializer_class(teacher, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(TeacherAccountSerializer(teacher).data)


class TeacherResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied('Only administrators can reset teacher passwords.')

        user_model = get_user_model()
        try:
            teacher = user_model.objects.get(id=user_id)
        except user_model.DoesNotExist:
            return Response({'detail': 'Teacher not found.'}, status=status.HTTP_404_NOT_FOUND)

        teacher.set_password(DEFAULT_TEACHER_PASSWORD)
        teacher.save()
        return Response({'detail': 'Password reset successfully.', 'password': DEFAULT_TEACHER_PASSWORD})
