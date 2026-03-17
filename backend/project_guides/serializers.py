from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import ProjectGuide


def normalize_text_list(values):
    normalized = []
    for value in values or []:
        item = str(value).strip()
        if item and item not in normalized:
            normalized.append(item)
    return normalized[:20]


class ProjectGuideSerializer(serializers.ModelSerializer):
    guide_level_display = serializers.CharField(source='get_guide_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()

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
            'application_deadline',
            'summary',
            'target_keywords',
            'target_disciplines',
            'support_amount',
            'eligibility_notes',
            'source_url',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_by', 'created_by_name', 'created_at', 'updated_at')

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

    def validate_support_amount(self, value):
        return value.strip()

    def validate_eligibility_notes(self, value):
        return value.strip()

    def validate_target_keywords(self, value):
        return normalize_text_list(value)

    def validate_target_disciplines(self, value):
        return normalize_text_list(value)

    def get_created_by_name(self, obj):
        if not obj.created_by_id:
            return ''
        return obj.created_by.real_name or obj.created_by.username


class ProjectGuideRecommendationSerializer(serializers.ModelSerializer):
    guide_level_display = serializers.CharField(source='get_guide_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    recommendation_score = serializers.IntegerField(read_only=True)
    recommendation_reasons = serializers.ListField(child=serializers.CharField(), read_only=True)
    matched_keywords = serializers.ListField(child=serializers.CharField(), read_only=True)
    matched_disciplines = serializers.ListField(child=serializers.CharField(), read_only=True)

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
            'application_deadline',
            'summary',
            'target_keywords',
            'target_disciplines',
            'support_amount',
            'eligibility_notes',
            'source_url',
            'recommendation_score',
            'recommendation_reasons',
            'matched_keywords',
            'matched_disciplines',
        )


class RecommendationTargetSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False)

    def validate_user_id(self, value):
        user_model = get_user_model()
        if not user_model.objects.filter(id=value).exists():
            raise serializers.ValidationError('目标教师不存在。')
        return value
