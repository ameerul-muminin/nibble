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

import json
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from fastapi import APIRouter, HTTPException, UploadFile, status
from pydantic import BaseModel

from app import config, llm, ocr
from app.chunking import chunk_pages
from app.db import get_db
from app.embeddings import EmbeddingUnavailable, cosine_similarity, embed_texts
from app.files import IMAGE_EXTENSIONS, extract_text, has_no_text

router = APIRouter()

# 20 MB in bytes — the maximum upload size we accept.
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024

# Extensions we allow. Anything else is rejected with a 400.
_ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", *IMAGE_EXTENSIONS}

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
            detail=(
                f"Unsupported file type '{suffix}'. Upload a .pdf, .txt or .md file, "
                "or a photo of your notes (.png, .jpg, .jpeg, .webp)."
            ),
        )

    # --- Read the bytes and validate the size -----------------------------
    data = await file.read()
    if len(data) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File is too large. Maximum size is 20 MB.",
        )

    # --- Get the words out ------------------------------------------------
    # Two things can go wrong here and both need a sentence rather than a
    # traceback: the file is broken, or it is a scan and the reading service
    # is unavailable.
    try:
        pages = extract_text(data, filename)

        # A scanned or handwritten PDF has no text inside it, so every page
        # comes back empty. Without this, the upload would succeed, the note
        # would look completely normal in the list, and searching would find
        # nothing in it — a silent failure, which is the worst kind.
        if suffix == ".pdf" and has_no_text(pages):
            if not config.OCR_ENABLED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "There's no text in that PDF — it looks like a scan or a photo. "
                        "Reading handwriting is switched off right now, so try a PDF you "
                        "can select text in."
                    ),
                )
            if len(pages) > config.OCR_MAX_PAGES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"That scan is {len(pages)} pages, and Nibble reads up to "
                        f"{config.OCR_MAX_PAGES} at a time. Try splitting it up."
                    ),
                )
            pages = ocr.read_pdf(data)

    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ocr.OcrUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nibble couldn't read that page. {exc}",
        ) from exc

    # Even after all that, a photo of a blank page reads as nothing. Say so,
    # rather than storing an empty note that quietly never matches anything.
    if has_no_text(pages):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nibble couldn't find any writing in that. Is the picture clear enough?",
        )

    page_count = len(pages)

    # --- Cut it into searchable pieces ------------------------------------
    # Before slice 2 the text stopped here: it was extracted, counted, and
    # thrown away. A note in the list held a filename and a page count and not
    # one searchable word — and a scan had spent vision tokens on every page to
    # produce text that nothing kept.
    chunks = chunk_pages(pages)

    # A document with no pieces would upload cleanly, sit in the list looking
    # perfectly normal, and never match a single search — the same silent
    # failure that reading handwriting was built to remove, arriving a
    # different way. It happens when a file has text but every page of it is
    # shorter than MIN_CHUNK_CHARS: a deck of title-only slides, mostly.
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "There's too little writing in that to search. Nibble needs a few "
                "sentences on a page, not just headings."
            ),
        )

    # --- Turn every piece into numbers ------------------------------------
    # One call with every piece, not one call per piece. The model is far
    # faster on a batch, and a 31-page chapter is the difference between a
    # pause and a wait.
    #
    # This happens BEFORE anything is written, on purpose. If it fails, the
    # upload fails and nothing is stored — because a document whose pieces have
    # no vectors is a note that sits in the list and never matches a search,
    # which is the same silent failure reading handwriting and chunking both
    # exist to remove.
    try:
        vectors = embed_texts([chunk["content"] for chunk in chunks])
    except EmbeddingUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nibble couldn't get that note ready to search. {exc}",
        ) from exc

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
        doc_id = cursor.lastrowid

        # executemany runs one statement over many rows, instead of a Python
        # loop calling execute() a few hundred times. Same result, one trip.
        #
        # `embedding` is filled in from slice 3 onwards. SQLite has no array
        # type, so the 384 numbers go in as a JSON string — json.dumps here,
        # json.loads in /search, and that is the whole conversion.
        #
        # zip pairs each chunk with its vector. They line up because embed_texts
        # returns its answers in the order it was given them; that guarantee is
        # in its docstring and pinned by a test, and it is the only reason this
        # line is safe.
        db.executemany(
            "INSERT INTO chunks (document_id, page, content, embedding) VALUES (?, ?, ?, ?)",
            [
                (doc_id, chunk["page"], chunk["content"], json.dumps(vector))
                for chunk, vector in zip(chunks, vectors, strict=True)
            ],
        )

        # One commit for both statements, on purpose. Committing the document
        # first would leave a window where it exists with no pieces, and if the
        # chunk insert then failed, that window would never close — an upload
        # that looks finished and can never be searched. Either both land or
        # neither does.
        db.commit()
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
        # Delete first, then ask how many rows that actually removed. In SQL a
        # DELETE against a row that is not there succeeds quietly and reports
        # no error, so something has to distinguish the two cases — but it must
        # not be a separate SELECT beforehand. Two requests deleting the same id
        # would both pass that check, and the loser would delete nothing and
        # still answer 204. Asking the DELETE itself is one statement, so there
        # is no gap in between for anything to change.
        cursor = db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        db.commit()

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="That note isn't here. It may already have been deleted.",
            )
    finally:
        db.close()

    # Nothing is returned. FastAPI sends the 204 declared in the decorator.


