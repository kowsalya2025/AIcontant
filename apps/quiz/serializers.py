from rest_framework import serializers
from .models import Quiz, QuizAttempt


class QuizGenerateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=100)
    topic = serializers.CharField(max_length=200)
    skill_level = serializers.ChoiceField(
        choices=['beginner', 'intermediate', 'advanced'],
        required=False
    )
    num_questions = serializers.IntegerField(min_value=3, max_value=15, default=5)


class QuizSubmitSerializer(serializers.Serializer):
    quiz_id = serializers.IntegerField()
    answers = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        min_length=1
    )
    time_taken_seconds = serializers.IntegerField(default=0)


class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ['id', 'subject', 'topic', 'skill_level', 'questions',
                  'num_questions', 'created_at']


class QuizAttemptSerializer(serializers.ModelSerializer):
    quiz_topic = serializers.CharField(source='quiz.topic', read_only=True)
    quiz_subject = serializers.CharField(source='quiz.subject', read_only=True)

    class Meta:
        model = QuizAttempt
        fields = ['id', 'quiz_topic', 'quiz_subject', 'score', 'correct_count',
                  'total_questions', 'time_taken_seconds', 'feedback',
                  'correct_answers', 'completed_at']
