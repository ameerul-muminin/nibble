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
(`openai/gpt-oss-120b`) for answers, and Vite + React in plain JavaScript.

**That chat model changed on 2026-09-07, and not by choice.** This said
`llama-3.3-70b-versatile` from the start, and the first real `POST /ask` came
back `404` — Groq had retired it. See the note under Slice 4; the lesson is
worth more than the model name.

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
| 3   | Search, no AI yet     | Slice 3 — Search          | done, merged            |
| 4   | Nibble answers        | Slice 4 — Nibble answers  | done, merged            |
| 4.5 | On the internet       | — (unplanned)             | built, not deployed     |
| 5   | Make it Nibble        | Slice 5 — Make it Nibble  | paused — now last       |
| 6   | Quiz yourself         | Slice 6 — Quiz yourself   | next                    |
| 7   | The classroom         | Slice 7 — The classroom   | open                    |
| 8   | Marking               | Slice 8 — Marking         | open                    |

**Build order is no longer the same as the numbering**, as of 2026-09-08: deploy
4.5, then 6, 7, 8, and slice 5 last. Why is under "Current state" below.

**The demo is safe from the end of Slice 4.** Everything after it is either polish
or the classroom feature, and both can be dropped if time runs out.

**Slice 3 is the pivotal one.** Semantic search with no chatbot involved — typing
"osmosis" and watching the right paragraph surface. It's the moment RAG stops being
magic, and it's a working demo on its own even if everything after it fails.

## Current state, 2026-09-08

`main` is at `b3219a4` and **Slices 0, 1, 1.5, 2, 3 and 4 are all merged.** #33
(chunking), #35 (the slice 2 handover and the open-backend decision), #34 (the
landing page), #36 (`embeddings.py`), #37 (the rest of search) and #40 (the whole
of slice 4) all landed within two days, and **#11 through #17 are closed.**

**This section drifted and is being corrected out loud, as the rules above ask.**
It was headed 2026-09-07 and said Slice 5 was the current slice. Slice 4.5 was
built the next day and its edit to this file was a pure insertion — it added a
whole slice after Slice 4 and updated nothing around it, so the table above had no
4.5 row and this paragraph never learned 4.5 existed. That is the mirror rotting in
the direction it always rots.

**Slice 4.5 is built and sitting uncommitted in the working tree.** `auth.py`,
`tests/conftest.py`, `tests/test_auth.py`, `Dockerfile`, `deploying.md` and
`adr/0003-hosting.md` are all untracked; `routes.py`, `db.py`, `config.py`,
`api.js` and `App.jsx` are modified. 147 backend tests pass. **Nothing has been
deployed.**

### The plan changed on 2026-09-08, and slice 5 moved to last

Nibble is growing a classroom: a teacher generates a quiz from a chapter, opens a
room, students join with a code, answer, and the teacher marks what comes back.
That is slices 6, 7 and 8 below, and it replaces the old one-line "Slice 6: Quiz
mode" stretch goal.

**Slice 5 is paused where it is, and that breaks "finish a slice before starting
the next."** It is written down rather than smoothed over, because it is a real
departure from [`team.md`](./team.md):

- **A classroom cannot be demoed on one laptop.** It needs a second person on a
  second device, which means the 4.5 deploy stops being optional the moment this
  feature exists. Deploying is now the next thing that happens.
- **Slice 6 is useful on its own to every user**, teacher or not — quiz yourself
  from your own notes. So the ordering does not gamble the demo on the classroom
  landing.
- **The cost is that the demo runs on slice 5's unfixed CSS.** Note rows and chunk
  boxes currently render with **no border at all** — see the four broken lines under
  Slice 5. So `fix/borders-and-danger-token` is pulled out of slice 5 and done on
  its own, first, because it is four lines and it is visible in every screenshot.

**The demo now exists.** Upload a chapter, ask a question in your own words, and
the right paragraph comes back with the page it is on and how well it matched —
and no language model is involved anywhere in that path. That was the point of
slice 3 being called the pivotal one, and it holds: if everything after this
failed, there would still be something worth showing.

**Slice 4 merged as PR #40**, and #15, #16 and #17 closed with it. The full
record is under Slice 4: what was built, the chat model Groq retired underneath
us mid-slice, the sign-out state leak review caught, and why PR #39 was not
merged.

**One thing merged unverified, and it is still unverified.** Nobody has opened
slice 4 in a browser. The API is proven end to end against real Groq calls and
the chat UI is proven by lint and build, which is not the same claim. The two
checks a person still owes are listed under Slice 4 — they did not stop the merge
and they have not stopped being owed.

**The demo is now complete.** Upload a chapter, ask a question in your own words,
and get an answer built from your own pages with the pages it read underneath it
— and when your notes do not cover the question, it says so instead of inventing
an answer. That refusal was checked by hand against a real key; the table is
under Slice 4.

**Who builds it went the same way as slice 3, and that is now a pattern rather
than an exception.** Alif built #16 and #17 as well. It is written up under Slice
4 rather than here, because it is a decision with a cost, not a status.

What works, end to end: upload a PDF, a text file, a Markdown file or a photo;
see it listed and delete it; a scan or handwriting gets read by a vision model
instead of arriving empty; the text is cut into overlapping pieces you can look
at; every piece is embedded as it is stored; search finds the closest ones; and
Nibble answers a question from those pieces, showing the pages it read and
refusing when they do not cover it.

### The board now agrees with the code

**22 issues, 16 closed.** It started as 22 with 6 closed — #2 through #7 — which
were built and merged weeks apart from being closed, and for a while this file
said so while the board did not. That gap is shut and has stayed shut: every
slice since has closed its issues on the merge that finished it.

