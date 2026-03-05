from django.db import models
from django.conf import settings

class Paper(models.Model):
    """
    科研论文模型
    """
    title = models.CharField(max_length=255, verbose_name="论文标题")
    publish_date = models.DateField(verbose_name="发表日期")
    journal_name = models.CharField(max_length=200, verbose_name="发表期刊/会议名称")
    
    # 使用 ManyToMany 关联系统内的教师，代表共同作者
    authors = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='papers', verbose_name="系统内作者")
    
    # 外部作者（非本系统用户）用字符串存储即可
    external_authors = models.CharField(max_length=255, blank=True, null=True, verbose_name="外部作者", help_text="逗号分隔")
    
    abstract = models.TextField(blank=True, null=True, verbose_name="摘要")
    keywords = models.JSONField(default=list, blank=True, verbose_name="提取的关键词")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="录入时间")

    class Meta:
        verbose_name = "科研论文"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title