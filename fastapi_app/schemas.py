"""
Pydantic v2 schemas for FastAPI request / response models.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────
# Shared / enums
# ─────────────────────────────────────────────────────────────────

class ContentType(str):
    NOTES = "notes"
    EXPLANATION = "explanation"
    EXAMPLES = "examples"
    SUMMARY = "summary"
    DEEP_DIVE = "deep_dive"


class SkillLevel(str):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# ─────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    framework: str
    llm: str
    vector_store: str
    embeddings: str
    database: str


# ─────────────────────────────────────────────────────────────────
# Content generation
# ─────────────────────────────────────────────────────────────────

class ContentGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=200, example="Python decorators")
    subject: str = Field(..., min_length=2, max_length=100, example="python")
    content_type: str = Field(default="notes", example="notes")
    skill_level: Optional[str] = Field(default=None, example="intermediate")
    custom_instructions: Optional[str] = Field(default=None, max_length=500)


class ContentGenerateResponse(BaseModel):
    id: int
    topic: str
    subject: str
    content_type: str
    skill_level: str
    content_body: str
    rag_used: bool
    rag_sources: list[str]
    points_earned: int
    message: str


# ─────────────────────────────────────────────────────────────────
# Quiz
# ─────────────────────────────────────────────────────────────────

class QuizGenerateRequest(BaseModel):
    topic: str = Field(..., min_length=2, max_length=200, example="List comprehensions")
    subject: str = Field(..., min_length=2, max_length=100, example="python")
    num_questions: int = Field(default=5, ge=1, le=20)
    skill_level: Optional[str] = Field(default=None)


class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    correct_answer: str
    explanation: str


class QuizGenerateResponse(BaseModel):
    id: int
    topic: str
    subject: str
    skill_level: str
    questions: list[QuizQuestion]
    message: str


# ─────────────────────────────────────────────────────────────────
# Recommendations
# ─────────────────────────────────────────────────────────────────

class RecommendationsResponse(BaseModel):
    recommendations: dict[str, Any]
    profile_summary: dict[str, Any]


# ─────────────────────────────────────────────────────────────────
# RAG
# ─────────────────────────────────────────────────────────────────

class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    top_k: int = Field(default=4, ge=1, le=20)


class RAGQueryResponse(BaseModel):
    query: str
    chunks: list[str]
    source: str
