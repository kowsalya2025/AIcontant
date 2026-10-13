from django.db import models
from apps.accounts.models import Student


class KnowledgeDocument(models.Model):
    """Uploaded documents that are indexed into the RAG knowledge base."""
    uploaded_by = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='documents',
        null=True, blank=True,
    )
    # ``student`` alias used by the FastAPI upload service
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='fastapi_documents',
        null=True, blank=True,
    )
    title = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=100, blank=True)
    # Original filename preserved when uploaded via FastAPI (no FileField path)
    original_filename = models.CharField(max_length=255, blank=True)
    file = models.FileField(upload_to='knowledge_base/', null=True, blank=True)
    file_type = models.CharField(max_length=10, blank=True)  # pdf, txt, docx
    chunk_count = models.IntegerField(default=0)
    is_indexed = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        name = self.title or self.original_filename or "Untitled"
        return f"{name} ({self.subject or 'no subject'})"
