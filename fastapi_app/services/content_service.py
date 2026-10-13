"""
Content generation service — FastAPI layer.

Orchestrates:
  RAG (FAISS) retrieval → LangChain PromptTemplate → Gemini LLM →
  Django ORM save → LearningProfile update → response.
"""
from __future__ import annotations

import logging
from langchain.prompts import PromptTemplate

from ai_services.llm_service import LLMService
from ai_services.rag_service import RAGService
from fastapi_app.schemas import ContentGenerateRequest, ContentGenerateResponse

logger = logging.getLogger(__name__)

# ── LangChain PromptTemplate for personalised content ─────────────
_CONTENT_PROMPT = PromptTemplate(
    input_variables=[
        "action", "topic", "subject", "skill_level",
        "learning_style", "rag_context", "custom_instructions",
    ],
    template="""You are an expert AI tutor. {action} about "{topic}" in {subject}.

Student Profile:
- Skill Level: {skill_level}
- Learning Style: {learning_style}
- Subject: {subject}

{rag_context}
{custom_instructions}

Requirements:
- Tailor complexity and language to a {skill_level} learner
- Use markdown formatting (headers, bullets, code blocks where appropriate)
- Include key concepts, definitions, and practical insights
- End with a "Key Takeaways" section

Generate the content now:""",
)

_CONTENT_TYPE_ACTIONS = {
    "notes": "Generate comprehensive, well-structured study notes",
    "explanation": "Provide a clear, detailed explanation with analogies",
    "examples": "Provide multiple practical examples with code/solutions",
    "summary": "Create a concise, bullet-point summary",
    "deep_dive": "Provide an in-depth technical deep dive",
}


def generate_personalised_content(
    student,
    payload: ContentGenerateRequest,
    llm: LLMService,
    rag: RAGService,
) -> ContentGenerateResponse | None:
    """
    Full content generation pipeline (synchronous — called via sync_to_async).

    1. Retrieve top-4 RAG chunks relevant to {subject} {topic}
    2. Format LangChain PromptTemplate
    3. Generate via Gemini
    4. Persist to Django GeneratedContent model
    5. Return Pydantic response
    """
    from apps.content.models import GeneratedContent

    skill_level = payload.skill_level or student.skill_level
    topic = payload.topic
    subject = payload.subject
    content_type = payload.content_type or "notes"
    custom_instructions = payload.custom_instructions or ""

    # Step 1 — RAG retrieval
    retrieved_chunks: list[str] = rag.retrieve(f"{subject} {topic}", k=4)
    rag_context = (
        f"Reference Knowledge Base Context:\n{chr(10).join(retrieved_chunks)}\n"
        if retrieved_chunks
        else ""
    )

    # Step 2 — Build prompt via LangChain PromptTemplate
    action = _CONTENT_TYPE_ACTIONS.get(content_type, "Generate study notes")
    custom_block = f"Additional Instructions: {custom_instructions}" if custom_instructions else ""

    prompt_text = _CONTENT_PROMPT.format(
        action=action,
        topic=topic,
        subject=subject,
        skill_level=skill_level,
        learning_style=student.learning_style,
        rag_context=rag_context,
        custom_instructions=custom_block,
    )

    # Step 3 — LLM generation
    generated_text = llm.generate(prompt_text)
    if not generated_text:
        logger.error("LLM returned empty content for topic=%s", topic)
        return None

    # Step 4 — Persist via Django ORM
    content_obj = GeneratedContent.objects.create(
        student=student,
        subject=subject,
        topic=topic,
        skill_level=skill_level,
        content_type=content_type,
        content_body=generated_text,
        rag_sources=retrieved_chunks[:2] if retrieved_chunks else [],
    )

    # Update LearningProfile
    try:
        lp = student.learning_profile
        lp.total_content_generated += 1
        if topic not in lp.completed_topics:
            lp.completed_topics.append(topic)
        lp.save()
    except Exception:
        pass

    student.total_points += 10
    student.save(update_fields=["total_points"])

    return ContentGenerateResponse(
        id=content_obj.pk,
        topic=topic,
        subject=subject,
        content_type=content_type,
        skill_level=skill_level,
        content_body=generated_text,
        rag_used=bool(retrieved_chunks),
        rag_sources=retrieved_chunks[:2],
        points_earned=10,
        message="Content generated successfully!",
    )
