from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers

import json

from evaluation_rules.models import EvaluationRuleItem

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
    RuleBasedAchievement,
    RuleBasedAchievementAttachment,
)
from .rule_entry_schema import build_rule_entry_form_schema, flatten_rule_entry_form_schema
from .rule_scoring import (
    apply_rule_snapshots,
    build_same_achievement_basis,
    build_same_achievement_key,
    build_score_preview,
    tokenize_keywords,
    validate_team_rule_constraints,
)


class CoAuthorDetailSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source='internal_teacher_id', read_only=True)

    class Meta:
        model = CoAuthor
        fields = ('id', 'name', 'author_rank', 'is_corresponding', 'organization', 'is_internal', 'internal_teacher', 'user_id')


class CoAuthorInputSerializer(serializers.Serializer):
    name = serializers.CharField()
    organization = serializers.CharField(required=False, allow_blank=True)
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
            organization = (item.get('organization') or '').strip()

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
                    organization = organization or (resolved_user.department or '')

            if not name:
                continue
            dedupe_key = (
                f'u:{resolved_user.id}'
                if resolved_user
                else f"n:{name}|o:{organization.lower()}"
            )
            if dedupe_key in seen_keys:
                continue
            is_corresponding = bool(item.get('is_corresponding', False))
            if author_rank is not None:
                if author_rank in used_ranks:
                    raise serializers.ValidationError('合作作者位次不能重复。')
                used_ranks.add(author_rank)
            seen_keys.add(dedupe_key)
            normalized.append(
                {
                    'name': name,
                    'organization': organization,
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
        return [
            {'name': name, 'organization': '', 'user_id': None, 'author_rank': None, 'is_corresponding': False}
            for name in coauthor_names
        ]

    def _replace_coauthors(self, paper, coauthor_records):
        paper.coauthors.all().delete()
        for item in coauthor_records:
            CoAuthor.objects.create(
                paper=paper,
                name=item.get('name', '').strip(),
                organization=(item.get('organization') or '').strip(),
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


class RuleBasedAchievementAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = RuleBasedAchievementAttachment
        fields = ('id', 'original_name', 'file', 'file_url', 'created_at')
        read_only_fields = fields

    def get_file_url(self, obj):
        request = self.context.get('request')
        if request is None:
            return obj.file.url if obj.file else ''
        return request.build_absolute_uri(obj.file.url) if obj.file else ''


class RuleBasedAchievementSerializer(serializers.ModelSerializer):
    UNIQUE_IDENTIFIER_MESSAGES = {
        'PAPER_BOOK': '请填写成果唯一识别信息，如 DOI、ISBN、检索号或刊号，不得使用简称。',
        'PROJECT': '请填写项目唯一识别信息，如立项编号、合同编号或任务书编号。',
        'AWARD': '请填写获奖成果唯一识别信息，如证书编号或通知文号。',
        'TRANSFORMATION': '请填写转化成果唯一识别信息，如专利号、标准号、合同号或证书编号。',
        'THINK_TANK': '请填写智库成果唯一识别信息，如批示编号、刊发编号或采纳编号。',
        'PLATFORM_TEAM': '请填写平台或团队唯一识别信息，如认定文号或正式编号。',
        'SCI_POP_AWARD': '请填写科普获奖唯一识别信息，如证书编号或通知文号。',
    }

    teacher_name = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_code = serializers.CharField(source='category.code', read_only=True)
    rule_item_title = serializers.CharField(source='rule_item.title', read_only=True)
    rule_item_code = serializers.CharField(source='rule_item.rule_code', read_only=True)
    score_preview = serializers.SerializerMethodField()
    same_achievement_key = serializers.SerializerMethodField()
    same_achievement_basis = serializers.SerializerMethodField()
    attachments = RuleBasedAchievementAttachmentSerializer(many=True, read_only=True)
    evidence_files = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = RuleBasedAchievement
        fields = (
            'id',
            'teacher',
            'teacher_name',
            'version',
            'category',
            'category_code',
            'category_name',
            'rule_item',
            'rule_item_code',
            'rule_item_title',
            'title',
            'external_reference',
            'date_acquired',
            'status',
            'status_label',
            'issuing_organization',
            'publication_name',
            'role_text',
            'author_rank',
            'is_corresponding_author',
            'is_representative',
            'school_unit_order',
            'amount_value',
            'amount_unit',
            'keywords_text',
            'coauthor_names',
            'team_identifier',
            'team_total_members',
            'team_allocated_score',
            'team_contribution_note',
            'evidence_note',
            'factual_payload',
            'provisional_score',
            'final_score',
            'score_detail',
            'score_preview',
            'same_achievement_key',
            'same_achievement_basis',
            'review_comment',
            'reviewed_by',
            'reviewed_at',
            'attachments',
            'evidence_files',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'teacher',
            'teacher_name',
            'version',
            'status',
            'status_label',
            'provisional_score',
            'final_score',
            'score_detail',
            'score_preview',
            'reviewed_by',
            'reviewed_at',
            'attachments',
            'created_at',
            'updated_at',
        )

    def get_teacher_name(self, obj):
        return obj.teacher.real_name or obj.teacher.username

    def get_status_label(self, obj):
        return obj.get_status_display()

    def get_score_preview(self, obj):
        return build_score_preview(
            rule_item=obj.rule_item,
            amount_value=obj.amount_value,
            team_allocated_score=obj.team_allocated_score,
            instance=obj,
        )

    def get_same_achievement_key(self, obj):
        return build_same_achievement_key(obj)

    def get_same_achievement_basis(self, obj):
        return build_same_achievement_basis(obj)

    def validate_title(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError('成果名称至少需要 2 个字符。')
        return cleaned

    def _normalize_factual_payload(self, raw_payload, base_payload=None):
        payload = dict(base_payload or {})
        if raw_payload is serializers.empty or raw_payload is None or raw_payload == '':
            return payload

        parsed_payload = raw_payload
        if isinstance(raw_payload, str):
            try:
                parsed_payload = json.loads(raw_payload)
            except json.JSONDecodeError as exc:
                raise serializers.ValidationError({'factual_payload': '扩展事实字段格式错误。'}) from exc

        if not isinstance(parsed_payload, dict):
            raise serializers.ValidationError({'factual_payload': '扩展事实字段必须是对象。'})

        for key, value in parsed_payload.items():
            if isinstance(value, str):
                payload[key] = value.strip()
            else:
                payload[key] = value
        return payload

    def _is_empty_entry_value(self, value) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip()
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) == 0
        return False

    def _normalize_root_fields(self, attrs):
        for field_name in (
            'external_reference',
            'issuing_organization',
            'publication_name',
            'role_text',
            'school_unit_order',
            'team_identifier',
            'team_contribution_note',
            'evidence_note',
        ):
            if field_name in attrs and isinstance(attrs[field_name], str):
                attrs[field_name] = attrs[field_name].strip()

        if 'coauthor_names' in attrs and isinstance(attrs['coauthor_names'], str):
            try:
                parsed_coauthors = json.loads(attrs['coauthor_names'])
                if isinstance(parsed_coauthors, list):
                    attrs['coauthor_names'] = parsed_coauthors
            except json.JSONDecodeError:
                attrs['coauthor_names'] = [item.strip() for item in attrs['coauthor_names'].split('，') if item.strip()]

        return attrs

    def _validate_form_schema(self, *, rule_item, attrs, instance):
        factual_payload = self._normalize_factual_payload(
            attrs.get('factual_payload', serializers.empty),
            base_payload=getattr(instance, 'factual_payload', {}) if instance else {},
        )
        schema_fields = flatten_rule_entry_form_schema(build_rule_entry_form_schema(rule_item))

        errors: dict[str, str] = {}
        factual_errors: list[str] = []
        for field in schema_fields:
            key = field.get('key')
            label = field.get('label') or key
            if field.get('storage') == 'root':
                value = attrs.get(key, getattr(instance, key, None) if instance else None)
            else:
                value = factual_payload.get(key)
            if field.get('required') and self._is_empty_entry_value(value):
                if field.get('storage') == 'root':
                    errors[key] = f'请填写{label}。'
                else:
                    factual_errors.append(f'请填写{label}。')

        if factual_errors:
            errors['factual_payload'] = '；'.join(factual_errors)
        if errors:
            raise serializers.ValidationError(errors)

        return factual_payload

    def _validate_unique_identifier_fields(self, *, category, attrs, instance):
        category_code = (getattr(category, 'code', '') or '').strip().upper()
        external_reference = attrs.get('external_reference', getattr(instance, 'external_reference', '') if instance else '')
        team_identifier = attrs.get('team_identifier', getattr(instance, 'team_identifier', '') if instance else '')

        errors: dict[str, str] = {}
        if category_code in self.UNIQUE_IDENTIFIER_MESSAGES and not self._is_empty_entry_value(external_reference):
            if len(str(external_reference).strip()) < 2:
                errors['external_reference'] = '成果唯一识别信息至少需要 2 个字符，并与正式材料保持一致。'

        if category_code == 'PLATFORM_TEAM':
            if self._is_empty_entry_value(team_identifier):
                errors['team_identifier'] = '请填写团队归并标识，同一平台或团队跨教师录入时必须保持一致。'
            elif len(str(team_identifier).strip()) < 2:
                errors['team_identifier'] = '团队归并标识至少需要 2 个字符，请填写正式且稳定的归并标识。'

        if errors:
            raise serializers.ValidationError(errors)

    def validate(self, attrs):
        request = self.context.get('request')
        instance = getattr(self, 'instance', None)
        rule_item = attrs.get('rule_item', getattr(instance, 'rule_item', None))
        category = attrs.get('category', getattr(instance, 'category', None))
        date_acquired = attrs.get('date_acquired', getattr(instance, 'date_acquired', None))

        if date_acquired and date_acquired > timezone.now().date():
            raise serializers.ValidationError({'date_acquired': '日期不能晚于今天。'})

        if rule_item is None:
            raise serializers.ValidationError({'rule_item': '请选择加分项。'})
        if category is None:
            raise serializers.ValidationError({'category': '请选择成果大类。'})
        if rule_item.category_ref_id != category.id:
            raise serializers.ValidationError({'rule_item': '所选加分项不属于当前成果大类。'})
        if rule_item.entry_policy == EvaluationRuleItem.ENTRY_FORBIDDEN:
            raise serializers.ValidationError({'rule_item': '当前规则条目不允许教师直接填报。'})

        attrs = self._normalize_root_fields(attrs)
        self._validate_unique_identifier_fields(category=category, attrs=attrs, instance=instance)

        if rule_item.requires_amount_input and attrs.get('amount_value', getattr(instance, 'amount_value', None)) in {None, ''}:
            raise serializers.ValidationError({'amount_value': '当前规则需要填写金额/数量计分基数。'})

        preview_errors = validate_team_rule_constraints(
            RuleBasedAchievement(
                teacher=request.user if request else getattr(instance, 'teacher', None),
                version=rule_item.version,
                category=category,
                rule_item=rule_item,
                title=attrs.get('title', getattr(instance, 'title', '')),
                external_reference=attrs.get('external_reference', getattr(instance, 'external_reference', '')),
                date_acquired=date_acquired,
                team_identifier=attrs.get('team_identifier', getattr(instance, 'team_identifier', '')),
                team_total_members=attrs.get('team_total_members', getattr(instance, 'team_total_members', None)),
                team_allocated_score=attrs.get('team_allocated_score', getattr(instance, 'team_allocated_score', None)),
            ),
            approval_phase=False,
        )
        if preview_errors:
            raise serializers.ValidationError({'team_identifier': '；'.join(preview_errors)})

        if 'keywords_text' in attrs:
            attrs['keywords_text'] = '，'.join(tokenize_keywords(attrs['keywords_text']))

        attrs['factual_payload'] = self._validate_form_schema(
            rule_item=rule_item,
            attrs=attrs,
            instance=instance,
        )
        attrs['version'] = rule_item.version
        return attrs

    def create(self, validated_data):
        evidence_files = validated_data.pop('evidence_files', [])
        instance = RuleBasedAchievement(**validated_data)
        apply_rule_snapshots(instance)
        instance.teacher = self.context['request'].user
        instance.status = 'PENDING_REVIEW'
        instance.save()
        self._save_attachments(instance, evidence_files)
        return instance

    def update(self, instance, validated_data):
        evidence_files = validated_data.pop('evidence_files', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        apply_rule_snapshots(instance)
        if instance.status in {'APPROVED', 'REJECTED'}:
            instance.status = 'PENDING_REVIEW'
            instance.review_comment = ''
            instance.reviewed_by = None
            instance.reviewed_at = None
            instance.final_score = 0
        instance.save()
        if evidence_files is not None:
            instance.attachments.all().delete()
            self._save_attachments(instance, evidence_files)
        return instance

    def _save_attachments(self, instance: RuleBasedAchievement, files):
        request = self.context.get('request')
        for file_obj in files or []:
            RuleBasedAchievementAttachment.objects.create(
                achievement=instance,
                file=file_obj,
                original_name=getattr(file_obj, 'name', ''),
                uploaded_by=request.user if request else None,
            )


class AchievementClaimRejectSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)

    def validate_reason(self, value):
        return value.strip()

