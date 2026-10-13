"""
HuggingFace Transformers Service
==================================
Provides local inference using Hugging Face `transformers` pipelines.

Used for:
  - Text classification (topic/subject tagging)
  - Summarisation fallback when Gemini is unavailable
  - Zero-shot classification of skill level from free-text

Models are loaded lazily on first use to avoid slowing startup.
All inference runs locally — no external API calls, completely free.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class HFService:
    """
    Thin wrapper around HuggingFace `transformers` pipelines.

    Lazy-loads each pipeline on first use to keep memory footprint
    low when a particular capability is not needed.
    """

    # ── Classifier: zero-shot topic / skill labelling ──────────────
    _ZERO_SHOT_MODEL = "typeform/distilbert-base-uncased-mnli"

    # ── Summariser: extractive/abstractive fallback ────────────────
    _SUMMARISER_MODEL = "sshleifer/distilbart-cnn-12-6"

    def __init__(self):
        self._classifier = None
        self._summariser = None

    # ─────────────────────────────────────────────────────────────
    # Zero-shot classification
    # ─────────────────────────────────────────────────────────────

    def _get_classifier(self):
        """Lazy-load zero-shot classification pipeline."""
        if self._classifier is None:
            try:
                from transformers import pipeline
                self._classifier = pipeline(
                    "zero-shot-classification",
                    model=self._ZERO_SHOT_MODEL,
                )
                logger.info("✅ HF zero-shot classifier loaded (%s).", self._ZERO_SHOT_MODEL)
            except Exception as exc:
                logger.warning("HF classifier unavailable: %s", exc)
        return self._classifier

    def classify_topic(
        self,
        text: str,
        candidate_labels: list[str],
        multi_label: bool = False,
    ) -> dict:
        """
        Classify `text` against `candidate_labels` using zero-shot inference.

        Returns:
            {
                "labels": [...],   # sorted by score descending
                "scores": [...],
                "best_label": "...",
            }
        Gracefully returns an empty dict if the model is unavailable.
        """
        classifier = self._get_classifier()
        if classifier is None:
            return {}
        try:
            result = classifier(text, candidate_labels, multi_label=multi_label)
            return {
                "labels": result["labels"],
                "scores": [round(s, 4) for s in result["scores"]],
                "best_label": result["labels"][0],
            }
        except Exception as exc:
            logger.error("Zero-shot classification failed: %s", exc)
            return {}

    def classify_skill_level(self, content: str) -> str:
        """
        Infer skill level (beginner / intermediate / advanced) from content.

        Useful for auto-tagging student-submitted notes or uploaded materials.
        """
        result = self.classify_topic(
            text=content[:512],  # truncate to model limit
            candidate_labels=["beginner level", "intermediate level", "advanced level"],
        )
        if not result:
            return "beginner"
        label: str = result.get("best_label", "beginner level")
        # Normalise to our enum
        if "advanced" in label:
            return "advanced"
        if "intermediate" in label:
            return "intermediate"
        return "beginner"

    # ─────────────────────────────────────────────────────────────
    # Summarisation
    # ─────────────────────────────────────────────────────────────

    def _get_summariser(self):
        """Lazy-load summarisation pipeline."""
        if self._summariser is None:
            try:
                from transformers import pipeline
                self._summariser = pipeline(
                    "summarization",
                    model=self._SUMMARISER_MODEL,
                )
                logger.info("✅ HF summariser loaded (%s).", self._SUMMARISER_MODEL)
            except Exception as exc:
                logger.warning("HF summariser unavailable: %s", exc)
        return self._summariser

    def summarise(
        self,
        text: str,
        max_length: int = 150,
        min_length: int = 40,
    ) -> Optional[str]:
        """
        Generate a short extractive summary of `text`.

        Returns None if the model is not available.
        Used as a local fallback when Gemini is offline.
        """
        summariser = self._get_summariser()
        if summariser is None:
            return None
        try:
            # DistilBART max input tokens ≈ 1024; truncate safely
            truncated = text[:3000]
            results = summariser(
                truncated,
                max_length=max_length,
                min_length=min_length,
                do_sample=False,
            )
            if results and results[0].get("summary_text"):
                return results[0]["summary_text"].strip()
        except Exception as exc:
            logger.error("HF summarisation failed: %s", exc)
        return None

    # ─────────────────────────────────────────────────────────────
    # Utility
    # ─────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        """Check if at least the zero-shot classifier can be loaded."""
        try:
            import transformers  # noqa: F401
            return True
        except ImportError:
            return False
