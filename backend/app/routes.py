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

from app.db import get_db
from app.files import extract_text

router = APIRouter()

# 20 MB in bytes — the maximum upload size we accept.
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024

# Extensions we allow. Anything else is rejected with a 400.
_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}

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

    This is the one ``async def`` route in the project, and the only one that
    should be. Every other route is a plain ``def`` so there is no async to
    explain. The exception is here because reading an upload is ``await
    file.read()`` — FastAPI hands us the file as something you have to await,
    and there is no sync equivalent. If you write a new route, write ``def``.
    """
    # --- Work out a filename we can trust ---------------------------------
    # The browser sends the filename, which means an attacker can send anything
    # they like. A name like "../../config.py" would walk straight out of the
    # uploads directory and overwrite a real file. Path(...).name throws away
    # every directory part and keeps only the last piece, so "../../x.txt"
    # becomes "x.txt". Never write a path built from a value the client sent.
    filename = Path(file.filename or "unnamed").name

    # --- Validate the extension -------------------------------------------
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
    (Path(_UPLOADS_DIR) / filename).write_bytes(data)  # filename is already cleaned above

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
