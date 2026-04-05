from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ProjectGuide
from .serializers import (
    ProjectGuideFavoriteToggleSerializer,
    ProjectGuideFeedbackSerializer,
    ProjectGuideRecommendationHistorySerializer,
    ProjectGuideRecommendationSerializer,
    ProjectGuideSerializer,
    RecommendationTargetSerializer,
)
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
        serializer.save(created_by=self.request.user, **self._build_lifecycle_updates(None, serializer.validated_data))

    def perform_update(self, serializer):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            raise PermissionDenied('只有管理员可以维护项目指南。')
        serializer.save(**self._build_lifecycle_updates(serializer.instance, serializer.validated_data))

    def perform_destroy(self, instance):
        if not (self.request.user.is_staff or self.request.user.is_superuser):
            raise PermissionDenied('只有管理员可以删除项目指南。')
        instance.delete()

    def _build_lifecycle_updates(self, instance, validated_data):
        now = timezone.now()
        next_status = validated_data.get('status', instance.status if instance else 'OPEN')
        current_status = instance.status if instance else ''
        updates = {}

        if next_status == 'OPEN' and (instance is None or current_status != 'OPEN') and not (instance and instance.published_at):
            updates['published_at'] = now
        if next_status == 'CLOSED' and (instance is None or current_status != 'CLOSED') and not (instance and instance.closed_at):
            updates['closed_at'] = now
        if next_status == 'ARCHIVED' and (instance is None or current_status != 'ARCHIVED') and not (instance and instance.archived_at):
            updates['archived_at'] = now
        return updates

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied('只有管理员可以查看项目指南生命周期摘要。')
        return Response(ProjectGuideRecommendationService.build_lifecycle_summary())

    @action(detail=True, methods=['post'], url_path='favorite')
    def favorite(self, request, pk=None):
        guide = self.get_object()
        serializer = ProjectGuideFavoriteToggleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = ProjectGuideRecommendationService.toggle_favorite(
            teacher=request.user,
            guide=guide,
            is_favorited=serializer.validated_data['is_favorited'],
        )
        return Response(payload)

    @action(detail=True, methods=['post'], url_path='feedback')
    def feedback(self, request, pk=None):
        guide = self.get_object()
        serializer = ProjectGuideFeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = ProjectGuideRecommendationService.capture_feedback(
            teacher=request.user,
            guide=guide,
            feedback_signal=serializer.validated_data['feedback_signal'],
            feedback_note=serializer.validated_data.get('feedback_note', ''),
        )
        return Response(payload)


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
            requested_by=request.user,
            compare_user=compare_teacher,
            include_admin_analysis=bool(request.user.is_staff or request.user.is_superuser),
        )
        recommendation_serializer = ProjectGuideRecommendationSerializer(result['recommendations'], many=True)
        history_serializer = ProjectGuideRecommendationHistorySerializer(result['history_preview'], many=True)

        return Response(
            {
                'recommendations': recommendation_serializer.data,
                'teacher_snapshot': result['teacher_snapshot'],
                'comparison_teacher_snapshot': result.get('comparison_teacher_snapshot'),
                'comparison_summary': result.get('comparison_summary'),
                'admin_analysis': result.get('admin_analysis'),
                'favorites': result['favorites'],
                'history_preview': history_serializer.data,
                'feedback_summary': result['feedback_summary'],
                'portrait_link_summary': result['portrait_link_summary'],
                'history_batch_token': result['history_batch_token'],
                'data_meta': result['data_meta'],
                'empty_state': result['empty_state'],
            },
            status=status.HTTP_200_OK,
        )


class ProjectGuideRecommendationHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        target_serializer = RecommendationTargetSerializer(data=request.query_params)
        target_serializer.is_valid(raise_exception=True)
        try:
            teacher = ProjectGuideRecommendationService.resolve_target_teacher(
                request,
                target_serializer.validated_data.get('user_id'),
            )
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc

        history = ProjectGuideRecommendationService.build_history_preview(teacher, limit=20)
        serializer = ProjectGuideRecommendationHistorySerializer(history, many=True)
        return Response(
            {
                'teacher_id': teacher.id,
                'history': serializer.data,
                'feedback_summary': ProjectGuideRecommendationService.build_feedback_summary(teacher),
            }
        )
