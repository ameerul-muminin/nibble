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
| 1   | Upload and list       | Slice 1 — Upload and list | done, merged            |
| 1.5 | Handwriting and scans | — (unplanned)             | done, merged            |
| 2   | Chunking              | Slice 2 — Chunking        | done, merged            |
| 3   | Search, no AI yet     | Slice 3 — Search          | built, PR open          |
| 4   | Nibble answers        | Slice 4 — Nibble answers  | open                    |
| 5   | Make it Nibble        | Slice 5 — Make it Nibble  | open                    |
| 6   | Quiz mode (stretch)   | Slice 6 — Quiz mode       | open                    |

**The demo is safe from the end of Slice 4.** Slices 5 and 6 are polish that can be
dropped if time runs out.

**Slice 3 is the pivotal one.** Semantic search with no chatbot involved — typing
"osmosis" and watching the right paragraph surface. It's the moment RAG stops being
magic, and it's a working demo on its own even if everything after it fails.

## Current state, 2026-09-07

`main` is at `bac397e` and **Slices 0, 1, 1.5 and 2 are all merged.** #33 (chunking),
#35 (the slice 2 handover and the open-backend decision), #34 (the landing page) and
#36 (`embeddings.py`) all landed in the last day.

**Slice 3 is built.** #11 is merged; #12, #13 and #14 are built and waiting on a
pull request, so search works end to end and the milestone still shows three open
issues. Slice 4 is next and nothing in it has started.

Slices 0, 1 and 1.5 are in `main` and work. You can upload a PDF, a text file, a
Markdown file or a photo, see it listed, and delete it — and a scanned or
handwritten PDF gets read by a vision model instead of silently arriving empty.

### The board now agrees with the code

**22 issues, 6 closed** — #2, #3, #4, #5, #6 and #7. They were built and merged
weeks apart from being closed, and for a while this file said so while the board
did not. That gap is shut.

The rule that produced the fix is worth keeping: an issue is done when it is
closed, not when a box here is ticked. Saying the two disagreed out loud, rather
than quietly ticking the boxes, is what got them closed.

Slice 2's three issues (#8, #9, #10) **closed when PR #33 merged**, which is the
mirror working the way it is supposed to.

**Slice 3 did not go to the people it was assigned to.** Alif built all four issues.
The reasoning is under Slice 3, along with what it costs and what it means for
slice 4 — it is written there rather than here because it is a decision, not a
status.

### Two things that are true and easy to misread as "finished"

**The extracted text used to be thrown away — Slice 2 fixed that.** `extract_text`
ran only to count pages and nothing stored the words, so an upload that looked
completely successful produced not one searchable word, and a scan spent vision
tokens on every page and discarded the result.

Chunking now runs inside the same upload request and stores the pieces. **What is
still true is that anything uploaded before Slice 2 has no chunks** — `ch1 DB.pdf`
is exactly that, and it comes back from the chunks endpoint as an empty list. It is
not being backfilled; delete it and upload it again.

**A note appearing in the list is not proof the text came out.** The first real
upload after the merge was `ch1 DB.pdf` — 31 pages, listed, looking perfect. It
was the Silberschatz textbook slides: a typed PDF with a 14,923-character text
layer, so `has_no_text` was False and the vision model was never called. The
handwriting path was not exercised at all.

The giveaway was in the data: 31 pages, against an `OCR_MAX_PAGES` of 5. A real
scan that long would have been refused. **Nobody has yet put an actual handwritten
page through this** — see the Slice 1.5 verification notes below.

### Clerk sign-in landed outside the plan

PR #27 added Clerk authentication to the frontend and merged on 2026-08-29. It has
**no slice, no issue, and no `docs/api.md` entry.** It is recorded here because it is
in `main` and pretending otherwise makes this file a worse map than no map.

It is not folded into a slice retroactively — inventing a slice after the fact would
make the plan look like it predicted something it did not. What it needed was a
decision, and the decision is now made — see below.

### Decision, 2026-09-07: the backend stays open, on purpose

**Clerk gates the UI and nothing else. We are keeping it that way through the demo.**

