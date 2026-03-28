from django.conf import settings
from django.db import models


class ProjectGuide(models.Model):
    GUIDE_LEVELS = (
        ('NATIONAL', '国家级'),
        ('PROVINCIAL', '省部级'),
        ('MUNICIPAL', '市厅级'),
        ('ENTERPRISE', '企业合作'),
    )

    STATUS_CHOICES = (
        ('DRAFT', '草稿'),
        ('OPEN', '申报中'),
        ('CLOSED', '已截止'),
        ('ARCHIVED', '已归档'),
    )

    RULE_PROFILES = (
        ('BALANCED', '均衡规则'),
        ('KEYWORD_FIRST', '主题优先'),
        ('DISCIPLINE_FIRST', '学科优先'),
        ('WINDOW_FIRST', '窗口优先'),
        ('ACTIVITY_FIRST', '活跃度优先'),
        ('PORTRAIT_FIRST', '画像联动优先'),
        ('FOUNDATION_FIRST', '申报基础优先'),
    )

    title = models.CharField(max_length=300, verbose_name='指南标题')
    issuing_agency = models.CharField(max_length=200, verbose_name='发布单位')
    guide_level = models.CharField(max_length=20, choices=GUIDE_LEVELS, default='PROVINCIAL', verbose_name='指南级别')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN', verbose_name='状态')
    application_deadline = models.DateField(blank=True, null=True, verbose_name='截止时间')
    summary = models.TextField(verbose_name='指南摘要')
    target_keywords = models.JSONField(default=list, blank=True, verbose_name='主题关键词')
    target_disciplines = models.JSONField(default=list, blank=True, verbose_name='面向学科/方向')
    recommendation_tags = models.JSONField(default=list, blank=True, verbose_name='推荐标签')
    rule_profile = models.CharField(
        max_length=20,
        choices=RULE_PROFILES,
        default='BALANCED',
        verbose_name='规则配置档位',
    )
    rule_config = models.JSONField(default=dict, blank=True, verbose_name='规则细化配置')
    support_amount = models.CharField(max_length=100, blank=True, verbose_name='资助强度')
    eligibility_notes = models.TextField(blank=True, verbose_name='申报要求')
    source_url = models.URLField(blank=True, verbose_name='来源链接')
    lifecycle_note = models.CharField(max_length=255, blank=True, verbose_name='生命周期说明')
    published_at = models.DateTimeField(blank=True, null=True, verbose_name='发布时间')
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name='关闭时间')
    archived_at = models.DateTimeField(blank=True, null=True, verbose_name='归档时间')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_project_guides',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('status', '-updated_at', '-created_at')
        verbose_name = '项目指南'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


class ProjectGuideFavorite(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_guide_favorites',
        verbose_name='教师',
    )
    guide = models.ForeignKey(
        ProjectGuide,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='项目指南',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('teacher', 'guide')
        ordering = ('-updated_at', '-created_at')
        verbose_name = '项目指南收藏'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.teacher_id}-{self.guide_id}'


class ProjectGuideRecommendationRecord(models.Model):
    FEEDBACK_SIGNALS = (
        ('', '未反馈'),
        ('INTERESTED', '感兴趣'),
        ('NOT_RELEVANT', '暂不相关'),
        ('PLAN_TO_APPLY', '计划申报'),
        ('APPLIED', '已申报'),
    )

    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_guide_recommendation_records',
        verbose_name='目标教师',
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='project_guide_recommendation_requests',
        verbose_name='触发账号',
    )
    guide = models.ForeignKey(
        ProjectGuide,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recommendation_records',
        verbose_name='项目指南',
    )
    batch_token = models.CharField(max_length=36, db_index=True, verbose_name='推荐批次标识')
    guide_title_snapshot = models.CharField(max_length=300, verbose_name='指南标题快照')
    guide_status_snapshot = models.CharField(max_length=20, blank=True, verbose_name='指南状态快照')
    rule_profile_snapshot = models.CharField(max_length=20, blank=True, verbose_name='规则档位快照')
    recommendation_score = models.PositiveIntegerField(default=0, verbose_name='推荐得分')
    priority_label = models.CharField(max_length=20, blank=True, verbose_name='关注等级')
    recommendation_reasons = models.JSONField(default=list, blank=True, verbose_name='推荐理由快照')
    explanation_dimensions = models.JSONField(default=list, blank=True, verbose_name='解释维度快照')
    recommendation_labels = models.JSONField(default=list, blank=True, verbose_name='推荐标签快照')
    matched_keywords = models.JSONField(default=list, blank=True, verbose_name='命中关键词快照')
    matched_disciplines = models.JSONField(default=list, blank=True, verbose_name='命中学科快照')
    portrait_dimension_links = models.JSONField(default=list, blank=True, verbose_name='画像联动快照')
    is_favorited_snapshot = models.BooleanField(default=False, verbose_name='生成时是否已收藏')
    feedback_signal = models.CharField(max_length=20, choices=FEEDBACK_SIGNALS, blank=True, verbose_name='反馈信号')
    feedback_note = models.TextField(blank=True, verbose_name='反馈备注')
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name='生成时间')
    last_feedback_at = models.DateTimeField(blank=True, null=True, verbose_name='最后反馈时间')

    class Meta:
        ordering = ('-generated_at', '-id')
        verbose_name = '项目指南推荐历史'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.teacher_id}-{self.guide_title_snapshot}-{self.generated_at:%Y%m%d%H%M%S}'
