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
from pathlib import Path, PurePosixPath

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


def _safe_filename(raw: str | None) -> str:
    r"""Turn a filename the browser sent into one we are willing to write to disk.

    The browser chooses this value, which means an attacker chooses it too. A
    name like "../../config.py" would walk straight out of the uploads directory
    and land on a real file. So we keep only the last piece of it and throw away
    every directory part.

    Taking the last piece at all is what stops the traversal, and that part works
    everywhere: "../../x.txt" becomes "x.txt" on any platform.

    The reason this replaces backslashes *first*, rather than just calling
    ``Path(raw).name``, is that ``Path`` means different things on different
    machines. On Windows both / and \ separate directories, so ``Path`` strips
    both. On Linux — which is what CI and any server run — a backslash is an
    ordinary character in a filename, so ``Path("..\..\x.txt").name`` hands
    back the whole string unchanged.

    On Linux that does not escape the directory: the file simply lands inside
    uploads/ under the literal, daft name "..\..\x.txt". Worth normalising anyway,
    for two reasons. The same upload should not produce two different stored
    filenames depending on which machine is running. And a name still carrying
    separators becomes a path again the moment anything Windows-shaped reads it.

    CI caught this, which is what CI is for — it runs on Linux and your laptop
    probably does not.
    """
    name = PurePosixPath((raw or "").replace("\\", "/")).name

    # "../.." leaves nothing behind, and "." and ".." are not usable names.
    if name in ("", ".", ".."):
        return "unnamed"

    return name


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
    filename = _safe_filename(file.filename)

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


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int):
    """Delete one document, and the chunks that belong to it.

    Contract, from docs/api.md: 204 with no body on success, 404 if there is
    no document with that id.

    Two things about this route are new. First, `{document_id}` in the path is
    a *path parameter* — FastAPI reads it out of the URL and hands it to this
    function, already converted to an int because that is what the type hint
    says. A request to /documents/abc is rejected before this code runs.

    Second, 204 means "done, there is nothing to send back". Returning None is
    correct here; do not return a {"deleted": true} body, because the status
    code already says that and the contract promises no body.

    The chunks go with the document through ON DELETE CASCADE, which db.py
    declares on the foreign key and get_db() enables with PRAGMA foreign_keys.
    Chosen over deleting from `chunks` by hand because it cannot be forgotten
    later: any future route that removes a document gets the same behaviour
    for free, whereas a hand-written DELETE has to be remembered every time.
    The risk of that choice — a dropped pragma silently doing nothing — is
    covered by a test in test_db.py and another through this route.

    The uploaded file in uploads/ is deliberately left on disk. Deleting it is
    not in the contract, and it would be wrong today: two uploads with the same
    name share one file (a known, accepted limitation of slice 1), so removing
    it here could take another document's file with it.
    """
    db = get_db()
    try:
        # Check it exists FIRST. In SQL, DELETE on a row that is not there
        # succeeds quietly and reports no error, so without this check a
        # request for a missing id would come back 204 instead of 404.
        row = db.execute("SELECT id FROM documents WHERE id = ?", (document_id,)).fetchone()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="That note isn't here. It may already have been deleted.",
            )

        db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        db.commit()
    finally:
        db.close()

    # Nothing is returned. FastAPI sends the 204 declared in the decorator.
