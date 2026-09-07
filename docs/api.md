# API contract

The agreement between frontend and backend. **Alif writes the entry here before
either side starts building a slice**, so Fahim and Arman can work at the same
time without waiting for each other.

Base URL in development: `http://localhost:8000`

A live, clickable version appears at <http://localhost:8000/docs> whenever the
backend is running. FastAPI generates it from the code, so it is never out of date.

---

## Slice 0 — built

### `GET /health`

Is the backend awake? The frontend calls this on page load.

```json
{ "status": "ok" }
```

---

## Slice 1 — built

### `GET /documents`

Every uploaded document, newest first.

```json
[
  {
    "id": 1,
    "filename": "biology-ch4.pdf",
    "page_count": 18,
    "created_at": "2026-08-07T09:14:22"
  }
]
```

### `POST /documents`

Upload a file. `multipart/form-data`, field name `file`.
Accepts `.pdf`, `.txt`, `.md`, and photos: `.png`, `.jpg`, `.jpeg`, `.webp`.
Maximum 20 MB.

Returns `201` with a single document object, shaped as above.

**A PDF with no text in it is a scan**, and Nibble reads it with a vision model
instead — see "Reading handwriting" below. That happens inside this one request,
so an upload of a scan takes seconds per page rather than being instant. The
frontend shows "Reading…" on the button for exactly this reason.

Errors:

| Code | When |
|---|---|
| `400` | Wrong file type |
| `400` | A scan, when reading handwriting is switched off |
| `400` | A scan longer than `OCR_MAX_PAGES` |
| `400` | Nothing readable found — a blank or unreadable photo |
| `413` | Larger than 20 MB |
| `503` | The reading service could not be reached, or the free daily limit is gone |
| `503` | The search model could not be loaded, so the note could not be made searchable |

Every one of those returns a `detail` written as a plain sentence for a person
to read. The frontend shows `detail` directly, so it must never contain SQL, a
stack trace, or a provider's own error text.

### `DELETE /documents/{id}`

Deletes the document and all of its chunks. Returns `204` with no body.

Errors: `404` not found.

---

## Reading handwriting and scans — built

Not a slice of its own. It sits inside `POST /documents` and changes no shape
here, which is the point: everything downstream still receives plain text and
never learns where it came from.

A typed PDF carries its words inside it and `pypdf` pulls them out. A scan, a
photo, or a page of handwriting carries **no words at all** — it is a picture.
`pypdf` returns empty strings, and without this the upload would succeed, the
note would look completely normal, and every search would find nothing in it.

So: if a PDF comes back with no text on any page, each page is drawn to a PNG
with `pypdfium2` and sent to Groq's vision model to be transcribed. Photos skip
the first step and go straight there. Free tier, same key as the chat model.

---

## Slice 2 — built

### `GET /documents/{id}/chunks`

The pieces a document was cut into, in the order they appear in the document.
Mostly so we can *see* that chunking worked.

```json
[
  { "id": 1, "page": 1, "content": "Osmosis is the net movement of water..." }
]
```

`page` is the real page the piece came from, and a piece never spans two pages —
that is what keeps the number honest all the way through to a source chip in
slice 4.

Consecutive pieces from the same page **overlap** — roughly `CHUNK_OVERLAP`
characters of one reappear at the start of the next. That is deliberate, not a bug
in the output: a sentence cut in half by a piece boundary still lands whole inside
at least one piece.

The overlap is "roughly" because each piece is trimmed of leading and trailing
whitespace, which shortens it by whatever whitespace sat on the boundary — a
character or two in ordinary prose. Where a boundary falls inside a long run of
blank space the overlap can vanish entirely, and that is harmless: nothing is
being split there, so there is nothing for an overlap to rescue. What holds
without exception is that no word is ever cut in two without landing whole in
some piece.

An empty array is a real answer — it means the document exists and has no pieces.
Anything uploaded before slice 2 is in exactly that state.

Errors: `404` not found — the same sentence as `DELETE`, because an id that is
not there is not there whichever way you ask.

**Chunking also happens inside `POST /documents`.** It changes no shape above: the
pieces are written in the same request that creates the document, and the response
is unchanged. Before slice 2 the extracted text was thrown away the moment the page
count had been taken from it.

---

## Slice 3 — built

### `POST /search`

Find the notes most relevant to some text. **No AI answer** — just the matching
pieces and how well each one matched.

Request:

```json
{ "query": "how does osmosis work" }
```

Response:

```json
{
  "results": [
    {
      "document_id": 1,
      "filename": "biology-ch4.pdf",
      "page": 4,
      "content": "Osmosis is the net movement of water...",
      "score": 0.82
    }
  ],
  "unsearchable_notes": 0
}
```

`results` holds at most `TOP_K` pieces (5), best match first. An empty list is a
real answer — nothing in your notes was close enough, or there is nothing to
search yet.

`score` runs from 0 to 1. Higher is a closer match. The raw measurement is a
cosine, which can technically come back negative for two pieces of text pointing
in opposite directions; anything below zero is reported as `0`, because "less
related than unrelated" is not a distinction worth showing anybody.

`unsearchable_notes` is how many uploaded notes **cannot be searched at all**,
because they were stored before search existed and have no embedding. It is
almost always `0`. When it is not, the frontend says so in a sentence — a note
that silently never matches anything is the exact failure this project keeps
having, and a count on screen is what stops it being silent. The fix is to delete
those notes and upload them again; nothing backfills them.

Errors:

| Code | When |
|---|---|
| `400` | The query is empty, or only whitespace |
| `503` | The embedding model could not be loaded |

Both return a `detail` written as a plain sentence, the same as everywhere else.

**Embedding also happens inside `POST /documents`.** It changes no shape there:
each piece is turned into 384 numbers in the same request that stores it, so an
upload gets slower and returns exactly what it returned before. It happens
*before* anything is written, so a note is never stored without its numbers — an
upload that cannot be embedded fails with the `503` above rather than landing in
the list as something no search can ever find.

---

## Slice 4 — planned

### `POST /ask`

The main endpoint. Searches, then asks the model to answer from what it found.

Request:

```json
{ "question": "explain osmosis simply" }
```

Response:

```json
{
  "answer": "Water moves across a membrane toward the side with more solute (p. 4).",
  "sources": [
    {
      "document_id": 1,
      "filename": "biology-ch4.pdf",
      "page": 4,
      "excerpt": "Osmosis is the net movement of water..."
    }
  ]
}
```

`sources` is empty when nothing relevant was found — and the answer says so
rather than guessing.

---

## Rules for changing this file

1. Alif writes the entry here **first**, before either side builds it.
2. If you need to change a shape that already exists, say so in the group chat
   before you write the code — someone else is building against it right now.
3. Update this file in the **same pull request** as the code, and say in the PR
   description what the other side needs to change.
