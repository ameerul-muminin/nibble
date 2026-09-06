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

## Slice 2 — planned

### `GET /documents/{id}/chunks`

The pieces a document was cut into. Mostly so we can *see* that chunking worked.

```json
[
  { "id": 1, "page": 1, "content": "Osmosis is the net movement of water..." }
]
```

---

## Slice 3 — planned

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
  ]
}
```

`score` runs from 0 to 1. Higher is a closer match.

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
