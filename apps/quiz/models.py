from django.db import models
from apps.accounts.models import Student


class Quiz(models.Model):
    """A generated quiz for a topic."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quizzes')
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=200)
    skill_level = models.CharField(max_length=20)
    questions = models.JSONField(default=list)  # list of question dicts
    num_questions = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Quizzes'

    def __str__(self):
        return f"Quiz: {self.topic} for {self.student.display_name}"


class QuizAttempt(models.Model):
    """A student's attempt at a quiz."""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='quiz_attempts')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    answers = models.JSONField(default=list)   # student's submitted answers
    correct_answers = models.JSONField(default=list)  # correct answer explanations
    score = models.FloatField(default=0.0)     # percentage 0-100
    total_questions = models.IntegerField(default=0)
    correct_count = models.IntegerField(default=0)
    time_taken_seconds = models.IntegerField(default=0)
    feedback = models.TextField(blank=True)    # AI-generated feedback
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-completed_at']

    def __str__(self):
        return f"{self.student.display_name} — {self.quiz.topic} ({self.score:.0f}%)"