This came up again while merging the landing page (PR #34), which wraps the app in
`<Show when="signed-out">`. That is worth having for how the product reads, but it
should not be mistaken for a gate. Checked against the running backend, with no
credentials sent at all:

```
GET http://localhost:8000/documents  ->  200, the real list of notes
```

`backend/app/routes.py` has no `Depends`, no token check, no `Authorization` header
anywhere, so `POST /documents` and `DELETE /documents/{id}` are open in the same way.
`documents` has no `user_id` either — every note belongs to everybody.

Why we are accepting that:

- The demo runs on one laptop. Nothing is deployed, `:8000` is not reachable from
  anywhere else, and there is no real user data in the database.
- Real auth is not small. It is Clerk token verification on every route, a `user_id`
  column, and reshaping a table that already has rows in it — the exact chore the
  `chunks` table was created early to avoid. That is a slice, and it would come out
  of Slices 3 and 4, which are the ones the demo actually depends on.
- The demo is safe from the end of Slice 4. Spending that time on auth risks the
  thing we are being marked on to fix something nobody can reach.

What this costs us, stated plainly so nobody is surprised at the demo:

- **Do not deploy this anywhere public as it stands.** The moment it is reachable
  from outside the laptop, this decision is wrong and has to be revisited first.
- Two people signed into different Clerk accounts on the same backend see the same
  notes. That is not a bug to file; it is this decision showing through.
- If somebody asks at the demo "what stops me reading your notes?", the honest answer
  is "nothing yet, and here is what it would take" — pointing at this section. That
  is a better answer than pretending the sign-in page does something it does not.
- Clerk is free at this scale, so the "everything is free" rule still holds.

Revisit this if the project is ever deployed, or if Slices 3-6 finish early.

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

Every one of these is **built and merged into `main`**. The boxes are unticked
because five of the six issues are still open on GitHub, and GitHub wins on
status. Close them and tick these together.

- [ ] #2 `db.py` — the SQLite connection and schema _(merged in #25; still open)_
- [ ] #3 `extract_text()` — pull the words out of a file _(merged in #24; still open)_
- [ ] #4 `POST /documents` and `GET /documents` _(merged in #25; still open)_
- [x] #5 The notes list and an upload button _(merged in #31; **closed**)_
- [ ] #6 `DELETE /documents/{id}` _(merged in #31; still open)_
- [ ] #7 A delete button on each note _(merged in #31; still open)_

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

**Capped at `OCR_MAX_PAGES` (5).** Not for the reason first assumed. The daily
request count is generous; the binding limit is 1000 output tokens *per minute*,
reserved against `max_tokens`, which works out at about two pages a minute. Five
pages is a two-and-a-half minute upload and twenty would look like a hang. Past
the cap it is refused with a sentence suggesting the file be split.

**`reasoning_effort: "none"`, and a stripper for `<think>` blocks.** This model
reasons out loud by default. That reasoning would otherwise be stored as though
it were the words on the page — chunked, embedded, and quoted back to a student
as their own notes.

**A rate-limited page waits and retries.** Running out of per-minute allowance
partway through a scan is the ordinary case, not a failure, so it should not
kill an upload that was already half done.

**`OCR_ENABLED` can switch it off.** If it misbehaves on demo day, one setting
turns it off and scans get refused politely instead of failing oddly.

**An empty result is refused, not stored.** If the model finds no writing, the
upload fails with a sentence. Storing an empty note would recreate the exact
silent failure this slice exists to remove.

### Costs, accepted

- **Uploads get slow for scans.** Seconds per page, in the request.
- **About two pages a minute**, which is the limit that actually bites — 1000
  output tokens per minute, reserved against `max_tokens`. The daily request
  count is generous by comparison. A five-page scan is a two-and-a-half minute
  upload, and it is shared with Slice 4's chat calls, so have a spare key for
  demo day.
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
- [x] 15 tests covering it, with the vision call stubbed. **48 tests pass.**
- [x] `api.md`, `.env.example` and `first-week.md` all updated

### Verified against the real API, and what that changed

**It works.** A three-page image-only PDF was uploaded through the real route
with a real key: detected as a scan, every page read, `201` in 24 seconds.

Three things only showed up by actually running it, and none would have been
found by reading the code:

**1. `max_tokens` is required, not optional.** Without it the first call failed
with a 429 before reading anything. Groq reserves against the *expected* output,
which with no limit set is the model's maximum — 1192 tokens against a cap of
1000. Nothing had been read, nothing had been spent, and the error said "rate
limit" while the account had its full allowance untouched.

**2. This model thinks out loud.** The first successful call returned 400 words
of `<think>` reasoning — *"Wait, looking closer at the bottom part…"* — before
the answer. Stored as-is, that reasoning would have been chunked, embedded and
eventually quoted back to a student as their own notes. Fixed with
`reasoning_effort: "none"`, plus a stripper for the block in case it ever
appears anyway, because the failure is silent and the cost is high.

**3. The real throughput is about two pages a minute.** The 1000-token cap is
per minute and is reserved against `max_tokens`, so the page budget is far
tighter than the daily request count suggests. Hitting it mid-scan is the
normal path, not an error, so a rate-limited page now waits and tries again
rather than failing an upload that was halfway done.

That last one is why **`OCR_MAX_PAGES` is 5, not 20.** Five pages is already a
two-and-a-half minute upload; twenty would look like the app had hung. The
original 20 was a guess made from the daily request limit, and it was wrong.

**Still not verified: quality on real handwriting.** Everything above was tested
with rendered type, which is easier to read than a person's writing. Neat
handwriting should be fine and messy cursive will have errors — but nobody has
put an actual handwritten page through it yet, and until someone does, the
quality claim is an expectation rather than a result.

**The first attempt at verifying it did not verify it.** After the merge, a file
was uploaded believing it was handwritten, it appeared in the list, and that was
read as the feature working. It was `ch1 DB.pdf`, the Silberschatz textbook
slides — a typed PDF carrying a 14,923-character text layer, so `has_no_text` was
False and no vision call happened.

This is worth keeping because the mistake is the natural one to make: **a note
appearing in the list proves the upload worked, and says nothing about where the
text came from — or whether there was any.** Two ways to tell them apart without
guessing:

- A real scan of more than five pages is *refused*. That upload was 31 pages and
  went through, which alone proved it was not being treated as a scan.
- A real scan is slow. Roughly two pages a minute, with the button reading
  "Reading…". Instant means there was a text layer.

Until a genuinely handwritten file of five pages or fewer has been through it, the
verification below stands as "the API works", not "handwriting works".

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

**Built 2026-09-06 and merged 2026-09-06 as PR #33.** #8, #9 and #10 are closed on
GitHub, so the boxes below are ticked. This section said "not merged" for a day
after it was merged, which is the mirror rotting in the direction it always rots —
the file lags the board, never the other way round.

- [x] #8 `chunk_pages()` and its tests
- [x] #9 Save chunks on upload, add `GET /documents/{id}/chunks`
- [x] #10 Click a note and see its chunks

### Ownership: a one-off, and it is over

Alif took ownership of all the code for **this slice only**, so it is written out
in full rather than scaffolded with `TODO(name)` the way slice 1 was. The names
were dropped from the checklist above for the same reason.

**That exception ends here.** Fahim is taking slice 3, so the table in
[`team.md`](./team.md) stands unchanged and needs no edit — and the rule it exists
to protect comes back with it: slice 3 gets **scaffolded, not solved**, because
whoever an issue is assigned to has to come out able to explain the change at
review. This is written down because a one-off that nobody closes quietly becomes
the new normal, and the next slice is where that would show.

### Decided

**`chunk_pages(pages: list[tuple[int, str]])`, not `list[str]`.** Issue #8 as
written asked for `list[str]`, which disagreed with what `extract_text()` already
returns. Matching the code means the upload route hands one function straight to
the other with no conversion step, and the page number is carried as a fact rather
than inferred from a list position. **Issue #8's text is wrong and needs the
one-line correction** — recorded here rather than quietly fixed in passing.

**A piece never spans two pages.** Every chunk carries the page it came from, and
slice 4 shows that number to a student as "p. 4". The cheap way to keep it honest
is to never let a window straddle a page boundary. The cost is that a short page
gives a short piece, which is fine.

**Fixed-size character windows, nothing cleverer.** No sentence detection, no
paragraph splitting, no tokeniser. `CHUNK_SIZE` characters, then step forward by
`CHUNK_SIZE - CHUNK_OVERLAP`. It is six lines of real work and it is explainable
at the demo, which is worth more here than the last few percent of retrieval
quality.

**The document and its chunks are written in one transaction, one commit.**
Committing the document first would open a window where it exists with no pieces,
and a failure in the chunk insert would leave that window open forever — an upload
that looks finished and can never be searched. Either both land or neither does.

**`GET /documents/{id}/chunks` asks the database two questions.** A single SELECT
against `chunks` cannot tell "no such document" apart from "a document with no
pieces" — both come back empty — and those deserve different answers. So it checks
the document exists first, and 404s with the same sentence `DELETE` uses.

**No backfill for anything uploaded before today.** `ch1 DB.pdf` is in the dev
database with a page count and zero chunks, and it stays that way. A migration
nobody runs twice costs more than deleting the note and uploading it again. The UI
says so in plain words rather than showing an unexplained empty panel.

### The rule that was wrong, and what the tests caught

The first version dropped **any** piece shorter than 40 characters. It looked
sensible and it was wrong twice over, and the existing slice 1 tests failed loudly
enough to show it:

- It deleted every title-only slide in a deck. "Chapter 4: Concurrency" is real
  searchable content with a real page number, not noise.
- It refused a legitimate small upload outright. `notes.txt` containing one
  sentence produced no chunks at all, so the upload 400'd.

The arithmetic nobody did first: with `CHUNK_OVERLAP` at 150, the loop always stops
a step early, so **the last piece of a page is always longer than 150 characters.**
A piece under 40 characters can therefore only ever be a whole short page — which
means the rule, as written, did nothing but delete short pages.

So `MIN_CHUNK_CHARS` now applies only to a piece that is **not the first piece of
its page**. Every page with any text produces at least one chunk. The rule still
earns its place as a guard for a hand-edited config with a small overlap, where a
genuine 11-character scrap can appear — there is a test that forces exactly that.

**Worth keeping:** the reasoning for the original rule was fine and the conclusion
was still wrong, because nobody checked whether the case it described could happen.
It could not.

### A silent failure that is now loud

An upload whose chunks come back empty is refused with a sentence, rather than
stored. That is the same failure shape slice 1.5 exists to remove — a note that
lists perfectly and matches no search — arriving by a different route.

With the current settings the branch is unreachable, because every page with text
produces a piece. It is kept anyway, with a test that stubs `chunk_pages` to return
nothing, so that a future change to chunking fails a test instead of quietly filling
the list with unsearchable notes.

### Checklist

- [x] `backend/app/chunking.py` — `chunk_pages()`, the window loop, `MIN_CHUNK_CHARS`
- [x] A guard that fails loudly if `CHUNK_OVERLAP >= CHUNK_SIZE`, which would
      otherwise hang the server building identical pieces forever
- [x] `backend/tests/test_chunking.py` — 13 tests, including overlap, no gaps
      between pieces, page numbers surviving, and nothing stored twice
- [x] `POST /documents` chunks the text and stores it with `executemany()`
- [x] `GET /documents/{document_id}/chunks`, with the 404
- [x] 9 more route tests. **70 tests pass**, up from 48
- [x] `getChunks(id)` in `api.js`
- [x] `App.jsx`: click a note to open it, a `useEffect` keyed on `selectedId`,
      loading, failed, empty and populated states, and Close
- [x] `docs/api.md` — Slice 2 moved from planned to built, and the 404 pinned
- [x] `ruff check`, `ruff format --check`, `npm run lint`, `npm run build` all clean

### Verified by actually running it

A 1769-character note through the real running server: **3 pieces, 900 / 900 / 266
characters, all page 1.** The head of piece 2 appears inside piece 1, so the overlap
is real and not just asserted in a test. `GET /documents/999/chunks` returns the
404 sentence; deleting a document and asking again returns the same, so the cascade
works through the endpoint and not only against the table.

`ch1 DB.pdf`, uploaded before this slice existed, returns `200` and `[]` — the
empty-pieces case, live, exactly as predicted above.

### Reviewed after building, and what the review got right

Two findings came back. **One was wrong about the code and right about the docs,
and that distinction is the useful part** — a reviewer describing a real mechanism
is not the same as a reviewer describing a real defect, and the way to tell them
apart is to measure rather than to argue.

**"Trimming each window erases the overlap" — the mechanism is real, the harm is
not.** Every window is `.strip()`ped, so whitespace sitting on a boundary is
removed from the piece and the overlap shrinks by that much. Measured on real
input: ordinary prose keeps **149-150 characters against a `CHUNK_OVERLAP` of
150**, so the cost is about one character. Given 200 spaces spanning the whole
overlap window the overlap really does drop to **0**.

That last case sounds alarming and is harmless, for a reason worth being able to
say out loud at the demo: **`.strip()` only ever removes whitespace.** So an
overlap that has collapsed to nothing is a boundary with nothing but blank space
on it — no word is being cut there, and there is nothing for an overlap to
rescue. No non-whitespace character is ever lost from a window either. The promise
that actually matters is about *words*, and it holds without exception.

So no code changed. What was genuinely wrong was a sentence in
[`api.md`](./api.md) claiming the tail of one piece is the head of the next, which
stops being true the moment a window is trimmed. Corrected, and two tests now pin
the real invariant instead of the overstated one: no word split across a
whitespace-collapsed boundary, and ordinary prose keeping all but a character or
two of the overlap.

**"A list reload leaves a stale selection" — valid, and fixed.** `selectedId`
survived a reload whose rows no longer contained it, so the panel kept showing a
deleted note's pieces under a heading that had quietly fallen back to the generic
"Pieces". `handleDelete` covered the note *you* delete; nothing covered the note
somebody else deleted, and every document here is shared by everyone.

**It was latent, not reachable** — nothing bumps `reloadKey` except the Try again
button, which only renders after a failed load, and you cannot select a note while
the list is in that state. Fixed anyway: the combination is wrong on its face and
becomes reachable the moment anything else reloads the list, which slice 3 is
likely to add.

The fix uses the function form of `setSelectedId` rather than reading `selectedId`
directly, and that is the same trap as the `ignore` guard next to it: `selectedId`
is not in that effect's dependency list, so the captured value would be whatever
it was when the load started, and clicking a note mid-flight would close the panel
that had just opened.

**72 tests pass**, up from 70.

### The real textbook, chunked

`ch1 DB.pdf` — the 31-page Silberschatz slide deck that fooled the slice 1.5
verification — was uploaded again after slice 2 was built, and it is the best
evidence this slice works on something nobody constructed for it:

- **31 pieces, one per page, and all 31 pages are present.**
- **14,923 characters stored**, which is exactly the text-layer size recorded for
  this file back in slice 1.5. Nothing was dropped on the way in.
- **No page needed cutting.** At about 481 characters a page it is comfortably
  under `CHUNK_SIZE`, so every page is one piece and the overlap never comes into
  play. Worth knowing before slice 3: a deck like this gives *page-sized* chunks,
  not 900-character ones.
- **Page 1 is 138 characters** — a title and copyright slide. Under the rule as
  first written, that page would have been deleted without a word. It is kept,
  which is the correction working on real input rather than in a test.

### Still open on this slice

- [ ] **Nobody has clicked it in a browser.** Lint and the production build are
      clean and the backend answers correctly with CORS for
      `http://localhost:5173`, but no person has opened a note and looked at the
      panel. That is the one thing left here, and it is a person's job.
- [x] **#8, #9 and #10 closed** when PR #33 merged, as they were supposed to.
- [ ] **Issue #8 closed still saying `chunk_text()` and `list[str]`.** Nobody
      corrected it before it closed, so the board now holds a permanent record of
      a signature the code never had. Harmless, since a closed issue is read by
      nobody, and left alone rather than reopened — but it is exactly how the next
      person reading the milestone gets the wrong idea, so: **the code is right.**

## Slice 3: Search — no AI yet

Semantic search over the chunks, with no language model anywhere in the path. Contract
in [`api.md`](./api.md) under "Slice 3".

### Ownership changed again, mid-slice, 2026-09-07

The plan above this line said Fahim takes #12 and #13 and Arman takes #14,
scaffolded rather than solved. **That is not what happened, and this is the
honest record of it.** After #11 merged, Alif reassigned the rest of the slice to
himself: Arman had finished the landing page and had nothing else outstanding,
and Fahim is being kept for slice 4, which is the bigger piece of learning.

So #12, #13 and #14 are **written out in full**, and two ownership lines in
[`team.md`](./team.md) were crossed to do it — `routes.py` and `backend/tests/`
are Fahim's, `frontend/src/` is Arman's. Crossing a boundary is a people problem
before it is a code problem, so: it was the lead's own call, on his own project,
with both owners unblocked rather than bypassed.

**Two things this costs, and they are worth naming rather than discovering.**
Slice 2 said "the write-it-all-out exception ends here" and it did not — it has
now happened twice, which makes it the pattern rather than the exception. And the
pull-request gate, *explain this in your own words*, only tests the person who
wrote the code; two of the three developers now have no slice-3 code of their own
to explain at the demo.

**What that implies for slice 4, and it should be decided before it starts:** if
Fahim is taking it, he takes it scaffolded, and the scaffolding has to be real —
signatures and plumbing, with the interesting part left as `TODO(Fahim)`. Slice 4
is the last slice the demo actually depends on. It is the wrong one to absorb.

- **Board is stale:** #12 and #13 are still assigned to Fahim on GitHub and #14 to
  Arman. **Reassign all three to Alif**, or the milestone will say three people
  built this slice when one did.
- **Slice 3 makes the stale-selection fix from slice 2 matter**, because search
  results are a second place a deleted note could linger. Handled — `handleDelete`
  now clears matching results too.

### Decided

**Embeddings run locally, on CPU, through `fastembed`.** Not because it is clever but
because it needs no key, no rate limit and no PyTorch. **Groq has no embeddings API** —
that is why this does not go through the same provider as Slice 4. Not an oversight.

**The model is loaded once, as a module-level singleton.** Loading it per request is
the difference between a search that feels instant and one that looks broken.

**`EMBEDDING_DIM` is 384.** Anything in `reference/original-scaffold` saying 1536 is
describing the old OpenAI setup and does not apply here.

**`fastembed` downloads the model the first time it runs.** It needs internet once
and is offline after.

Two corrections to that sentence, both found by measuring rather than by reading,
2026-09-07. **It is about 65 MB, not 130.** The 130 figure had been repeated in four
files since the plan was written and nobody had ever looked; the model directory on
disk is 65 MB and the CI cache it produces is 61 MB compressed. And it was **not**
flagged in [`first-week.md`](./first-week.md), which this file claimed twice — that
doc did not mention the download at all until now. A setup doc that goes quiet for a
minute during `pytest -q` with no explanation is the thing that doc exists to prevent,
so it now says what the pause is.

### Decided 2026-09-07, before building

**The model loads lazily, not at import.** "Module-level singleton" says it loads
*once*; it does not say *when*. Loading at import means every `uvicorn --reload`
after a saved file, and every test collection, pays several seconds for a model
nobody has asked to use yet. So `get_model()` builds it on first use and hands back
the same object forever after. The cost is that the first search after a restart is
slow and every one after it is not — and the frontend says "Searching…" for exactly
that moment.

**No BGE query prefix.** This model's authors suggest prefixing a search query with
"Represent this sentence for searching relevant passages:". It buys a little accuracy
on short queries and it costs a fourth new idea in a slice that already has vectors,
cosine similarity and numpy. Skipped deliberately, and written down here so nobody
finds it in the model card later and thinks it was missed.

**Negative scores are clamped to 0 at the route, not in the maths.**
`cosine_similarity` returns the honest −1 to 1, because that is what a cosine is and
a function that lies about its own range is worse than one you have to read. The
route clamps, because [`api.md`](./api.md) promises 0 to 1 and "less related than
unrelated" is not a distinction worth showing a student. There is a test on each half
of that.

**Chunks with no embedding are skipped, and the count is shown.** Everything stored
during slice 2 has `embedding` NULL, including all 31 pieces of `ch1 DB.pdf`. Three
options were on the table — skip them, backfill with a script, or backfill on
startup — and skipping won, for the same reason slice 2 refused to backfill: a
migration nobody runs twice costs more than deleting a note and uploading it again.

What makes that safe rather than silent is the counting. `POST /search` returns
`unsearchable_note_ids`, and the search box says how many notes cannot be searched and
what to do about it. A note that sits in the list and quietly never matches anything
is the exact failure slice 1.5 and slice 2 both exist to remove; this is the third
door into it, and it is shut the same way — loudly.

**An upload that cannot be embedded fails entirely.** Same single transaction as
slice 2: embed after chunking and before the insert, so there is never a document
whose pieces have no vectors. The alternative — store it now, embed it later — is a
job queue, which is a whole second system to explain.

**`test_embeddings.py` uses the real model; everything else stubs it.** A stubbed
embedder returning made-up numbers cannot be wrong about *meaning*, so it would pass
the cat/kitten test while proving nothing. The 65 MB download is cached in CI, keyed
on the model name — change `EMBEDDING_MODEL` and that key has to change with it, or
CI restores the wrong model and downloads on every run. Route tests stub `embed_texts`
so the suite stays fast.

### Checklist

- [x] #11 `embeddings.py` — meaning as numbers, and how to compare them _(Alif)_
- [ ] #12 Embed each chunk as it is saved _(built; closes when the PR merges)_
- [ ] #13 `POST /search` — find the right notes, with no AI _(built; closes when the PR merges)_
- [ ] #14 The search box, showing results with scores _(built; closes when the PR merges)_

### #11 built, 2026-09-07

Written out in full rather than scaffolded, because `embeddings.py` is a tech-lead
file in [`team.md`](./team.md). #12, #13 and #14 were meant to be scaffolded at this
point — see the ownership note above for what actually happened.

- [x] `backend/app/embeddings.py` — `get_model()`, `embed_texts()`,
      `cosine_similarity()`, and `EmbeddingUnavailable` for a load that fails
- [x] `backend/tests/test_embeddings.py` — 11 tests. **83 pass**, up from 72
- [x] `docs/api.md` — the Slice 3 errors, the clamp, and the unsearchable notes,
      written **before** #12 and #13 start, which is what the contract rule is for
- [x] The fastembed model cached in CI, so only the first run pays for the download
- [x] A `threading.Lock` around the model build, after review found two threads
      could both build one — see the review note below

### Reviewed, 2026-09-07 — one fixed, one declined

**"Two threads can both build the model." Valid, and fixed.** `get_model()` checked
`_model is None` and built one with nothing stopping a second thread doing the same.
It is reachable, not theoretical: our routes are plain `def`, so FastAPI runs them in
a **pool of threads**, and two people uploading at once is enough. Both would see
None, both would build — double the memory and the wait, and on a first run, two
threads writing into the same download directory. The second model then replaces the
first and nothing looks wrong, which is the worst shape a problem can have.

This is the reason [`team.md`](./team.md) puts the engine modules with the tech lead
in the first place: *"non-obvious failure modes (threading, model loading, network
errors)"*. That sentence predicted this exact bug.

