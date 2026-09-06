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
Accepts `.pdf`, `.txt`, `.md`. Maximum 20 MB.

Returns `201` with a single document object, shaped as above.

Errors: `400` wrong file type · `413` too large.

### `DELETE /documents/{id}`

Deletes the document and all of its chunks. Returns `204` with no body.

Errors: `404` not found.

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
