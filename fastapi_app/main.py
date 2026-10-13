"""
FastAPI Application — EduAI Personalized Learning Content Generator
===================================================================
Mounted at /fastapi/ inside the Django WSGI app (see config/urls.py).

Provides modern async API endpoints that complement the Django REST
Framework API.  Both share the same PostgreSQL / SQLite database via
Django's ORM (accessed through sync_to_async where needed).

Endpoints
---------
POST /fastapi/generate/content   — generate personalised learning content
POST /fastapi/generate/quiz      — generate MCQ quiz
GET  /fastapi/recommendations    — adaptive topic recommendations
POST /fastapi/rag/upload         — upload document into FAISS/Chroma index
GET  /fastapi/rag/query          — query RAG context
GET  /fastapi/health             — health check
"""

import os
import sys
import logging
from pathlib import Path

# ── Make the project root importable ──────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Bootstrap Django so we can use its ORM inside FastAPI
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from asgiref.sync import sync_to_async

from fastapi_app.schemas import (
    ContentGenerateRequest,
    ContentGenerateResponse,
    QuizGenerateRequest,
    QuizGenerateResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    RecommendationsResponse,
    HealthResponse,
)
from fastapi_app.auth import get_current_student
from fastapi_app.dependencies import get_llm_service, get_rag_service

logger = logging.getLogger(__name__)

# ── FastAPI app instance ───────────────────────────────────────────
app = FastAPI(
    title="EduAI — Personalized AI Learning Content Generator",
    description=(
        "AI-powered learning platform: personalized notes, quizzes, "
        "and recommendations via Gemini + RAG (FAISS/Chroma) + LangChain."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Quick health check — used by Docker and load-balancers."""
    return HealthResponse(
        status="ok",
        framework="FastAPI + Django ORM",
        llm="Google Gemini 1.5 Flash",
        vector_store="FAISS + ChromaDB",
        embeddings="sentence-transformers/all-MiniLM-L6-v2",
        database=os.getenv("DB_ENGINE", "SQLite"),
    )


# ─────────────────────────────────────────────────────────────────
# Content Generation
# ─────────────────────────────────────────────────────────────────

@app.post("/generate/content", response_model=ContentGenerateResponse, tags=["AI Content"])
async def generate_content(
    payload: ContentGenerateRequest,
    student=Depends(get_current_student),
    llm=Depends(get_llm_service),
    rag=Depends(get_rag_service),
):
    """
    Generate personalised AI learning content using RAG + LangChain + Gemini.

    Steps:
    1. RAG retrieval — fetch top-k relevant chunks from FAISS/Chroma index
    2. Build a LangChain PromptTemplate using student profile
    3. Call Gemini 1.5 Flash via LangChain LLMChain
    4. Persist result to PostgreSQL via Django ORM
    5. Return structured response
    """
    from fastapi_app.services.content_service import generate_personalised_content
    result = await sync_to_async(generate_personalised_content)(student, payload, llm, rag)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Content generation failed. Check your Gemini API key.",
        )
    return result


# ─────────────────────────────────────────────────────────────────
# Quiz Generation
# ─────────────────────────────────────────────────────────────────

@app.post("/generate/quiz", response_model=QuizGenerateResponse, tags=["Quiz"])
async def generate_quiz(
    payload: QuizGenerateRequest,
    student=Depends(get_current_student),
    llm=Depends(get_llm_service),
):
    """
    Generate a personalised MCQ quiz using Gemini via LangChain.

    Returns questions with options, correct answers, and explanations.
    Difficulty is auto-scaled to the student's skill level.
    """
    from fastapi_app.services.quiz_service import generate_quiz_for_student
    result = await sync_to_async(generate_quiz_for_student)(student, payload, llm)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quiz generation failed. Please try again.",
        )
    return result


# ─────────────────────────────────────────────────────────────────
# Recommendations
# ─────────────────────────────────────────────────────────────────

@app.get("/recommendations", response_model=RecommendationsResponse, tags=["Recommendations"])
async def get_recommendations(
    student=Depends(get_current_student),
    llm=Depends(get_llm_service),
):
    """
    Return adaptive learning recommendations using student's performance profile.

    Reads LearningProfile (weak_topics, strong_topics, avg_score) and asks
    Gemini for personalised next steps via LangChain.
    """
    from fastapi_app.services.recommendation_service import build_recommendations
    result = await sync_to_async(build_recommendations)(student, llm)
    return result


# ─────────────────────────────────────────────────────────────────
# RAG — document upload & query
# ─────────────────────────────────────────────────────────────────

@app.post("/rag/upload", tags=["RAG"])
async def upload_document(
    file: UploadFile = File(...),
    student=Depends(get_current_student),
    rag=Depends(get_rag_service),
):
    """
    Upload a PDF/TXT/DOCX file and index it into FAISS + Chroma.

    The file is chunked with LangChain's RecursiveCharacterTextSplitter,
    embedded with sentence-transformers, and stored in both vector stores.
    """
    import tempfile, shutil
    from fastapi_app.services.rag_upload_service import index_uploaded_file

    suffix = Path(file.filename).suffix.lower()
    if suffix not in {".pdf", ".txt", ".docx", ".md"}:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    # Save upload to a temp file then index
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        chunk_count = await sync_to_async(index_uploaded_file)(tmp_path, file.filename, student, rag)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {"filename": file.filename, "chunks_indexed": chunk_count, "message": "Document indexed successfully."}


@app.post("/rag/query", response_model=RAGQueryResponse, tags=["RAG"])
async def query_rag(
    payload: RAGQueryRequest,
    student=Depends(get_current_student),
    rag=Depends(get_rag_service),
):
    """
    Query the RAG index and return top-k relevant context chunks.

    Uses semantic search (FAISS) by default; falls back to keyword search.
    """
    chunks = await sync_to_async(rag.retrieve)(payload.query, k=payload.top_k)
    return RAGQueryResponse(query=payload.query, chunks=chunks, source="FAISS")
