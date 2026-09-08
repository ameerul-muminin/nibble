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
import sqlite3
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel

from app import config, llm, ocr, quiz
from app.auth import current_user_id
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
async def upload_document(file: UploadFile, user_id: str = Depends(current_user_id)):
    """Upload a PDF, TXT, or MD file and save it as a document.

    ``user_id`` is not something the caller sends. ``Depends(current_user_id)``
    makes FastAPI verify the Clerk token first and hand the route the id inside
    it — see auth.py. If the token is missing or bad, this function never runs.
    Every route below does the same thing, and the note is written out once here
    rather than repeated on each of them.

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
            "INSERT INTO documents (user_id, filename, page_count, created_at) VALUES (?, ?, ?, ?)",
            (user_id, filename, page_count, created_at),
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
def list_documents(user_id: str = Depends(current_user_id)):
    """Return the signed-in person's uploaded documents, newest first.

    "Every uploaded document" until slice 4.5, which is what a shared demo
    database looked like. The `WHERE` is the whole difference, and it is the
    reason two people can now use one deployed backend.
    """
    db = get_db()
    try:
        rows = db.execute(
            "SELECT id, filename, page_count, created_at FROM documents "
            "WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
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
def delete_document(document_id: int, user_id: str = Depends(current_user_id)):
    """Delete one of your own documents, and the chunks that belong to it.

    Contract, from docs/api.md: 204 with no body on success, 404 if there is
    no document with that id.

    **Somebody else's note is a 404, not a 403.** The `AND user_id = ?` below
    makes "does not exist" and "is not yours" the same answer, deliberately. A
    403 would be more precise and that is exactly the problem: it would confirm
    that the note exists, which lets anyone with the URL map out what other
    people have uploaded, one id at a time.

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
        cursor = db.execute(
            "DELETE FROM documents WHERE id = ? AND user_id = ?",
            (document_id, user_id),
        )
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
def list_chunks(document_id: int, user_id: str = Depends(current_user_id)):
    """Return the pieces one of your documents was cut into, in reading order.

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
        # This lookup is what makes the query below safe. Proving the document
        # is yours here means the chunks SELECT does not need its own ownership
        # check — the chunks of a document you own are yours by definition.
        document = db.execute(
            "SELECT id FROM documents WHERE id = ? AND user_id = ?",
            (document_id, user_id),
        ).fetchone()

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


def _retrieve(query: str, user_id: str) -> tuple[list[dict], list[int]]:
    """Find the pieces of *this person's* notes that mean the closest thing to some text.

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
        # d.user_id = ? is doing something bigger than it looks. Without it,
        # asking a question searches every note in the database, including other
        # people's — and because /ask hands what it finds to a model, the answer
        # would quote them. This one clause is the difference between a shared
        # demo and a private one.
        rows = db.execute(
            """
            SELECT c.document_id, c.page, c.content, c.embedding, d.filename
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.embedding IS NOT NULL
              AND d.user_id = ?
            """,
            (user_id,),
        ).fetchall()

        # ...and this is what stops that skip being silent. A note that can
        # never match anything, sitting in the list looking perfectly normal, is
        # the failure this project keeps having. Counting them lets the frontend
        # say so in a sentence instead.
        #
        # The ids rather than a COUNT, because a second kind of unsearchable
        # note is found below and the two sets have to be added together without
        # counting the same note twice.
        # The same ownership filter as above, and it needs the join to get one:
        # `chunks` has no user_id of its own, on purpose — it reaches its owner
        # through the document. Forgetting it here would be quiet and nasty
        # rather than loud: no other person's *content* would leak, but the
        # count of "notes Nibble can't search" would include theirs, so the UI
        # would tell you to go and delete notes that are not yours and that you
        # cannot see.
        unsearchable_ids = {
            row["document_id"]
            for row in db.execute(
                """
                SELECT DISTINCT c.document_id
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.embedding IS NULL
                  AND d.user_id = ?
                """,
                (user_id,),
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
def search(request: SearchRequest, user_id: str = Depends(current_user_id)):
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
        results, unsearchable_note_ids = _retrieve(query, user_id)
    except EmbeddingUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nibble couldn't search just now. {exc}",
        ) from exc

    return {"results": results, "unsearchable_note_ids": unsearchable_note_ids}


# ---------------------------------------------------------------------------
# Slice 4 — Nibble answers, from your notes, with the pages it used
# ---------------------------------------------------------------------------


class AskTurn(BaseModel):
    """One thing already said in this conversation, on the way back to us.

    ``role`` is a Literal rather than a plain string on purpose: Pydantic turns
    anything that is not "user" or "nibble" into a 422 before this code runs, the
    same way `document_id: int` rejects /documents/abc. It is the cheapest place
    to stop a browser sending a role of its own invention.

    "nibble" rather than "assistant" because that is the word the rest of the
    project uses. llm.py translates it on the way to the model.
    """

    role: Literal["user", "nibble"]
    content: str


class AskRequest(BaseModel):
    """The body of a POST /ask request.

    ``history`` is optional and defaults to empty, so an older frontend — or
    curl — still works exactly as it did.
    """

    question: str
    history: list[AskTurn] = []


def _recent_turns(history: list[AskTurn]) -> list[dict]:
    """The last few turns, trimmed, as plain dicts.

    Two limits, and both exist because this came from a browser.

    ``ASK_HISTORY_TURNS`` takes the most recent turns rather than the first
    ones: a follow-up is about what was just said, and an hour-old exchange is
    noise wearing the costume of context.

    ``ASK_HISTORY_CHARS`` cuts each one. Without it, a long enough transcript
    pushes the retrieved notes out of what the model can hold — which is the one
    way to make Nibble answer from something that is not your notes, arriving
    through the front door.

    **Nibble's own turns are thrown away here, and that is a security decision
    rather than a tidying one.** The browser sends back a transcript it claims is
    this conversation, and nothing about it can be verified: the backend stores
    no conversations, so it has no copy to check against. A turn labelled
    "nibble" is therefore just text a client asserted Nibble once said.

    Passed on to the model as an assistant message, that text is trusted — it
    reads as something the model itself concluded earlier. So a crafted request
    could put a fabricated claim, or an instruction, into the model's own mouth
    and have the answer built on it — while the reply comes back wearing a list
    of note sources, which says the answer came from the student's notes. That
    is precisely the guarantee this whole project exists to make.

    Keeping only the `user` turns closes it completely, and costs almost
    nothing: what a follow-up needs is the subject, and the subject is in the
    questions. "what are the experiments" then "name them" resolves fine with no
    assistant turn anywhere near it.

    The API still *accepts* `nibble` turns, because the frontend sends the
    transcript it is drawing and rejecting half of it would be a strange
    contract. They are accepted and ignored.
    """
    recent = history[-config.ASK_HISTORY_TURNS :] if config.ASK_HISTORY_TURNS else []

    return [
        {"role": turn.role, "content": turn.content.strip()[: config.ASK_HISTORY_CHARS]}
        for turn in recent
        if turn.role == "user" and turn.content.strip()
    ]


def _search_text(question: str, turns: list[dict]) -> str:
    """What we actually embed and search for, which is not always the question.

    **This function is the fix for the worst bug slice 4 shipped with.** Somebody
    asked "What are the experiments?", got an answer, then typed "name them" —
    and Nibble replied with one unrelated item. It read like the model inventing
    things. It was not. "name them" was embedded on its own, and two words with
    no subject match nothing in particular, so search returned near-random
    pieces and the model answered from those. It did exactly as it was told.

    So the question is searched together with what was recently asked, and
    "name them" goes looking for the experiments again.

    **Only the `user` turns.** Nibble's own answers are deliberately left out,
    and that is the non-obvious half. Feeding a model's replies back into the
    search makes each question drift toward what it has already said — it finds
    the pages it already used, answers from them again, and gets more confident
    about a wrong turn every time. Searching for what the *person* asked keeps
    the conversation anchored to them.

    **History is only used for a question that cannot stand on its own.** Joining
    it onto every question was wrong, and wrong in a way that showed up the first
    time somebody had two subjects in one Nibble. Ask about a database chapter,
    then ask "for the CSE 224 lab, name the six experiments", and the database
    questions were still glued to the front of the search — so the search went
    looking for something half about databases, and pieces of the wrong chapter
    came back and were handed to the model as if they were relevant.

    A question long enough to name its own subject does not need the ones before
    it. "name them" does; "for the CSE 224 lab, can you name the 6 experiments"
    plainly does not, and is only hurt by it.

    Word count is a blunt way to tell those apart, and it is chosen over anything
    cleverer precisely because it can be explained in one line and predicted
    without running it. It is not perfect: a short question that *does* change
    the subject — "summarise the DB chapter" — still picks up the previous ones.
    That failure is smaller than the one it replaces and is written down in
    docs/scope.md rather than hidden here.
    """
    asked = [turn["content"] for turn in turns if turn["role"] == "user"]

    if not asked or len(question.split()) > config.ASK_FOLLOWUP_MAX_WORDS:
        return question

    return " ".join([*asked, question])


def _dedupe_sources(results: list[dict]) -> list[dict]:
    """One entry per page, keeping the best-scoring piece of each.

    Retrieval works on pieces, and one page often supplies two of them. Shown
    raw, that is "p. 1" listed twice under an answer with two different
    excerpts, which reads as a bug to anybody who notices it.

    This runs **after** the model has been given everything. It does not change
    what Nibble read — only what is listed on screen — so the claim the sources
    list makes stays true.

    ``results`` arrives sorted best-first, so the first time a page is seen is
    its best piece, and every later one is dropped.
    """
    seen = set()
    unique = []

    for result in results:
        key = (result["filename"], result["page"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)

    return unique


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
def ask(request: AskRequest, user_id: str = Depends(current_user_id)):
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

    # What was recently said, and what to search for because of it. A first
    # question searches for itself; a follow-up searches for itself plus what
    # led to it. See _search_text above for why that matters so much.
    turns = _recent_turns(request.history)

    try:
        results, _unsearchable = _retrieve(_search_text(question, turns), user_id)
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
        text = llm.answer(question, llm.build_context(results), history=turns)
    except llm.AnswerUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nibble couldn't answer just now. {exc}",
        ) from exc

    # Deduplicated only now, after the model has seen every piece. What it read
    # is unchanged; this is about what the list on screen looks like.
    return {
        "answer": text,
        "sources": [
            {
                "document_id": result["document_id"],
                "filename": result["filename"],
                "page": result["page"],
                "excerpt": _excerpt(result["content"]),
            }
            for result in _dedupe_sources(results)
        ],
    }


# ---------------------------------------------------------------------------
# Slice 6 — Quiz yourself
# ---------------------------------------------------------------------------
#
# Six routes, and every one starts the same way: prove the quiz is yours, then
# do the work. That repetition is why _own_quiz below exists.
#
# There is no route for TAKING a quiz, and that is a decision rather than an
# omission. GET /quizzes/{id} returns `correct` — it is your quiz, made from
# your notes — so the browser already holds the answer key and marks as you go.
# Solo practice therefore stores nothing: the score is on screen, and closing
# the tab ends it. Marks are only stored for a classroom, where somebody other
# than you needs to see them, and that is slice 8.


class QuizRequest(BaseModel):
    """The body of POST /quizzes: which note, what to call it, how many."""

    document_id: int
    title: str
    count: int = config.QUIZ_QUESTION_COUNT


class QuestionPatch(BaseModel):
    """The body of PATCH on a question. Every field optional — send what changed.

    ``options`` and ``correct`` are checked together in the route rather than
    here, because the rule is about the pair and not about either one on its
    own. Pydantic validates fields; a rule spanning two of them belongs where it
    can see both.
    """

    prompt: str | None = None
    options: list[str] | None = None
    correct: int | None = None


def _own_quiz(db, quiz_id: int, user_id: str) -> None:
    """Raise 404 unless this quiz exists and belongs to this person.

    **Not found and not yours are deliberately the same answer.** Telling
    somebody a quiz exists but is not theirs confirms the id is real, which is
    an invitation to go looking. It is also the honest answer: a quiz that is
    not yours is, as far as you are concerned, not there. Same reasoning and
    same sentence as GET /documents/{id}/chunks.
    """
    row = db.execute(
        "SELECT id FROM quizzes WHERE id = ? AND user_id = ?",
        (quiz_id, user_id),
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That quiz isn't here. It may already have been deleted.",
        )


def _questions_of(db, quiz_id: int) -> list[dict]:
    """Every question of one quiz, in the order they are asked.

    ORDER BY position, then id. The second is a tie-breaker that stops two
    questions sharing a position from swapping places between requests —
    positions are unique today, but a later edit that reorders them should not
    be able to make a quiz render differently on a refresh.
    """
    rows = db.execute(
        "SELECT id, position, prompt, options, correct, page FROM questions "
        "WHERE quiz_id = ? ORDER BY position, id",
        (quiz_id,),
    ).fetchall()

    return [
        {
            "id": row["id"],
            "position": row["position"],
            "prompt": row["prompt"],
            "options": json.loads(row["options"]),
            "correct": row["correct"],
            "page": row["page"],
        }
        for row in rows
    ]


@router.post("/quizzes", status_code=status.HTTP_201_CREATED)
def create_quiz(request: QuizRequest, user_id: str = Depends(current_user_id)):
    """Write a quiz from one of your notes. Calls the model, so it takes a moment.

    Contract, from docs/api.md: the quiz with its questions, 201.

    **This is scoped to one note, and that turns out to matter more than it
    looks.** /ask searches every note you own, and with two chapters uploaded it
    retrieves pieces of the wrong one — the dilution measured under Slice 4.6.
    A quiz takes a document_id, so that problem cannot arise here.
    """
    title = request.title.strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Give the quiz a name so you can find it again.",
        )

    if not 1 <= request.count <= config.QUIZ_MAX_QUESTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Nibble writes between 1 and {config.QUIZ_MAX_QUESTIONS} questions at a time."
            ),
        )

    db = get_db()
    try:
        # Ownership first, and through the document rather than the quiz —
        # there is no quiz yet. Without this, anybody could build a quiz out of
        # somebody else's note and read its contents back through the questions.
        document = db.execute(
            "SELECT id, filename FROM documents WHERE id = ? AND user_id = ?",
            (request.document_id, user_id),
        ).fetchone()

        if document is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="That note isn't here. It may already have been deleted.",
            )

        chunks = db.execute(
            "SELECT page, content FROM chunks WHERE document_id = ? ORDER BY id",
            (request.document_id,),
        ).fetchall()

        if not chunks:
            # A note from before slice 2 has no pieces, so there is nothing to
            # write questions from. 422 rather than 400: the request was fine,
            # the stored note is the problem, and re-uploading is the fix.
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    "That note was added before Nibble could read it properly. "
                    "Delete it and upload it again, then make a quiz from it."
                ),
            )

        pieces = [
            {"filename": document["filename"], "page": row["page"], "content": row["content"]}
            for row in chunks
        ]
        pages = {row["page"] for row in chunks}
    finally:
        db.close()

    # The model call happens with no database connection open. It takes seconds,
    # and SQLite holds a lock for as long as a connection lives — so waiting on
    # the network with one open is how two people generating quizzes at the same
    # moment turn into one of them seeing "database is locked".
    try:
        questions = quiz.make_questions(quiz.build_prompt(pieces), request.count, pages)
    except quiz.QuizUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Nibble couldn't write questions just now. {exc}",
        ) from exc

    created_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S")
    db = get_db()
    try:
        # **The note was checked before the model call, and this is after it.**
        # In between, several seconds passed with no connection open — long
        # enough for another tab to delete that note. The foreign key is ON, so
        # inserting against a document that is gone raises IntegrityError, and
        # uncaught that is a 500 with a traceback for something the person did
        # deliberately in the next window along.
        #
        # Catching rather than re-checking, because a re-check is the same race
        # one line further down: the note could go between the SELECT and the
        # INSERT. The constraint is the only thing that can answer this without
        # a gap, so the constraint is what gets asked.
        try:
            cursor = db.execute(
                "INSERT INTO quizzes (user_id, document_id, title, created_at) VALUES (?, ?, ?, ?)",
                (user_id, request.document_id, title, created_at),
            )
        except sqlite3.IntegrityError as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "That note was deleted while Nibble was writing the questions, "
                    "so there is nothing to attach them to."
                ),
            ) from exc

        quiz_id = cursor.lastrowid

        db.executemany(
            "INSERT INTO questions (quiz_id, position, prompt, options, correct, page) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    quiz_id,
                    position,
                    question["prompt"],
                    json.dumps(question["options"]),
                    question["correct"],
                    question["page"],
                )
                for position, question in enumerate(questions)
            ],
        )
        db.commit()

        stored = _questions_of(db, quiz_id)
    finally:
        db.close()

    return {
        "id": quiz_id,
        "document_id": request.document_id,
        "title": title,
        "created_at": created_at,
        "questions": stored,
    }


