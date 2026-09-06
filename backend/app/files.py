"""Extract text from uploaded files (PDF, plain text, Markdown).

Nibble allows students to upload lecture notes and documents. This module
handles reading the raw bytes of an uploaded file and extracting its text
content page by page so it can be chunked, embedded, and searched.
"""

from io import BytesIO

from pypdf import PdfReader


def extract_text(data: bytes, filename: str) -> list[tuple[int, str]]:
    """Extract text from a file, returning a list of (page_number, text) tuples.

    Parameters:
        data: The raw binary bytes of the file.
        filename: The original name of the file (e.g. 'notes.pdf', 'lecture.txt').

    Returns:
        A list of tuples where each tuple is (page_number, page_text):
        - For PDFs: each page is extracted separately with 1-based page numbers.
        - For text files (.txt, .md): the entire content is returned as page 1.

    Raises:
        ValueError: If the file type/extension is unsupported or data is invalid.
    """
    name = filename.lower()

    if name.endswith(".pdf"):
        try:
            reader = PdfReader(BytesIO(data))
        except Exception as e:
            raise ValueError(f"Could not read PDF file '{filename}': {e}") from e

        pages: list[tuple[int, str]] = []
        for page_num, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            pages.append((page_num, text))
        return pages

    if name.endswith((".txt", ".md")):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")
        return [(1, text.strip())]

    raise ValueError(
        f"Unsupported file type for '{filename}'. Only .pdf, .txt, and .md files are supported."
    )