**The six still open are #18, #19, #20 and #21 (slice 5), then #22 and #23.**
Nothing before slice 5 is outstanding on the board.

**The board does not know about the 2026-09-08 replan yet, and that is work owed
rather than a disagreement.** #22 and #23 were written for the one-line "Quiz
mode" stretch goal; they now belong to Slice 6 and Slice 7 respectively and their
milestones have to move. Slices 7 and 8 have no milestone and no issues at all,
and slice 4.5 never had either. Until somebody creates them, this file is ahead of
the board — which is the opposite of the usual drift and just as worth saying out
loud. **GitHub still wins on status**; it simply has not been told yet.

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

**Done and merged, 2026-09-07**, in two pull requests: #36 for `embeddings.py` and
#37 for the rest. All four issues are closed. **99 backend tests pass.**

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

- **The board now says three people built this slice, and one did.** #12 and #13
  closed still assigned to Fahim and #14 to Arman, because they were never
  reassigned before the merge. Same fossil as #8's wrong signature: harmless in
  itself, since nobody reads a closed issue, and misleading to anyone reading the
  milestone later. Recorded here because this file is the truth for reasoning and
  the board is not going to be corrected retroactively.
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
- [x] #12 Embed each chunk as it is saved _(merged in #37)_
- [x] #13 `POST /search` — find the right notes, with no AI _(merged in #37)_
- [x] #14 The search box, showing results with scores _(merged in #37)_

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

**The browser, second attempt.** The stale server was stopped, a current one was
started, and `POST /search` was checked against it at the port the frontend actually
uses: 200, the osmosis note at **0.821**, and `unsearchable_note_ids` empty. What is
still not written down by anybody is a person confirming they *saw* a result on
screen — the slice merged on the strength of everything else, which is a reasonable
call and not the same thing as having looked.

### Left over from this slice

- [ ] **There is no test runner in `frontend/` at all.** `npm run lint` and
      `npm run build` are the only automated checks, and neither can see a race.
      Four review findings in this slice were about state going stale, three of
      them fixed in `App.jsx` with nothing able to verify them, and slice 4 puts
      more async state on the same page. **This wants an issue of its own.**
- [ ] **A person has not confirmed a search result on screen**, as above.
- [ ] **`osmosis-slice3.txt` is sitting in the dev database**, uploaded while
      verifying. It is the only searchable note there, so it is worth keeping until
      somebody does the browser check, and worth deleting after.

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

**`sources` is what Nibble read, not what it quoted.** Every retrieved piece is
listed, not just the ones a sentence cites. Working out which pages an answer
actually used means parsing citations back out of prose, and being wrong there is
worse than not guessing: it hides a page that was used, or claims one that was
not. "These are the only pages it was allowed to look at" is true, checkable, and
the sentence to say at the demo.

**Retrieval lives in one function, `_retrieve()`, that both routes call.** `/search`
returns what it finds; `/ask` hands what it finds to the model. That was issue #16's
whole lesson — reuse your own code rather than copying it — and the reason is
concrete: every later fix to how searching works would otherwise have to be
remembered twice, and the second copy is the one that gets missed.

**`/search` stays, and stays visible in the UI, now that `/ask` exists.** The
temptation is to fold it in once there is a chat on the page. Keeping it is what
makes the answer above it believable: you can watch the retrieval happen with no
model anywhere near it, then watch the same pieces come back as a sentence.

### Built and merged, 2026-09-07 — PR #40

**PR #40 squash-merged to `main` as `b3219a4`, and #15, #16 and #17 closed with
it.** Slice 4 is done and the milestone is empty. Two checks a person owes are
still owed and are listed below — they are recorded as open rather than being
quietly dropped at the merge.

### Built, 2026-09-07

- [x] #15 `llm.py` — `SYSTEM_PROMPT`, `build_context()`, `answer()`, and an
      `AnswerUnavailable` error that mirrors `OcrUnavailable` and
      `EmbeddingUnavailable`. Nothing else in the backend calls the chat model.
- [x] #16 `POST /ask` — retrieval reused through `_retrieve()`, a short-circuit
      that returns a friendly sentence **without calling the model** when nothing
      came back, and 200/400/503 exactly as `api.md` now describes.
- [x] #17 `ask()` in `api.js`, and the chat on the page — a `turns` array that is
      only ever appended to, question bubbles that appear instantly, and a source
      chip per page read.
- [x] 33 new tests (`test_llm.py`, `test_ask.py`). **132 backend tests pass**,
      lint and format clean, frontend lint and build clean.
- [x] Verified against the real Groq API, not just fakes: a covered question
      answered with a real page citation in ~2s, an uncovered one refused, an
      empty database short-circuited in under a second.

### The chat model was retired mid-slice, and that is the lesson here

The first real `POST /ask` returned **503, "The answering service answered with
404."** `llama-3.3-70b-versatile` — named in this file, in `config.py` and in
`HANDOFF.md` since the beginning — no longer exists on Groq. Not deprecated with
a warning; gone, answering 404 like a typo would.

`GET /models` on the same key listed what was actually there, and
`openai/gpt-oss-120b` replaced it.

**A hosted model is not a decision you make once.** Every other choice in this
project stays made: SQLite is a file, numpy is numpy, and `fastembed` runs on the
laptop and will still run in a year with no internet at all. The one component
rented from somebody else is the one that broke, without a line of our code
changing. That is the honest trade for "free chat with no card", and it is worth
being able to say out loud at the demo rather than being surprised by.

Two things that made this a ten-minute problem instead of an afternoon:

