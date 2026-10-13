from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import GeneratedContent
from .serializers import ContentGenerateSerializer, GeneratedContentSerializer
from ai_services.rag_service import RAGService
from ai_services.llm_service import LLMService


rag_service = RAGService()
llm_service = LLMService()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_content_view(request):
    """Generate personalized AI learning content using RAG + Gemini."""
    serializer = ContentGenerateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    student = request.user
    skill_level = data.get('skill_level') or student.skill_level
    topic = data['topic']
    subject = data['subject']
    content_type = data.get('content_type', 'notes')
    custom_instructions = data.get('custom_instructions', '')

    # Step 1: RAG retrieval — find relevant knowledge base chunks
    retrieved_chunks = rag_service.retrieve(
        query=f"{subject} {topic}",
        k=4
    )
    rag_context = "\n\n".join(retrieved_chunks) if retrieved_chunks else ""

    # Step 2: Build prompt
    content_type_prompts = {
        'notes': 'Generate comprehensive, well-structured study notes',
        'explanation': 'Provide a clear, detailed explanation with analogies',
        'examples': 'Provide multiple practical examples with code/solutions',
        'summary': 'Create a concise, bullet-point summary',
        'deep_dive': 'Provide an in-depth technical deep dive',
    }
    action = content_type_prompts.get(content_type, 'Generate study notes')

    prompt = f"""You are an expert AI tutor. {action} about "{topic}" in {subject}.

Student Profile:
- Skill Level: {skill_level}
- Learning Style: {student.learning_style}
- Subject: {subject}

{f"Reference Knowledge Base Context:{chr(10)}{rag_context}{chr(10)}" if rag_context else ""}
{f"Additional Instructions: {custom_instructions}" if custom_instructions else ""}

Requirements:
- Tailor the complexity and language to a {skill_level} learner
- Use markdown formatting (headers, bullets, code blocks where appropriate)
- Include key concepts, definitions, and practical insights
- For {student.learning_style} learners: {"use diagrams described in text, visual metaphors" if student.learning_style == "visual" else "include step-by-step processes" if student.learning_style == "kinesthetic" else "provide detailed written explanations"}
- End with a "Key Takeaways" section

Generate the content now:"""

    # Step 3: LLM generation
    generated_text = llm_service.generate(prompt)

    if not generated_text:
        return Response(
            {'error': 'Content generation failed. Please try again.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    # Step 4: Save to database
    content_obj = GeneratedContent.objects.create(
        student=student,
        subject=subject,
        topic=topic,
        skill_level=skill_level,
        content_type=content_type,
        content_body=generated_text,
        rag_sources=retrieved_chunks[:2] if retrieved_chunks else [],
    )

    # Update student profile stats
    try:
        lp = student.learning_profile
        lp.total_content_generated += 1
        if topic not in lp.completed_topics:
            lp.completed_topics.append(topic)
        lp.save()
    except Exception:
        pass

    student.total_points += 10
    student.save(update_fields=['total_points'])

    return Response({
        'content': GeneratedContentSerializer(content_obj).data,
        'rag_used': bool(retrieved_chunks),
        'points_earned': 10,
        'message': 'Content generated successfully!'
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def content_history_view(request):
    """Retrieve student's content generation history."""
    contents = GeneratedContent.objects.filter(student=request.user).order_by('-created_at')[:20]
    return Response({
        'count': contents.count(),
        'contents': GeneratedContentSerializer(contents, many=True).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def content_detail_view(request, pk):
    """Retrieve a specific generated content item."""
    try:
        content = GeneratedContent.objects.get(pk=pk, student=request.user)
        return Response(GeneratedContentSerializer(content).data)
    except GeneratedContent.DoesNotExist:
        return Response({'error': 'Content not found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bookmark_content_view(request, pk):
    """Toggle bookmark on a content item."""
    try:
        content = GeneratedContent.objects.get(pk=pk, student=request.user)
        content.is_bookmarked = not content.is_bookmarked
        content.save(update_fields=['is_bookmarked'])
        return Response({
            'bookmarked': content.is_bookmarked,
            'message': 'Bookmarked!' if content.is_bookmarked else 'Bookmark removed.'
        })
    except GeneratedContent.DoesNotExist:
        return Response({'error': 'Content not found.'}, status=status.HTTP_404_NOT_FOUND)
