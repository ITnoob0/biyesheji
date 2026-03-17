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
    )

    title = models.CharField(max_length=300, verbose_name='指南标题')
    issuing_agency = models.CharField(max_length=200, verbose_name='发布单位')
    guide_level = models.CharField(max_length=20, choices=GUIDE_LEVELS, default='PROVINCIAL', verbose_name='指南级别')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='OPEN', verbose_name='状态')
    application_deadline = models.DateField(blank=True, null=True, verbose_name='截止时间')
    summary = models.TextField(verbose_name='指南摘要')
    target_keywords = models.JSONField(default=list, blank=True, verbose_name='主题关键词')
    target_disciplines = models.JSONField(default=list, blank=True, verbose_name='面向学科/方向')
    support_amount = models.CharField(max_length=100, blank=True, verbose_name='资助强度')
    eligibility_notes = models.TextField(blank=True, verbose_name='申报要求')
    source_url = models.URLField(blank=True, verbose_name='来源链接')
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