Fixed with a `threading.Lock` taken on **every** call, not the "check first, then
lock" version. That is double-checked locking; it saves nanoseconds, it is fiddly to
get right, and the work waiting behind this lock is embedding text, which takes
millions of times longer. Obvious beats clever here.

**The test was checked against the broken code before being trusted.** Eight threads,
a deliberately slow fake model, and an assertion that the constructor ran once. With
the lock removed it reports "the model was built 8 times, not once". A concurrency
test that has never been seen to fail is not evidence of anything. **84 tests pass.**

**"Pin `actions/cache@v4` to a commit SHA." Real mechanism, declined here.** A moving
tag can be repointed, and an action in CI can do anything the job can. Not fixed, for
two reasons.

It would be the only pinned action of five — `checkout@v7`, `setup-python@v7` and
`setup-node@v7` are all mutable tags, and `checkout` runs *first*, in the same job,
with the same permissions. Pinning the cache step while leaving those alone does not
close the hole; it just makes one line look safer than it is. And this workflow holds
no secrets: `GROQ_API_KEY` is never given to CI, so the realistic worst case is a lie
about whether the tests passed, which a human review of the diff still catches.

The honest fix is all five or none, and all five means five 40-character SHAs that
nobody on this team can read and nobody will remember to bump. **If this project is
ever deployed, or CI is ever given a secret, pin them all — that is when this becomes
the wrong call.** Recorded here rather than argued in a PR thread that closes.

