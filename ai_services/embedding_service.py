"""
Embedding Service — Sentence Transformers (Free, Local)
Converts text into dense vector embeddings for FAISS similarity search.
Model: all-MiniLM-L6-v2 (lightweight, fast, high quality)
Lazy loads model on demand to keep Django boot instant and prevent OOM/paging issues.
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Wraps Sentence Transformers for generating text embeddings.
    Runs fully locally — no API calls, completely free.
    Lazy loads the underlying model only when embedding is actually invoked.
    """

    MODEL_NAME = 'all-MiniLM-L6-v2'

    def __init__(self):
        self.model = None
        self._init_attempted = False

    def _get_model(self):
        if self._init_attempted:
            return self.model

        self._init_attempted = True
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.MODEL_NAME)
            logger.info(f"SentenceTransformer '{self.MODEL_NAME}' loaded successfully.")
        except ImportError:
            logger.warning("sentence-transformers not installed. Embeddings disabled.")
        except Exception as e:
            logger.warning(f"Could not load SentenceTransformer locally ({e}). Will use keyword search fallback.")
            self.model = None
        return self.model

    def embed(self, texts: list[str]) -> np.ndarray | None:
        """
        Embed a list of text strings.
        Returns numpy array of shape (n, embedding_dim).
        """
        model = self._get_model()
        if not model or not texts:
            return None
        try:
            embeddings = model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False,
                batch_size=32,
                normalize_embeddings=True
            )
            return embeddings
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return None

    def embed_single(self, text: str) -> np.ndarray | None:
        """Embed a single string."""
        result = self.embed([text])
        return result[0] if result is not None else None

    @property
    def dimension(self) -> int:
        """Return embedding vector dimension."""
        return 384  # all-MiniLM-L6-v2 output dim
