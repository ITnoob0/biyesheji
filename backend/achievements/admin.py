# backend/achievements/admin.py
from django.contrib import admin
from .models import (
    TeacherProfile, Paper, ResearchKeyword, PaperKeyword, 
    CoAuthor, Project, IntellectualProperty, 
    TeachingAchievement, AcademicService
)

@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'discipline', 'title', 'h_index')
    search_fields = ('user__username', 'department', 'discipline')

# 新增：定义合作者的内联表单，这样在论文编辑页就能直接录入合作者
class CoAuthorInline(admin.TabularInline):
    model = CoAuthor
    extra = 1

@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    # 保留你原来的字段设置：注意这里 date_acquired 保持不变
    list_display = ('title', 'teacher', 'paper_type', 'journal_level', 'date_acquired', 'citation_count')
    list_filter = ('paper_type', 'journal_level')
    search_fields = ('title', 'teacher__username')
    inlines = [CoAuthorInline] # 启用合作者内联编辑

    # 重写 save_related，确保论文基础信息和合作者保存后，再触发 AI 和图数据库
    def save_related(self, request, form, formsets, change):
        # 1. 首先调用父类方法，确保 Paper 和 CoAuthor 已经保存到 MySQL
        super().save_related(request, form, formsets, change)
        
        instance = form.instance
        
        # 2. 检查摘要长度，触发 AI 逻辑
        if instance.abstract and len(instance.abstract) > 10:
            print(f"\n🚀 Admin 检测到论文保存: {instance.title}，正在呼叫 Qwen2.5 推理...")
            
            # 局部导入工具类，防止开发环境下的循环引用
            from ai_assistant.utils import AcademicAI
            from graph_engine.utils import Neo4jEngine
            
            try:
                # A. 调用 AI 提取关键词
                ai = AcademicAI()
                kw_names = ai.extract_tags(instance.title, instance.abstract)
                print(f"✅ AI 提取关键词: {kw_names}")
                
                # B. 将关键词存入 MySQL
                for kw in kw_names:
                    kw_obj, _ = ResearchKeyword.objects.get_or_create(name=kw)
                    PaperKeyword.objects.get_or_create(paper=instance, keyword=kw_obj)
                
                # C. 同步到 Neo4j 图数据库
                # 构建作者列表：当前教师 + 所有合作者
                author_names = [instance.teacher.username] 
                for coauthor in instance.coauthors.all():
                    author_names.append(coauthor.name)

                graph = Neo4jEngine()
                graph.sync_paper_to_graph(
                    paper_id=instance.id,
                    title=instance.title,
                    author_names=author_names,
                    keywords=kw_names
                )
                graph.close()
                print("✅ Neo4j 学术拓扑同步完成！\n")
                
            except Exception as e:
                print(f"❌ AI 或 Neo4j 模块运行出错: {e}\n")

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'level', 'role', 'funding_amount', 'status', 'date_acquired')
    list_filter = ('level', 'status', 'role')
    search_fields = ('title', 'teacher__username')

# 注册其他图谱和画像相关的表
admin.site.register(ResearchKeyword)
admin.site.register(PaperKeyword)
# CoAuthor 已在 PaperAdmin 中作为 Inline 注册，通常不需要再单独注册
admin.site.register(IntellectualProperty)
admin.site.register(TeachingAchievement)
admin.site.register(AcademicService)