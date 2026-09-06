# Scope: Nibble

Upload a chapter, ask a question, get an answer that comes from _your own notes_,
with the page it came from. Retrieve the relevant chunks, hand them to a language
model, make it answer only from those.

Build it in **vertical slices**. Every slice ends in something you could demo that
day — never a half-finished layer. A demo where one thing works completely beats
four things that half work. Before building anything, decide what you're doing and
why in a few plain sentences, then build it, and if the plan turns out wrong once
it's actually built, say so and fix the plan too, not just the code.

Whenever a build step actually gets underway, break it into a short list of what's
genuinely being done and check each part off, right in this file. That way this file
can be opened fresh, in a brand new conversation, and it's obvious what's already
done and what's still left, without anyone re-explaining the project from scratch.

## How this file stays in sync with GitHub

This file **mirrors** the GitHub milestones and issues. That duplication is
deliberate, and it only survives if the direction is one-way:

- **GitHub is the truth for status.** An issue is done when it's closed, not when a
  box here is ticked.
- **This file is the truth for reasoning.** Why a thing is built the way it is, what
  the build turned out to be, what was rejected. An issue thread can't hold that, and
  nobody re-reads a closed one anyway.
- **Update this file at two moments only:** when a PR merges, and when a slice starts
  or finishes. Not continuously — that's how a mirror rots.
- **If the two disagree, GitHub wins on status and this file gets corrected.** Say so
  out loud when correcting it; a silent fix hides the fact that the mirror drifted.

Issue numbers are written as `#N` so the link is one click and the checkboxes stay
honest.

## Stack

Already decided, nothing open here: FastAPI with sync routes, SQLite through stdlib
`sqlite3` with plain SQL, numpy cosine similarity for search, `fastembed` with
`BAAI/bge-small-en-v1.5` at 384 dimensions running locally, Groq's free tier
(`llama-3.3-70b-versatile`) for answers, and Vite + React in plain JavaScript.

Everything is free. There is no paid API and no credit card anywhere in this project.

Each of those is a trade of sophistication for comprehensibility, made on purpose.
[`adr/0001-sqlite-and-numpy.md`](./adr/0001-sqlite-and-numpy.md) holds the pgvector
reasoning and what was given up; [`adr/0002-monorepo.md`](./adr/0002-monorepo.md)
holds the one-repository decision. Read the ADR before reopening a decision it has
already closed.

## At a glance

| #   | Slice                 | Milestone                 | Status                  |
| --- | --------------------- | ------------------------- | ----------------------- |
| 0   | The two programs talk | —                         | done, merged            |
| 1   | Upload and list       | Slice 1 — Upload and list | built, PR open           |
| 1.5 | Handwriting and scans | — (unplanned)             | built, PR open           |
| 2   | Chunking              | Slice 2 — Chunking        | open                    |
| 3   | Search, no AI yet     | Slice 3 — Search          | open                    |
| 4   | Nibble answers        | Slice 4 — Nibble answers  | open                    |
| 5   | Make it Nibble        | Slice 5 — Make it Nibble  | open                    |
| 6   | Quiz mode (stretch)   | Slice 6 — Quiz mode       | open                    |

**The demo is safe from the end of Slice 4.** Slices 5 and 6 are polish that can be
dropped if time runs out.

**Slice 3 is the pivotal one.** Semantic search with no chatbot involved — typing
"osmosis" and watching the right paragraph surface. It's the moment RAG stops being
magic, and it's a working demo on its own even if everything after it fails.

## Current state, 2026-09-06

**Correcting the mirror.** The section below used to say "three pull requests are
open, and nothing has merged in three weeks", dated 2026-08-29. That was wrong on the
day it was written: #26 and #27 had both already merged. GitHub wins on status, so
this is the correction, said out loud rather than quietly fixed — which is exactly the
failure mode the rule at the top of this file exists to catch.

22 issues, **0 closed**. `main` is at `683a7ed`.

| PR  | Branch                       | Opened     | State                                  |
| --- | ---------------------------- | ---------- | -------------------------------------- |
| #24 | `feat/extract-text`          | 2026-08-09 | open, review findings fixed, CI green  |
| #25 | `feat/upload-list-documents` | 2026-08-10 | open, review findings fixed, CI green  |
| #26 | `chore/workflow-skills`      | 2026-08-20 | **merged** 2026-08-29                  |
| #27 | `feat/clerk-auth`            | —          | **merged** 2026-08-29                  |

