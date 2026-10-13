"""
FastAPI dependency injection — shared AI service singletons.

Services are initialised once at startup and injected into route handlers.
This avoids the cost of re-loading the embedding model on every request.
"""
from functools import lru_cache
from ai_services.llm_service import LLMService
from ai_services.rag_service import RAGService


@lru_cache(maxsize=1)
def _llm_singleton() -> LLMService:
    return LLMService()


@lru_cache(maxsize=1)
def _rag_singleton() -> RAGService:
    return RAGService()


def get_llm_service() -> LLMService:
    """FastAPI dependency: returns the shared LLMService instance."""
    return _llm_singleton()


def get_rag_service() -> RAGService:
    """FastAPI dependency: returns the shared RAGService instance."""
    return _rag_singleton()
