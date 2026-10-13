from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Student, LearningProfile


@admin.register(Student)
class StudentAdmin(UserAdmin):
    list_display = ['email', 'full_name', 'skill_level', 'total_points', 'current_streak']
    list_filter = ['skill_level', 'learning_style', 'is_active']
    search_fields = ['email', 'full_name']
    ordering = ['-created_at']
    fieldsets = UserAdmin.fieldsets + (
        ('Learning Profile', {'fields': (
            'full_name', 'skill_level', 'learning_style',
            'preferred_subjects', 'daily_goal_minutes',
            'total_points', 'current_streak', 'longest_streak',
        )}),
    )


@admin.register(LearningProfile)
class LearningProfileAdmin(admin.ModelAdmin):
    list_display = ['student', 'average_quiz_score', 'total_quizzes_taken', 'total_content_generated']
