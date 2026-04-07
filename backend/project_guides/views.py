from datetime import datetime, time

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.dateparse import parse_date
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
from users.access import get_user_college_id, is_admin_user, is_college_admin_user, is_system_admin_user
from users.models import UserNotification
from users.services import bulk_create_user_notifications


class ProjectGuideViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ProjectGuideSerializer
    queryset = ProjectGuide.objects.all()

    def create(self, request, *args, **kwargs):
        if not is_admin_user(request.user):
            raise PermissionDenied('只有管理员可以维护项目指南。')
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not is_admin_user(request.user):
            raise PermissionDenied('只有管理员可以维护项目指南。')
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not is_admin_user(request.user):
            raise PermissionDenied('只有管理员可以维护项目指南。')
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not is_admin_user(request.user):
            raise PermissionDenied('只有管理员可以删除项目指南。')
        return super().destroy(request, *args, **kwargs)

    def get_queryset(self):
        queryset = self.queryset.select_related('academy', 'created_by').order_by('status', '-updated_at', '-created_at')
        request = self.request
        status_filter = ProjectGuide.LEGACY_STATUS_MAP.get(request.query_params.get('status', '').strip(), request.query_params.get('status', '').strip())
        scope_filter = request.query_params.get('scope', '').strip()
        search = request.query_params.get('search', '').strip()

        if is_system_admin_user(request.user):
            scoped_queryset = queryset
        elif is_college_admin_user(request.user):
            college_name = get_user_college_id(request.user)
            scoped_queryset = queryset.filter(
                Q(scope=ProjectGuide.SCOPE_GLOBAL)
                | Q(scope=ProjectGuide.SCOPE_ACADEMY, academy__name=college_name)
            )
            if self.action in {'update', 'partial_update', 'destroy', 'targeted_push'}:
                scoped_queryset = scoped_queryset.filter(
                    scope=ProjectGuide.SCOPE_ACADEMY,
                    academy__name=college_name,
                )
        else:
            scoped_queryset = queryset.filter(
                status__in=[ProjectGuide.STATUS_ACTIVE, ProjectGuide.STATUS_URGENT]
            ).filter(
                Q(scope=ProjectGuide.SCOPE_GLOBAL)
                | Q(scope=ProjectGuide.SCOPE_ACADEMY, academy__name=get_user_college_id(request.user))
            )

        if search:
            scoped_queryset = scoped_queryset.filter(Q(title__icontains=search) | Q(issuing_agency__icontains=search))

        if status_filter:
            scoped_queryset = scoped_queryset.filter(status=status_filter)
        if scope_filter in {item[0] for item in ProjectGuide.SCOPE_CHOICES}:
            scoped_queryset = scoped_queryset.filter(scope=scope_filter)

        return self._apply_date_range_filters(scoped_queryset)

    def _parse_iso_date_or_raise(self, raw_value: str, field_name: str):
        parsed = parse_date(raw_value)
        if not parsed:
            raise ValidationError({field_name: '日期格式不合法，请使用 YYYY-MM-DD。'})
        return parsed

    def _to_day_start(self, date_value):
        return timezone.make_aware(datetime.combine(date_value, time.min), timezone.get_current_timezone())

    def _to_day_end(self, date_value):
        return timezone.make_aware(datetime.combine(date_value, time.max), timezone.get_current_timezone())

    def _apply_date_range_filters(self, queryset):
        request = self.request
        deadline_from = (request.query_params.get('deadline_from') or '').strip()
        deadline_to = (request.query_params.get('deadline_to') or '').strip()
        updated_from = (request.query_params.get('updated_from') or '').strip()
        updated_to = (request.query_params.get('updated_to') or '').strip()
        published_from = (request.query_params.get('published_from') or '').strip()
        published_to = (request.query_params.get('published_to') or '').strip()
        archived_from = (request.query_params.get('archived_from') or '').strip()
        archived_to = (request.query_params.get('archived_to') or '').strip()

        if deadline_from:
            queryset = queryset.filter(application_deadline__gte=self._parse_iso_date_or_raise(deadline_from, 'deadline_from'))
        if deadline_to:
            queryset = queryset.filter(application_deadline__lte=self._parse_iso_date_or_raise(deadline_to, 'deadline_to'))

        if updated_from:
            queryset = queryset.filter(updated_at__gte=self._to_day_start(self._parse_iso_date_or_raise(updated_from, 'updated_from')))
        if updated_to:
            queryset = queryset.filter(updated_at__lte=self._to_day_end(self._parse_iso_date_or_raise(updated_to, 'updated_to')))

        if published_from:
            queryset = queryset.filter(published_at__gte=self._to_day_start(self._parse_iso_date_or_raise(published_from, 'published_from')))
        if published_to:
            queryset = queryset.filter(published_at__lte=self._to_day_end(self._parse_iso_date_or_raise(published_to, 'published_to')))

        if archived_from:
            queryset = queryset.filter(archived_at__gte=self._to_day_start(self._parse_iso_date_or_raise(archived_from, 'archived_from')))
        if archived_to:
            queryset = queryset.filter(archived_at__lte=self._to_day_end(self._parse_iso_date_or_raise(archived_to, 'archived_to')))

        return queryset

    def _resolve_or_create_user_academy(self):
        from .models import Academy

        academy_name = get_user_college_id(self.request.user)
        if not academy_name:
            raise ValidationError({'academy_id': '当前管理员账号未绑定学院，无法创建学院级指南。'})
        academy, _ = Academy.objects.get_or_create(name=academy_name)
        return academy

    def perform_create(self, serializer):
        if not is_admin_user(self.request.user):
            raise PermissionDenied('只有管理员可以维护项目指南。')
        updates = self._build_lifecycle_updates(None, serializer.validated_data)
        if is_college_admin_user(self.request.user):
            academy = self._resolve_or_create_user_academy()
            serializer.save(
                created_by=self.request.user,
                scope=ProjectGuide.SCOPE_ACADEMY,
                academy=academy,
                **updates,
            )
            return

        scope = serializer.validated_data.get('scope', ProjectGuide.SCOPE_GLOBAL)
        academy = serializer.validated_data.get('academy')
        if scope == ProjectGuide.SCOPE_GLOBAL:
            academy = None
        serializer.save(created_by=self.request.user, scope=scope, academy=academy, **updates)

    def perform_update(self, serializer):
        if not is_admin_user(self.request.user):
            raise PermissionDenied('只有管理员可以维护项目指南。')
        updates = self._build_lifecycle_updates(serializer.instance, serializer.validated_data)
        if is_college_admin_user(self.request.user):
            academy = self._resolve_or_create_user_academy()
            serializer.save(scope=ProjectGuide.SCOPE_ACADEMY, academy=academy, **updates)
            return
        serializer.save(**updates)

    def perform_destroy(self, instance):
        if not is_admin_user(self.request.user):
            raise PermissionDenied('只有管理员可以删除项目指南。')
        instance.delete()

    def _build_lifecycle_updates(self, instance, validated_data):
        now = timezone.now()
        next_status = validated_data.get('status', instance.status if instance else ProjectGuide.STATUS_DRAFT)
        next_status = ProjectGuide.LEGACY_STATUS_MAP.get(next_status, next_status)
        current_status = instance.status if instance else ''
        updates = {}

        if next_status in ProjectGuide.ACTIVE_PUSH_STATUSES and (
            instance is None or current_status not in ProjectGuide.ACTIVE_PUSH_STATUSES
        ) and not (instance and instance.published_at):
            updates['published_at'] = now
        if next_status == ProjectGuide.STATUS_ARCHIVED and (
            instance is None or current_status != ProjectGuide.STATUS_ARCHIVED
        ):
            if not (instance and instance.closed_at):
                updates['closed_at'] = now
            if not (instance and instance.archived_at):
                updates['archived_at'] = now
        elif instance and instance.status == ProjectGuide.STATUS_ARCHIVED and next_status in ProjectGuide.ACTIVE_PUSH_STATUSES:
            updates['archived_at'] = None
            updates['closed_at'] = None
        return updates

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        if not is_admin_user(request.user):
            raise PermissionDenied('只有管理员可以查看项目指南生命周期摘要。')
        return Response(ProjectGuideRecommendationService.build_lifecycle_summary(request_user=request.user))

    @action(detail=True, methods=['post'], url_path='targeted_push')
    def targeted_push(self, request, pk=None):
        if not is_admin_user(request.user):
            raise PermissionDenied('只有管理员可以执行定向推送。')

        guide = self.get_object()
        if guide.status not in ProjectGuide.ACTIVE_PUSH_STATUSES:
            raise ValidationError({'detail': '仅 ACTIVE 或 URGENT 状态的指南支持定向推送。'})

        user_model = get_user_model()
        teacher_queryset = user_model.objects.filter(
            is_active=True,
            is_staff=False,
            is_superuser=False,
        )
        if guide.scope == ProjectGuide.SCOPE_ACADEMY and guide.academy_id:
            teacher_queryset = teacher_queryset.filter(department=guide.academy.name)

        keywords = [str(item).strip().lower() for item in (guide.target_keywords or []) if str(item).strip()]
        matched_count = 0
        matched_teachers = []
        if keywords:
            for teacher in teacher_queryset:
                try:
                    profile = teacher.profile
                except Exception:
                    profile = None
                corpus = ' '.join(
                    [
                        teacher.real_name or '',
                        teacher.username or '',
                        teacher.department or '',
                        teacher.title or '',
                        teacher.discipline if hasattr(teacher, 'discipline') else '',
                        getattr(profile, 'research_interests', '') if profile else '',
                        ' '.join(teacher.research_direction or []),
                        teacher.bio or '',
                    ]
                ).lower()
                if any(keyword in corpus for keyword in keywords):
                    matched_count += 1
                    matched_teachers.append(teacher)

        notification_count = 0
        if matched_teachers:
            deadline_text = f"，截止时间 {guide.application_deadline}" if guide.application_deadline else ""
            notification_count = bulk_create_user_notifications(
                recipients=matched_teachers,
                sender=request.user,
                category=UserNotification.CATEGORY_PROJECT_GUIDE_PUSH,
                title='收到新的项目指南推送',
                content_builder=lambda recipient: (
                    f"管理员已向你推送《{guide.title}》{deadline_text}。"
                    f"请前往项目推荐查看并决定是否收藏或反馈。"
                ),
                action_path='/project-recommendations',
                action_query_builder=lambda recipient: {
                    'source': 'notification',
                    'section': 'recommendation-evidence',
                    'guide_id': str(guide.id),
                },
                payload_builder=lambda recipient: {
                    'guide_id': guide.id,
                    'guide_title': guide.title,
                    'guide_status': guide.status,
                    'scope': guide.scope,
                },
            )

        return Response(
            {
                'detail': '定向推送任务已模拟执行。',
                'guide_id': guide.id,
                'guide_status': guide.status,
                'scope': guide.scope,
                'matched_count': matched_count,
                'notification_count': notification_count,
            }
        )

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
