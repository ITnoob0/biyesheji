from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Academy, ProjectGuide, ProjectGuideFavorite, ProjectGuideRecommendationRecord


def normalize_text_list(values):
    normalized = []
    for value in values or []:
        item = str(value).strip()
        if item and item not in normalized:
            normalized.append(item)
    return normalized[:20]


ALLOWED_RULE_CONFIG_KEYS = {
    'keyword_bonus',
    'discipline_bonus',
    'activity_bonus',
    'window_bonus',
    'support_bonus',
    'portrait_bonus',
}


class ProjectGuideSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(
        choices=list(ProjectGuide.STATUS_CHOICES) + [('OPEN', '申报中'), ('CLOSED', '已截止')],
    )
    guide_level_display = serializers.CharField(source='get_guide_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    rule_profile_display = serializers.CharField(source='get_rule_profile_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    academy_id = serializers.PrimaryKeyRelatedField(
        source='academy',
        queryset=Academy.objects.all(),
        required=False,
        allow_null=True,
    )
    academy_name = serializers.SerializerMethodField()
    status_timeline = serializers.SerializerMethodField()

    class Meta:
        model = ProjectGuide
        fields = (
            'id',
            'title',
            'issuing_agency',
            'guide_level',
            'guide_level_display',
            'status',
            'status_display',
            'scope',
            'scope_display',
            'academy_id',
            'academy_name',
            'rule_profile',
            'rule_profile_display',
            'rule_config',
            'application_deadline',
            'summary',
            'target_keywords',
            'target_disciplines',
            'recommendation_tags',
            'support_amount',
            'eligibility_notes',
            'source_url',
            'lifecycle_note',
            'published_at',
            'closed_at',
            'archived_at',
            'status_timeline',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'created_by',
            'created_by_name',
            'published_at',
            'closed_at',
            'archived_at',
            'status_timeline',
            'created_at',
            'updated_at',
        )

    def validate_title(self, value):
        cleaned = value.strip()
        if len(cleaned) < 4:
            raise serializers.ValidationError('指南标题至少需要 4 个字符。')
        return cleaned

    def validate_issuing_agency(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError('发布单位不能为空。')
        return cleaned

    def validate_summary(self, value):
        cleaned = value.strip()
        if len(cleaned) < 10:
            raise serializers.ValidationError('指南摘要至少需要 10 个字符。')
        return cleaned

    def validate_status(self, value):
        normalized = ProjectGuide.LEGACY_STATUS_MAP.get(value, value)
        valid_statuses = {item[0] for item in ProjectGuide.STATUS_CHOICES}
        if normalized not in valid_statuses:
            raise serializers.ValidationError('指南状态不合法。')
        return normalized

    def validate_support_amount(self, value):
        return value.strip()

    def validate_eligibility_notes(self, value):
        return value.strip()

    def validate_lifecycle_note(self, value):
        return value.strip()

    def validate_target_keywords(self, value):
        return normalize_text_list(value)

    def validate_target_disciplines(self, value):
        return normalize_text_list(value)

    def validate_recommendation_tags(self, value):
        return normalize_text_list(value)

    def validate_rule_config(self, value):
        if not isinstance(value or {}, dict):
            raise serializers.ValidationError('规则细化配置必须为对象。')

        normalized = {}
        for key, raw in (value or {}).items():
            if key not in ALLOWED_RULE_CONFIG_KEYS:
                continue
            try:
                number = int(raw)
            except (TypeError, ValueError) as exc:
                raise serializers.ValidationError(f'{key} 必须是整数。') from exc
            normalized[key] = max(0, min(number, 20))
        return normalized

    def validate(self, attrs):
        scope = attrs.get('scope', getattr(self.instance, 'scope', ProjectGuide.SCOPE_GLOBAL))
        academy_id = attrs.get('academy', getattr(self.instance, 'academy', None))
        if scope == ProjectGuide.SCOPE_GLOBAL:
            attrs['academy'] = None
        elif scope == ProjectGuide.SCOPE_ACADEMY and not academy_id:
            raise serializers.ValidationError({'academy_id': '学院范围指南必须绑定归属学院。'})
        return attrs

    def get_created_by_name(self, obj):
        if not obj.created_by_id:
            return ''
        return obj.created_by.real_name or obj.created_by.username

    def get_academy_name(self, obj):
        if not obj.academy_id:
            return ''
        return obj.academy.name

    def get_status_timeline(self, obj):
        timeline = []
        if obj.published_at:
            timeline.append({'key': 'published', 'label': '已发布', 'time': obj.published_at})
        if obj.closed_at:
            timeline.append({'key': 'closed', 'label': '已关闭', 'time': obj.closed_at})
        if obj.archived_at:
            timeline.append({'key': 'archived', 'label': '已归档', 'time': obj.archived_at})
        return timeline


class ProjectGuideRecommendationSerializer(serializers.ModelSerializer):
    guide_level_display = serializers.CharField(source='get_guide_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    rule_profile_display = serializers.CharField(source='get_rule_profile_display', read_only=True)
    recommendation_score = serializers.IntegerField(read_only=True)
    recommendation_reasons = serializers.ListField(child=serializers.CharField(), read_only=True)
    matched_keywords = serializers.ListField(child=serializers.CharField(), read_only=True)
    matched_disciplines = serializers.ListField(child=serializers.CharField(), read_only=True)
    match_category_tags = serializers.ListField(child=serializers.CharField(), read_only=True)
    recommendation_labels = serializers.ListField(child=serializers.CharField(), read_only=True)
    explanation_dimensions = serializers.ListField(child=serializers.DictField(), read_only=True)
    priority_label = serializers.CharField(read_only=True)
    recommendation_summary = serializers.CharField(read_only=True)
    compare_score = serializers.IntegerField(read_only=True)
    compare_delta = serializers.IntegerField(read_only=True)
    comparison_summary = serializers.CharField(read_only=True)
    portrait_dimension_links = serializers.ListField(child=serializers.DictField(), read_only=True)
    supporting_records = serializers.ListField(child=serializers.DictField(), read_only=True)
    is_favorited = serializers.BooleanField(read_only=True)
    latest_feedback_signal = serializers.CharField(read_only=True)
    latest_feedback_label = serializers.CharField(read_only=True)
    latest_feedback_note = serializers.CharField(read_only=True)
    last_feedback_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = ProjectGuide
        fields = (
            'id',
            'title',
            'issuing_agency',
            'guide_level',
            'guide_level_display',
            'status',
            'status_display',
            'rule_profile',
            'rule_profile_display',
            'application_deadline',
            'summary',
            'target_keywords',
            'target_disciplines',
            'recommendation_tags',
            'support_amount',
            'eligibility_notes',
            'source_url',
            'recommendation_score',
            'recommendation_reasons',
            'matched_keywords',
            'matched_disciplines',
            'match_category_tags',
            'recommendation_labels',
            'explanation_dimensions',
            'portrait_dimension_links',
            'supporting_records',
            'priority_label',
            'recommendation_summary',
            'compare_score',
            'compare_delta',
            'comparison_summary',
            'is_favorited',
            'latest_feedback_signal',
            'latest_feedback_label',
            'latest_feedback_note',
            'last_feedback_at',
            'updated_at',
        )


class RecommendationTargetSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)
    compare_user_id = serializers.IntegerField(required=False)

    def validate_user_id(self, value):
        user_model = get_user_model()
        if not user_model.objects.filter(id=value).exists():
            raise serializers.ValidationError('目标教师不存在。')
        return value

    def validate_compare_user_id(self, value):
        user_model = get_user_model()
        if not user_model.objects.filter(id=value).exists():
            raise serializers.ValidationError('对比教师不存在。')
        return value


class ProjectGuideFavoriteSerializer(serializers.ModelSerializer):
    guide_id = serializers.SerializerMethodField()

    class Meta:
        model = ProjectGuideFavorite
        fields = ('guide_id', 'created_at', 'updated_at')
        read_only_fields = fields

    def get_guide_id(self, obj):
        return obj.guide_id


class ProjectGuideFavoriteToggleSerializer(serializers.Serializer):
    is_favorited = serializers.BooleanField()


class ProjectGuideFeedbackSerializer(serializers.Serializer):
    feedback_signal = serializers.ChoiceField(
        choices=[item[0] for item in ProjectGuideRecommendationRecord.FEEDBACK_SIGNALS if item[0]],
    )
    feedback_note = serializers.CharField(required=False, allow_blank=True, max_length=300)


class ProjectGuideRecommendationHistorySerializer(serializers.ModelSerializer):
    guide_id = serializers.SerializerMethodField()
    feedback_label = serializers.SerializerMethodField()
    requested_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectGuideRecommendationRecord
        fields = (
            'id',
            'batch_token',
            'guide_id',
            'guide_title_snapshot',
            'guide_status_snapshot',
            'rule_profile_snapshot',
            'recommendation_score',
            'priority_label',
            'recommendation_labels',
            'portrait_dimension_links',
            'is_favorited_snapshot',
            'feedback_signal',
            'feedback_label',
            'feedback_note',
            'generated_at',
            'last_feedback_at',
            'requested_by_name',
        )

    def get_guide_id(self, obj):
        return obj.guide_id

    def get_feedback_label(self, obj):
        return obj.get_feedback_signal_display() if obj.feedback_signal else ''

    def get_requested_by_name(self, obj):
        if not obj.requested_by_id:
            return ''
        return obj.requested_by.real_name or obj.requested_by.username
