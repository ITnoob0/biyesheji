from __future__ import annotations

from django.conf import settings
from django.db import models


class EvaluationRuleVersion(models.Model):
    STATUS_DRAFT = 'DRAFT'
    STATUS_ACTIVE = 'ACTIVE'
    STATUS_ARCHIVED = 'ARCHIVED'
    STATUS_CHOICES = (
        (STATUS_DRAFT, '草稿'),
        (STATUS_ACTIVE, '启用'),
        (STATUS_ARCHIVED, '归档'),
    )

    code = models.CharField(max_length=80, unique=True, verbose_name='版本编码')
    name = models.CharField(max_length=200, verbose_name='版本名称')
    source_document = models.CharField(max_length=255, blank=True, verbose_name='来源文件')
    summary = models.TextField(blank=True, verbose_name='版本说明')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, verbose_name='状态')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='created_evaluation_rule_versions',
        null=True,
        blank=True,
        verbose_name='创建人',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        ordering = ('-updated_at', '-created_at')
        verbose_name = '评价规则版本'
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return self.name


class EvaluationRuleCategory(models.Model):
    version = models.ForeignKey(
        EvaluationRuleVersion,
        on_delete=models.CASCADE,
        related_name='categories',
        verbose_name='所属版本',
    )
    code = models.CharField(max_length=80, verbose_name='分类编码')
    name = models.CharField(max_length=120, verbose_name='分类名称')
    description = models.TextField(blank=True, verbose_name='分类说明')
    dimension_key = models.CharField(max_length=80, blank=True, verbose_name='画像维度键')
    dimension_label = models.CharField(max_length=120, blank=True, verbose_name='画像维度名称')
    entry_enabled = models.BooleanField(default=True, verbose_name='是否允许教师填报')
    include_in_total = models.BooleanField(default=True, verbose_name='是否参与总分')
    include_in_radar = models.BooleanField(default=True, verbose_name='是否进入能力雷达')
    sort_order = models.PositiveIntegerField(default=100, verbose_name='排序值')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        ordering = ('sort_order', 'id')
        constraints = [
            models.UniqueConstraint(fields=('version', 'code'), name='uniq_rule_category_version_code'),
        ]
        indexes = [
            models.Index(fields=('version', 'is_active')),
            models.Index(fields=('version', 'sort_order')),
        ]
        verbose_name = '评价规则分类'
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return self.name