**A float32 lesson, from a test that failed.** `cosine_similarity([1,2,3], [[1,2,3]])`
does not return 1.0. It returns 0.99999994, because dividing by a length and
multiplying back in 32-bit floats does not land exactly where it started. The first
version of the test asserted exact equality and failed — correctly. Nothing in this
project should ever compare two scores with `==`.

### Verified against the real database, before `/search` exists

The 34 chunks already in the dev database — the 31-page Silberschatz deck plus a
short osmosis note — embedded and scored by hand:

- **34 chunks embedded in 3.9 seconds.** A query embeds and scores against all 34 in
  **0.01 seconds**, which is the number that makes the no-index decision in
  [`adr/0001-sqlite-and-numpy.md`](./adr/0001-sqlite-and-numpy.md) look obviously
  right rather than merely defensible.
- **"what is a database schema" → p.15, scoring 0.83.** Page 15 is the slide titled
  *Instances and Schemas*. **"how does a transaction work" → p.26**, the slide titled
  *Transaction Management*. Neither query shares its wording with the slide it found.
- **"recipe for banana bread" → 0.46, top score.** Nothing matched, and this is the
  demo moment.

**One number worth knowing before #14 is built.** The floor is not zero. Total
nonsense still scores about **0.46**, because two pieces of ordinary English are
never truly unrelated to this model. So the honest demo line is "watch the scores
fall from 0.83 to 0.46", not "watch them fall to nothing" — and any threshold slice 4
uses to decide it found nothing has to be set from real numbers like these, not from
an intuition that irrelevant means near zero.

