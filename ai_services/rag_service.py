"""
RAG Service — FAISS + ChromaDB Vector Stores + LangChain Document Loading
==========================================================================
Handles: document ingestion, chunking, embedding, dual-indexing, and retrieval.
All free and local — no external API calls for retrieval.

Dual vector-store strategy:
  - FAISS  : fast in-memory approximate nearest-neighbour search (IndexFlatIP)
  - Chroma : persistent on-disk store with metadata filtering support

Both stores are written on every ``add_document`` call so they stay in sync.
``retrieve()`` defaults to FAISS; call ``retrieve_chroma()`` for filtered search.
"""
import os
import logging
from pathlib import Path
from django.conf import settings

from .embedding_service import EmbeddingService
from .chroma_service import ChromaService

logger = logging.getLogger(__name__)


class RAGService:
    """
    Retrieval-Augmented Generation pipeline using FAISS.
    - Ingests PDFs, TXTs, DOCXs from the knowledge_base directory
    - Chunks text using LangChain's RecursiveCharacterTextSplitter
    - Embeds chunks with Sentence Transformers
    - Stores in FAISS index (persisted to disk)
    - Retrieves top-k relevant chunks for any query
    """

    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    INDEX_FILE = 'faiss.index'
    TEXTS_FILE = 'texts.pkl'

    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.chroma_service = ChromaService()   # dual vector store
        self.index = None
        self.texts = []
        self.index_dir = Path(getattr(settings, 'FAISS_INDEX_DIR',
                                      Path(settings.BASE_DIR) / 'faiss_index'))
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._load_index()

    def _index_path(self):
        return self.index_dir / self.INDEX_FILE

    def _texts_path(self):
        return self.index_dir / self.TEXTS_FILE

    def _load_index(self):
        """Load existing FAISS index from disk."""
        import pickle
        try:
            import faiss
            if self._index_path().exists() and self._texts_path().exists():
                self.index = faiss.read_index(str(self._index_path()))
                with open(self._texts_path(), 'rb') as f:
                    self.texts = pickle.load(f)
                logger.info(f"✅ FAISS index loaded: {len(self.texts)} chunks.")
            else:
                self.index = None
                self.texts = []
        except ImportError:
            logger.warning("FAISS not installed. RAG retrieval disabled.")
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}")
            self.index = None
            self.texts = []

    def _save_index(self):
        """Persist FAISS index to disk."""
        import pickle
        try:
            import faiss
            if self.index is not None:
                faiss.write_index(self.index, str(self._index_path()))
                with open(self._texts_path(), 'wb') as f:
                    pickle.dump(self.texts, f)
                logger.info(f"💾 FAISS index saved: {len(self.texts)} chunks.")
        except Exception as e:
            logger.error(f"Error saving FAISS index: {e}")

    def _index_knowledge_base(self):
        """Index all files in the knowledge_base directory on startup."""
        kb_dir = Path(getattr(settings, 'KNOWLEDGE_BASE_DIR',
                              Path(settings.BASE_DIR) / 'knowledge_base'))
        if not kb_dir.exists():
            return
        for filepath in kb_dir.rglob('*'):
            if filepath.suffix.lower() in ['.txt', '.pdf', '.docx', '.md']:
                try:
                    self.add_document(str(filepath))
                    logger.info(f"📄 Indexed: {filepath.name}")
                except Exception as e:
                    logger.warning(f"Could not index {filepath.name}: {e}")

    def _load_document(self, file_path: str) -> list[str]:
        """Load and split a document into text chunks."""
        ext = Path(file_path).suffix.lower()
        raw_text = ''

        try:
            if ext == '.txt' or ext == '.md':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_text = f.read()
            elif ext == '.pdf':
                try:
                    from pypdf import PdfReader
                    reader = PdfReader(file_path)
                    raw_text = '\n'.join(
                        page.extract_text() or '' for page in reader.pages
                    )
                except ImportError:
                    logger.warning("pypdf not installed. Cannot load PDF.")
            elif ext == '.docx':
                try:
                    import docx
                    doc = docx.Document(file_path)
                    raw_text = '\n'.join(p.text for p in doc.paragraphs)
                except ImportError:
                    logger.warning("python-docx not installed. Cannot load DOCX.")
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return []

        if not raw_text.strip():
            return []

        # Chunk the text
        return self._chunk_text(raw_text)

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=self.CHUNK_SIZE,
                chunk_overlap=self.CHUNK_OVERLAP,
                separators=['\n\n', '\n', '. ', ' ', '']
            )
            return splitter.split_text(text)
        except ImportError:
            # Manual chunking fallback
            chunks = []
            words = text.split()
            chunk_words = self.CHUNK_SIZE // 5  # approx words per chunk
            for i in range(0, len(words), chunk_words - 10):
                chunk = ' '.join(words[i:i + chunk_words])
                if chunk:
                    chunks.append(chunk)
            return chunks

    def add_document(self, file_path: str) -> int:
        """
        Index a new document into FAISS.
        Returns the number of chunks added.
        """
        import numpy as np
        chunks = self._load_document(file_path)
        if not chunks:
            return 0

        embeddings = self.embedding_service.embed(chunks)
        if embeddings is None:
            # Store text-only without embeddings (retrieval will use keyword fallback)
            self.texts.extend(chunks)
            return len(chunks)

        try:
            import faiss
            dim = embeddings.shape[1]
            embeddings = embeddings.astype('float32')

            if self.index is None:
                self.index = faiss.IndexFlatIP(dim)  # Inner product (cosine with normalized vecs)

            self.index.add(embeddings)
            self.texts.extend(chunks)
            self._save_index()

            # ── Dual-write to ChromaDB (silently skipped if not installed) ──
            if self.chroma_service.available:
                metadata = [{"source": file_path, "chunk_index": i} for i in range(len(chunks))]
                self.chroma_service.add_documents(chunks, metadatas=metadata)

            return len(chunks)
        except Exception as e:
            logger.error(f"FAISS indexing error: {e}")
            self.texts.extend(chunks)
            return len(chunks)

    def retrieve(self, query: str, k: int = 4) -> list[str]:
        """
        Retrieve top-k relevant text chunks for a query.
        Falls back to keyword search if FAISS is unavailable.
        """
        if not self.texts:
            self._index_knowledge_base()
        if not self.texts:
            return []

        # FAISS semantic search
        if self.index is not None and self.embedding_service.model is not None:
            try:
                import numpy as np
                query_emb = self.embedding_service.embed_single(query)
                if query_emb is not None:
                    query_emb = query_emb.reshape(1, -1).astype('float32')
                    distances, indices = self.index.search(query_emb, min(k, len(self.texts)))
                    results = []
                    for idx in indices[0]:
                        if 0 <= idx < len(self.texts):
                            results.append(self.texts[idx])
                    return results
            except Exception as e:
                logger.error(f"FAISS search error: {e}")

        # Keyword fallback
        query_words = set(query.lower().split())
        scored = []
        for chunk in self.texts:
            chunk_words = set(chunk.lower().split())
            score = len(query_words & chunk_words)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(reverse=True, key=lambda x: x[0])
        return [c for _, c in scored[:k]]

    def retrieve_chroma(
        self,
        query: str,
        k: int = 4,
        where: dict | None = None,
    ) -> list[str]:
        """
        Retrieve top-k relevant chunks from ChromaDB (with optional metadata filter).

        Example filter: ``where={"subject": "python"}``
        Falls back to FAISS ``retrieve()`` if Chroma is unavailable.
        """
        if self.chroma_service.available:
            results = self.chroma_service.retrieve(query, k=k, where=where)
            if results:
                return results
        # Fallback to FAISS
        return self.retrieve(query, k=k)