# ---------------------------------------------------------------------------
# Slice 2 — Chunking
# ---------------------------------------------------------------------------


@router.get("/documents/{document_id}/chunks")
def list_chunks(document_id: int):
    """Return the pieces one document was cut into, in reading order.

    This endpoint exists mainly so chunking can be *seen*. Everything slice 2
    does happens invisibly inside the upload, and a feature you cannot look at
    is a feature you cannot tell is broken.

    Contract, from docs/api.md: a list of {id, page, content}, or 404 if there
    is no document with that id.

    The 404 is why this asks the database two questions instead of one. Selecting
    only from `chunks` cannot tell the difference between a document that does not
    exist and one that exists with no pieces — both come back as an empty list —
    and those two deserve different answers. Anything uploaded before slice 2 is
    genuinely the second case: a real document, with nothing stored under it.

    No ORDER BY, deliberately. The ids are handed out in insertion order and the
    upload inserts in reading order, so `ORDER BY id` and "the order they were
    written" are the same thing here. It is spelled out anyway, because relying on
    a database to return rows in any particular order without being asked is a
    habit that works right up until it does not.
    """
    db = get_db()
    try:
        document = db.execute("SELECT id FROM documents WHERE id = ?", (document_id,)).fetchone()

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="That note isn't here. It may already have been deleted.",
            )

        rows = db.execute(
            "SELECT id, page, content FROM chunks WHERE document_id = ? ORDER BY id",
            (document_id,),
        ).fetchall()
    finally:
        db.close()

    return [{"id": row["id"], "page": row["page"], "content": row["content"]} for row in rows]


# ---------------------------------------------------------------------------
# Slice 3 — Search, with no AI anywhere in it
# ---------------------------------------------------------------------------


class SearchRequest(BaseModel):
    """The body of a POST /search request: {"query": "how does osmosis work"}.

    This is the first request body in the project, and it is the first time
    Pydantic does any work for us. Everything before this took a file or an id
    out of the URL. Declaring the shape as a class means FastAPI reads the JSON,
    checks it has a `query` that is a string, and rejects anything else with a
    422 before this code runs — the same way `document_id: int` rejects
    /documents/abc.
    """

    query: str


