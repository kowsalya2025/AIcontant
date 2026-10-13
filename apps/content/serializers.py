from rest_framework import serializers
from .models import GeneratedContent


class ContentGenerateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=100)
    topic = serializers.CharField(max_length=200)
    skill_level = serializers.ChoiceField(
        choices=['beginner', 'intermediate', 'advanced'],
        required=False
    )
    content_type = serializers.ChoiceField(
        choices=['notes', 'explanation', 'examples', 'summary', 'deep_dive'],
        default='notes'
    )
    custom_instructions = serializers.CharField(required=False, allow_blank=True)


class GeneratedContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedContent
        fields = ['id', 'subject', 'topic', 'skill_level', 'content_type',
                  'content_body', 'rag_sources', 'is_bookmarked', 'created_at']
        read_only_fields = ['id', 'content_body', 'rag_sources', 'created_at']