@router.get("/quizzes")
def list_quizzes(user_id: str = Depends(current_user_id)):
    """Every quiz you own, newest first. No questions — this is the list you pick from.

    ``question_count`` comes from a LEFT JOIN rather than a query per quiz. With
    ten quizzes that difference is invisible; it is written this way because the
    other version gets slower the more you use the app, and that is a bad habit
    to leave in a file people copy from.

    LEFT rather than INNER, so a quiz whose questions were somehow all deleted
    still appears showing 0. An INNER JOIN would hide it, and a quiz you cannot
    see is a quiz you cannot delete.
    """
    db = get_db()
    try:
        rows = db.execute(
            """
            SELECT q.id, q.document_id, q.title, q.created_at,
                   COUNT(x.id) AS question_count
            FROM quizzes q
            LEFT JOIN questions x ON x.quiz_id = q.id
            WHERE q.user_id = ?
            GROUP BY q.id
            ORDER BY q.id DESC
            """,
            (user_id,),
        ).fetchall()
    finally:
        db.close()

    return [
        {
            "id": row["id"],
            "document_id": row["document_id"],
            "title": row["title"],
            "question_count": row["question_count"],
            "created_at": row["created_at"],
        }
        for row in rows
    ]


@router.get("/quizzes/{quiz_id}")
def get_quiz(quiz_id: int, user_id: str = Depends(current_user_id)):
    """One quiz and all its questions, in order, with the answers.

    ``correct`` is included because it is your quiz, made from your notes — the
    single rule from docs/scope.md is that seeing answers follows ownership. It
    is what lets practice work with no other route and nothing stored.
    """
    db = get_db()
    try:
        _own_quiz(db, quiz_id, user_id)

        row = db.execute(
            "SELECT id, document_id, title, created_at FROM quizzes WHERE id = ?",
            (quiz_id,),
        ).fetchone()

        questions = _questions_of(db, quiz_id)
    finally:
        db.close()

    return {
        "id": row["id"],
        "document_id": row["document_id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "questions": questions,
    }


@router.patch("/quizzes/{quiz_id}/questions/{question_id}")
def update_question(
    quiz_id: int,
    question_id: int,
    patch: QuestionPatch,
    user_id: str = Depends(current_user_id),
):
    """Fix a question the model got wrong. Send only what changed.

    **Sending options without correct is a 400, and it is the important rule in
    this slice.** ``correct`` is a POSITION in ``options``, not the text of the
    right answer. Replace the list without restating which entry is right and
    the index points at whatever now sits in that slot — so the quiz still
    renders, still marks, and marks the wrong thing. Nothing looks broken, for
    one person practising or for a whole class at once.

    One-directional on purpose: ``correct`` may be sent alone, because changing
    which entry is right does not disturb the list it points into. Only changing
    the list invalidates the index. So fixing a mis-keyed answer stays a
    one-field request.
    """
    if patch.options is not None and patch.correct is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Say which of the new options is the right one. The answer is stored as "
                "a position in the list, so changing the list without it would leave the "
                "answer pointing at the wrong line."
            ),
        )

    if patch.options is not None:
        if len(patch.options) != quiz.OPTION_COUNT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A question needs exactly {quiz.OPTION_COUNT} options.",
            )
        if not all(option.strip() for option in patch.options):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="None of the options can be blank.",
            )
        # The same rule quiz._validate_one applies to a generated question, and
        # it was missing here — so a question Nibble would have refused to write
        # could be typed in by hand. Two identical options means two identical
        # buttons where only one of them scores, which is unanswerable and reads
        # as the app being broken rather than the question being bad.
        #
        # Worth stating as a principle: an edit must not be able to produce a
        # question that generation would have thrown away. Anywhere those two
        # sets of rules disagree, the looser one is a bug.
        if len({option.strip() for option in patch.options}) != quiz.OPTION_COUNT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Every option has to be different from the others.",
            )

    if patch.correct is not None and not 0 <= patch.correct < quiz.OPTION_COUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The right answer has to be one of the {quiz.OPTION_COUNT} options.",
        )

    if patch.prompt is not None and not patch.prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A question needs something to ask.",
        )

    db = get_db()
    try:
        _own_quiz(db, quiz_id, user_id)

        existing = db.execute(
            "SELECT id FROM questions WHERE id = ? AND quiz_id = ?",
            (question_id, quiz_id),
        ).fetchone()

        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="That question isn't here. It may already have been deleted.",
            )

        # Built rather than written out, because three optional fields make
        # seven combinations and writing them all out is how one gets forgotten.
        changes: list[str] = []
        values: list[object] = []

        if patch.prompt is not None:
            changes.append("prompt = ?")
            values.append(patch.prompt.strip())

        if patch.options is not None:
            changes.append("options = ?")
            values.append(json.dumps([option.strip() for option in patch.options]))

        if patch.correct is not None:
            changes.append("correct = ?")
            values.append(patch.correct)

        if changes:
            values.extend([question_id, quiz_id])
            db.execute(
                f"UPDATE questions SET {', '.join(changes)} WHERE id = ? AND quiz_id = ?",
                values,
            )
            db.commit()

        row = db.execute(
            "SELECT id, position, prompt, options, correct, page FROM questions WHERE id = ?",
            (question_id,),
        ).fetchone()
    finally:
        db.close()

    return {
        "id": row["id"],
        "position": row["position"],
        "prompt": row["prompt"],
        "options": json.loads(row["options"]),
        "correct": row["correct"],
        "page": row["page"],
    }


