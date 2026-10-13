from django.contrib import admin
from .models import Quiz, QuizAttempt


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['student', 'topic', 'subject', 'skill_level', 'num_questions', 'created_at']
    list_filter = ['subject', 'skill_level']


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['student', 'quiz', 'score', 'correct_count', 'total_questions', 'completed_at']
    list_filter = ['completed_at']
    ordering = ['-completed_at']
