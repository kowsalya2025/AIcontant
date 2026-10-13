from django.db import models
from apps.accounts.models import Student


CONTENT_TYPES = [
    ('notes', 'Study Notes'),
    ('explanation', 'Explanation'),
    ('examples', 'Examples'),
    ('summary', 'Summary'),
    ('deep_dive', 'Deep Dive'),
]


class GeneratedContent(models.Model):
    """Stores AI-generated learning content for each student."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='contents')
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=200)
    skill_level = models.CharField(max_length=20)
    content_type = models.CharField(max_length=30, choices=CONTENT_TYPES, default='notes')
    content_body = models.TextField()
    rag_sources = models.JSONField(default=list, blank=True)  # retrieved chunks used
    tokens_used = models.IntegerField(default=0)
    is_bookmarked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Generated Content'

    def __str__(self):
        return f"{self.student.display_name} — {self.topic} ({self.content_type})"