def _retrieve(query: str) -> tuple[list[dict], list[int]]:
    """Find the pieces of the notes that mean the closest thing to some text.

    **No language model is involved anywhere in here.** This is retrieval on its
    own, and it is worth understanding before reading the ``/ask`` route below:
    everything that makes Nibble able to find the right page happens in this
    function. Slice 4 only adds the sentence on the end of it.

    Four steps, and none of them is clever:

    1. Turn the query into 384 numbers, the same way every piece was turned into
       384 numbers when it was uploaded.
    2. Read every piece that has an embedding out of the database.
    3. Score all of them at once against the query.
    4. Return the best TOP_K, highest first.

    Returns ``(results, unsearchable_note_ids)``. Raises ``EmbeddingUnavailable``
    if the model could not be loaded — each route catches that itself, because
    "Nibble couldn't search" and "Nibble couldn't answer" are different sentences
    to the person reading them.

    This lives outside a route because two routes need it. ``/search`` returns
    what it finds, and ``/ask`` hands what it finds to the model. Copying the
    body of one into the other would mean every future fix to how searching works
    has to be remembered twice, and the second copy is the one that gets missed.
    """
    query_vector = embed_texts([query])[0]

    db = get_db()
    try:
        # WHERE embedding IS NOT NULL is doing real work here. Anything stored
        # before slice 3 has no vector, and json.loads(None) raises. Skipping
        # those rows is the decision recorded in docs/scope.md — they are not
        # backfilled.
        rows = db.execute(
            """
            SELECT c.document_id, c.page, c.content, c.embedding, d.filename
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.embedding IS NOT NULL
            """
        ).fetchall()

        # ...and this is what stops that skip being silent. A note that can
        # never match anything, sitting in the list looking perfectly normal, is
        # the failure this project keeps having. Counting them lets the frontend
        # say so in a sentence instead.
        #
        # The ids rather than a COUNT, because a second kind of unsearchable
        # note is found below and the two sets have to be added together without
        # counting the same note twice.
        unsearchable_ids = {
            row["document_id"]
            for row in db.execute(
                "SELECT DISTINCT document_id FROM chunks WHERE embedding IS NULL"
            ).fetchall()
        }
    finally:
        db.close()

    # Every stored vector, back from JSON text into numbers.
    #
    # A vector of the wrong width is skipped here, and its note joins the
    # unsearchable count. This happens if EMBEDDING_MODEL and EMBEDDING_DIM are
    # ever changed: everything stored before the change was embedded at the old
    # width, and comparing a 384-number query against a 768-number piece is not
    # a close match or a distant one, it is a numpy shape error — a 500 with a
    # traceback, for every search, until somebody works out why.
    #
    # Treating it as "cannot be searched" rather than as an error reuses a
    # concept that already exists instead of adding a new one, and the fix the
    # UI already names is the right fix here too: delete the note and upload it
    # again.
    matrix = []
    comparable = []
    for row in rows:
        vector = json.loads(row["embedding"])
        if len(vector) != len(query_vector):
            unsearchable_ids.add(row["document_id"])
            continue
        matrix.append(vector)
        comparable.append(row)

    rows = comparable

    # The ids, not a count, and sorted so the answer is the same every time.
    #
    # A count cannot be reconciled with anything. Delete one of these notes and
    # the frontend has a number it can no longer trust: it does not know whether
    # the note it just deleted was one of the ones being counted, so it either
    # leaves a stale sentence on screen telling somebody to delete a note that is
    # already gone, or hides a true one. With ids it filters them exactly the way
    # it filters results, through the same set, and the number it shows is
    # counted from what is left.
    unsearchable_note_ids = sorted(unsearchable_ids)

    # No pieces to compare against is an ordinary state — a fresh install, a
    # database holding only pre-slice-3 notes, or one where every stored vector
    # was made by a different model. An empty list is a real answer.
    if not rows:
        return [], unsearchable_note_ids

    scores = cosine_similarity(query_vector, matrix)

    # argsort gives the positions that would sort the scores from low to high,
    # so [::-1] flips it to high-to-low and the slice takes the best few.
    best = scores.argsort()[::-1][: config.TOP_K]

    results = [
        {
            "document_id": rows[i]["document_id"],
            "filename": rows[i]["filename"],
            "page": rows[i]["page"],
            "content": rows[i]["content"],
            # Two conversions, both deliberate. float() because numpy's own
            # float32 is not JSON. max(0.0, ...) because a cosine runs -1 to
            # 1 and docs/api.md promises 0 to 1 — "less related than
            # unrelated" is not a distinction worth showing a student.
            "score": round(max(0.0, float(scores[i])), 3),
        }
        for i in best
    ]

    return results, unsearchable_note_ids