- **The error was already a plain sentence.** `llm.py` never passes Groq's own
  words through, so the failure arrived as "The answering service answered with
  404" rather than a traceback — and 404 pointed straight at the model name.
- **`CHAT_MODEL` was in `config.py` and nowhere else.** One line changed.

**Check `GET /models` first when answering suddenly stops working.** It is the
one failure in this project that nobody's code caused.

### What "low" reasoning is doing in config

`openai/gpt-oss-120b` thinks before it answers, and how much is a setting.
Running the same five questions at `low` and `medium`: the answers were no
better at `medium` and cost two to four times the tokens. On a free tier shared
with reading handwriting, tokens are the budget.

Not zero, though. Deciding *"is this actually in the notes?"* is the one piece of
thinking this project genuinely wants — it is the refusal, and the refusal is the
product.

Worth knowing before anyone swaps the model: this one keeps its thinking in a
separate `reasoning` field, so there is nothing to strip out. The vision model in
`ocr.py` inlines it in `<think>` tags and `_strip_thinking()` exists for exactly
that reason. A model that inlines its thinking would put it straight on screen.

### The refusal, checked by hand

The one behaviour no test can assert — a test would only be checking a fake. Run
against real notes about osmosis and a real key:

| Asked | Answered |
| --- | --- |
| "how does osmosis work" | the definition, citing `(p. 1)` |
| "explain how a black hole forms" | "That isn't in your notes yet." |
| "what is the capital of France" | "That isn't in your notes yet." |
| **"what is diffusion"** | **"That isn't in your notes yet."** |

The last row is the one that matters. Diffusion is one concept away from osmosis,
every model on earth knows what it is, and the notes did not mention it — so it
refused. A model that answers that one from training is a model that will invent
a fact under exam conditions and sound completely confident doing it.

**Re-run these four after any change to `SYSTEM_PROMPT` or `CHAT_MODEL`.** The
prompt is the only thing holding this behaviour up, and nothing in CI can tell
you it stopped working.

### Fixed in review: the conversation outlived the person who had it

Found by review on PR #40. **Signing out does not clear anything on this page.**

`App` returns `<Landing />` when nobody is signed in, and a `return` is not the
component going away — React keeps it mounted in the same position and every
`useState` in it keeps its value. Sign out, sign in as somebody else in the same
tab, and the previous person's questions and answers are still on screen.

It is broader than the chat. `searched` from slice 3 is rendered verbatim — "5
pieces for *"…"*" — so the last thing the previous person typed into the search
box was sitting there too. Fixing only the transcript would have left an
identical leak beside it, looking fixed.

**This is not covered by the open-backend decision above.** That decision says
everyone shares the same notes, and it is written down so nobody is surprised.
The *questions somebody typed* are not shared by any decision, and they are the
most personal thing on the page — you can tell what a person did not understand.

The fix is `<Nibble key={userId ?? 'signed-out'} />`. Changing a `key` tells
React the thing at that position is a different one now, so it throws the old
component away and builds a new one with fresh state.

Chosen over clearing each piece of state by hand for the reason `ON DELETE
CASCADE` was chosen over a hand-written `DELETE` in slice 1: **a list of things
to reset is a list somebody has to remember to add to**, and the day it is
forgotten it fails silently. Every state added from here on is covered for free,
including an answer still in flight when the user changes — that arrives to a
component that no longer exists and React drops it.

- [ ] **Not yet verified in a browser.** Lint and build pass. Actually signing
      out and back in as a second Clerk account, in one tab, is a person's job.
      It is the second item under "Still needing a person" below — the same
      check, not a second one.

### Still needing a person

These two outlived the merge. Slice 5 rebuilds most of this screen, so whoever
picks up #19 will be looking straight at both — do them then rather than treating
them as slice 4 leftovers nobody owns.

- [ ] **Nobody has opened this in a browser yet.** The API is verified end to end
      with real Groq calls; the chat UI is verified only by lint and build.
- [ ] **Signing out and back in as a second Clerk account, in one tab.** The
      `key={userId}` fix above is verified by lint and build and by reasoning
      about how React treats a changed `key`. That is not the same as watching
      the previous person's questions disappear.

- [x] **The board.** #15, #16 and #17 closed when PR #40 merged.
- [x] **Who built it.** This was the second slice in a row where the work did not
      go to the people it was assigned to — #16 was Fahim's and #17 was Arman's.
      Recorded rather than fixed; it is a decision with a cost, and slice 5 is
      where that cost gets paid or not.

### PR #39 was not merged, and why

Fahim opened #39 for slice 4 on 2026-09-07. It was **branched from `6afb799`**,
the rebuild commit, so it had never seen slices 1, 1.5, 2 or 3. Merging it would
have reverted `routes.py` and `files.py` to their slice-0 state: no
`_safe_filename()`, so the path-traversal fix would have come back out; no
chunking, no embedding on upload, no `POST /search`, no `DELETE`, and the
`.text`/`.markdown` extensions the contract had already settled.

Its `/ask` also could not run. It imported `search_chunks` from `app.embeddings`,
a function that has never existed there, and the import sat above the `try` — so
every request would have been a 500. The `except Exception: results = []`
underneath would then have called Groq with no notes at all, which is the exact
short-circuit #16 exists to prevent.

**None of that is a review comment about code quality — it is a branching
problem**, and it is worth writing down because it will happen again:

- **Always `git checkout main && git pull` before `git checkout -b`.** #39 was
  branched once and worked on while five PRs merged underneath it.
- **A PR that adds a file which already exists on `main` is the tell.** #39 added
  `db.py` and `files.py` as new files. That is never a rebase away from correct.

