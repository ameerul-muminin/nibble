# API contract

The agreement between frontend and backend. **Alif writes the entry here before
either side starts building a slice**, so Fahim and Arman can work at the same
time without waiting for each other.

Base URL in development: `http://localhost:8000`

A live, clickable version appears at <http://localhost:8000/docs> whenever the
backend is running. FastAPI generates it from the code, so it is never out of date.

---

## Authentication — every route below except `GET /health`

From Slice 4.5, the backend knows who is calling and answers only about that
person's notes. Two people signed into different Clerk accounts share a backend
and see nothing of each other's.

**The frontend sends the Clerk session token on every request:**

```
Authorization: Bearer <clerk session token>
```

`api.js` does this for you — it asks Clerk for a fresh token before each call, so
no component builds this header by hand. A token is short-lived by design and
Clerk refreshes it; nothing caches one.

**The backend verifies the signature** against Clerk's public keys and reads the
`sub` claim. That claim is the user id, and it is the only thing about a person
this project stores. No email, no name.

Every protected route can therefore return one status that is not listed in its
own table below:

| Status | When |
| --- | --- |
| `401` | No `Authorization` header, or a token that is missing, expired, or not signed by Clerk |

**A note belonging to someone else is a `404`, not a `403`.** `GET
/documents/4/chunks` and `DELETE /documents/4` both answer "no document with
that id" whether the id does not exist or simply is not yours. A `403` would
confirm it exists, which is a thing worth not saying.

