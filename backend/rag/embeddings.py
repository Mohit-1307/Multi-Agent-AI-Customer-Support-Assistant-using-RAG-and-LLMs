"""
TechMart AI Support — Embeddings Manager

Uses sentence-transformers to turn text into dense vector embeddings,
which are what the FAISS retriever uses to find semantically similar
knowledge-base chunks for a given user query.
"""

import logging
from typing import List
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingManager:
    
    """
    Wraps sentence-transformers for generating embeddings.
    Uses a singleton pattern — only one model is loaded per process,
    since loading the model is relatively slow and memory-heavy.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):

        self.model_name = model_name

        # The actual model object — not loaded yet, see _load_model() below
        self._model = None

        logger.info(f"EmbeddingManager initialized (model will load on first use): {model_name}")

    def _load_model(self):
        
        "Lazily load the sentence-transformer model on first use, so app startup isn't slowed down if embeddings are never needed."

        if self._model is None:

            logger.info(f"Loading embedding model: {self.model_name}")

            from sentence_transformers import SentenceTransformer

            # Strip the "sentence-transformers/" HuggingFace prefix if present,
            # since the library expects just the bare model name
            clean_name = self.model_name.replace("sentence-transformers/", "")

            self._model = SentenceTransformer(clean_name)

            logger.info("Embedding model loaded successfully.")

        return self._model

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        
        """
        Generate embeddings for a list of texts.
        Returns a (N, dim) float32 numpy array, one row per input text.
        """

        model = self._load_model()

        embeddings = model.encode(

            texts,

            batch_size = 8,

            show_progress_bar = True,

            normalize_embeddings = True,  # normalized vectors make cosine similarity easier to compute

            convert_to_numpy = True

        )

        # Cast to float32 to keep memory usage down and match FAISS's expected dtype
        return embeddings.astype(np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        
        """
        Generate an embedding for a single query string.
        Returns a (1, dim) float32 numpy array.
        """

        return self.embed_texts([query])

    @property
    def embedding_dim(self) -> int:
        
        "The dimensionality of vectors this model produces (needed when creating the FAISS index)."

        model = self._load_model()

        return model.get_sentence_embedding_dimension()


# ------------------------------------------------------------------
# Module-level singleton, imported and reused by the retriever
# ------------------------------------------------------------------
_embedding_manager: EmbeddingManager | None = None


def get_embedding_manager(model_name: str = "all-MiniLM-L6-v2") -> EmbeddingManager:
    
    "Return the shared EmbeddingManager instance, creating it on first call."

    global _embedding_manager

    if _embedding_manager is None:

        _embedding_manager = EmbeddingManager(model_name)

    return _embedding_manager