@router.post("/search")
def search(request: SearchRequest):
    """Show which pieces of your notes came closest to what you typed.

    All of the work is in ``_retrieve`` above. This route exists to make that
    work visible on its own, with no model anywhere near it — which is why it
    stays after slice 4 rather than being folded into ``/ask``. Being able to
    see the retrieval by itself is what makes the answer above it believable.

    Contract, from docs/api.md: {"results": [...], "unsearchable_note_ids": [...]}.
    """
    # A blank box is a person pressing enter, not an error worth a stack trace.
    # .strip() first, because "   " is blank to a human and truthy to Python.
    query = request.query.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type something to search for and Nibble will look through your notes.",
        )

    try:
        results, unsearchable_note_ids = _retrieve(query)
    except EmbeddingUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nibble couldn't search just now. {exc}",
        ) from exc

    return {"results": results, "unsearchable_note_ids": unsearchable_note_ids}


# ---------------------------------------------------------------------------
# Slice 4 — Nibble answers, from your notes, with the pages it used
# ---------------------------------------------------------------------------


class AskRequest(BaseModel):
    """The body of a POST /ask request: {"question": "explain osmosis simply"}."""

    question: str


# How much of a chunk goes into an excerpt on screen.
#
# The chip under an answer is there so somebody can tell at a glance which page
# a claim came from, then go and read it. A couple of sentences does that; the
# whole 900-character chunk would bury the answer it is supposed to support.
_EXCERPT_CHARS = 200


def _excerpt(content: str) -> str:
    """The first couple of sentences of a chunk, with an ellipsis if it was cut."""
    if len(content) <= _EXCERPT_CHARS:
        return content

    # rstrip() so the ellipsis does not end up after a space, which looks like a
    # mistake rather than a truncation.
    return content[:_EXCERPT_CHARS].rstrip() + "…"


@router.post("/ask")
def ask(request: AskRequest):
    """The endpoint the whole project exists for. Search the notes, then answer from them.

    This route is deliberately mostly glue, and that is the point of it. It does
    three things:

    1. Run exactly the same retrieval ``/search`` runs — the same function, not a
       copy of it.
    2. If nothing came back, say so and stop. **The model is not called at all**,
       which is why this check is before the call and not a special case inside
       it: there is no point paying for a request whose answer is already known,
       and a model handed no notes is a model with nothing to do but invent.
    3. Otherwise hand those pieces to llm.py and return what it says, along with
       the pages it was allowed to look at.

    Contract, from docs/api.md: {"answer": "...", "sources": [...]}.

    **``sources`` is what Nibble read, not what it happened to quote.** Working
    out which pages a sentence actually used would mean parsing citations back
    out of the answer, and guessing wrong there is worse than not guessing —
    it would either hide a page that was used or claim one that was not. What
    is honest, and checkable, is the list of pieces put in front of the model:
    every page it could possibly have drawn on is on screen, and nothing else
    was available to it. That is the sentence to say at the demo.
    """
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ask Nibble something and it will look through your notes.",
        )

    try:
        results, _unsearchable = _retrieve(question)
    except EmbeddingUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nibble couldn't read your notes just now. {exc}",
        ) from exc

    # Nothing to answer from. An empty database, or one holding only notes from
    # before search existed. This is a real answer rather than an error, and it
    # is returned without going anywhere near the model.
    if not results:
        return {
            "answer": "There's nothing in your notes about that yet. Add the chapter it "
            "should be in and ask me again.",
            "sources": [],
        }

    try:
        text = llm.answer(question, llm.build_context(results))
    except llm.AnswerUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nibble couldn't answer just now. {exc}",
        ) from exc

    return {
        "answer": text,
        "sources": [
            {
                "document_id": result["document_id"],
                "filename": result["filename"],
                "page": result["page"],
                "excerpt": _excerpt(result["content"]),
            }
            for result in results
        ],
    }