The work was rebuilt on current `main` rather than rebased — three commits of
divergence against a tree that had moved that far is not a rebase, it is a
rewrite with extra steps.

- [x] #15 `llm.py` — ask Groq, and force it to stay grounded _(Alif)_
- [x] #16 `POST /ask` — search, then answer _(built by Alif; #39 not merged)_
- [x] #17 Turn the page into a chat with Nibble _(built by Alif)_

## Slice 4.5: Nibble on the internet

A public URL anyone can open: the frontend on Vercel, the backend on Render,
and — first, because nothing else is safe without it — real auth on every route.

This slice was not in the original plan. It exists because someone asked whether
Nibble could go on Vercel's free tier, and answering that honestly turned up a
decision this project had already made and deferred.

### Decided, 2026-09-08 — Vercel cannot host the backend, and that is not a config problem

Vercel hosts the frontend for free and hosts it well. It cannot host this
backend, for three reasons that are all structural rather than fixable:

- **No disk.** A Vercel function's filesystem is read-only except `/tmp`, which
  is per-instance and does not survive. `nibble.db` *is* this app's memory. Upload
  a chapter and the next request can land on an instance that has never seen it.
  There is no version of this that keeps `sqlite3` and a file on disk, and that
  file is the whole bet in [`adr/0001-sqlite-and-numpy.md`](./adr/0001-sqlite-and-numpy.md).
- **Too big.** The Hobby plan caps a Python function at 250 MB unzipped.
  `fastembed` brings `onnxruntime` and tokenizers with it; add numpy and
  pypdfium2 and that is gone before the 65 MB model file is counted.
- **Too slow.** Hobby functions cap at 60 seconds. The first search after any
  cold start downloads *and* loads the model — so the platform defeats the
  module-level singleton rule from CLAUDE.md by construction, paying that cost
  again on every cold start. OCR is worse on purpose: `OCR_MAX_PAGES = 5` at
  `OCR_RETRY_WAIT_SECONDS = 20` is a deliberately multi-minute upload.

The full reasoning is in [`adr/0003-hosting.md`](./adr/0003-hosting.md). It
originally chose a free Hugging Face Space over Render; **that half of it is
superseded** — see the next section.

### The blocker that mattered more than the hosting

The auth decision under Slice 1 said it in one line: **do not deploy this
anywhere public as it stands.** No route checks who is calling, `documents` has
no `user_id`, and Clerk gates the UI and nothing else. A public URL without auth
hands strangers a delete button on your notes.

That decision was made on the explicit condition that nothing is deployed. So
deploying does not "also need a bit of auth" — it reopens a slice-1 decision, and
that reopening is most of this slice. The earlier entry deferred auth to protect
slices 3 and 4; those are now built, which is exactly the condition it named for
revisiting.

### Decided, 2026-09-08 — how auth is done

- **Clerk verifies, we trust the `sub`.** The frontend already has a Clerk
  session. It sends the session token as `Authorization: Bearer <token>`, and
  the backend verifies the signature against Clerk's public keys and reads the
  `sub` claim. That claim is the user id. We store nothing about a person
  beyond that opaque string — no email, no name, nothing to leak.
- **One new dependency, `pyjwt[crypto]`.** `PyJWKClient` fetches and caches
  Clerk's signing keys. Verifying a JWT by hand is the kind of code that is
  wrong in ways nobody notices until it matters, and this is the standard tool.
- **`documents` gets `user_id`; `chunks` does not.** A chunk reaches its owner
  through `document_id`, which is already indexed and already cascades on
  delete. A second copy of the same fact is a second thing to keep true.
- **A note you do not own is a 404, not a 403.** 403 confirms it exists.
- **`/health` stays open.** The host's health check calls it, and it says
  nothing about anybody.

### Decided, 2026-09-08 — an old database fails loudly instead of migrating

`CREATE TABLE IF NOT EXISTS` will not add `user_id` to a `documents` table that
already exists, so an existing `nibble.db` would keep working and quietly ignore
the new column. That is the silent failure this project keeps trying to avoid.

The options were a migration system or a loud error. We took the loud error:
`db.py` checks the shape of the table it found and, if it is the old one, raises
a plain sentence telling you to delete the file. Migrations are a genuinely
useful idea and a whole new one to explain, the data is a demo database, and the
deploy target starts empty regardless. If Nibble ever holds notes somebody would
be upset to lose, this is the decision to revisit first.

### The host disappeared before we could deploy to it, 2026-09-08

**Hugging Face made the Docker SDK a paid feature in early July 2026**, and we
found out by trying to create the Space. A Docker Space now needs PRO on a
personal account. There was no announcement, no changelog entry and no
documentation update — people found it because a "Paid" badge appeared on the
new-Space form. Static Spaces are still free, and a static host cannot run Python.

Everything in this project is free, so PRO is not an option. **The backend goes to
Render instead**, which [`adr/0003-hosting.md`](./adr/0003-hosting.md) had
considered and turned down because its free tier sleeps after 15 minutes while a
Space idled out after 48 hours. That reasoning was right and the thing it was
compared against no longer exists.
[`adr/0005-render.md`](./adr/0005-render.md) is the replacement decision.

**This is the second time an external provider changed underneath this project
without a line of our code changing.** Groq retired `llama-3.3-70b-versatile`
mid-slice-4 and every `/ask` came back 404; now this. Worth saying out loud at the
demo, because it is the same lesson twice: the parts that run on our own machine —
SQLite, numpy, `fastembed` — are the parts that have never broken. Everything
rented from somebody else has.

### The hosting limit found a real bug, and that is the part worth keeping

Render's free tier is 512 MB of RAM, and the obvious question was whether the
backend fits. Measuring it turned up a defect that had nothing to do with hosting.

