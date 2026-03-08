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

@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    # 注意这里：已经将 publish_date 改为了 date_acquired
    list_display = ('title', 'teacher', 'paper_type', 'journal_level', 'date_acquired', 'citation_count')
    list_filter = ('paper_type', 'journal_level')
    search_fields = ('title', 'teacher__username')

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'level', 'role', 'funding_amount', 'status', 'date_acquired')
    list_filter = ('level', 'status', 'role')
    search_fields = ('title', 'teacher__username')

# 注册其他图谱和画像相关的表
admin.site.register(ResearchKeyword)
admin.site.register(PaperKeyword)
admin.site.register(CoAuthor)
admin.site.register(IntellectualProperty)
admin.site.register(TeachingAchievement)
admin.site.register(AcademicService)