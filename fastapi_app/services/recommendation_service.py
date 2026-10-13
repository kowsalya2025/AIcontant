"""
Recommendation service — FastAPI layer.

Builds adaptive learning recommendations using the student's LearningProfile
and Gemini (via LangChain PromptTemplate).
"""
from __future__ import annotations

import json
import logging
import re

from langchain.prompts import PromptTemplate

from ai_services.llm_service import LLMService
from fastapi_app.schemas import RecommendationsResponse

logger = logging.getLogger(__name__)

_REC_PROMPT = PromptTemplate(
    input_variables=[
        "skill_level", "preferred_subjects", "weak_topics",
        "strong_topics", "completed_topics", "avg_score", "learning_style",
    ],
    template="""You are a personalized learning advisor. Based on this student's profile, generate learning recommendations.

Student Profile:
- Skill Level: {skill_level}
- Preferred Subjects: {preferred_subjects}
- Weak Topics: {weak_topics}
- Strong Topics: {strong_topics}
- Completed Topics: {completed_topics}
- Average Quiz Score: {avg_score}%
- Learning Style: {learning_style}

Generate a JSON response with this exact structure:
{{
  "next_topics": ["topic1", "topic2", "topic3"],
  "suggested_skill_level": "{skill_level}",
  "focus_areas": ["area1", "area2"],
  "study_tip": "A personalized study tip based on their profile",
  "daily_challenge": "A specific micro-task or challenge for today",
  "motivational_message": "A short motivational message"
}}

Return only valid JSON, no markdown.""",
)


def build_recommendations(
    student,
    llm: LLMService,
) -> RecommendationsResponse:
    """Synchronous recommendation pipeline (called via sync_to_async)."""
    try:
        lp = student.learning_profile
        weak_topics = lp.weak_topics
        strong_topics = lp.strong_topics
        completed = lp.completed_topics
        avg_score = lp.average_quiz_score
    except Exception:
        weak_topics, strong_topics, completed, avg_score = [], [], [], 0.0

    prompt_text = _REC_PROMPT.format(
        skill_level=student.skill_level,
        preferred_subjects=", ".join(student.preferred_subjects) or "Not specified",
        weak_topics=", ".join(weak_topics) or "None identified yet",
        strong_topics=", ".join(strong_topics) or "None yet",
        completed_topics=", ".join(completed[:5]) or "None yet",
        avg_score=f"{avg_score:.1f}",
        learning_style=student.learning_style,
    )

    raw = llm.generate(prompt_text)
    recommendations: dict = {}
    if raw:
        try:
            recommendations = json.loads(raw.strip())
        except Exception:
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                try:
                    recommendations = json.loads(match.group())
                except Exception:
                    pass

    if not recommendations:
        subject = (student.preferred_subjects or ["Python Programming"])[0]
        recommendations = {
            "next_topics": [
                f"Introduction to {subject}",
                f"{subject} Basics",
                f"{subject} Practice",
            ],
            "suggested_skill_level": student.skill_level,
            "focus_areas": weak_topics[:2] or ["Core Concepts", "Practice Problems"],
            "study_tip": f"Focus on hands-on practice as a {student.skill_level} learner.",
            "daily_challenge": f"Generate content on one new {subject} topic today!",
            "motivational_message": "Every expert was once a beginner. Keep going! 🚀",
        }

    return RecommendationsResponse(
        recommendations=recommendations,
        profile_summary={
            "skill_level": student.skill_level,
            "avg_quiz_score": round(avg_score, 1),
            "topics_completed": len(completed),
            "weak_areas": weak_topics[:3],
        },
    )
