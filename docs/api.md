# API contract

The agreement between frontend and backend. **Agree on changes here before
writing code**, so both sides can work at the same time.

Base URL in development: `http://localhost:8000`

A live, clickable version is generated automatically at
<http://localhost:8000/docs> whenever the backend is running.

---

## `GET /health`

Is the server up and can it reach the database?

```json
{ "status": "ok" }
```

## `GET /documents`

Every document belonging to the current user, newest first.

```json
[
  {
    "id": "9f1c...",
    "filename": "biology-ch4.pdf",
    "status": "ready",
    "page_count": 18,
    "created_at": "2026-08-07T09:14:22Z"
  }
]
```

`status` is one of `processing`, `ready`, `failed`.

## `POST /documents`

Upload a file. `multipart/form-data`, field name `file`.
Accepts `.pdf`, `.txt`, `.md`. Maximum 20 MB.

Returns `201` with a single document object, shaped as above.

Errors: `400` wrong file type · `413` too large.

## `DELETE /documents/{id}`

Deletes the document and all of its chunks. Returns `204` with no body.

Errors: `404` not found, or it belongs to someone else.

## `POST /chat/ask`

The main endpoint.

Request:

```json
{
  "question": "explain osmosis simply",
  "session_id": null
}
```

Send `session_id: null` for a new conversation; reuse the id you get back to
continue the same one.

Response:

```json
{
  "session_id": "3ab8...",
  "answer": "Water moves across a membrane toward the side with more solute (p. 4).",
  "sources": [
    {
      "document_id": "9f1c...",
      "filename": "biology-ch4.pdf",
      "page": 4,
      "excerpt": "Osmosis is the net movement of water..."
    }
  ]
}
```

`sources` is empty when nothing relevant was found — the answer will say so
rather than guess.

---

## Rules for changing this file

1. Propose the change in the group chat before you build it.
2. Update this file **and** `backend/app/schemas/dto.py` in the same pull request.
3. Say clearly in the PR description what the other side needs to change.
