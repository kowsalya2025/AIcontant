from django.contrib.auth.models import AbstractUser
from django.db import models


SKILL_LEVELS = [
    ('beginner', 'Beginner'),
    ('intermediate', 'Intermediate'),
    ('advanced', 'Advanced'),
]

LEARNING_STYLES = [
    ('visual', 'Visual'),
    ('reading', 'Reading/Writing'),
    ('auditory', 'Auditory'),
    ('kinesthetic', 'Kinesthetic'),
]

SUBJECT_CHOICES = [
    ('python', 'Python Programming'),
    ('mathematics', 'Mathematics'),
    ('data_science', 'Data Science'),
    ('machine_learning', 'Machine Learning'),
    ('web_development', 'Web Development'),
    ('algorithms', 'Algorithms & Data Structures'),
    ('databases', 'Databases'),
    ('networking', 'Computer Networking'),
    ('cybersecurity', 'Cybersecurity'),
    ('general', 'General'),
]


class Student(AbstractUser):
    """Custom user model with learning profile."""
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=200, blank=True)
    avatar_url = models.URLField(blank=True)

    # Learning profile
    preferred_subjects = models.JSONField(default=list, blank=True)
    skill_level = models.CharField(max_length=20, choices=SKILL_LEVELS, default='beginner')
    learning_style = models.CharField(max_length=20, choices=LEARNING_STYLES, default='visual')
    daily_goal_minutes = models.IntegerField(default=30)

    # Gamification
    total_points = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)
    longest_streak = models.IntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return f"{self.full_name or self.email}"

    @property
    def display_name(self):
        return self.full_name or self.email.split('@')[0]

    class Meta:
        verbose_name = 'Student'
        verbose_name_plural = 'Students'


class LearningProfile(models.Model):
    """Detailed learning preferences and performance summary."""
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='learning_profile')
    weak_topics = models.JSONField(default=list, blank=True)
    strong_topics = models.JSONField(default=list, blank=True)
    completed_topics = models.JSONField(default=list, blank=True)
    average_quiz_score = models.FloatField(default=0.0)
    total_content_generated = models.IntegerField(default=0)
    total_quizzes_taken = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.student}"