### #12, #13 and #14 built, 2026-09-07

The slice is complete: type a question, watch the right paragraph surface, with a
percentage next to it and no language model anywhere in the path.

- [x] `POST /documents` embeds every piece in **one batched call**, before anything
      is written, and stores each vector as JSON in the `embedding` column
- [x] `POST /search` — a Pydantic `SearchRequest`, the 400 for a blank query, one
      SELECT joining `chunks` to `documents`, `cosine_similarity`, and the best
      `TOP_K` with the score clamped at 0
- [x] `backend/tests/test_search.py` — 14 tests. **96 pass**, up from 83
- [x] `search()` in `api.js`, and the search card in `App.jsx` with all five states:
      nothing searched, searching, results, nothing found, and failed
- [x] `.input` and `.visually-hidden` added to `global.css`, both following
      [`design.md`](./design.md) rather than inventing anything
- [x] `docs/api.md` — Slice 3 moved from planned to built, and the upload 503 pinned
- [x] `ruff check`, `ruff format --check`, `npm run lint`, `npm run build` all clean

### Decided while building

**The single transaction now covers the vectors too.** Embedding happens *before*
the document row is written, not after, so a failure means no document at all. The
alternative — store it now and embed later — is a job queue, which is a second
system to explain, and it would leave a window where a note exists that no search
can find. That window is the exact failure slices 1.5 and 2 both exist to close.

