"""
TechMart AI Support — Document Processor

Loads text files from the knowledge base directory and splits them
into smaller, overlapping chunks. Chunking is necessary because
embedding models and the LLM both work better with shorter, focused
pieces of text rather than one giant document.
"""

import logging
import os
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


class TextChunk:
    
    "A single chunk of text along with metadata about where it came from."

    def __init__(self, text: str, source: str, chunk_id: int):

        self.text = text

        self.source = source  # filename (without extension)

        self.chunk_id = chunk_id

        # Bundled metadata dict, stored alongside the vector in FAISS
        self.metadata = {"source": source, "chunk_id": chunk_id}

    def __repr__(self):

        return (f"TextChunk(source = {self.source}, id = {self.chunk_id}, len = {len(self.text)})")


def load_text_file(path: Path) -> str:
    
    "Read a .txt file and return its content, trying a few common encodings in order until one works. Handles files that aren't strictly UTF-8 (e.g. exported from Windows tools)."

    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:

        try:

            with open(path, "r", encoding = encoding, errors = "ignore") as f:

                return f.read()

        except Exception:

            # This encoding didn't work — try the next one
            continue

    raise ValueError(f"Could not read file: {path}")


def split_text(text: str, chunk_size: int = 600, chunk_overlap: int = 80) -> List[str]:
    
    """
    Split text into overlapping chunks by character count.
    Tries to break on a sentence boundary ('. ') near the target chunk
    size, so chunks don't end mid-sentence when possible.
    """

    chunks: List[str] = []

    start = 0

    text_len = len(text)

    while start < text_len:

        end = min(start + chunk_size, text_len)

        # If this isn't the final chunk, try to break on a sentence boundary
        if end < text_len:

            # Look for the last '. ' within the final 150 characters of this chunk
            look_back = text.rfind(". ", max(start, end - 150), end)

            if look_back != -1:

                end = look_back + 2  # include the period and the following space

        chunk = text[start:end].strip()

        if chunk:

            chunks.append(chunk)

        # Move the start position back by chunk_overlap so consecutive
        # chunks share some text — this helps preserve context across the split
        start = end - chunk_overlap

    return chunks


def load_knowledge_base(kb_dir: Path, chunk_size: int = 600, chunk_overlap: int = 80) -> Tuple[List[TextChunk], dict]:
    
    "Load every .txt file from the knowledge base directory, split each one into chunks, and return (all_chunks, per_file_stats)."

    if not kb_dir.exists():

        logger.warning(f"Knowledge base directory not found: {kb_dir}")

        return [], {}

    all_chunks: List[TextChunk] = []

    stats: dict = {}

    # Sorted so the processing order is stable/deterministic across runs
    txt_files = sorted(kb_dir.glob("*.txt"))

    if not txt_files:

        logger.warning(f"No .txt files found in {kb_dir}")

        return [], {}

    for txt_path in txt_files:

        try:

            raw_text = load_text_file(txt_path)

            source_name = txt_path.stem  # filename without the .txt extension

            text_chunks = split_text(raw_text, chunk_size, chunk_overlap)

            file_size = txt_path.stat().st_size

            # Wrap each chunk string in a TextChunk object with source metadata attached
            for idx, chunk_text in enumerate(text_chunks):

                all_chunks.append(TextChunk(chunk_text, source_name, idx))

            stats[source_name] = {

                "path": str(txt_path),

                "chunks": len(text_chunks),

                "file_size_bytes": file_size

            }

            logger.info(

                f"Loaded '{source_name}': {len(text_chunks)} chunks "

                f"({file_size} bytes)"

            )

        except Exception as e:

            import traceback

            # Don't let one bad file stop the whole knowledge base from loading —
            # log the error and move on to the next file
            logger.error(f"Failed to load {txt_path}: {e}")

            logger.error(traceback.format_exc())

    logger.info(

        f"Knowledge base loaded: {len(txt_files)} files → "

        f"{len(all_chunks)} total chunks"

    )

    return all_chunks, stats
