from django.contrib import admin

from .models import EvaluationRuleCategory, EvaluationRuleItem, EvaluationRuleVersion, FilingWorkflowStep


@admin.register(EvaluationRuleVersion)
class EvaluationRuleVersionAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'status', 'updated_at')
    list_filter = ('status',)
    search_fields = ('name', 'code', 'source_document')


@admin.register(EvaluationRuleCategory)
class EvaluationRuleCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'version', 'dimension_label', 'entry_enabled', 'is_active', 'sort_order')
    list_filter = ('version', 'entry_enabled', 'include_in_total', 'include_in_radar', 'is_active')
    search_fields = ('name', 'code', 'description', 'dimension_label')
    ordering = ('sort_order', 'id')


@admin.register(EvaluationRuleItem)
class EvaluationRuleItemAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'version',
        'category_ref',
        'discipline',
        'score_mode',
        'entry_policy',
        'score_text',
        'sort_order',
        'is_active',
    )
    list_filter = ('version', 'category_ref', 'discipline', 'score_mode', 'entry_policy', 'is_active')
    search_fields = ('title', 'rule_code', 'description', 'score_text', 'conflict_group')
    ordering = ('sort_order', 'id')


@admin.register(FilingWorkflowStep)
class FilingWorkflowStepAdmin(admin.ModelAdmin):
    list_display = ('title', 'version', 'step_order', 'actor', 'is_required', 'is_active')
    list_filter = ('version', 'actor', 'is_required', 'is_active')
    search_fields = ('title', 'description', 'material_requirements', 'operation_note')
    ordering = ('step_order', 'id')
