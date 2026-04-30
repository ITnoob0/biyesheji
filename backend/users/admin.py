from django.contrib import admin

from .models import College


@admin.register(College)
class CollegeAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "sort_order", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("sort_order", "id")
