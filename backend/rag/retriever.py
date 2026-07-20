"""
TechMart AI Support — FAISS Retriever

Builds and queries a FAISS vector index over the knowledge-base chunks,
enabling semantic search: given a user's question, find the most
relevant pieces of text from the knowledge base to use as context.
"""

import logging
import os
import pickle
from pathlib import Path
from typing import List, Optional, Tuple
import numpy as np
from ..config import settings
from .document_processor import TextChunk, load_knowledge_base
from .embeddings import EmbeddingManager, get_embedding_manager

logger = logging.getLogger(__name__)


class RetrievalResult:
    
    "One retrieved chunk, along with its relevance score."

    def __init__(self, text: str, source: str, score: float, chunk_id: int):

        self.text = text

        self.source = source

        self.score = score  # distance score — lower means more relevant for this index type

        self.chunk_id = chunk_id

    def __repr__(self):

        return f"RetrievalResult(source={self.source}, score={self.score:.3f})"


class FAISSRetriever:
    
    "Builds a FAISS flat-L2 index and enables semantic search over knowledge-base chunks. The index and chunk data are saved to disk so they can be reloaded on the next app startup without rebuilding."

    def __init__(self):

        self.index = None

        self.chunks: List[TextChunk] = []

        self.embedder: Optional[EmbeddingManager] = None

        self._ready = False

        self._index_path = settings.VECTOR_STORE_PATH / "faiss.index"

        self._chunks_path = settings.VECTOR_STORE_PATH / "chunks.pkl"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def build_index(self, force_rebuild: bool = False) -> dict:
        
        """
        Load the knowledge base and build (or reload) the FAISS index.
        If a saved index already exists on disk and force_rebuild is False,
        it's reloaded instead of rebuilt from scratch — much faster.
        Returns a stats dict describing what happened.
        """

        import faiss

        self.embedder = get_embedding_manager(settings.EMBEDDING_MODEL)

        # Try to reload from disk first, unless the caller explicitly wants a fresh rebuild
        if (

            not force_rebuild

            and self._index_path.exists()

            and self._chunks_path.exists()

        ):

            try:

                self._load_from_disk()

                logger.info(f"Reloaded FAISS index from disk ({len(self.chunks)} chunks).")

                self._ready = True

                return {"status": "reloaded", "chunks": len(self.chunks)}

            except Exception as e:

                # If the saved index is corrupted or incompatible, fall through and rebuild
                logger.warning(f"Failed to reload index from disk: {e}. Rebuilding.")

        # ------------------------------------------------------------------
        # Build a fresh index from the raw knowledge-base text files
        # ------------------------------------------------------------------
        logger.info("Building FAISS index from knowledge base...")

        chunks, file_stats = load_knowledge_base(

            settings.KNOWLEDGE_BASE_DIR,

            settings.CHUNK_SIZE,

            settings.CHUNK_OVERLAP

        )

        if not chunks:

            logger.error("No chunks to index. Knowledge base may be empty.")

            return {"status": "error", "chunks": 0}

        self.chunks = chunks

        texts = [c.text for c in chunks]

        logger.info(f"Generating embeddings for {len(texts)} chunks...")

        embeddings = self.embedder.embed_texts(texts)

        dim = embeddings.shape[1]

        # Flat L2 index — exact nearest-neighbor search using Euclidean distance
        self.index = faiss.IndexFlatL2(dim)

        self.index.add(embeddings)

        # Save the index and chunk data to disk so future startups can reload instead of rebuilding
        self._save_to_disk()

        self._ready = True

        total_docs = len(set(c.source for c in chunks))

        logger.info(f"FAISS index built: {len(chunks)} chunks across {total_docs} documents.")

        return {

            "status": "built",

            "chunks": len(chunks),

            "documents": total_docs,

            "file_stats": file_stats

        }

    def retrieve(self, query: str, top_k: int = None, source_filter: Optional[List[str]] = None) -> List[RetrievalResult]:
        
        """
        Semantic search: return the top-k most relevant chunks for a query.
        Optionally filter results down to one or more source documents
        (e.g. an agent's relevant_sources list). Pass a single-item list
        to filter to one source, or None/[] to search the whole knowledge base.
        """

        if not self._ready or self.index is None:

            logger.warning("Retriever not ready. Call build_index() first.")

            return []

        k = top_k or settings.TOP_K_RESULTS

        query_emb = self.embedder.embed_query(query)  # shape: (1, dim)

        # When filtering by source, search for more candidates than needed
        # up front, since some of them will get discarded by the filter below
        search_k = k * 5 if source_filter else k

        scores, indices = self.index.search(query_emb, min(search_k, len(self.chunks)))

        results: List[RetrievalResult] = []

        for score, idx in zip(scores[0], indices[0]):

            # FAISS returns -1 for empty slots when there aren't enough results
            if idx < 0 or idx >= len(self.chunks):

                continue

            chunk = self.chunks[idx]

            # Support both dict-based and TextChunk-object chunk storage,
            # in case older saved indexes used a different chunk format
            if isinstance(chunk, dict):

                chunk_text = chunk.get("text", "")

                chunk_source = chunk.get("source", "unknown")

                chunk_id = chunk.get("chunk_id", idx)

            else:

                chunk_text = chunk.text

                chunk_source = chunk.source

                chunk_id = chunk.chunk_id

            # Skip this result if it doesn't match any of the requested source(s)
            if source_filter and chunk_source not in source_filter:

                continue

            results.append(

                RetrievalResult(

                    text = chunk_text,

                    source = chunk_source,

                    score = float(score),

                    chunk_id = chunk_id

                )

            )

            # Stop as soon as we have enough results after filtering
            if len(results) >= k:

                break

        return results

    def format_context(self, results: List[RetrievalResult]) -> str:
        
        "Format a list of retrieval results into a single context string, ready to be inserted into the LLM's system prompt."

        if not results:

            return ""

        parts = []

        for i, r in enumerate(results, 1):

            # Turn "refund_policy" into "Refund Policy" for a cleaner label
            source_label = r.source.replace("_", " ").title()

            parts.append(f"[Source: {source_label}]\n{r.text}")

        return "\n\n---\n\n".join(parts)

    @property
    def is_ready(self) -> bool:
        
        "True once the index has been built or successfully reloaded."

        return self._ready

    @property
    def chunk_count(self) -> int:
        
        "Total number of chunks currently indexed."

        return len(self.chunks)

    # ------------------------------------------------------------------
    # Private helpers — saving/loading the index to/from disk
    # ------------------------------------------------------------------
    def _save_to_disk(self):
        
        "Persist the FAISS index and chunk metadata to disk."

        import faiss

        # Make sure the target directory exists before writing to it
        self._index_path.parent.mkdir(parents = True, exist_ok = True)

        faiss.write_index(self.index, str(self._index_path))

        with open(self._chunks_path, "wb") as f:

            pickle.dump(self.chunks, f)

        logger.info(f"FAISS index saved to {self._index_path}")

    def _load_from_disk(self):
        
        "Load a previously saved FAISS index and its chunk metadata."

        import faiss

        self.index = faiss.read_index(str(self._index_path))

        with open(self._chunks_path, "rb") as f:

            self.chunks = pickle.load(f)

        self.embedder = get_embedding_manager(settings.EMBEDDING_MODEL)


# ------------------------------------------------------------------
# Module-level singleton, shared across the whole app
# ------------------------------------------------------------------
_retriever: Optional[FAISSRetriever] = None


def get_retriever() -> FAISSRetriever:
    
    "Return the shared FAISSRetriever instance, creating it on first call."

    global _retriever

    if _retriever is None:

        _retriever = FAISSRetriever()

    return _retriever