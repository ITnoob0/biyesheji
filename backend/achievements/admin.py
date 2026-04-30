from django.contrib import admin

from .models import (
    AcademicService,
    CoAuthor,
    IntellectualProperty,
    Paper,
    PaperKeyword,
    Project,
    ResearchKeyword,
    RuleBasedAchievement,
    RuleBasedAchievementAttachment,
    TeacherProfile,
)


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'department', 'discipline', 'title')
    search_fields = ('user__username', 'department', 'discipline')


class CoAuthorInline(admin.TabularInline):
    model = CoAuthor
    extra = 1


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'paper_type', 'journal_level', 'date_acquired')
    list_filter = ('paper_type', 'journal_level')
    search_fields = ('title', 'teacher__username')
    inlines = [CoAuthorInline]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'teacher', 'level', 'role', 'funding_amount', 'status', 'date_acquired')
    list_filter = ('level', 'status', 'role')
    search_fields = ('title', 'teacher__username')


@admin.register(RuleBasedAchievement)
class RuleBasedAchievementAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'teacher',
        'category_name_snapshot',
        'rule_title_snapshot',
        'status',
        'provisional_score',
        'final_score',
        'date_acquired',
    )
    list_filter = ('status', 'category', 'rule_item', 'teacher__department')
    search_fields = ('title', 'external_reference', 'team_identifier', 'teacher__username', 'teacher__real_name')
    readonly_fields = ('score_detail',)


@admin.register(RuleBasedAchievementAttachment)
class RuleBasedAchievementAttachmentAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'achievement', 'uploaded_by', 'created_at')
    search_fields = ('original_name', 'achievement__title', 'uploaded_by__username')


admin.site.register(ResearchKeyword)
admin.site.register(PaperKeyword)
admin.site.register(IntellectualProperty)
admin.site.register(AcademicService)
