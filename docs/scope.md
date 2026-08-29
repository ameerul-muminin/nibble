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
| 1   | Upload and list       | Slice 1 — Upload and list | in progress, 2 PRs open |
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

## Current state, 2026-08-29

22 issues, 0 closed. `main` is at `6afb799` and carries Slice 0.

**Three pull requests are open, and nothing has merged in three weeks.** That is the
project's actual bottleneck — not a missing feature.

| PR  | Branch                      | Opened     | Note                        |
| --- | --------------------------- | ---------- | --------------------------- |
| #24 | `feat/extract-text`         | 2026-08-09 | Must merge before #25       |
| #25 | `feat/upload-list-documents` | 2026-08-10 | Stacked on #24              |
| #26 | `chore/workflow-skills`     | 2026-08-20 | Shared skills for the team  |

Review order is forced: **#24, then #25.** Unblocking these comes before starting
anything new.

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

**A filename from a client is untrusted input.** Uploads are written with
`Path(filename).name`, never the raw value, because a name like `../../something`
otherwise escapes the uploads directory. This is the first place in the project where
"never trust the client" stops being an abstraction, and it is worth understanding
rather than pasting.

**`PRAGMA foreign_keys = ON` on every connection.** SQLite has foreign keys **off** by
default, which means a cascade delete silently does nothing at all. `DELETE
/documents/{id}` in #6 depends on it, so it lands with `db.py` rather than being
discovered later as a mystery.

**The schema needs `chunks` from the start, not just `documents`.** Slice 2 stores
chunks and Slice 3 adds an `embedding` column on them (TEXT, holding JSON). Designing
the table once, now, is cheaper than migrating a SQLite file later.

**The allowed extensions and `api.md` must say the same thing.** They drifted once
already — the code accepted `.text` and `.markdown` while the contract named only
`.pdf`, `.txt`, `.md`. Pick one and change both. A contract that disagrees with the
code is worse than no contract, because people trust it.

**`async def` is the exception here, and only for `await file.read()`.** The project
rule is sync routes so there is no async to explain. The upload route genuinely needs
it. Write the sentence saying why, so the exception is understood rather than copied
into the next route.

**Same-name uploads currently overwrite each other silently.** Known, minor, not being
fixed in this slice. Written down so it is not rediscovered later as a bug.

### Checklist

- [ ] #2 `db.py` — the SQLite connection and schema _(Alif)_
- [ ] #3 `extract_text()` — pull the words out of a file _(Fahim, PR #24)_
- [ ] #4 `POST /documents` and `GET /documents` _(Fahim, PR #25)_
- [ ] #5 The notes list and an upload button _(Arman)_
- [ ] #6 `DELETE /documents/{id}` _(Fahim)_
- [ ] #7 A delete button on each note _(Arman)_

### Open question, needs a decision

**What shape does the frontend scaffold take?** #5 asks for API functions, `useState`,
`useEffect`, array rendering and the hidden-file-input `ref` trick — five unfamiliar
ideas at once. The agreed model is "the lead scaffolds, they build". Three options, in
order of preference:

1. **Layout and TODOs.** Page structure, component shells, CSS classes and props are
   built; every piece of behaviour is left marked `TODO`. The interesting half is
   learned and the fiddly half is skipped. _Recommended._
2. **One worked example.** The upload card is built completely and correctly, and the
   rest are shells to imitate.
3. **Full static UI with fake data.** Motivating, but no component ever gets designed.

Also worth deciding: whether to pull the `Button` component (#18, Slice 5) forward, so
no raw `<button>` gets written now and replaced later.

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
