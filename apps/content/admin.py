from django.contrib import admin
from .models import GeneratedContent


@admin.register(GeneratedContent)
class GeneratedContentAdmin(admin.ModelAdmin):
    list_display = ['student', 'topic', 'subject', 'skill_level', 'content_type', 'is_bookmarked', 'created_at']
    list_filter = ['subject', 'skill_level', 'content_type', 'is_bookmarked']
    search_fields = ['topic', 'student__email']
    ordering = ['-created_at']