@router.delete("/quizzes/{quiz_id}/questions/{question_id}", status_code=204)
def delete_question(quiz_id: int, question_id: int, user_id: str = Depends(current_user_id)):
    """Drop a question that came out wrong.

    The remaining questions keep their ``position`` values rather than being
    renumbered. Nothing reads them as a count, only as an order, so renumbering
    would be work that could only introduce a bug.

    Deleting the last question is refused: an empty quiz is the same non-result
    as a generation that produced nothing, and it would sit in the list looking
    takeable. Delete the quiz instead.
    """
    db = get_db()
    try:
        _own_quiz(db, quiz_id, user_id)

        existing = db.execute(
            "SELECT id FROM questions WHERE id = ? AND quiz_id = ?",
            (question_id, quiz_id),
        ).fetchone()

        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="That question isn't here. It may already have been deleted.",
            )

        remaining = db.execute(
            "SELECT COUNT(*) AS n FROM questions WHERE quiz_id = ?",
            (quiz_id,),
        ).fetchone()["n"]

        if remaining <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "That's the last question. Delete the whole quiz instead of "
                    "leaving an empty one."
                ),
            )

        db.execute("DELETE FROM questions WHERE id = ? AND quiz_id = ?", (question_id, quiz_id))
        db.commit()
    finally:
        db.close()


@router.delete("/quizzes/{quiz_id}", status_code=204)
def delete_quiz(quiz_id: int, user_id: str = Depends(current_user_id)):
    """Delete a quiz and its questions.

    The questions go through ON DELETE CASCADE rather than a second DELETE here
    — which only works because get_db turns foreign keys on for every
    connection. Without that PRAGMA this would silently leave every question
    behind, attached to a quiz that no longer exists.
    """
    db = get_db()
    try:
        _own_quiz(db, quiz_id, user_id)
        db.execute("DELETE FROM quizzes WHERE id = ? AND user_id = ?", (quiz_id, user_id))
        db.commit()
    finally:
        db.close()
