from rest_framework import serializers
from .models import GeneratedContent


class ContentGenerateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=150)
    topic = serializers.CharField(max_length=250, required=False, allow_blank=True, default='')
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