**Search is a snapshot, so deleting a note clears matching results.** Results are
fetched once and sit there; nothing else would ever remove them. Without this,
deleting a note leaves its pieces on screen under a filename that no longer exists
— the same shape of bug the slice 2 review found with the pieces panel, arriving
by a different route. `handleDelete` filters them out by `document_id`.

**The search box is a `<form>`, not a button with an onClick.** That is what makes
Enter work, and typing a question and pressing Enter is how everybody expects a
search box to behave. It costs one `event.preventDefault()` and a comment saying
why forms reload the page without it.

**Two pieces of state for one query, not one.** `query` is what is in the box;
`searched` is what produced the results on screen. They differ the moment somebody
starts typing their next question, and the heading should keep naming the search
that the results below it actually came from.

### Verified against the real running server

Not tests — the actual backend, on the real dev database, which still holds the
pre-slice-3 notes:

- **A blank query** returns 400 and the sentence, not a stack trace.
- **Before uploading anything new: `{"results": [], "unsearchable_notes": 2}`.** (That
  field was renamed to `unsearchable_note_ids` in review afterwards — the quote is
  what the server said at the time.) The
  skip-and-count decision, working on real rows rather than in a fixture. Those two
  notes are `ch1 DB.pdf` and an older osmosis note, both stored before slice 3.
- **Uploading a note took 2.1 seconds**, embedding included, and it was immediately
  searchable.
- **"why do cells swell in pure water" → 0.705.** The note never says "swell", or
  "cells". **"diffusion" → 0.684**, and the note never says that either. **"recipe
  for banana bread" → 0.449.** That spread is the demo.

### Reviewed after building — three findings, all three valid

Worth noticing as a set: **each one is a snapshot going stale**, in a different
place. Nothing here is about the maths or the model.

**1. A slow search overwrites a newer one.** Two searches in flight, the older
answer lands last, and the screen shows results and a heading for a question
nobody is asking any more. **Not reachable today** — the Search button is disabled
while a search runs, and a disabled default button also stops the Enter key
submitting. Fixed anyway, matching what slice 2 did with the stale selection: a
`searchRun` counter in a ref, and an answer that is not the newest is dropped.
The ref is the same idea as the `ignore` flag on the effects nearby, in the shape
an event handler needs — an effect gets a cleanup function to mark itself stale
and a click handler does not.

**2. A finished search puts a deleted note back on screen.** `handleDelete`
filtered the results, but a search already in the air would arrive afterwards
carrying that note and replace the filtered list. **This one is reachable right
now:** start a search, click × on a note, wait. Delete buttons are not disabled
during a search, and nothing else clears results, so the note's pieces would sit
there under a filename that no longer exists. Fixed with a `deletedIds` ref that
arriving results are filtered through.

