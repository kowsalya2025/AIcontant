"""
Quiz generation service — FastAPI layer.

Uses LangChain PromptTemplate + Gemini to create adaptive MCQ quizzes.
"""
from __future__ import annotations

import json
import logging
import re

from langchain.prompts import PromptTemplate

from ai_services.llm_service import LLMService
from fastapi_app.schemas import QuizGenerateRequest, QuizGenerateResponse, QuizQuestion

logger = logging.getLogger(__name__)

_QUIZ_PROMPT = PromptTemplate(
    input_variables=["num_questions", "topic", "subject", "skill_level"],
    template="""Generate a {num_questions}-question multiple choice quiz about "{topic}" in {subject}.
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

Generate exactly {num_questions} questions appropriate for {skill_level} level. Return only the JSON array.""",
)


def generate_quiz_for_student(
    student,
    payload: QuizGenerateRequest,
    llm: LLMService,
) -> QuizGenerateResponse | None:
    """Synchronous quiz generation pipeline (called via sync_to_async)."""
    from apps.quiz.models import Quiz

    skill_level = payload.skill_level or student.skill_level
    topic = payload.topic
    subject = payload.subject
    num_questions = payload.num_questions

    prompt_text = _QUIZ_PROMPT.format(
        num_questions=num_questions,
        topic=topic,
        subject=subject,
        skill_level=skill_level,
    )

    raw_response = llm.generate(prompt_text)
    questions_raw = _parse_quiz_json(raw_response, num_questions)
    if not questions_raw:
        logger.error("Failed to parse quiz JSON for topic=%s", topic)
        return None

    quiz = Quiz.objects.create(
        student=student,
        subject=subject,
        topic=topic,
        skill_level=skill_level,
        questions=questions_raw,
        num_questions=len(questions_raw),
    )

    questions = [
        QuizQuestion(
            question=q.get("question", ""),
            options=q.get("options", []),
            correct_answer=q.get("correct_answer", ""),
            explanation=q.get("explanation", ""),
        )
        for q in questions_raw
    ]

    return QuizGenerateResponse(
        id=quiz.pk,
        topic=topic,
        subject=subject,
        skill_level=skill_level,
        questions=questions,
        message=f"Quiz with {len(questions)} questions generated!",
    )


def _parse_quiz_json(raw_text: str, expected_count: int) -> list[dict]:
    if not raw_text:
        return []
    try:
        data = json.loads(raw_text.strip())
        if isinstance(data, list):
            return data
    except Exception:
        pass
    match = re.search(r"\[[\s\S]*\]", raw_text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []
