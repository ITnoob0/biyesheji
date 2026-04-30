from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from .models import EvaluationRuleCategory, EvaluationRuleItem, EvaluationRuleVersion, FilingWorkflowStep


def _parse_score_text(score_text: str) -> dict:
    raw = (score_text or '').strip()
    if not raw:
        return {}

    try:
        return {
            'score_mode': EvaluationRuleItem.SCORE_MODE_FIXED,
            'base_score': Decimal(raw),
        }
    except (InvalidOperation, ValueError, ArithmeticError):
        for suffix, unit_label in (
            ('/万元', '万元'),
            ('/万字', '万字'),
            ('/辑', '辑'),
            ('/首', '首'),
        ):
            if raw.endswith(suffix):
                try:
                    return {
                        'score_mode': EvaluationRuleItem.SCORE_MODE_PER_AMOUNT,
                        'score_per_unit': Decimal(raw.removesuffix(suffix).strip()),
                        'score_unit_label': unit_label,
                        'requires_amount_input': True,
                    }
                except (InvalidOperation, ValueError, ArithmeticError):
                    return {}
        if '人工' in raw or '评议' in raw:
            return {
                'score_mode': EvaluationRuleItem.SCORE_MODE_MANUAL,
            }
        return {}


class EvaluationRuleVersionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = EvaluationRuleVersion
        fields = (
            'id',
            'code',
            'name',
            'source_document',
            'summary',
            'status',
            'status_display',
            'created_by',
            'created_by_name',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_by', 'created_by_name', 'created_at', 'updated_at')

    def get_created_by_name(self, obj):
        if not obj.created_by_id:
            return ''
        return obj.created_by.real_name or obj.created_by.username


class EvaluationRuleCategorySerializer(serializers.ModelSerializer):
    version_name = serializers.CharField(source='version.name', read_only=True)

    class Meta:
        model = EvaluationRuleCategory
        fields = (
            'id',
            'version',
            'version_name',
            'code',
            'name',
            'description',
            'dimension_key',
            'dimension_label',
            'entry_enabled',
            'include_in_total',
            'include_in_radar',
            'sort_order',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')


class EvaluationRuleItemSerializer(serializers.ModelSerializer):
    category_display = serializers.SerializerMethodField()
    discipline_display = serializers.CharField(source='get_discipline_display', read_only=True)
    entry_policy_display = serializers.CharField(source='get_entry_policy_display', read_only=True)
    score_mode_display = serializers.CharField(source='get_score_mode_display', read_only=True)
    multi_match_policy_display = serializers.CharField(source='get_multi_match_policy_display', read_only=True)
    version_name = serializers.CharField(source='version.name', read_only=True)
    category_name = serializers.CharField(source='category_ref.name', read_only=True)
    category_code = serializers.CharField(source='category_ref.code', read_only=True)
    category_dimension_key = serializers.CharField(source='category_ref.dimension_key', read_only=True)
    category_dimension_label = serializers.CharField(source='category_ref.dimension_label', read_only=True)

    class Meta:
        model = EvaluationRuleItem
        fields = (
            'id',
            'version',
            'version_name',
            'category_ref',
            'category_code',
            'category_name',
            'category_dimension_key',
            'category_dimension_label',
            'rule_code',
            'category',
            'category_display',
            'discipline',
            'discipline_display',
            'entry_policy',
            'entry_policy_display',
            'score_mode',
            'score_mode_display',
            'base_score',
            'score_per_unit',
            'score_unit_label',
            'requires_amount_input',
            'is_team_rule',
            'team_distribution_note',
            'team_max_member_ratio',
            'conflict_group',
            'multi_match_policy',
            'multi_match_policy_display',
            'entry_form_schema',
            'title',
            'description',
            'score_text',
            'note',
            'evidence_requirements',
            'include_in_total',
            'include_in_radar',
            'sort_order',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def get_category_display(self, obj):
        if obj.category_ref_id:
            return obj.category_ref.name
        return obj.category or ''

    def validate(self, attrs):
        instance = getattr(self, 'instance', None)
        category_ref = attrs.get('category_ref', getattr(instance, 'category_ref', None))
        entry_policy = attrs.get('entry_policy', getattr(instance, 'entry_policy', EvaluationRuleItem.ENTRY_REQUIRED))
        score_mode = attrs.get('score_mode', getattr(instance, 'score_mode', EvaluationRuleItem.SCORE_MODE_FIXED))
        score_text = attrs.get('score_text', getattr(instance, 'score_text', ''))

        if category_ref is not None:
            attrs['category'] = category_ref.code
            if 'include_in_total' not in attrs:
                attrs['include_in_total'] = category_ref.include_in_total
            if 'include_in_radar' not in attrs:
                attrs['include_in_radar'] = category_ref.include_in_radar

        if entry_policy == EvaluationRuleItem.ENTRY_FORBIDDEN:
            attrs['include_in_total'] = False
            attrs['include_in_radar'] = False

        parsed = _parse_score_text(score_text)
        if parsed and 'score_mode' not in attrs and instance is None:
            attrs.update({key: value for key, value in parsed.items() if key not in attrs})

        if score_mode == EvaluationRuleItem.SCORE_MODE_PER_AMOUNT and not (
            attrs.get('score_per_unit', getattr(instance, 'score_per_unit', None))
        ):
            raise serializers.ValidationError({'score_per_unit': '按金额/数量计分的规则必须配置每单位积分。'})

        if score_mode == EvaluationRuleItem.SCORE_MODE_FIXED and attrs.get('requires_amount_input'):
            raise serializers.ValidationError({'requires_amount_input': '固定积分规则不应要求金额/数量输入。'})

        if attrs.get('is_team_rule', getattr(instance, 'is_team_rule', False)):
            attrs.setdefault(
                'team_distribution_note',
                '平台、团队负责人按照成员贡献大小确定积分分配，计分人数不得超过总成员数的 1/3。',
            )

        return attrs


class FilingWorkflowStepSerializer(serializers.ModelSerializer):
    actor_display = serializers.CharField(source='get_actor_display', read_only=True)
    version_name = serializers.CharField(source='version.name', read_only=True)

    class Meta:
        model = FilingWorkflowStep
        fields = (
            'id',
            'version',
            'version_name',
            'step_order',
            'actor',
            'actor_display',
            'title',
            'description',
            'material_requirements',
            'operation_note',
            'is_required',
            'is_active',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
