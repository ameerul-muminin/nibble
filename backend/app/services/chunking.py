"""Turn a file into a list of text chunks.

Why chunk at all? An LLM has a size limit on what you can hand it, and
retrieval works better on small focused pieces than on a whole 40-page PDF.
We cut with overlap so a sentence that straddles a boundary still lands
whole inside at least one chunk.
"""

from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader

from app.core.config import get_settings


@dataclass
class TextChunk:
    ordinal: int
    page: int
    content: str


def extract_pages(data: bytes, filename: str) -> list[str]:
    """Return one string per page. Plain text files count as a single page."""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(BytesIO(data))
        return [(page.extract_text() or "").strip() for page in reader.pages]
    return [data.decode("utf-8", errors="replace")]


def chunk_pages(pages: list[str]) -> list[TextChunk]:
    settings = get_settings()
    size, overlap = settings.chunk_size, settings.chunk_overlap
    step = max(size - overlap, 1)

    chunks: list[TextChunk] = []
    ordinal = 0
    for page_no, text in enumerate(pages, start=1):
        cleaned = " ".join(text.split())
        if not cleaned:
            continue
        for start in range(0, len(cleaned), step):
            piece = cleaned[start : start + size]
            if len(piece) < 40:  # skip scraps
                continue
            chunks.append(TextChunk(ordinal=ordinal, page=page_no, content=piece))
            ordinal += 1
    return chunks