Review order is still **#24, then #25**. #25 contains #24's commit and targets `main`
directly, so merging #25 alone would land both — #24 goes first anyway, so the
authorship of each piece stays visible.

**No issue has ever been closed.** Twenty-two open, zero done, across five weeks. The
bottleneck is the review queue, not a missing feature, and it stays the bottleneck
until #24 and #25 land.

### Clerk sign-in landed outside the plan

PR #27 added Clerk authentication to the frontend and merged on 2026-08-29. It has
**no slice, no issue, and no `docs/api.md` entry.** It is recorded here because it is
in `main` and pretending otherwise makes this file a worse map than no map.

It is not folded into a slice retroactively — inventing a slice after the fact would
make the plan look like it predicted something it did not. What it needs is a decision,
and the decision is owed before Slice 4:

- Sign-in currently gates the UI but **no backend route checks anything.** Anyone who
  can reach `:8000` can upload, list and — once #6 lands — delete. If that is fine for
  a demo on a laptop, write that down here; if it is not, it needs an issue.
- Every document is currently shared by everyone. There is no `user_id` on `documents`.
  Adding one later means reshaping a table that has rows in it, which is the same chore
  the `chunks` table was created early to avoid.
- Clerk is free at this scale, so the "everything is free" rule still holds.

## What was fixed in review, 2026-09-06

Both open PRs were reviewed and the findings fixed on their branches rather than sent
back, so Slice 1 stops being blocked. Each fix is one that **fails quietly rather than
loudly**, which is why each got a test that fails against the old code:

- [x] **Path traversal in `routes.py`.** Uploads were written using the filename the
      browser sent, so `../../config.py` would have escaped the uploads directory.
      Now cleaned through `_safe_filename()`, with tests verified failing before the
      fix. **The first attempt at this fix was wrong, and CI caught it** — see below.
- [x] **`PRAGMA foreign_keys = ON` in `db.py`.** SQLite defaults it OFF, *per
      connection*. Without it `ON DELETE CASCADE` does nothing and says nothing, so
      #6 would have looked correct while leaving orphaned chunks behind.
- [x] **The `chunks` table**, with every column created up front — `embedding`
      included, TEXT and NULL until Slice 3 fills it — plus a plain index on
      `document_id`. To be unambiguous, because the wording here first read as though
      it might have been one: that is **not** an index on the vectors. The ADR rules
      that out and nothing here changes it.
- [x] **Extension drift.** `.text` and `.markdown` were accepted by the code and
      absent from `docs/api.md`. The contract won; a test now pins the three.
- [x] **The one `async def`.** A comment now says why `upload_document` is the
      exception, so it is understood rather than copied into the next route.
- [x] Verified in the really running server, not just tests: `../../../pwned.txt`
      stored as `pwned.txt`, `.markdown` rejected with 400, normal upload 201.

