"""Embedding adapter with deterministic fallback."""
import os
import hashlib
import numpy as np
from typing import List
import logging

logger = logging.getLogger(__name__)

class EmbedAdapter:
    def __init__(self, api_key: str = None, model: str = "all-MiniLM-L6-v2"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        # Try to import sentence_transformers for local fallback if available
        self.local_model = None
        try:
            from sentence_transformers import SentenceTransformer
            self.local_model = SentenceTransformer(model)
        except ImportError:
            logger.info("sentence-transformers not installed, using deterministic fallback")

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embed a list of texts."""
        # 1. Try Local Model (preferred for offline/testing if installed)
        if self.local_model:
            return self.local_model.encode(texts)
        
        # 2. Try API (if implemented/configured - placeholder for now as Gemini embedding API usage varies)
        # For this Phase 1, we prioritize local or deterministic fallback as requested.
        
        # 3. Deterministic Fallback
        return self._deterministic_fallback(texts)

    def _deterministic_fallback(self, texts: List[str]) -> np.ndarray:
        """Generate deterministic random vectors based on text hash."""
        dim = 384 # Standard for MiniLM
        vectors = []
        for text in texts:
            # Seed based on text content
            seed = int(hashlib.sha256(text.encode('utf-8')).hexdigest(), 16) % (2**32)
            rng = np.random.RandomState(seed)
            vec = rng.randn(dim)
            # Normalize
            vec = vec / np.linalg.norm(vec)
            vectors.append(vec)
        return np.array(vectors, dtype=np.float32)
