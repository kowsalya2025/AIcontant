from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ai_services.llm_service import LLMService

llm_service = LLMService()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommendations_view(request):
    """Generate personalized learning recommendations based on student profile."""
    student = request.user
    try:
        lp = student.learning_profile
        weak_topics = lp.weak_topics
        strong_topics = lp.strong_topics
        completed = lp.completed_topics
        avg_score = lp.average_quiz_score
    except Exception:
        weak_topics, strong_topics, completed, avg_score = [], [], [], 0

    prompt = f"""You are a personalized learning advisor. Based on this student's profile, generate learning recommendations.

Student Profile:
- Skill Level: {student.skill_level}
- Preferred Subjects: {', '.join(student.preferred_subjects) or 'Not specified'}
- Weak Topics: {', '.join(weak_topics) or 'None identified yet'}
- Strong Topics: {', '.join(strong_topics) or 'None yet'}
- Completed Topics: {', '.join(completed[:5]) or 'None yet'}
- Average Quiz Score: {avg_score:.1f}%
- Learning Style: {student.learning_style}

Generate a JSON response with this exact structure:
{{
  "next_topics": ["topic1", "topic2", "topic3"],
  "suggested_skill_level": "{student.skill_level}",
  "focus_areas": ["area1", "area2"],
  "study_tip": "A personalized study tip based on their profile",
  "daily_challenge": "A specific micro-task or challenge for today",
  "motivational_message": "A short motivational message"
}}

Return only valid JSON, no markdown."""

    raw = llm_service.generate(prompt)

    import json, re
    recommendations = {}
    if raw:
        try:
            recommendations = json.loads(raw.strip())
        except Exception:
            match = re.search(r'\{[\s\S]*\}', raw)
            if match:
                try:
                    recommendations = json.loads(match.group())
                except Exception:
                    pass

    # Fallback defaults
    if not recommendations:
        subject = (student.preferred_subjects or ['Python Programming'])[0]
        recommendations = {
            'next_topics': [f'Introduction to {subject}', f'{subject} Basics', f'{subject} Practice'],
            'suggested_skill_level': student.skill_level,
            'focus_areas': weak_topics[:2] or ['Core Concepts', 'Practice Problems'],
            'study_tip': f'Focus on hands-on practice as a {student.skill_level} learner.',
            'daily_challenge': f'Generate content on one new {subject} topic today!',
            'motivational_message': 'Every expert was once a beginner. Keep going! 🚀'
        }

    return Response({
        'recommendations': recommendations,
        'profile_summary': {
            'skill_level': student.skill_level,
            'avg_quiz_score': round(avg_score, 1),
            'topics_completed': len(completed),
            'weak_areas': weak_topics[:3],
        }
    })