**The bit worth keeping: `Path(...).name` is not the same function on every machine.**
The first fix used it directly. It passed on Windows and failed on CI, because
`pathlib` follows the rules of whatever platform it runs on — Windows treats both `/`
and `\` as separators, Linux treats a backslash as an ordinary character in a filename.

**Being precise about what that did and did not mean**, because the first version of
this note overstated it. `Path(...).name` *did* stop the traversal, on both platforms:
the dangerous shape is `../../x.txt` with forward slashes, and `.name` reduces that to
`x.txt` everywhere. What it got wrong on Linux was the other shape — `..\..\x.txt` came
back untouched, and the upload was then written to a file called literally
`..\..\x.txt` **inside** `uploads/`. A daft filename, not an escape.

So this was a consistency bug rather than a second security hole: the same upload
produced a different stored filename depending on the machine, and left a name still
carrying separators — which is a path again the moment anything Windows-shaped reads
it. `_safe_filename()` normalises first, so every machine stores the same clean name.

Two things it is worth remembering for:

- **Test what you assume is platform-independent.** `pathlib` looks like it abstracts
  the platform away. It does the opposite — it faithfully implements whichever one it
  is running on. Local green meant nothing here; the Linux run was the real check.
- It is a concrete answer to "why bother with CI when it passes on my laptop", which is
  a fair thing to have been wondering.

**Still open on these two PRs, and needing a person:**

- [ ] **Both PR bodies are the unfilled template.** Every question blank, no boxes
      ticked, #25 still auto-titled "Feat/upload list documents". The learning gate
      has not actually been used yet, on either PR.
- [ ] **`db.py` is issue #2, assigned to Alif, and Fahim wrote it in #25.** An
      ownership boundary was crossed. Accepting it or reasserting it are both
      defensible; picking neither is not.

## Slice 0: The two programs talk to each other

Done and merged. The frontend loads, calls `GET /health`, and reports whether the
backend is up. Verified in a real browser, on both the success and the failure path.

**The gate on this slice was never fully closed.** It was that all three developers
see "Backend is up" on their own laptop using only
[`first-week.md`](./first-week.md), without asking a setup question. Not everyone has
confirmed that. If someone got stuck, the doc is wrong — fix the doc, not the person.

- [x] Backend serves `GET /health`
- [x] Frontend calls it and reports up or down
- [x] Both the failure and the success path seen in a browser
- [ ] Every developer has run it locally from `first-week.md` alone

## Slice 1: Upload and list

Upload a PDF, see it in a list, delete it. The contract is written in
[`api.md`](./api.md) under "Slice 1".

### Decided

**A filename from a client is untrusted input.** Uploads are written through
`_safe_filename()` in `routes.py`, never the raw value, because a name like
`../../something` otherwise escapes the uploads directory.

**Do not reach for `Path(filename).name` on its own.** This decision used to say
exactly that, and it is incomplete: `pathlib` follows the rules of the platform it
runs on, so that line strips a `\` on Windows and leaves it as part of the filename
on Linux. `_safe_filename()` normalises both separators before taking the last piece,
producing the same clean filename everywhere. Corrected 2026-09-06 after CI caught the
platform-dependent result — see the review record above.

This is the first place in the project where "never trust the client" stops being an
abstraction, and it is worth understanding rather than pasting.

**`PRAGMA foreign_keys = ON` on every connection.** SQLite has foreign keys **off** by
default, which means a cascade delete silently does nothing at all. `DELETE
/documents/{id}` in #6 depends on it, so it lands with `db.py` rather than being
discovered later as a mystery.

**The schema needs `chunks` from the start, not just `documents`.** Every column is
**created now, in Slice 1**, including `embedding` (TEXT, holding JSON). Slice 2 starts
inserting chunk rows and Slice 3 starts filling `embedding` in — it is NULL until then,
but the column already exists and neither slice alters the table. Designing it once,
now, is cheaper than migrating a SQLite file later.

This used to read "Slice 3 adds an `embedding` column", which contradicted the sentence
right after it about not migrating later. Slice 3 *fills* the column; it does not add
it. Clarified 2026-09-06.

**The only index is on `document_id`**, because every chunk lookup is "the chunks
belonging to this document". There is deliberately **no index on the vectors** —
[`adr/0001-sqlite-and-numpy.md`](./adr/0001-sqlite-and-numpy.md) rules that out on
purpose, and nothing in Slice 1 changes it.

**The allowed extensions and `api.md` must say the same thing.** They drifted once
already — the code accepted `.text` and `.markdown` while the contract named only
`.pdf`, `.txt`, `.md`. Pick one and change both. A contract that disagrees with the
code is worse than no contract, because people trust it. **Resolved 2026-09-06:** the
contract won, the two extra extensions were dropped from `files.py` and `routes.py`,
and a test now pins the three so they cannot drift apart again.

**`async def` is the exception here, and only for `await file.read()`.** The project
rule is sync routes so there is no async to explain. The upload route genuinely needs
it. Write the sentence saying why, so the exception is understood rather than copied
into the next route.

**Same-name uploads currently overwrite each other silently.** Known, minor, not being
fixed in this slice. Written down so it is not rediscovered later as a bug. Note this
is now the *cleaned* name: two uploads called `a/notes.txt` and `b/notes.txt` both
become `notes.txt` and collide, which is the same known behaviour, not a new bug.

### Checklist

- [ ] #2 `db.py` — the SQLite connection and schema _(Alif)_
- [ ] #3 `extract_text()` — pull the words out of a file _(Fahim, PR #24)_
- [ ] #4 `POST /documents` and `GET /documents` _(Fahim, PR #25)_
- [ ] #5 The notes list and an upload button _(built, PR #30)_
- [ ] #6 `DELETE /documents/{id}` _(built, PR #30)_
- [ ] #7 A delete button on each note _(built, PR #30)_

### Built, 2026-09-06

Slice 1 is complete: upload a file, see it listed, delete it. This started as a
scaffold with the behaviour left as `TODO`, and was then finished in the same PR —
the scaffold is gone and nothing is left marked TODO.

**Who did it changed partway.** The plan was that the lead scaffolds and Arman and
Fahim build. Alif took the remaining work directly instead. #5, #6 and #7 are still
assigned to them on GitHub, so **the board and the code disagree and one of them
should move** — that is a people question, not a code one, and it should not be left
to drift.

- [x] `DELETE /documents/{document_id}` — 204 on success, 404 for an id that is not
      there. The existence check runs **before** the delete, because `DELETE` on a
      missing row succeeds silently in SQL and the route would otherwise answer 204
      for something it never deleted.
- [x] Chunks go with the document through `ON DELETE CASCADE`, not a hand-written
      `DELETE FROM chunks`. Chosen because it cannot be forgotten later: any future
      route that removes a document gets it for free. The risk of that choice — a
      dropped pragma silently doing nothing — is covered by a test in `test_db.py`
      and another through the route itself.
- [x] Six tests for the route, including deleting twice and a non-numeric id.
      **32 backend tests pass, none skipped.**
- [x] `listDocuments`, `uploadDocument` and `deleteDocument` in `api.js`.
- [x] The notes list loads on page open, an upload appears at the top of the list
      without a refresh, and deleting removes the row immediately.
- [x] Every `eslint-disable` the scaffold needed is gone. `npm run lint` passes with
      none left, which was the marker that the wiring was finished.

**The uploaded file in `uploads/` is deliberately left on disk when a document is
deleted.** It is not in the contract, and removing it would be wrong today: two
uploads with the same name share one file, so deleting it could take another
document's file with it. Worth fixing when same-name uploads are fixed, not before.

## Slice 1.5: Reading handwriting and scans

**Built 2026-09-06.** Not on the original plan. It was added because testing
found a failure bad enough to sink the demo, and because "upload any document"
is what people actually expect the app to mean.

### The problem it fixes

A handwritten or scanned PDF uploaded successfully and contained **nothing**.

`pypdf` reads a PDF's *text layer* — the words stored inside the file by
whatever typed it. A scan, a phone photo, or a page of handwriting has no text
layer at all; it is a picture of writing. `pypdf` returns the right number of
pages, every one an empty string:

```
pages found      : 2
  page 1: 0 characters of text -> ''
  page 2: 0 characters of text -> ''