`POST /documents` embeds every piece of a document in **one** `embed_texts` call —
which slice 3 chose deliberately, and which is still right. What nobody looked at
is that `fastembed` groups the texts internally, in batches of **256** by default.
So peak memory grew with the size of the upload, with no ceiling short of the
20 MB file limit. Measured on real 900-character English, embedding a 400-piece
document:

| `batch_size` | Peak memory | Time |
| --- | --- | --- |
| 256 (the default) | **1275 MB** | 27.8s |
| 32 | 473 MB | 29.6s |
| 16 | 341 MB | 29.5s |
| **8 (chosen)** | **278 MB** | 29.5s |

**Every row took the same thirty seconds.** The work is identical either way; only
how much of it is held at one moment changes. So the smaller batch is free, and it
buys something better than a smaller number: **memory is now flat.** At 8, a
40-piece chapter and a 400-piece book peak at the same place. Before, the ceiling
was whatever the largest file anybody happened to upload.

The fix is one argument — `batch_size=config.EMBED_BATCH_SIZE` on the `.embed()`
call — not a loop, which is why it is worth having rather than clever.

Three things this is worth remembering for:

- **A 16 GB laptop hides this completely.** Nothing in 147 tests could have caught
  it, because nothing asserts memory and the test documents are tiny. It would
  have appeared as the deployed backend dying on the first real upload, with a log
  line about a killed process and nothing pointing at embedding.
- **The constraint found the bug.** Nobody was looking for this. Being forced onto
  a 512 MB host is the only reason anybody measured, and the measurement improved
  the app on every machine, not just that one.
- **"Call it once with everything" was good advice that hid a cost.** The slice 3
  docstring is still right — batching is much faster than one call per piece — but
  it said nothing about memory, because on the machine it was written on there was
  nothing to say.

### What this costs, stated before the demo rather than during it

- **The database resets.** A free Render service has no persistent disk, so
  `nibble.db` empties whenever it restarts or redeploys. Re-upload your chapter
  before demoing. This is the ADR-0001 trade showing its edge, and it is the
  honest answer if someone asks at the demo where the data goes.
- **Clerk production keys need a domain you control**, and `.vercel.app` is not
  one. Development keys work on a Vercel URL, with a dev banner and lower rate
  limits. Fine for a demo; the thing to fix first if Nibble ever gets a real
  domain.
- **The first question after a quiet spell is slow.** A free Render service
  sleeps after **15 minutes** of no traffic and takes about 50 seconds to wake —
  much more often than the 48 hours a Space would have given us. Open the URL a
  minute before the demo starts.
- **Everything is still free.** Vercel Hobby, Render's free tier, Clerk's free
  tier, and the Groq key we already use. No card anywhere.

### Ownership: this slice crossed every boundary at once

Deploying is not a folder. This slice touches `routes.py` and `tests/` (Fahim),
`db.py` and `config.py` (Alif), and `api.js` and `App.jsx` (Arman) — and it was
built by Alif in one pass, because the halves do not work separately: routes
that demand a token cannot merge before a frontend that sends one.

That is the third slice in a row where the work did not go to the person it was
assigned to, and this time it was not an accident of who was free. It is
recorded here rather than smoothed over. Adding auth to a route is a repeating
pattern over six routes — exactly the shape of task the "don't do the learning
for them" rule exists to protect, and exactly what was taken away here. If
slice 5 goes the same way, the problem is the plan, not the week.

### Checklist

- [x] `adr/0003-hosting.md` — why the backend cannot go where the frontend goes
- [x] `adr/0005-render.md` — why Render, once a free Space stopped existing
- [x] `api.md` — the auth header, and the 401 every protected route can now return
- [x] `config.py` — `CLERK_ISSUER`, `CORS_ORIGINS` from the environment
- [x] `auth.py` — verify the token, return the user id
- [x] `db.py` — `user_id` on `documents`, and the loud error for an old database
- [x] `embeddings.py` and `config.py` — `EMBED_BATCH_SIZE`, so memory is flat
      instead of growing with the size of the upload. 1275 MB down to 278 MB,
      at no cost in time. Without it the backend does not fit on the host
- [x] `routes.py` — six routes scoped to the person calling them
- [x] `tests/conftest.py` — one signed-in user for every test that had none
- [x] `api.js` and `App.jsx` — send the token on every request
- [x] `Dockerfile` — the backend as a container, with the model baked in
- [x] `deploying.md` — the steps, for someone who has never deployed anything
- [x] Lint, format, tests, and the production build, both sides

### Verified by actually running it, 2026-09-08

147 backend tests pass, both linters and both formatters are clean, and the
frontend production build succeeds. Beyond that, against a real `uvicorn`:

- `GET /health` with no token → `200 {"status":"ok"}`. It has to stay open; the
  host's health check calls it.
- `GET /documents` and `POST /ask` with no token → `401`, with the sentence a
  person should read rather than a mention of headers.
- `GET /documents` with `Authorization: Bearer junk` → `401`, and **not** the
  JWT library's own wording.
- `CLERK_ISSUER` unset → the backend refuses to start and names the file to copy.

### The bug the run caught, which the tests did not

The old-database guard was written to run *after* `_SCHEMA`, and every test
passed. Pointing it at the real `backend/nibble.db` — which predates slice 4.5 —
produced this instead of the friendly sentence:

```
sqlite3.OperationalError: no such column: user_id
```

`CREATE INDEX ... ON documents(user_id)` runs as part of the schema and hits the
missing column before anything gets a chance to explain it. So the check now
runs *before* the schema, and returns early when `documents` does not exist at
all, which is a new database rather than an old one.

Worth noting what let this through. Every test builds its database from the
current schema, so no test had an old-shaped one to find — the check was being
exercised only in the case it was not written for. The regression test in
`test_db.py` now creates a slice-1 `documents` table by hand, which is the only
way to have the thing being guarded against.

This is the second time on this project that a check written for a failure was
verified only against the success case. It is also exactly the argument for the
"actually run it" rule in CLAUDE.md: the suite was green and the feature was
broken for the single database that most matters — the one already on the
laptop.

### Still needing a person

- [ ] **The actual deploy.** Everything here is verified locally. Nobody has
      created the Render service or the Vercel project yet, and a deploy that has
      not run is a deploy that does not work. [`deploying.md`](./deploying.md) is
      the script to follow.
- [ ] **Time one real upload on Render.** The free tier gives 0.1 of a CPU and
      every timing in this project was measured on a laptop. Nobody knows yet how
      slow embedding is on a fraction of a shared core. This is the open risk in
      [`adr/0005-render.md`](./adr/0005-render.md), and the fallback if it is
      unusable is a laptop behind a free `cloudflared` tunnel.
- [ ] **Two accounts, two sets of notes, one deployed backend.** The whole point
      of this slice. Sign in as one person, upload something, sign in as another
      in a private window, and confirm the second sees nothing of the first.

## Slice 5: Make it Nibble

Design system, mascot, voice. Everything here is already decided in
[`design.md`](./design.md) — read it rather than inventing styling.

### Decided, 2026-09-08, before building

**This is not a restyle, and assuming it is would be the expensive mistake.** The
design system already exists and is already used: `tokens.css` holds every colour,
radius and shadow, `global.css` holds `.btn`, `.card`, `.input`, `.bubble`,
`.source-chip` and `.streak`, and `Landing.jsx` uses all of it correctly.
`App.jsx` largely does too — its inline styles are flex layout built from tokens,
not raw values, so there is no token rule being broken there and nothing to
extract for its own sake. Ripping 1,029 lines of working page apart to move
`display: flex` into a stylesheet would be a 2,000-line pull request that buys
nothing anybody can see.

So slice 5 is four narrow things, in files that mostly already look right.

**`Mascot.jsx` is imported by nothing.** That is the finding that made this slice
concrete. It was written in the rebuild, it takes a `mood` prop, it has a bob
animation — and no file anywhere imports it. `Landing.jsx` draws Nibble with a
flat `<img src="/wave-nibble.svg">` instead, and the signed-in app draws no cat at
all. Nibble is currently a cat-branded product with no cat in it, which is exactly
the hole #19 exists to fill.

**Four things are broken in a way that only shows up when you look at the CSS**,
and they go first because every other pull request in this slice touches those
lines:

- `'2px solid var(--border, #eee)'`, in two places, expands to
  `2px solid 3px solid var(--ink)`. That is not valid CSS, so the browser throws
  the whole declaration away: **the note rows and the chunk boxes have no border
  at all right now.** The fallback never fires — `--border` _is_ defined, as a
  whole shorthand rather than a colour, so the fallback was never the problem.
- `var(--danger, #b3261e)`, in two places. `--danger` is not a token and never has
  been, so this always renders the raw hex — a red that is in no palette,
  appearing on a page whose errors are supposed to be `--coral`.

Both are precisely what `design.md`'s "never type a raw hex code in a component"
rule exists to prevent, and both are invisible until somebody reads the file.

### Who is building it, and the cost, stated accurately

**Alif is building all four**, the same as slices 3 and 4.

The first version of this note said the cost was "three slices in a row where
Arman ships nothing he can explain at the demo". **That was wrong, and it is worth
recording that it was wrong rather than quietly deleting it.** Arman authored PR
#34 — `Landing.jsx` and `landing.css`, the entire signed-out front door. He has
already built against `design.md`, using its tokens and its components correctly,
and it is the most finished-looking screen in the app. He has a change to explain.

So the honest cost is narrower: slice 5 is the slice most suited to somebody
learning the frontend — visual, checkable in a browser, no threading and no
network failure modes — and it is being handed to the person who needs it least.
That is a real cost and it is being accepted with eyes open, not overlooked.

### Checklist

- [ ] **`fix/borders-and-danger-token`** — the four broken lines above. Its own
      pull request, first, because "these borders do not render" is its own claim
      and deserves its own review rather than being buried in a restyle.
- [ ] **#18 `Button.jsx`** — `variant` of `primary` / `secondary` / `accent`, plus
      a `plain` variant for the note-row filename toggle, which has to stay a real
      `<button>` for the keyboard while not looking like one. Replaces every raw
      `<button>` in `App.jsx` and `Landing.jsx`.
- [ ] **#19 Nibble's moods, empty states and loading states** — `happy` and
      `curious` on `Mascot`, then Nibble in the header, in both empty states,
      thinking while an answer is in flight, and happy beside the newest answer.
- [ ] **#20 Accessibility pass** — the gaps that are actually left, listed below.
- [ ] **#21 Nibble's voice** — every user-visible string, frontend and backend.

### The trap in #18, written down before somebody falls into it

`Landing.jsx` wraps its buttons in Clerk's `<SignInButton mode="modal">`. That
component does not render a button of its own — it **clones the child it is given
and attaches its own `onClick`**. A `Button` component that names only the props
it cares about, and drops the rest, therefore throws that `onClick` on the floor,
and sign-in stops working with no error anywhere: the button still draws, still
presses, still animates, and does nothing.

So `Button` spreads its remaining props onto the real element. That is the reason
a component takes props it does not name, and it is a better example of why than
any explanation in the abstract.

