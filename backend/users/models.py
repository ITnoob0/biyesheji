from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    """
    自定义用户模型 (代表系统中的教师/科研人员)
    """
    real_name = models.CharField(max_length=50, verbose_name="真实姓名")
    title = models.CharField(max_length=50, blank=True, null=True, verbose_name="职称", help_text="如：教授、副教授、讲师")
    department = models.CharField(max_length=100, blank=True, null=True, verbose_name="所属院系")
    research_direction = models.JSONField(default=list, blank=True, verbose_name="研究方向标签")
    bio = models.TextField(blank=True, null=True, verbose_name="个人简介")
    
    class Meta:
        verbose_name = "教师/用户"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.real_name if self.real_name else self.username