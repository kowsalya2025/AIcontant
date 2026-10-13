"""
RAG upload service — FastAPI layer.

Indexes an uploaded file into both FAISS (via RAGService) and ChromaDB.
"""
from __future__ import annotations

import logging
from pathlib import Path

from ai_services.rag_service import RAGService

logger = logging.getLogger(__name__)


def index_uploaded_file(
    tmp_path: str,
    original_filename: str,
    student,
    rag: RAGService,
) -> int:
    """
    Index a temporary file into FAISS + Django KnowledgeDocument model.

    Returns the number of chunks indexed.
    """
    from apps.knowledge.models import KnowledgeDocument

    chunk_count = rag.add_document(tmp_path)

    # Record in Django DB
    try:
        KnowledgeDocument.objects.create(
            student=student,
            original_filename=original_filename,
            chunk_count=chunk_count,
            is_indexed=True,
        )
    except Exception as exc:
        logger.warning("Could not save KnowledgeDocument record: %s", exc)

    logger.info("Indexed '%s' → %d chunks via FastAPI RAG upload", original_filename, chunk_count)
    return chunk_count
