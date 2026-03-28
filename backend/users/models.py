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
