"""
ChromaDB Vector Store Service
==============================
An alternative / additive vector store alongside FAISS.

ChromaDB provides:
  - Persistent on-disk storage (no separate save/load cycle)
  - Metadata filtering (subject, skill_level, student_id)
  - HTTP client mode for scaled deployments

Usage:
  from ai_services.chroma_service import ChromaService
  chroma = ChromaService()
  chroma.add_documents(chunks, metadatas=[{"subject": "python"}])
  results = chroma.retrieve("list comprehensions", k=4)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# Default on-disk persistence directory
_DEFAULT_PERSIST_DIR = str(Path(settings.BASE_DIR) / "chroma_index")


class ChromaService:
    """
    Wraps ChromaDB for persistent semantic search.

    - Collection name: ``eduai_knowledge``
    - Embedding function: sentence-transformers ``all-MiniLM-L6-v2``
      (same model used by FAISS — consistent embedding space)
    - Falls back to no-op when chromadb is not installed
    """

    COLLECTION_NAME = "eduai_knowledge"

    def __init__(self, persist_dir: Optional[str] = None):
        self._persist_dir = persist_dir or _DEFAULT_PERSIST_DIR
        self._client = None
        self._collection = None
        self._embedding_fn = None
        self._initialize()

    # ─────────────────────────────────────────────────────────────
    # Initialisation
    # ─────────────────────────────────────────────────────────────

    def _initialize(self):
        try:
            import chromadb  # noqa: F401
            from chromadb.utils.embedding_functions import (
                SentenceTransformerEmbeddingFunction,
            )

            self._embedding_fn = SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )

            # PersistentClient keeps the index on disk between restarts
            self._client = chromadb.PersistentClient(path=self._persist_dir)
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=self._embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "✅ ChromaDB initialized. Collection '%s' has %d documents.",
                self.COLLECTION_NAME,
                self._collection.count(),
            )
        except ImportError:
            logger.debug("chromadb not installed — ChromaService disabled. FAISS is used instead.")
        except Exception as exc:
            logger.debug("ChromaDB initialization skipped: %s", exc)

    @property
    def available(self) -> bool:
        return self._collection is not None

    # ─────────────────────────────────────────────────────────────
    # Document ingestion
    # ─────────────────────────────────────────────────────────────

    def add_documents(
        self,
        texts: list[str],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ) -> int:
        """
        Add text chunks to the Chroma collection.

        Args:
            texts:     List of text strings to embed and store.
            metadatas: Optional per-chunk metadata dicts (subject, skill_level, …).
            ids:       Optional stable IDs; auto-generated if not provided.

        Returns the number of chunks successfully added.
        """
        if not self.available or not texts:
            return 0

        # Auto-generate IDs if not provided
        if ids is None:
            import hashlib, time
            base = str(time.time())
            ids = [
                hashlib.md5(f"{base}_{i}_{t[:40]}".encode()).hexdigest()
                for i, t in enumerate(texts)
            ]

        metas = metadatas or [{} for _ in texts]

        try:
            # Upsert so re-indexing is idempotent
            self._collection.upsert(
                documents=texts,
                metadatas=metas,
                ids=ids,
            )
            logger.info("ChromaDB: upserted %d chunks.", len(texts))
            return len(texts)
        except Exception as exc:
            logger.error("ChromaDB add_documents failed: %s", exc)
            return 0

    # ─────────────────────────────────────────────────────────────
    # Retrieval
    # ─────────────────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        k: int = 4,
        where: Optional[dict] = None,
    ) -> list[str]:
        """
        Semantic search for the most relevant chunks.

        Args:
            query: Natural-language query string.
            k:     Number of results to return.
            where: Optional metadata filter, e.g. {"subject": "python"}.

        Returns a list of matching text strings.
        """
        if not self.available or not query.strip():
            return []
        try:
            n = min(k, self._collection.count())
            if n == 0:
                return []
            kwargs: dict = {"query_texts": [query], "n_results": n}
            if where:
                kwargs["where"] = where
            results = self._collection.query(**kwargs)
            documents = results.get("documents", [[]])[0]
            return [d for d in documents if d]
        except Exception as exc:
            logger.error("ChromaDB retrieve failed: %s", exc)
            return []

    # ─────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────

    def count(self) -> int:
        """Return total number of stored chunks."""
        if not self.available:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0

    def delete_collection(self):
        """Delete the collection entirely (use with caution)."""
        if self._client and self.available:
            try:
                self._client.delete_collection(self.COLLECTION_NAME)
                self._collection = None
                logger.info("ChromaDB collection '%s' deleted.", self.COLLECTION_NAME)
            except Exception as exc:
                logger.error("ChromaDB delete_collection failed: %s", exc)