`GET /health` is deliberately open. The host's health check calls it, and it says
nothing about anybody.

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
  "unsearchable_note_ids": []
}
```

`results` holds at most `TOP_K` pieces (5), best match first. An empty list is a
real answer — nothing in your notes was close enough, or there is nothing to
search yet.

`score` runs from 0 to 1. Higher is a closer match. The raw measurement is a
cosine, which can technically come back negative for two pieces of text pointing
in opposite directions; anything below zero is reported as `0`, because "less
related than unrelated" is not a distinction worth showing anybody.

`unsearchable_note_ids` names the uploaded notes that **cannot be searched at
all**. It is usually empty. A note lands in it for one of two reasons: it was
stored before search existed and has no embedding, or its stored numbers were
made by a different embedding model and are the wrong width to compare against
anything. Both mean the same thing to a person, and both have the same fix —
delete that note and upload it again. Nothing backfills them.

The frontend shows the length of this list in a sentence, because a note that
silently never matches anything is the exact failure this project keeps having.

**It is a list of ids rather than a count on purpose.** The frontend has to
reconcile it with deletions, and a bare number cannot be reconciled: delete one
of these notes and the number cannot say whether that note was one of the ones it
counted, so the page either keeps telling somebody to delete a note that is
already gone, or hides a warning that is still true. With ids it filters this
list exactly the way it filters `results`, and counts what is left.

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

## Slice 4 — built

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

**`sources` is what Nibble read, not what it quoted.** It is the same pieces
`POST /search` would return for that question, capped at the same `TOP_K`, and
they are the only thing the model was shown. Working out which pages a given
sentence actually used would mean parsing the citations back out of the answer,
and being wrong there is worse than not guessing: it would either hide a page
that was used or claim one that was not. Show these as the pages it read.

`excerpt` is the first 200 characters of the piece, with `…` on the end if it
was cut. It is there to point at a page, not to reprint it.

**A refusal is a normal `200`.** When the notes do not cover the question the
answer says so — "That isn't in your notes yet." — and `sources` still lists what
was read, because seeing what it had is how somebody understands why it could
not answer. Never render that as an error.

When there is nothing to answer from at all — no notes uploaded, or only notes
stored before search existed — the answer says so, `sources` is `[]`, and **the
model is not called at all.**

| Status | When |
| --- | --- |
| `200` | An answer, a refusal, or "nothing in your notes about that yet" |
| `400` | The question is empty, or only whitespace |
| `503` | The embedding model could not be loaded, or the answering service could not be reached |

---

## Slice 6 — planned

Quizzes. Nibble reads one of your notes and writes multiple-choice questions from
it, each carrying the page it came from. **Anyone can do this** — it is part of the
regular app, not a teacher feature. Slice 7 adds rooms on top, and a room runs a
quiz that already exists.

**One rule governs the answer key, everywhere:** `correct` follows ownership. You
can always see the answers to a quiz you own, because it was made from your notes.
You can never see the answers to somebody else's quiz you are sitting a room for —
slice 7's student endpoint strips the field out entirely.

### `POST /quizzes`

Generate a quiz from one of your own notes. This calls the language model, so it
takes a few seconds.

Request:

```json
{ "document_id": 1, "title": "Chapter 4 — Cells", "count": 5 }
```

`count` is optional and defaults to 5. It must be between 1 and 10; the ceiling is
Groq's free tier, which caps output at 1,000 tokens per minute and reserves against
the requested maximum, so ten questions is already most of a minute's allowance.

Response, `201`:

```json
{
  "id": 3,
  "document_id": 1,
  "title": "Chapter 4 — Cells",
  "created_at": "2026-09-08T14:02:11",
  "questions": [
    {
      "id": 11,
      "position": 0,
      "prompt": "What drives water across a semi-permeable membrane?",
      "options": ["Active transport", "Osmosis", "Mitosis", "Respiration"],
      "correct": 1,
      "page": 4
    }
  ]
}
```

`correct` is the index into `options`, `0` to `3`. `page` is the page of your note
the question came from, and it is shown while editing so the question can be
checked against what the page actually says — the same claim `POST /ask` makes with
its sources.

**Questions come only from the note.** If a chapter cannot support `count`
questions, fewer come back rather than invented ones. An empty list is never
returned; that is a `503` instead, because a quiz with no questions is not a
result, it is a failure that looks like one.

Errors:

| Status | When |
| --- | --- |
| `400` | `count` is outside 1-10, or the title is empty |
| `404` | No note with that id, or it is not yours |
| `422` | The note has no chunks — it was uploaded before Slice 2. Delete it and upload it again |
| `503` | The answering service could not be reached, or returned something that was not a usable quiz |

### `GET /quizzes`

Every quiz you own, newest first. No questions in the response — this is the list
you pick from.

```json
[
  {
    "id": 3,
    "document_id": 1,
    "title": "Chapter 4 — Cells",
    "question_count": 5,
    "created_at": "2026-09-08T14:02:11"
  }
]
```

### `GET /quizzes/{id}`

One quiz and all of its questions, in `position` order. Same shape as the `POST`
response, **`correct` included** — it is your quiz.

This is the endpoint practice uses. The browser holds the key and marks your
answers as you go, which is why practising alone needs no other route and stores
nothing. Close the tab and the score is gone.

Errors: `404` not found, or not yours.

### `PATCH /quizzes/{id}/questions/{qid}`

Customise a question. Send only the fields you are changing — with one exception,
which is the next paragraph and is not optional.

```json
{ "prompt": "Which process moves water across a membrane?", "correct": 1 }
```

**Sending `options` requires sending `correct` with it.** `correct` is a *position*
in `options`, not the text of the right answer. So replacing the list without
restating which entry is right leaves an index pointing at whatever now happens to
sit in that slot — reorder four options, or rewrite them, and the answer key is
silently wrong. Nothing looks broken: the quiz still renders, still marks, and
marks the wrong thing, for one person practising and for a whole class at once.
`options` on its own is a `400`.

The rule is deliberately one-directional. `correct` **may** be sent alone, because
changing which entry is right does not disturb the list it points into; it is only
changing the list that invalidates the index. So fixing a mis-keyed answer stays a
one-field request.

`options` is always the whole array of exactly four strings — individual options
cannot be patched one at a time, for the same reason.

Returns the updated question.

Errors:

| Status | When |
| --- | --- |
| `400` | `options` was sent without `correct` |
| `400` | `correct` is not 0-3, `options` is not four strings, or a field is empty |
| `404` | No such quiz or question, or the quiz is not yours |

### `DELETE /quizzes/{id}/questions/{qid}`

Drop a question that came out wrong. `204`, no body. The remaining questions keep
their `position` values rather than being renumbered — nothing reads them as a
count, only as an order.

Deleting the last question of a quiz is refused with a `400`, because an empty quiz
is the same non-result as a generation that produced nothing. Delete the quiz
instead.

Errors: `400` as above, `404` not found or not yours.

### `DELETE /quizzes/{id}`

Deletes the quiz and its questions. `204`, no body.

Errors: `404` not found, or not yours.

**Deleting a note deletes the quizzes made from it**, through `ON DELETE CASCADE`,
the same way it already takes the note's chunks. That is worth knowing before
someone tidies up their notes the morning of a lesson.

---

## Rules for changing this file

1. Alif writes the entry here **first**, before either side builds it.
2. If you need to change a shape that already exists, say so in the group chat
   before you write the code — someone else is building against it right now.
3. Update this file in the **same pull request** as the code, and say in the PR
   description what the other side needs to change.