class EvaluationRuleItem(models.Model):
    DISCIPLINE_NATURAL = 'NATURAL'
    DISCIPLINE_HUMANITIES = 'HUMANITIES'
    DISCIPLINE_GENERAL = 'GENERAL'
    DISCIPLINE_CHOICES = (
        (DISCIPLINE_NATURAL, '自然科学'),
        (DISCIPLINE_HUMANITIES, '人文社科'),
        (DISCIPLINE_GENERAL, '通用'),
    )

    ENTRY_REQUIRED = 'REQUIRED'
    ENTRY_FORBIDDEN = 'FORBIDDEN'
    ENTRY_POLICY_CHOICES = (
        (ENTRY_REQUIRED, '纳入填报'),
        (ENTRY_FORBIDDEN, '不允许填报'),
    )

    SCORE_MODE_FIXED = 'FIXED'
    SCORE_MODE_PER_AMOUNT = 'PER_AMOUNT'
    SCORE_MODE_MANUAL = 'MANUAL'
    SCORE_MODE_CHOICES = (
        (SCORE_MODE_FIXED, '固定积分'),
        (SCORE_MODE_PER_AMOUNT, '按金额/数量积分'),
        (SCORE_MODE_MANUAL, '人工认定'),
    )

    MULTI_MATCH_EXCLUSIVE_HIGHER = 'EXCLUSIVE_HIGHER'
    MULTI_MATCH_STACKABLE = 'STACKABLE'
    MULTI_MATCH_MANUAL_REVIEW = 'MANUAL_REVIEW'
    MULTI_MATCH_POLICY_CHOICES = (
        (MULTI_MATCH_EXCLUSIVE_HIGHER, '命中多项时取高'),
        (MULTI_MATCH_STACKABLE, '允许叠加'),
        (MULTI_MATCH_MANUAL_REVIEW, '需管理员确认'),
    )

    version = models.ForeignKey(
        EvaluationRuleVersion,
        on_delete=models.CASCADE,
        related_name='rule_items',
        verbose_name='所属版本',
    )
    category_ref = models.ForeignKey(
        EvaluationRuleCategory,
        on_delete=models.SET_NULL,
        related_name='items',
        null=True,
        blank=True,
        verbose_name='所属分类',
    )
    rule_code = models.CharField(max_length=80, blank=True, verbose_name='规则编码')
    category = models.CharField(max_length=50, blank=True, default='', verbose_name='分类编码快照')
    discipline = models.CharField(max_length=20, choices=DISCIPLINE_CHOICES, default=DISCIPLINE_GENERAL, verbose_name='学科归属')
    entry_policy = models.CharField(
        max_length=20,
        choices=ENTRY_POLICY_CHOICES,
        default=ENTRY_REQUIRED,
        verbose_name='填报策略',
    )
    score_mode = models.CharField(max_length=20, choices=SCORE_MODE_CHOICES, default=SCORE_MODE_FIXED, verbose_name='计分方式')
    base_score = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name='基础积分')
    score_per_unit = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True, verbose_name='每单位积分')
    score_unit_label = models.CharField(max_length=40, blank=True, verbose_name='计分单位')
    requires_amount_input = models.BooleanField(default=False, verbose_name='是否需要金额/数量')
    is_team_rule = models.BooleanField(default=False, verbose_name='是否团队分配规则')
    team_distribution_note = models.TextField(blank=True, verbose_name='团队积分说明')
    team_max_member_ratio = models.DecimalField(max_digits=4, decimal_places=3, default=0.333, verbose_name='团队积分人数上限比例')
    conflict_group = models.CharField(max_length=80, blank=True, verbose_name='互斥组')
    multi_match_policy = models.CharField(
        max_length=24,
        choices=MULTI_MATCH_POLICY_CHOICES,
        default=MULTI_MATCH_EXCLUSIVE_HIGHER,
        verbose_name='多规则命中处理',
    )
    entry_form_schema = models.JSONField(default=list, blank=True, verbose_name='录入字段配置')
    title = models.CharField(max_length=255, verbose_name='规则名称')
    description = models.TextField(blank=True, verbose_name='规则说明')
    score_text = models.CharField(max_length=120, blank=True, verbose_name='积分展示')
    note = models.TextField(blank=True, verbose_name='备注')
    evidence_requirements = models.TextField(blank=True, verbose_name='佐证要求')
    include_in_total = models.BooleanField(default=True, verbose_name='是否参与总分')
    include_in_radar = models.BooleanField(default=True, verbose_name='是否进入能力雷达')
    sort_order = models.PositiveIntegerField(default=100, verbose_name='排序值')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        ordering = ('sort_order', 'id')
        indexes = [
            models.Index(fields=('version', 'category_ref', 'discipline')),
            models.Index(fields=('version', 'category', 'discipline')),
            models.Index(fields=('version', 'entry_policy', 'is_active')),
        ]
        verbose_name = '评价规则条目'
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        category_name = self.category_ref.name if self.category_ref_id else self.category or '未分类'
        return f'{category_name} / {self.title}'


class FilingWorkflowStep(models.Model):
    ACTOR_TEACHER = 'TEACHER'
    ACTOR_COLLEGE_ADMIN = 'COLLEGE_ADMIN'
    ACTOR_SYSTEM_ADMIN = 'SYSTEM_ADMIN'
    ACTOR_SYSTEM = 'SYSTEM'
    ACTOR_CHOICES = (
        (ACTOR_TEACHER, '教师'),
        (ACTOR_COLLEGE_ADMIN, '学院管理员'),
        (ACTOR_SYSTEM_ADMIN, '系统管理员'),
        (ACTOR_SYSTEM, '系统'),
    )

    version = models.ForeignKey(
        EvaluationRuleVersion,
        on_delete=models.CASCADE,
        related_name='workflow_steps',
        verbose_name='所属版本',
    )
    step_order = models.PositiveIntegerField(default=10, verbose_name='步骤顺序')
    actor = models.CharField(max_length=20, choices=ACTOR_CHOICES, default=ACTOR_TEACHER, verbose_name='执行角色')
    title = models.CharField(max_length=200, verbose_name='步骤名称')
    description = models.TextField(verbose_name='步骤说明')
    material_requirements = models.TextField(blank=True, verbose_name='材料要求')
    operation_note = models.TextField(blank=True, verbose_name='操作提示')
    is_required = models.BooleanField(default=True, verbose_name='是否必经步骤')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        ordering = ('step_order', 'id')
        indexes = [
            models.Index(fields=('version', 'step_order')),
        ]
        verbose_name = '填报流程步骤'
        verbose_name_plural = verbose_name

    def __str__(self) -> str:
        return f'{self.step_order}. {self.title}'