### What #20 actually has left

Most of the accessibility floor is already standing, built in as each slice went
by rather than bolted on here: real `<label>`s that are visually hidden rather
than absent, `role="status"` on both the search and the answer, `aria-label` on
the icon-only delete, `aria-expanded` on the note toggle, a `:focus-visible` ring
in `global.css`, and `prefers-reduced-motion` honoured. A real button was used
everywhere a `<div onClick>` would have been easier.

That is the point worth making at the demo — the pass is short _because_ the floor
was built from the start. What is left:

- **Coral error text carries its meaning by colour alone.** `design.md` forbids
  exactly that. It needs a word or an icon beside it.
- **`.btn:disabled` is `opacity: 0.45`.** Ink on lime at 45% is almost certainly
  under 4.5:1, and the Ask button spends every slow answer in that state.
- **`Mascot` has a hardcoded `aria-label="Nibble the cat"`.** That becomes a lie
  the moment it has moods, and in most of the places #19 puts it the text beside
  it already says the thing — so it is decorative there and should be hidden from
  a screen reader rather than announced twice.
- **The keyboard run-through needs a person.** Unplug the mouse; upload, search,
  ask and delete. Nothing here can assert that.

### The two strings in #21 that are not really wording

- **The "Slice 0 — is everything talking?" card.** A developer's debug panel,
  sitting at the top of the product, above the thing the product is for. It says
  "Next up: Slice 1, uploading a PDF" to a person who is looking at four finished
  slices. The health check behind it is worth keeping; the card is not.
- **The backend's `detail` sentences.** `docs/api.md` promises they are written
  for a person and shown verbatim, so the voice pass has to cross into the
  backend to finish. **`routes.py` is Fahim's file** — #21 assigns this rewrite to
  Alif, so the crossing is sanctioned by the issue rather than taken, but it gets
  named in the pull request rather than passing silently.

## Slice 6: Quiz yourself

Nibble reads one of your notes and writes multiple-choice questions from it, each
carrying the page it came from. You fix the ones that came out wrong and then
practise. Contract in [`api.md`](./api.md) under "Slice 6".

**This absorbs the old slice 6, "Quiz mode".** #22 — generate quiz questions from
the notes — is this slice. #23, the quiz screen, moves to Slice 7. Neither issue is
orphaned and no issue is being invented after the fact, which is the mistake the
Clerk sign-in note above warns about.

**No teacher, no code, no classroom in this slice.** It is demoable on one laptop
and it is useful to every single user. That is deliberate: the classroom needs a
deploy and a second device before it can be shown to anybody, and betting the whole
feature on that is how a slice stops being vertical.

### Decided, 2026-09-08, before building

**A teacher is not a role. A teacher is someone who owns a room.** The requirement
is that _anyone_ can be a teacher, and "anyone can be" is the same sentence as
"there is no role". `rooms.owner_id` holds a Clerk `sub` exactly as
`documents.user_id` already does, so this is the sixth use of an idea already in the
codebase rather than a new one. The full reasoning, and the three roads not taken —
an allowlist in `config.py`, a `role` claim in Clerk's token, a local roles table —
are in [`adr/0004-teacher-is-an-owner.md`](./adr/0004-teacher-is-an-owner.md).

**The two doors on the landing page are navigation, not permission.** "Log in as a
teacher" picks the screen you land on and grants nothing. This is worth saying in
exactly those words, because the failure it prevents is silent: if the backend ever
trusted a role the browser sent, a student could send it too. Authority is always a
`WHERE owner_id = ?` in the same query that fetches the data.

It follows that the doors are not a partition. A student joins a class from inside
the regular app; a teacher quizzes himself from his own notes. Nobody is stuck
behind the door they came through.

**A quiz is a thing you own; a room is a session that runs one.** Keeping them
separate is what lets a regular user get value with no classroom anywhere near them,
and it lets a teacher run the same quiz in two classes. Folding them together would
have made "practise alone" a room with one member and no teacher, which is a
contortion you would have to explain every time.

**`correct` follows ownership.** You can always see the answers to a quiz you own —
it was made from your notes. You can never see the answers to somebody else's quiz
you are sitting a room for. That is one rule rather than two, and it is why solo
practice needs no marking endpoint at all: the browser already holds a key it is
entitled to.

**Solo practice stores nothing.** You take your own quiz, the score is on screen,
and closing the tab ends it. An attempt history is a whole extra table and screen
for something nobody asked for. Marks are only ever stored for a classroom, where
somebody other than you needs to see them.

**Five new tables, and nothing existing changes.** `quizzes`, `questions`, `rooms`,
`room_members` and `answers` — none of them touching `documents` or `chunks`. This
is not tidiness, it is forced: `db.py` has no migrations, `CREATE TABLE IF NOT
EXISTS` silently will not add a _column_ to a table that already exists, and
`_check_shape()` exists precisely because slice 4.5 hit that. New tables are free; a
new column would make everybody delete their `nibble.db`.

**The model's JSON is validated, not trusted.** `quiz.py` asks Groq for a JSON
object and then checks the reply itself — the right number of questions, four
options each, `correct` in range, a page that exists. Anything else is a
`QuizUnavailable` and a 503 sentence. A model returning _almost_ right JSON is the
realistic failure here, and storing it puts a broken question in front of a class.

**Ten questions is the ceiling, and the reason is the same one as slice 1.5.**
Groq's free tier caps output at 1,000 tokens per minute and reserves against
`max_tokens`. Ten questions is roughly 800 tokens — most of a minute's allowance, on
a key already shared with reading handwriting and with `/ask`.

### Checklist

