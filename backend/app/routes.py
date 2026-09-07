"""Every URL the frontend can call.

Fahim owns this file. Each slice adds one or two more functions here, and the
shape never changes:

    @router.get("/some-url")     <- which URL, and which HTTP verb
    def some_name():             <- a completely normal Python function
        return {"hello": "world"} <- whatever you return becomes JSON

That is the whole idea. A route reads the request, does a small amount of
work (or asks another file to do it), and returns something.

Keep routes short. When a route starts doing real thinking — chunking text,
comparing numbers, calling the model — that logic belongs in its own file and
the route just calls it. It keeps this file readable and makes the logic
testable without starting a server.
"""

from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.db import get_db
from app.files import extract_text

router = APIRouter()

# 20 MB in bytes — the maximum upload size we accept.
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024

# Extensions we allow. Anything else is rejected with a 400.
_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".text", ".markdown"}

# Where uploaded files are saved on disk.
_UPLOADS_DIR = Path("uploads")


@router.get("/health")
def health():
    """Is the backend awake?

    The frontend calls this the moment the page loads, so you find out
    immediately if the server isn't running. Deliberately does nothing else —
    if this ever fails, the problem is the server itself, not your code.
    """
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Slice 1 — Upload and list
# ---------------------------------------------------------------------------


@router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile):
    """Upload a PDF, TXT, or MD file and save it as a document.

    The route reads the file, validates the extension and size, calls
    extract_text to pull out the words, saves the file to disk, inserts a
    row into the documents table, and returns the new document.
    """
    # --- Validate the extension -------------------------------------------
    filename = file.filename or "unnamed"
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{suffix}'. Upload a .pdf, .txt, or .md file.",
        )

    # --- Read the bytes and validate the size -----------------------------
    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File is too large. Maximum size is 20 MB.",
        )

    # --- Extract text to get the page count -------------------------------
    pages = extract_text(data, filename)
    page_count = len(pages)

    # --- Save the file to disk --------------------------------------------
    _UPLOADS_DIR.mkdir(exist_ok=True)
    (Path(_UPLOADS_DIR) / filename).write_bytes(data)

    # --- Insert into the database -----------------------------------------
    created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO documents (filename, page_count, created_at) VALUES (?, ?, ?)",
            (filename, page_count, created_at),
        )
        db.commit()
        doc_id = cursor.lastrowid
    finally:
        db.close()

    return {
        "id": doc_id,
        "filename": filename,
        "page_count": page_count,
        "created_at": created_at,
    }


@router.get("/documents")
def list_documents():
    """Return every uploaded document, newest first."""
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, filename, page_count, created_at FROM documents ORDER BY id DESC"
        ).fetchall()
    finally:
        db.close()

    return [
        {
            "id": row["id"],
            "filename": row["filename"],
            "page_count": row["page_count"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Slice 4 — Nibble answers, with sources
# ---------------------------------------------------------------------------


class AskRequest(BaseModel):
    """The shape of a POST /ask request body."""

    question: str


@router.post("/ask")
def ask_question(body: AskRequest):
    """The main endpoint. Search the notes, then ask the model to answer.

    1. Call search_chunks to find the five most relevant pieces of the
       student's notes.
    2. Hand those pieces plus the question to ask_with_sources, which builds
       a prompt and calls the Groq API.
    3. Return the answer and which files/pages it came from.

    If no documents have been uploaded or no relevant chunks are found, the
    answer says so and sources is empty.
    """
    # Late imports — these modules depend on Slices 2/3 which your friend
    # built. The late import keeps the app startable even if those modules
    # are not merged yet (only this route would fail, not the whole server).
    from app.embeddings import search_chunks
    from app.llm import ask_with_sources

    question = body.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question cannot be empty.",
        )

    # --- Step 1: find relevant chunks -------------------------------------
    try:
        results = search_chunks(question)
    except Exception:
        # If embeddings aren't set up yet (no documents uploaded, model not
        # downloaded, etc.), treat it as "nothing found".
        results = []

    # --- Step 2: ask the model --------------------------------------------
    try:
        answer_data = ask_with_sources(question, results)
    except RuntimeError as exc:
        # Missing API key or Groq failure — tell the frontend clearly.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    return answer_data
