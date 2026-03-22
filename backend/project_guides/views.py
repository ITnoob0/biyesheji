from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ProjectGuide
from .serializers import ProjectGuideRecommendationSerializer, ProjectGuideSerializer, RecommendationTargetSerializer
from .services import ProjectGuideRecommendationService


class ProjectGuideViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectGuideSerializer
    queryset = ProjectGuide.objects.all()

    def get_queryset(self):
        queryset = self.queryset.order_by('status', '-updated_at', '-created_at')
        request = self.request
        status_filter = request.query_params.get('status', '').strip()
        search = request.query_params.get('search', '').strip()

        if not (request.user.is_staff or request.user.is_superuser):
            queryset = queryset.filter(status='OPEN')
        elif status_filter:
            queryset = queryset.filter(status=status_filter)

        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(issuing_agency__icontains=search))

        return queryset

    def perform_create(self, serializer):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            raise PermissionDenied('只有管理员可以维护项目指南。')
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            raise PermissionDenied('只有管理员可以维护项目指南。')
        serializer.save()

    def perform_destroy(self, instance):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            raise PermissionDenied('只有管理员可以删除项目指南。')
        instance.delete()


class ProjectGuideRecommendationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_serializer = RecommendationTargetSerializer(data=request.query_params)
        target_serializer.is_valid(raise_exception=True)

        try:
            teacher = ProjectGuideRecommendationService.resolve_target_teacher(
                request,
                target_serializer.validated_data.get('user_id'),
            )
            compare_teacher = ProjectGuideRecommendationService.resolve_compare_teacher(
                request,
                target_serializer.validated_data.get('compare_user_id'),
                primary_teacher=teacher,
            )
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        except Exception as exc:
            raise ValidationError({'detail': f'推荐参数校验未通过：{exc}'}) from exc

        result = ProjectGuideRecommendationService.build_recommendations(
            teacher,
            compare_user=compare_teacher,
            include_admin_analysis=bool(request.user.is_staff or request.user.is_superuser),
        )
        recommendation_serializer = ProjectGuideRecommendationSerializer(result['recommendations'], many=True)

        return Response(
            {
                'recommendations': recommendation_serializer.data,
                'teacher_snapshot': result['teacher_snapshot'],
                'comparison_teacher_snapshot': result.get('comparison_teacher_snapshot'),
                'comparison_summary': result.get('comparison_summary'),
                'admin_analysis': result.get('admin_analysis'),
                'data_meta': result['data_meta'],
                'empty_state': result['empty_state'],
            },
            status=status.HTTP_200_OK,
        )