**3. A stored vector of the wrong width crashes every search.** Change
`EMBEDDING_MODEL` and `EMBEDDING_DIM` together — the realistic upgrade — and
everything already stored is the old width. Comparing a 384-number query to a
768-number piece is not a weak match, it is a numpy `ValueError`, which is a 500
and a traceback on **every search** until somebody works out which rows to delete.
Verified by removing the guard and watching two tests fail exactly that way.

Fixed by treating a wrong-width vector as **unsearchable**, not as an error. That
reuses a concept that already exists rather than adding a new failure path, and
the remedy the UI already names — delete the note and upload it again — is the
right remedy here too. The two kinds of unsearchable note are found in different
places, one in SQL and one in Python, so they are collected as a **set of ids** and
counted at the end; adding two counts would report one note twice.

**4. The unsearchable count went stale after a delete, and a count could not be
fixed.** Reported as a race — delete an unsearchable note while a search is in
the air, and the arriving response reinstates a count that includes it. True, and
**the same bug is reachable with no race at all**: search, read "1 note was added
before search existed — delete it and upload again", delete exactly that note, and
the sentence stays until the next search.

The interesting part is *why* the first three fixes did not cover this one. A
count cannot be reconciled with a deletion. The frontend has a number and no way
to know whether the note it just deleted was one of the notes being counted, so
whatever it does — leave the number, or decrement it — is wrong half the time.

So the contract changed while it still costs nothing to change it: `POST /search`
now returns **`unsearchable_note_ids`**, a list, instead of `unsearchable_notes`,
a number. The frontend filters that list through the same `deletedIds` set it
already filters results through, and counts what is left. **Two lists, one rule** —
that is fewer ideas on the page than a list and a number that need different
handling, not more.

`docs/api.md` changed in the same commit, which is what the contract rule asks
for. Nobody else was building against it: slice 3 is one unmerged branch, which is
exactly the window where changing a shape is free. After a merge this would have
been a conversation first.

**99 tests pass**, up from 96. The three new backend tests were run against the
old code first and fail there — the two width tests with numpy's `ValueError`, and
the ids test because a count cannot name which note went away.

**The frontend fixes have no tests, and that is a real gap.** There is no test
runner in `frontend/` at all — `npm run lint` and `npm run build` are the only
automated checks, and neither can see a race. Both fixes are reasoned and read
carefully; neither is proven. Worth an issue of its own rather than pretending
otherwise.

### The browser check happened, and it earned its place

Somebody typed "How does osmosis work?" into the box and got **"Not Found"** in
coral. Two separate things were wrong, and only one of them was a bug.

**The cause was a stale backend, not the code.** The `uvicorn` running on port 8000
had been started before slice 3 existed, so it served `/health` happily and had no
`/search` at all. Confirmed by asking it directly: `GET /health` → 200,
`POST /search` → 404. Restarting it fixes the search. Nothing on this branch was
wrong.

**The bug was that the screen said "Not Found".** Those are FastAPI's words, not
ours, and [`CLAUDE.md`](../CLAUDE.md) says a person never sees a raw error — a plain
sentence and a way to try again. `api.js` trusted `detail` from any failed response,
which is right for the sentences our own routes write and wrong for the two kinds of
failure the framework generates:

- **404 "Not Found"** means the backend has no route at that address, which is never
  the user's doing. It means the two halves of the app disagree about what exists —
  almost always a backend running older code, which is precisely what this was.
- **422** carries a *list of objects* in `detail`, not a string, so
  `new Error(thatList)` would have put "[object Object]" on screen. Latent, and one
  malformed request away from being seen.

Now both get a written sentence, and the 404 one names the fix: restart the backend
with `uvicorn app.main:app --reload`. **The error message went from a fact nobody can
act on to the actual diagnosis** — which is the whole point of the rule.

**This is the argument for clicking things, in one screenshot.** 96 tests, a clean
production build, and every endpoint verified against a real server, and the first
thing a person saw was a red error. No test could have caught it: the tests run
against the code as it is now, and the failure was a *running process* that was not.

**Still not verified: a successful search in the browser.** The stale server needs
restarting first, and then it takes a minute — there is one searchable note in the
dev database ready for it.

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
