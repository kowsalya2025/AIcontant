from django.contrib import admin
from .models import KnowledgeDocument


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'subject', 'file_type', 'chunk_count', 'is_indexed', 'uploaded_by', 'uploaded_at']
    list_filter = ['subject', 'file_type', 'is_indexed']