```

The upload returned `201`, `page_count` was correct, and the note looked
completely normal in the list. Slice 2 would have chunked nothing, Slice 3
searched nothing, and Slice 4 answered "I can't find that in your notes" about
a document sitting on screen. **It failed silently**, which is the worst
possible shape for a live demo with an audience uploading their own files.

### How it works

There is no clever trick for this, and it is worth saying plainly because it
comes up constantly: **the only way to read handwriting is to look at it.**
That is what a vision model does, and it is exactly what happens when you paste
a photo of your notes into Claude. Same idea, different model.

1. `extract_text` runs as before.
2. If a PDF comes back with **no text on any single page**, it is a scan.
3. Each page is drawn to a PNG by `pypdfium2`.
4. Each PNG goes to Groq's vision model with an instruction to transcribe and
   nothing else.
5. The result is plain text, so chunking, embedding, search and answers all
   carry on without knowing any of this happened.

Photos (`.png`, `.jpg`, `.jpeg`, `.webp`) skip step 2 — there is no text in a
photo to try first — and count as a single page.

### Decided

**Groq's free vision model, not OCR software.** Tesseract is free and genuinely
poor at cursive handwriting; the good handwriting engines are paid or need
PyTorch, which
[`adr/0001-sqlite-and-numpy.md`](./adr/0001-sqlite-and-numpy.md) already avoids.
Groq is already the provider, already free, already keyless-at-signup, and a
vision model reads handwriting far better than classical OCR does.

**`pypdfium2` to draw the pages, not `pdf2image`.** `pdf2image` needs poppler
installed as a separate program, and on Windows that is exactly the kind of
afternoon this project exists to avoid — the same reasoning that removed Docker.
`pypdfium2` is a plain `pip install` with no system dependency.

**Only when there is no text at all.** A typed PDF never touches the vision
model, so it stays instant, stays free, and cannot be made worse by a bad
transcription. There is a test asserting the model is never called for a PDF
that has text in it.

**It runs inside the upload request, not in the background.** A job queue is a
whole second system to explain, and the honest cost is a slow upload rather
than a hidden one. The button says "Reading…" while it works.

**Capped at `OCR_MAX_PAGES` (20).** The free tier is roughly 250 requests a day
and each page is one request, so somebody scanning a whole textbook would burn
the day's allowance in a single upload. Past the cap it is refused with a
sentence suggesting the file be split.

**`OCR_ENABLED` can switch it off.** If it misbehaves on demo day, one setting
turns it off and scans get refused politely instead of failing oddly.

**An empty result is refused, not stored.** If the model finds no writing, the
upload fails with a sentence. Storing an empty note would recreate the exact
silent failure this slice exists to remove.

### Costs, accepted

- **Uploads get slow for scans.** Seconds per page, in the request.
- **~250 pages a day**, free tier, shared with Slice 4's chat calls. Fine for
  three developers; a demo where the audience uploads their own scans could hit
  it, so have a spare key.
- **Quality is good, not perfect.** Neat handwriting transcribes well; messy
  cursive will have errors, and those errors flow into search and answers.
- **The key is now needed earlier than Slice 4.** `first-week.md` and
  `.env.example` both say so.

### Checklist

- [x] `pypdfium2` added to `pyproject.toml`
- [x] `VISION_MODEL`, `OCR_ENABLED`, `OCR_IMAGE_WIDTH`, `OCR_MAX_PAGES` in `config.py`
- [x] `ocr.py` — page rendering, the vision call, and `OcrUnavailable`
- [x] `has_no_text()` in `files.py`, and image files routed to the model
- [x] The fallback and all its error sentences in `POST /documents`
- [x] Photo uploads accepted by the file picker; the button reads "Reading…"
- [x] `api.js` surfaces the backend's sentence instead of a status code
- [x] 11 tests covering it, with the vision call stubbed. **44 tests pass.**
- [x] `api.md`, `.env.example` and `first-week.md` all updated

### Not verified against the real API

**There is no `GROQ_API_KEY` on this machine, so the live vision call has never
actually run.** Everything around it is tested — the scan detection, the PNG
rendering (really producing PNGs through `pypdfium2`), the fallback, the error
handling, the switch-off — but the request itself is stubbed in tests.

The request shape follows Groq's documented vision format, and the model id
comes from their current model list. **Someone has to put a key in `.env` and
upload a real handwritten page before this is trusted.** Until that happens,
treat it as written-but-unproven.

### Still open

**`.docx` is not supported.** "Any document" reasonably includes Word files, and
they are not pictures — `python-docx` would read them directly with no vision
model involved. Left out to keep this change reviewable; worth its own issue.

### Answered, 2026-09-06 — what shape the frontend scaffold takes

**Option 1, layout and TODOs.** #5 asks for API functions, `useState`, `useEffect`,
array rendering and the hidden-file-input `ref` trick — five unfamiliar ideas at once,
which is what made this worth asking. The other two were:

2. **One worked example.** The upload card built completely, the rest shells to
   imitate. More to copy from, but the first component gets designed for you.
3. **Full static UI with fake data.** Motivating and demos immediately, but no
   component ever actually gets designed.

Option 1 won because the fiddly half — the `ref` plumbing, clearing the input value so
the same file can be picked twice, the empty and failed states — is trivia rather than
an idea, and the interesting half is small enough to be worth writing by hand.

What is built and what is left is listed under "The scaffold" above. **`Button` (#18)
is not being pulled forward**, and the reasoning is there too.

## Slice 2: Chunking

Cut documents into pieces small enough to search. Contract in [`api.md`](./api.md)
under "Slice 2".

- [ ] #8 `chunk_text()` and its tests _(Fahim)_
- [ ] #9 Save chunks on upload, add `GET /documents/{id}/chunks` _(Fahim)_
- [ ] #10 Click a note and see its chunks _(Arman)_

## Slice 3: Search — no AI yet

Semantic search over the chunks, with no language model anywhere in the path. Contract
in [`api.md`](./api.md) under "Slice 3".

### Decided

**Embeddings run locally, on CPU, through `fastembed`.** Not because it is clever but
because it needs no key, no rate limit and no PyTorch. **Groq has no embeddings API** —
that is why this does not go through the same provider as Slice 4. Not an oversight.

**The model is loaded once, as a module-level singleton.** Loading it per request is
the difference between a search that feels instant and one that looks broken.

**`EMBEDDING_DIM` is 384.** Anything in `reference/original-scaffold` saying 1536 is
describing the old OpenAI setup and does not apply here.

**`fastembed` downloads about 130 MB the first time it runs.** It needs internet once
and is offline after. Flagged in [`first-week.md`](./first-week.md) so it reads as
expected rather than as a hang.

- [ ] #11 `embeddings.py` — meaning as numbers, and how to compare them _(Alif)_
- [ ] #12 Embed each chunk as it is saved _(Fahim)_
- [ ] #13 `POST /search` — find the right notes, with no AI _(Fahim)_
- [ ] #14 The search box, showing results with scores _(Arman)_

## Slice 4: Nibble answers

Grounded answers with sources. Contract in [`api.md`](./api.md) under "Slice 4".

### Decided

**The model answers only from the retrieved chunks, and says so when it cannot.** The
whole claim of this project is that the answer came from your notes. An answer that
quietly comes from the model's own training breaks that claim, and a source chip
underneath it makes the break invisible.

**Groq's free tier is roughly 1,000 requests a day per key.** Three developers will not
hit it. A live demo with an audience uploading their own PDFs might — have a spare key
on demo day.

- [ ] #15 `llm.py` — ask Groq, and force it to stay grounded _(Alif)_
- [ ] #16 `POST /ask` — search, then answer _(Fahim)_
- [ ] #17 Turn the page into a chat with Nibble _(Arman)_

## Slice 5: Make it Nibble

Design system, mascot, voice. Everything here is already decided in
[`design.md`](./design.md) — read it rather than inventing styling.

- [ ] #18 The `Button` component with the solid-edge press _(Arman)_
- [ ] #19 Nibble's moods, empty states and loading states _(Arman)_
- [ ] #20 Accessibility pass _(Arman)_
- [ ] #21 Rewrite every message in Nibble's voice _(Alif)_

## Slice 6: Quiz mode

Stretch. Drop it without regret if the demo date gets close.

- [ ] #22 Generate quiz questions from the notes _(Fahim)_
- [ ] #23 Quiz screen _(Arman)_

## Not doing right now

- **Postgres and pgvector.** Replaced by SQLite and numpy. Docker Desktop on Windows
  was the single biggest predictable time-sink and bought nothing at a few thousand
  chunks. See [`adr/0001-sqlite-and-numpy.md`](./adr/0001-sqlite-and-numpy.md).
- **TypeScript.** A second language to learn on top of React, inside a few weeks.
- **An ORM.** Plain SQL is readable and explainable. An ORM is a second thing to learn
  that hides the first.
- **Async routes.** No `async`/`await` to explain, with the one upload exception noted
  under Slice 1.
- **Building on `reference/original-scaffold`.** Archived, and useful to peek at when
  something is genuinely hard. It is not a base to build on — the whole point of the
  rebuild was that nobody could read it.

## Housekeeping, once #24 and #25 land

The admin bypass on `main` was only needed to land the Slice 0 rebuild. Removing it
makes branch protection apply to everyone, the lead included. Ruleset `20557004`,
named `protect-main`.

The CI job names `backend` and `frontend` are wired into that ruleset as required
checks. **Renaming a job silently switches protection off for that check.** Change the
steps freely and leave the names alone. There is a comment saying so at the top of
`.github/workflows/ci.yml`.
