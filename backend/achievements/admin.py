from django.contrib import admin
from .models import Paper

@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ('title', 'journal_name', 'publish_date') # 在列表页显示的字段