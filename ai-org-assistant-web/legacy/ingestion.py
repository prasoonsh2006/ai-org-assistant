"""
Extracts text from uploaded files (PDF, DOCX, TXT, CSV) and splits it into
overlapping chunks suitable for embedding + retrieval.
"""

import pandas as pd
from PyPDF2 import PdfReader
import docx
import io

from config import CHUNK_SIZE, CHUNK_OVERLAP


def extract_text(file_bytes: bytes, file_type: str) -> str:
    file_type = file_type.lower().strip(".")

    if file_type == "pdf":
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    if file_type == "docx":
        d = docx.Document(io.BytesIO(file_bytes))
        return "\n".join(p.text for p in d.paragraphs)

    if file_type == "txt":
        return file_bytes.decode("utf-8", errors="ignore")

    if file_type == "csv":
        df = pd.read_csv(io.BytesIO(file_bytes))
        # Turn tabular data into readable text for the RAG chat mode
        return df.to_string(index=False)

    raise ValueError(f"Unsupported file type for text extraction: {file_type}")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Splits text into overlapping word-based chunks."""
    words = text.split()
    if not words:
        return []

    chunks = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(words):
        chunk_words = words[start: start + chunk_size]
        chunk = " ".join(chunk_words).strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks
