from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

from .governance import build_paper_metadata_alert_details, build_paper_metadata_alerts
from .models import (
    AcademicService,
    AchievementClaim,
    AchievementOperationLog,
    CoAuthor,
    IntellectualProperty,
    Paper,
    PaperKeyword,
    PaperOperationLog,
    Project,
    TeachingAchievement,
)


class CoAuthorDetailSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='internal_teacher_id', read_only=True)

    class Meta:
        model = CoAuthor
        fields = ('id', 'name', 'author_rank', 'is_corresponding', 'organization', 'is_internal', 'internal_teacher', 'user_id')


class CoAuthorInputSerializer(serializers.Serializer):
    name = serializers.CharField()
    user_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    order = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    author_rank = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    is_corresponding = serializers.BooleanField(required=False)


class TeacherOwnedAchievementSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()

    read_only_fields = ('id', 'teacher', 'teacher_name', 'created_at', 'status')

    def validate_title(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError('标题至少需要 2 个字符。')
        return cleaned

    def validate(self, attrs):
        date_acquired = attrs.get('date_acquired')
        if date_acquired and date_acquired > timezone.now().date():
            raise serializers.ValidationError({'date_acquired': '日期不能晚于今天。'})
        return attrs

    def get_teacher_name(self, obj):
        return obj.teacher.real_name or obj.teacher.username

    def get_status_label(self, obj):
        return obj.get_status_display() if hasattr(obj, 'get_status_display') else ''

    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and request.user.id == instance.teacher_id and instance.status in {'APPROVED', 'REJECTED'}:
            validated_data['status'] = 'PENDING_REVIEW'
        return super().update(instance, validated_data)


class PaperSerializer(TeacherOwnedAchievementSerializer):
    coauthors = serializers.ListField(
        child=serializers.CharField(),
        write_only=True,
        required=False,
        default=list,
    )
    coauthor_records = CoAuthorInputSerializer(many=True, write_only=True, required=False)
    coauthor_details = CoAuthorDetailSerializer(source='coauthors', many=True, read_only=True)
    keywords = serializers.SerializerMethodField()
    paper_type_display = serializers.CharField(source='get_paper_type_display', read_only=True)
    publication_year = serializers.SerializerMethodField()
    metadata_alerts = serializers.SerializerMethodField()
    metadata_alert_details = serializers.SerializerMethodField()

    class Meta:
        model = Paper
        fields = (
            'id',
            'teacher',
            'teacher_name',
            'title',
            'abstract',
            'date_acquired',
            'paper_type',
            'paper_type_display',
            'journal_name',
            'journal_level',
            'published_volume',
            'published_issue',
            'pages',
            'source_url',
            'citation_count',
            'is_first_author',
            'is_corresponding_author',
            'is_representative',
            'doi',
            'publication_year',
            'created_at',
            'status',
            'status_label',
            'coauthors',
            'coauthor_records',
            'coauthor_details',
            'keywords',
            'metadata_alerts',
            'metadata_alert_details',
        )
        read_only_fields = TeacherOwnedAchievementSerializer.read_only_fields + (
            'coauthor_details',
            'keywords',
            'publication_year',
            'metadata_alerts',
            'metadata_alert_details',
        )

    def validate_journal_name(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError('期刊或会议名称不能为空。')
        return cleaned

    def validate_citation_count(self, value):
        if value < 0:
            raise serializers.ValidationError('引用次数不能为负数。')
        return value

    def validate_coauthors(self, value):
        normalized = []
        for item in value:
            name = item.strip()
            if name and name not in normalized:
                normalized.append(name)
        return normalized[:20]

    def validate_coauthor_records(self, value):
        normalized: list[dict] = []
        seen_keys: set[str] = set()
        used_ranks: set[int] = set()
        user_model = get_user_model()
        for item in value:
            user_id = item.get('user_id')
            order = item.get('order')
            author_rank = item.get('author_rank')
            if order is not None:
                author_rank = order
            name = (item.get('name') or '').strip()

            resolved_user = None
            if user_id:
                resolved_user = (
                    user_model.objects.filter(
                        id=user_id,
                        is_active=True,
                        is_staff=False,
                        is_superuser=False,
                    )
                    .only('id', 'real_name', 'username')
                    .first()
                )
                if resolved_user:
                    name = name or (resolved_user.real_name or resolved_user.username)

            if not name:
                continue
            dedupe_key = f'u:{resolved_user.id}' if resolved_user else f'n:{name}'
            if dedupe_key in seen_keys:
                continue
            is_corresponding = bool(item.get('is_corresponding', False))
            if author_rank is not None:
                if author_rank in used_ranks:
                    raise serializers.ValidationError('合作者位次不能重复。')
                used_ranks.add(author_rank)
            seen_keys.add(dedupe_key)
            normalized.append(
                {
                    'name': name,
                    'user_id': resolved_user.id if resolved_user else None,
                    'author_rank': author_rank,
                    'is_corresponding': is_corresponding,
                }
            )
        return normalized[:20]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get('request')
        doi = (attrs.get('doi') or '').strip().lower()

        if doi and request and request.user and request.user.is_authenticated:
            existing = Paper.objects.filter(teacher=request.user, doi=doi)
            if self.instance:
                existing = existing.exclude(pk=self.instance.pk)
            if existing.exists():
                raise serializers.ValidationError({'doi': '当前账号下已存在相同 DOI 的论文。'})
            attrs['doi'] = doi

        for field in ('journal_level', 'published_volume', 'published_issue', 'pages', 'source_url'):
            if field in attrs and attrs[field]:
                attrs[field] = attrs[field].strip()

        return attrs

    def create(self, validated_data):
        coauthor_names = validated_data.pop('coauthors', [])
        coauthor_records = validated_data.pop('coauthor_records', None)
        paper = Paper.objects.create(**validated_data)
        self._replace_coauthors(paper, self._resolve_coauthor_records(coauthor_names, coauthor_records))
        return paper

    def update(self, instance, validated_data):
        coauthor_names = validated_data.pop('coauthors', None)
        coauthor_records = validated_data.pop('coauthor_records', None)
        if instance.status in {'APPROVED', 'REJECTED'}:
            validated_data['status'] = 'PENDING_REVIEW'
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if coauthor_names is not None or coauthor_records is not None:
            self._replace_coauthors(
                instance,
                self._resolve_coauthor_records(coauthor_names or [], coauthor_records),
            )
        return instance

    def get_keywords(self, obj):
        keyword_relations = PaperKeyword.objects.filter(paper=obj).select_related('keyword')
        return [relation.keyword.name for relation in keyword_relations]

    def get_publication_year(self, obj):
        return obj.date_acquired.year if obj.date_acquired else None

    def get_metadata_alerts(self, obj):
        return build_paper_metadata_alerts(obj)

    def get_metadata_alert_details(self, obj):
        return build_paper_metadata_alert_details(obj)

    def _resolve_coauthor_records(self, coauthor_names: list[str], coauthor_records: list[dict] | None):
        if coauthor_records:
            return coauthor_records
        return [{'name': name, 'user_id': None, 'author_rank': None, 'is_corresponding': False} for name in coauthor_names]

    def _replace_coauthors(self, paper, coauthor_records):
        paper.coauthors.all().delete()
        for item in coauthor_records:
            CoAuthor.objects.create(
                paper=paper,
                name=item.get('name', '').strip(),
                internal_teacher_id=item.get('user_id'),
                author_rank=item.get('author_rank'),
                is_corresponding=bool(item.get('is_corresponding', False)),
                is_internal=bool(item.get('user_id')),
            )


class ProjectSerializer(TeacherOwnedAchievementSerializer):
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = Project
        fields = (
            'id',
            'teacher',
            'teacher_name',
            'title',
            'date_acquired',
            'status',
            'status_label',
            'level',
            'level_display',
            'role',
            'role_display',
            'funding_amount',
            'project_status',
            'created_at',
        )
        read_only_fields = TeacherOwnedAchievementSerializer.read_only_fields + ('level_display', 'role_display')

    def to_internal_value(self, data):
        mutable_data = data.copy()
        raw_status = mutable_data.get('status')
        if raw_status and raw_status not in {'DRAFT', 'PENDING_REVIEW', 'APPROVED', 'REJECTED'} and not mutable_data.get('project_status'):
            mutable_data['project_status'] = raw_status
            mutable_data.pop('status', None)
        return super().to_internal_value(mutable_data)

    def validate_funding_amount(self, value):
        if value < 0:
            raise serializers.ValidationError('项目经费不能为负数。')
        return value


class IntellectualPropertySerializer(TeacherOwnedAchievementSerializer):
    ip_type_display = serializers.CharField(source='get_ip_type_display', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = IntellectualProperty
        fields = (
            'id',
            'teacher',
            'teacher_name',
            'title',
            'date_acquired',
            'status',
            'status_label',
            'ip_type',
            'ip_type_display',
            'role',
            'role_display',
            'registration_number',
            'is_transformed',
            'created_at',
        )
        read_only_fields = TeacherOwnedAchievementSerializer.read_only_fields + ('ip_type_display', 'role_display')

    def validate_registration_number(self, value):
        cleaned = value.strip()
        if len(cleaned) < 3:
            raise serializers.ValidationError('登记号不能为空。')
        return cleaned


class TeachingAchievementSerializer(TeacherOwnedAchievementSerializer):
    achievement_type_display = serializers.CharField(source='get_achievement_type_display', read_only=True)
    role_display = serializers.SerializerMethodField()

    class Meta:
        model = TeachingAchievement
        fields = (
            'id',
            'teacher',
            'teacher_name',
            'title',
            'date_acquired',
            'status',
            'status_label',
            'achievement_type',
            'achievement_type_display',
            'role',
            'role_display',
            'level',
            'created_at',
        )
        read_only_fields = TeacherOwnedAchievementSerializer.read_only_fields + ('achievement_type_display', 'role_display')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        achievement_type = attrs.get('achievement_type')
        if achievement_type is None and self.instance is not None:
            achievement_type = self.instance.achievement_type

        if achievement_type in {'COMPETITION', 'THESIS'}:
            attrs['role'] = 'PI'

        return attrs

    def get_role_display(self, obj):
        if obj.achievement_type in {'COMPETITION', 'THESIS'}:
            return '指导教师'
        return obj.get_role_display()


class AcademicServiceSerializer(TeacherOwnedAchievementSerializer):
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)

    class Meta:
        model = AcademicService
        fields = (
            'id',
            'teacher',
            'teacher_name',
            'title',
            'date_acquired',
            'status',
            'status_label',
            'service_type',
            'service_type_display',
            'organization',
            'created_at',
        )
        read_only_fields = TeacherOwnedAchievementSerializer.read_only_fields + ('service_type_display',)

    def validate_organization(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError('服务机构不能为空。')
        return cleaned


class PaperOperationLogSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source='get_action_display', read_only=True)
    source_label = serializers.CharField(source='get_source_display', read_only=True)

    class Meta:
        model = PaperOperationLog
        fields = (
            'id',
            'paper',
            'action',
            'action_label',
            'source',
            'source_label',
            'summary',
            'changed_fields',
            'metadata_flags',
            'paper_title_snapshot',
            'paper_doi_snapshot',
            'created_at',
        )


class AchievementOperationLogSerializer(serializers.ModelSerializer):
    action_label = serializers.CharField(source='get_action_display', read_only=True)
    source_label = serializers.CharField(source='get_source_display', read_only=True)
    achievement_type_label = serializers.CharField(source='get_achievement_type_display', read_only=True)
    operator_name = serializers.SerializerMethodField()

    def get_operator_name(self, obj):
        if not obj.operator:
            return ''
        return obj.operator.real_name or obj.operator.username

    class Meta:
        model = AchievementOperationLog
        fields = (
            'id',
            'achievement_type',
            'achievement_type_label',
            'achievement_id',
            'action',
            'action_label',
            'source',
            'source_label',
            'operator',
            'operator_name',
            'summary',
            'changed_fields',
            'change_details',
            'title_snapshot',
            'detail_snapshot',
            'snapshot_payload',
            'review_comment',
            'created_at',
        )


class PaperRepresentativeBatchSerializer(serializers.Serializer):
    paper_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
    is_representative = serializers.BooleanField()


class PaperCleanupApplySerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('normalize_text_fields', '标准化 DOI/链接/卷期页'),
    )

    paper_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=False)
    action = serializers.ChoiceField(choices=ACTION_CHOICES)


class AchievementReviewActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)

    def validate_reason(self, value):
        return value.strip()


class AchievementRejectSerializer(AchievementReviewActionSerializer):
    reason = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)


class AchievementClaimSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    achievement_id = serializers.IntegerField(source='achievement.id', read_only=True)
    achievement_title = serializers.CharField(source='achievement.title', read_only=True)
    achievement_abstract = serializers.CharField(source='achievement.abstract', read_only=True)
    achievement_date_acquired = serializers.DateField(source='achievement.date_acquired', read_only=True)
    achievement_journal = serializers.CharField(source='achievement.journal_name', read_only=True)
    achievement_status = serializers.CharField(source='achievement.status', read_only=True)
    initiator_name = serializers.SerializerMethodField()
    target_user_name = serializers.SerializerMethodField()
    pending_days = serializers.SerializerMethodField()
    coauthor_name = serializers.SerializerMethodField()
    proposed_order = serializers.IntegerField(source='proposed_author_rank', read_only=True)
    actual_order = serializers.IntegerField(source='confirmed_author_rank', read_only=True)
    actual_is_corresponding = serializers.BooleanField(source='confirmed_is_corresponding', read_only=True)

    def get_initiator_name(self, obj):
        return obj.initiator.real_name or obj.initiator.username

    def get_target_user_name(self, obj):
        return obj.target_user.real_name or obj.target_user.username

    def get_pending_days(self, obj):
        delta = timezone.now() - obj.created_at
        return max(delta.days, 0)

    def get_coauthor_name(self, obj):
        if obj.coauthor_id:
            return obj.coauthor.name
        return ''

    class Meta:
        model = AchievementClaim
        fields = (
            'id',
            'achievement',
            'achievement_id',
            'achievement_title',
            'achievement_abstract',
            'achievement_date_acquired',
            'achievement_journal',
            'achievement_status',
            'initiator',
            'initiator_name',
            'target_user',
            'target_user_name',
            'status',
            'status_label',
            'coauthor',
            'coauthor_name',
            'proposed_order',
            'proposed_author_rank',
            'proposed_is_corresponding',
            'actual_order',
            'confirmed_author_rank',
            'actual_is_corresponding',
            'confirmed_is_corresponding',
            'confirmation_note',
            'rank_confirmed_at',
            'pending_days',
            'created_at',
        )
        read_only_fields = fields


class AchievementClaimAcceptSerializer(serializers.Serializer):
    actual_order = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    actual_is_corresponding = serializers.BooleanField(required=False)
    confirmed_author_rank = serializers.IntegerField(required=False, min_value=1, allow_null=True)
    confirmed_is_corresponding = serializers.BooleanField(required=False)
    confirmation_note = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)

    def validate_confirmation_note(self, value):
        return value.strip()


class AchievementClaimRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)

    def validate_reason(self, value):
        return value.strip()