- [ ] `adr/0004-teacher-is-an-owner.md` — why a teacher is an owner
- [ ] `api.md` — the six quiz routes, **written before either side starts**
- [ ] `db.py` — `quizzes` and `questions`
- [ ] `config.py` — `QUIZ_QUESTION_COUNT`, `QUIZ_MAX_QUESTIONS`,
      `QUIZ_MAX_OUTPUT_TOKENS`, `QUIZ_MAX_CONTEXT_CHARS`, `QUIZ_REASONING_EFFORT`
- [ ] `quiz.py` — `QUIZ_SYSTEM_PROMPT`, `QuizUnavailable`, `make_questions()`, and
      the validator. Reuses `llm.build_context()` rather than formatting chunks a
      second time — the lesson #16 already taught
- [ ] `routes.py` — `POST`/`GET` `/quizzes`, `GET /quizzes/{id}`, `PATCH` and
      `DELETE` on a question, `DELETE /quizzes/{id}` _(Fahim, scaffolded)_
- [ ] `App.jsx` — the "Quiz me" card: pick a note, generate, edit a question,
      practise, see your score _(Arman, scaffolded)_
- [ ] `api.js` — one function per route, and `error.status` attached in `request()`
- [ ] `tests/test_quiz.py`, quiz-route tests, and every new route added to
      `PROTECTED` in `test_auth.py`

## Slice 7: The classroom

A teacher opens a room around a quiz, students join with a code, everyone answers at
once, and the room closes. Contract in [`api.md`](./api.md) under "Slice 7", written
when this slice starts.

**This is the slice that needs the deploy.** A classroom cannot be demoed on one
laptop — it needs a teacher on one device and a student on another, against the
Space. Nothing local proves it works.

### Decided, 2026-09-08, before building

**A room is a three-state machine: `waiting`, `open`, `closed`.** The teacher moves
it with Start and End. Everything the student screen does is a consequence of which
state it is in, which keeps "what should be on screen right now" answerable from one
value rather than from four booleans that can disagree with each other.

**The student screen finds out by asking every three seconds.** A `setInterval`
inside a `useEffect` whose cleanup clears it. Polling is the boring choice and it is
the right one here: a websocket is a second protocol, a second failure mode and a
second thing to explain, to save a couple of seconds in a classroom where nobody is
racing.

The honest cost: thirty students at one request every three seconds is about ten
requests a second against a free Space. SQLite reads handle that comfortably. If it
ever bites, the fix is a longer interval, not a websocket.

**`correct` is stripped for anyone who is not the owner.** The student endpoint
builds its response field by field — never `dict(row)`, never `SELECT *`. This gets
its own test, because the failure is invisible: an answer key sitting in a JSON
response looks completely normal on screen and hands the class the answers.

**Students are signed out when the room closes**, which is what was asked for.
Stated as a cost rather than discovered as one: it is a real Clerk sign-out, so a
student who wants to go back to their own notes has to sign in again.

**A student sees "Submitted", not a score.** The mark is computed automatically but
the teacher can change it in slice 8, and showing a number that later moves is worse
than showing none. Solo practice is the opposite case and shows the score at once —
because there, nobody is going to overrule it.

### Checklist

- [ ] `api.md` — the eight room routes, written first
- [ ] `db.py` — `rooms`, `room_members`, `answers`
- [ ] `routes.py` — `POST /rooms`, `GET /rooms`, `POST /rooms/{id}/state`,
      `POST /rooms/join`, `GET /rooms/code/{code}`, `POST /rooms/{id}/answers`
      _(Fahim, scaffolded)_
- [ ] Room codes from `secrets`, not `random`, six characters with no `O`/`0` or
      `I`/`1` in the alphabet — it gets read off a projector and typed
- [ ] `Landing.jsx` — the two doors, minding the `SignInButton` trap already written
      up under Slice 5 _(Arman, scaffolded)_
- [ ] `App.jsx` — the header switch, the teacher's room screen with the code and a
      live joiner count, Start and End _(Arman, scaffolded)_
- [ ] The student path: "Join a class", the lobby, the questions, "Submitted", then
      sign-out — #23 _(Arman, scaffolded; the polling effect's shell and cleanup
      written out, the fetch inside left as `TODO(Arman)`)_
- [ ] Tests for the four rules: no answer key to a student, no answering before
      Start or after End, no answering a room you did not join, 404 for a room that
      is not yours

## Slice 8: Marking

The teacher reads what came back and decides the marks. Contract in
[`api.md`](./api.md) under "Slice 8", written when this slice starts.

### Decided, 2026-09-08, before building

**Marks are auto-computed and the teacher can override any of them.** That is the
answer to "the teacher will judge the submissions and mark them" that costs a
multiple-choice quiz rather than a written-answer one, and the teacher still has the
last word on every number.

**`mark` is stored, not derived.** It would be tempting to compute
`chosen == correct` on the fly and skip the column. The override is why not: the
moment a teacher changes a mark there are two rules for one number, and every screen
has to know which one applies. Writing it once at submit time makes the override an
ordinary `UPDATE`, and "was this changed?" is still answerable by comparing it with
`chosen == correct` at read time.

**A question most of the class got wrong is flagged.** It is usually a bad question
rather than a bad class, and that is the most useful thing this screen can tell a
teacher.

### Checklist

- [ ] `api.md` — `GET /rooms/{id}/results` and `PATCH /rooms/{id}/answers/{aid}`
- [ ] `routes.py` — both, scoped by `WHERE owner_id = ?` _(Fahim, scaffolded)_
- [ ] `App.jsx` — the results table, per student and per question, with the override
      _(Arman, scaffolded)_
- [ ] The flag for a question most of the room got wrong

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
