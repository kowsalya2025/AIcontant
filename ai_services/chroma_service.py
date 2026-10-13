"""
ChromaDB Vector Store Service
==============================
An alternative / additive vector store alongside FAISS.

ChromaDB provides:
  - Persistent on-disk storage (no separate save/load cycle)
  - Metadata filtering (subject, skill_level, student_id)
  - HTTP client mode for scaled deployments
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from django.conf import settings

logger = logging.getLogger(__name__)


def _get_default_persist_dir():
    try:
        base_dir = getattr(settings, 'BASE_DIR', Path.cwd())
        return str(Path(base_dir) / "chroma_index")
    except Exception:
        return str(Path.cwd() / "chroma_index")


class ChromaService:
    """
    Wraps ChromaDB for persistent semantic search.
    Initializes lazily on first call to prevent blocking server boot.
    """

    COLLECTION_NAME = "eduai_knowledge"

    def __init__(self, persist_dir: Optional[str] = None):
        self._persist_dir = persist_dir or _get_default_persist_dir()
        self._client = None
        self._collection = None
        self._embedding_fn = None
        self._init_attempted = False

    def _initialize(self):
        if self._init_attempted:
            return
        self._init_attempted = True

        try:
            import chromadb
            from chromadb.utils.embedding_functions import (
                SentenceTransformerEmbeddingFunction,
            )

            self._embedding_fn = SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )

            self._client = chromadb.PersistentClient(path=self._persist_dir)
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=self._embedding_fn,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB initialized successfully.")
        except ImportError:
            logger.debug("chromadb not installed — ChromaService disabled.")
        except Exception as exc:
            logger.debug("ChromaDB initialization skipped: %s", exc)

    @property
    def available(self) -> bool:
        self._initialize()
        return self._collection is not None

    def add_documents(
        self,
        documents: list[str],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ) -> int:
        if not self.available or not documents:
            return 0

        import uuid
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        if metadatas is not None:
            clean_metadatas = []
            for meta in metadatas:
                clean_meta = {}
                for k, v in meta.items():
                    if isinstance(v, (str, int, float, bool)):
                        clean_meta[k] = v
                    elif v is None:
                        clean_meta[k] = ""
                    else:
                        clean_meta[k] = str(v)
                clean_metadatas.append(clean_meta)
            metadatas = clean_metadatas

        try:
            self._collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids,
            )
            return len(documents)
        except Exception as exc:
            logger.error("ChromaDB add_documents failed: %s", exc)
            return 0

    def retrieve(
        self,
        query: str,
        k: int = 4,
        where: Optional[dict] = None,
    ) -> list[str]:
        if not self.available or not query.strip():
            return []

        try:
            kwargs: dict = {"query_texts": [query], "n_results": k}
            if where:
                kwargs["where"] = where

            results = self._collection.query(**kwargs)
            docs = results.get("documents", [[]])
            return docs[0] if docs else []
        except Exception as exc:
            logger.error("ChromaDB retrieve failed: %s", exc)
            return []
