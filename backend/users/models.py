from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    自定义用户模型，教师和管理员共享同一套基础账户字段。
    """

    real_name = models.CharField(max_length=50, verbose_name="真实姓名")
    title = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="职称",
        help_text="如：教授、副教授、讲师",
    )
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name="所属院系")
    research_direction = models.JSONField(default=list, blank=True, verbose_name="研究方向标签")
    bio = models.TextField(blank=True, null=True, verbose_name="个人简介")
    avatar_url = models.URLField(blank=True, null=True, verbose_name="头像地址")
    contact_phone = models.CharField(max_length=30, blank=True, null=True, verbose_name="联系电话")
    contact_visibility = models.CharField(
        max_length=20,
        default="email_only",
        verbose_name="联系方式展示策略",
        help_text="控制个人中心公开资料卡如何展示联系方式。",
    )
    password_reset_required = models.BooleanField(
        default=False,
        verbose_name="需修改密码",
        help_text="管理员初始化或重置密码后，提醒用户登录后尽快修改密码。",
    )
    password_updated_at = models.DateTimeField(blank=True, null=True, verbose_name="密码更新时间")

    class Meta:
        verbose_name = "教师/用户"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.real_name if self.real_name else self.username


class UserNotification(models.Model):
    CATEGORY_PROJECT_GUIDE_PUSH = "PROJECT_GUIDE_PUSH"
    CATEGORY_ACHIEVEMENT_CLAIM = "ACHIEVEMENT_CLAIM"
    CATEGORY_CLAIM_REMINDER = "CLAIM_REMINDER"
    CATEGORY_PASSWORD_RESET_REQUEST = "PASSWORD_RESET_REQUEST"
    CATEGORY_CHOICES = (
        (CATEGORY_PROJECT_GUIDE_PUSH, "项目指南推送"),
        (CATEGORY_ACHIEVEMENT_CLAIM, "成果认领邀请"),
        (CATEGORY_CLAIM_REMINDER, "成果认领提醒"),
        (CATEGORY_PASSWORD_RESET_REQUEST, "密码重置申请"),
    )

    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name="接收人",
    )
    sender = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
        verbose_name="发送人",
    )
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, verbose_name="通知类型")
    title = models.CharField(max_length=200, verbose_name="通知标题")
    content = models.TextField(blank=True, verbose_name="通知内容")
    action_path = models.CharField(max_length=200, blank=True, verbose_name="跳转路径")
    action_query = models.JSONField(default=dict, blank=True, verbose_name="跳转参数")
    payload = models.JSONField(default=dict, blank=True, verbose_name="补充载荷")
    is_read = models.BooleanField(default=False, verbose_name="是否已读")
    read_at = models.DateTimeField(null=True, blank=True, verbose_name="已读时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ("is_read", "-created_at", "-id")
        indexes = [
            models.Index(fields=("recipient", "is_read")),
            models.Index(fields=("category", "created_at")),
        ]
        verbose_name = "用户通知"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.recipient_id}-{self.category}-{self.title}"
