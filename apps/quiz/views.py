from django.db import transaction
from django.db.models import Avg
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Quiz, QuizAttempt
from .serializers import (
    QuizGenerateSerializer, QuizSubmitSerializer,
    QuizSerializer, QuizAttemptSerializer
)
from ai_services.llm_service import LLMService
from ai_services.validators import (
    validate_subject_topic_relevance,
    build_language_and_domain_rules,
)
import json
import re

llm_service = LLMService()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_quiz_view(request):
    """Generate a quiz for a given topic using Gemini AI."""
    serializer = QuizGenerateSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    student = request.user
    skill_level = data.get('skill_level') or student.skill_level
    subject = data['subject'].strip()
    topic = (data.get('topic') or '').strip()
    if not topic:
        topic = f"{subject} Fundamentals"
    num_questions = data.get('num_questions', 5)

    is_valid_topic, validation_error = validate_subject_topic_relevance(
        subject, topic, llm_service=llm_service
    )
    if not is_valid_topic:
        return Response(
            {'error': validation_error},
            status=status.HTTP_400_BAD_REQUEST
        )

    language_domain_rules = build_language_and_domain_rules(
        subject=subject,
        topic=topic,
        is_quiz=True,
    )

    prompt = f"""Generate a {num_questions}-question multiple choice quiz about "{topic}" in the subject "{subject}".
{language_domain_rules}
Skill Level: {skill_level}

Return ONLY a valid JSON array with this exact structure (no markdown, no explanation):
[
  {{
    "question": "Question text here?",
    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
    "correct_answer": "A",
    "explanation": "Brief explanation of why A is correct"
  }}
]

Generate exactly {num_questions} questions appropriate for {skill_level} level. Return only the JSON array."""

    raw_response = llm_service.generate(prompt, temperature=0.2)

    # Parse JSON from LLM response
    questions = _parse_quiz_json(raw_response, num_questions)

    if not questions:
        return Response(
            {'error': 'Failed to generate quiz. Please try again.'},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    quiz = Quiz.objects.create(
        student=student,
        subject=subject,
        topic=topic,
        skill_level=skill_level,
        questions=questions,
        num_questions=len(questions)
    )

    return Response({
        'quiz': QuizSerializer(quiz).data,
        'message': f'Quiz with {len(questions)} questions generated!'
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_quiz_view(request):
    """Submit quiz answers and get AI-evaluated results."""
    serializer = QuizSubmitSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    student = request.user

    with transaction.atomic():
        try:
            quiz = Quiz.objects.select_for_update().get(pk=data['quiz_id'], student=student)
        except Quiz.DoesNotExist:
            return Response({'error': 'Quiz not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Idempotency guard: prevent duplicate submissions for the same quiz
        existing_attempt = QuizAttempt.objects.filter(
            student=student, quiz=quiz
        ).order_by('-completed_at').first()
        if existing_attempt:
            points_earned = int(existing_attempt.score / 10) * 5
            return Response({
                'attempt': QuizAttemptSerializer(existing_attempt).data,
                'points_earned': points_earned,
                'duplicate_prevented': True,
                'message': f'Quiz submitted! You scored {existing_attempt.score:.0f}%'
            })

        student_answers = data['answers']
        questions = quiz.questions
        correct_count = 0
        correct_answers = []

        for i, question in enumerate(questions):
            student_ans = student_answers[i] if i < len(student_answers) else ''
            correct_ans = question.get('correct_answer', '')
            is_correct = student_ans.strip().upper()[:1] == correct_ans.strip().upper()[:1]
            if is_correct:
                correct_count += 1
            correct_answers.append({
                'question': question.get('question', ''),
                'your_answer': student_ans,
                'correct_answer': correct_ans,
                'is_correct': is_correct,
                'explanation': question.get('explanation', '')
            })

        score = (correct_count / len(questions)) * 100 if questions else 0

        # Generate AI feedback
        feedback_prompt = f"""A student scored {score:.0f}% ({correct_count}/{len(questions)}) on a quiz about "{quiz.topic}" in {quiz.subject} at {quiz.skill_level} level.
Write 2-3 sentences of encouraging, personalized feedback that:
1. Acknowledges their performance
2. Identifies a key area to improve
3. Suggests their next step

Be concise and motivating."""

        feedback = llm_service.generate(feedback_prompt, temperature=0.2) or "Great effort! Keep practicing to improve your understanding."

        attempt = QuizAttempt.objects.create(
            student=student,
            quiz=quiz,
            answers=student_answers,
            correct_answers=correct_answers,
            score=score,
            total_questions=len(questions),
            correct_count=correct_count,
            time_taken_seconds=data.get('time_taken_seconds', 0),
            feedback=feedback
        )

        # Update learning profile accurately from actual attempt records
        try:
            lp = student.learning_profile
            attempts_qs = QuizAttempt.objects.filter(student=student)
            lp.total_quizzes_taken = attempts_qs.count()
            lp.average_quiz_score = attempts_qs.aggregate(avg=Avg('score'))['avg'] or 0.0
            if score < 60 and quiz.topic not in lp.weak_topics:
                lp.weak_topics.append(quiz.topic)
            elif score >= 80 and quiz.topic not in lp.strong_topics:
                lp.strong_topics.append(quiz.topic)
            lp.save()
        except Exception:
            pass

        points_earned = int(score / 10) * 5  # up to 50 points
        student.total_points += points_earned
        student.save(update_fields=['total_points'])

    return Response({
        'attempt': QuizAttemptSerializer(attempt).data,
        'points_earned': points_earned,
        'message': f'Quiz submitted! You scored {score:.0f}%'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def quiz_history_view(request):
    """Retrieve student's quiz attempt history."""
    attempts = QuizAttempt.objects.filter(student=request.user).order_by('-completed_at')[:20]
    return Response({
        'count': len(attempts),
        'attempts': QuizAttemptSerializer(attempts, many=True).data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def quiz_attempt_detail_view(request, pk):
    """Retrieve a single completed quiz attempt for answer review."""
    try:
        attempt = QuizAttempt.objects.select_related('quiz').get(pk=pk, student=request.user)
    except QuizAttempt.DoesNotExist:
        return Response({'error': 'Quiz attempt not found.'}, status=status.HTTP_404_NOT_FOUND)
    return Response({'attempt': QuizAttemptSerializer(attempt).data})


def _parse_quiz_json(raw_text, expected_count):
    """Robustly extract JSON array from LLM response."""
    if not raw_text:
        return []
    # Try direct parse first
    try:
        data = json.loads(raw_text.strip())
        if isinstance(data, list):
            return data
    except Exception:
        pass
    # Extract JSON array from markdown code block or text
    match = re.search(r'\[[\s\S]*\]', raw_text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []
