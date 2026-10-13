from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from .models import Student, LearningProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = Student
        fields = ['email', 'username', 'full_name', 'password', 'password2',
                  'skill_level', 'learning_style', 'preferred_subjects']
        extra_kwargs = {'username': {'required': False}}

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        if 'username' not in validated_data or not validated_data.get('username'):
            validated_data['username'] = validated_data['email'].split('@')[0]
        student = Student.objects.create_user(password=password, **validated_data)
        LearningProfile.objects.create(student=student)
        return student


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(username=data['email'], password=data['password'])
        if not user:
            raise serializers.ValidationError('Invalid email or password.')
        data['user'] = user
        return data


class StudentSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()

    class Meta:
        model = Student
        fields = ['id', 'email', 'username', 'full_name', 'display_name',
                  'skill_level', 'learning_style', 'preferred_subjects',
                  'daily_goal_minutes', 'total_points', 'current_streak',
                  'longest_streak', 'created_at']
        read_only_fields = ['id', 'email', 'total_points', 'current_streak',
                            'longest_streak', 'created_at']


class LearningProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningProfile
        fields = ['weak_topics', 'strong_topics', 'completed_topics',
                  'average_quiz_score', 'total_content_generated',
                  'total_quizzes_taken', 'updated_at']
        read_only_fields = ['average_quiz_score', 'total_content_generated',
                            'total_quizzes_taken', 'updated_at']
