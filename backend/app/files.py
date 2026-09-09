"""Extract text from uploaded files (PDF, plain text, Markdown).

Nibble allows students to upload lecture notes and documents. This module
handles reading the raw bytes of an uploaded file and extracting its text
content page by page so it can be chunked, embedded, and searched.
"""

from io import BytesIO

from pypdf import PdfReader

from app import ocr

# Pictures of pages: a phone photo of handwritten notes, or a screenshot.
# These have no text to extract, so they always go through the vision model.
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def extract_text(data: bytes, filename: str) -> list[tuple[int, str]]:
    """Extract text from a file, returning a list of (page_number, text) tuples.

    Parameters:
        data: The raw binary bytes of the file.
        filename: The original name of the file (e.g. 'notes.pdf', 'lecture.txt').

    Returns:
        A list of tuples where each tuple is (page_number, page_text):
        - For PDFs: each page is extracted separately with 1-based page numbers.
          A PDF that is a scan has no text in it, so every page comes back
          empty — see has_no_text() and the upload route, which then reads the
          pages as pictures instead.
        - For text files (.txt, .md): the entire content is returned as page 1.
        - For images (.png, .jpg, .jpeg, .webp): read by the vision model and
          returned as page 1, because a photo is one page.

    Raises:
        ValueError: If the file type/extension is unsupported or data is invalid.
    """
    name = filename.lower()

    if name.endswith(".pdf"):
        try:
            reader = PdfReader(BytesIO(data))
        except Exception as e:
            # Whatever pypdf says here is written for whoever is debugging
            # pypdf. It went straight through routes.py into a sentence a
            # student reads, which is the rule in CLAUDE.md about never showing
            # a raw exception, broken by accident. `from e` keeps the real cause
            # attached to the traceback for anybody reading a server log.
            raise ValueError(
                f"Nibble couldn't open '{filename}'. It may be damaged or "
                "password-protected — try re-saving it and uploading again."
            ) from e

        pages: list[tuple[int, str]] = []
        for page_num, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            pages.append((page_num, text))
        return pages

    if name.endswith(IMAGE_EXTENSIONS):
        # A photo of a page is all picture and no text, so there is nothing to
        # pull out here — it goes straight to the vision model. Returned as a
        # single page, because a photo is one page by definition.
        return [(1, ocr.read_image(data))]

    if name.endswith((".txt", ".md")):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            text = data.decode("utf-8", errors="replace")
        return [(1, text.strip())]

    raise ValueError(
        f"Unsupported file type for '{filename}'. "
        "Upload a .pdf, .txt, .md, or a photo (.png, .jpg, .jpeg, .webp)."
    )


def has_no_text(pages: list[tuple[int, str]]) -> bool:
    """Did this file turn out to be a picture of writing rather than writing?

    True when there is not a single character on any page. That is what a
    scanned or photographed PDF looks like coming out of pypdf: the right
    number of pages, every one of them empty.

    Worth being strict about "not a single character". Some scans carry a stray
    page number or a header from the scanner software, and a document where one
    page has three characters and forty have none is still a scan — but this is
    the honest, simple version, and the upload route falls back on it rather
    than guessing at a threshold nobody could defend.
    """
    return all(not text.strip() for _, text in pages)
