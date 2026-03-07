# backend/achievements/models.py
from django.db import models
from django.conf import settings
# 导入你写好的 AI 工具类
from ai_assistant.utils import AcademicAI 

class Paper(models.Model):
    """
    科研论文模型
    """
    title = models.CharField(max_length=255, verbose_name="论文标题")
    publish_date = models.DateField(verbose_name="发表日期")
    journal_name = models.CharField(max_length=200, verbose_name="发表期刊/会议名称")
    
    # 使用 ManyToMany 关联系统内的教师
    authors = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='papers', verbose_name="系统内作者")
    
    # 外部作者
    external_authors = models.CharField(max_length=255, blank=True, null=True, verbose_name="外部作者", help_text="逗号分隔")
    
    abstract = models.TextField(blank=True, null=True, verbose_name="摘要")
    # 存储 AI 提取的关键词
    keywords = models.JSONField(default=list, blank=True, verbose_name="提取的关键词")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="录入时间")

    # 重写 save 方法，实现无论是 Admin 还是 API 保存时都能触发 AI
    def save(self, *args, **kwargs):
        # 如果关键词目前为空，且摘要有内容，则调用本地 Qwen 模型
        if not self.keywords and self.abstract and len(self.abstract) > 10:
            try:
                ai = AcademicAI()
                # 调用 extract_tags 函数提取标签
                self.keywords = ai.extract_tags(self.title, self.abstract)
            except Exception as e:
                print(f"AI 提取关键词失败: {e}")
        
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "科研论文"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title