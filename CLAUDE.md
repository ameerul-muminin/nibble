# Nibble

## What this is

Upload a chapter, ask a question, get an answer that comes from *your own notes*,
with the page it came from. It's a RAG system: retrieve the relevant chunks, hand
them to a language model, make it answer only from those.

Read `docs/scope.md` before building anything. It's the living plan, broken into
slices, and it tracks what's actually done versus what's still open. Keep it up to
date as you go — that's not optional housekeeping, it's how a fresh conversation
picks this project up without anyone re-explaining it.

`docs/team.md` is the working agreement between people. This file is the working
agreement with the AI. Where they overlap, `docs/team.md` wins.

## The one rule everything else answers to

This is a learning project. The team is learning to program on it, and every
technical decision here trades sophistication for comprehensibility, deliberately.

Before proposing anything, check it against: **can the person who owns this file
explain it at the demo?** If not, it's the wrong choice here — however good it
would be somewhere else.

Nibble was rebuilt once, from an AI-generated scaffold into something simpler,
because nobody on the team could read the original. Presenting a system you can't
answer questions about is worse than presenting a simpler one everybody
understands. Don't quietly rebuild that problem.

## Don't do the learning for them

The point of an issue is that whoever it's assigned to comes out able to explain
the change. Handing them a finished answer takes that away, and the pull request
gate — *explain this in your own words* — then fails at review instead of here.

So, on anything assigned to someone else:

- Scaffold, don't solve. Build the structure — page layout, component shells,
  function signatures, CSS classes, props, the fiddly plumbing — and leave the
  interesting behaviour marked `TODO(name)` with a sentence saying what goes there.
- Explain rather than write. Asked "how does `useEffect` work here", answer the
  question; don't produce the finished component.
- One new idea at a time. If a task already introduces three unfamiliar concepts,
  don't add a fourth because it's tidier.

Full solutions are fine for anything the tech lead owns, and for a bug that is
blocking someone else's work.

## How to work

Before building anything, decide what you're doing and why, in a few plain
sentences. Don't write code yet at that point. Report the decision, then stop and
wait — don't move on to building until you're told to go ahead. Every slice, no
exceptions, even ones that look obvious.

If something genuinely forks, where a reasonable person could go two ways and it
matters which, ask about it: one question at a time, with two or three concrete
options, so a short reply settles it. Not a long list of questions, and not silence
when a real fork exists. Most things don't need asking — decide those and say what
you decided.

Then build it. If the plan turns out wrong once it's actually built, or contradicts
something already in the codebase, say so and fix the plan too, not just the code.
Don't quietly work around a contradiction.

When a build step is underway, break it into its own short checklist of what's
genuinely being done, and check items off in `docs/scope.md` as they're finished.

When you report back, especially anything a person has to go do — verify by hand,
review a PR, make a choice — write that part as a short bulleted list of concrete
steps, not a paragraph. The detailed reasoning belongs in `docs/scope.md`, where
dense is fine. The reply should be the short version.

## Ownership

Ownership is by folder and the table in `docs/team.md` is the authority. Don't edit
a file someone else owns without saying so and why — crossing that boundary is a
people problem before it's a code problem, even when the change is correct.

`docs/api.md` is the contract between frontend and backend, and the tech lead
writes each entry **before** a slice starts so both sides can build in parallel.
If code and `docs/api.md` disagree, that's a bug in one of them — say which, don't
pick silently.

## Stack — already decided, nothing open here

FastAPI with **sync `def` routes** (no async/await to explain, and `await file.read()`
is the one justified exception). **SQLite via stdlib `sqlite3`, plain SQL** — no ORM,
no Docker, no connection string; the file *is* the database. **numpy cosine
similarity** for search, about six readable lines. **`fastembed`** with
`BAAI/bge-small-en-v1.5`, 384 dimensions, running locally on CPU. **Groq free tier**
for chat. **Vite + React in plain JavaScript** — no TypeScript.

Every one of those is a deliberate trade for comprehensibility, and the reasoning is
in `docs/adr/`. Don't reach for the more sophisticated option without reading the ADR
that already rejected it.

## Rules

- Everything is free. No paid API, no credit card, anywhere in this project.
- Never push to `main`. Branch per piece of work, PR, squash-merge on green CI.
- Never commit `.env`, an API key, or `HANDOFF.md`.
- Vertical slices only. Every slice ends in something demoable — never a half-built
  layer. Finish a slice before starting the next.
- Fail loudly on a missing setting at startup, don't let it fail silently later.
  Everything configurable lives in `backend/app/config.py`.
- Never trust a filename, a path, or any other value that came from the client.
- SQLite foreign keys are **off** by default — `PRAGMA foreign_keys = ON` per
  connection.
- The embedding model loads **once**, as a module-level singleton, never per request.
- Never show a raw exception or provider error to a user. A plain sentence and a way
  to try again.
- Keep pull requests small. A 200-line PR gets a real review; a 2,000-line one gets a
  rubber stamp.
- After building or changing anything, actually run it — lint, format, tests, and the
  real thing in a browser. Not just read the code and assume. `docs/coding-standards.md`
  has the commands.

## Design

Colours, type, the solid-edge press button, Nibble's voice, and the accessibility
floor are all decided in `docs/design.md`. Read it before touching any styling; don't
guess and don't restate it here. It survived the rebuild unchanged and is genuinely
good — use it rather than inventing something.

## The docs, and what each one is for

| File | What it holds |
|---|---|
| `docs/scope.md` | The plan: slices, decisions, and what's done |
| `docs/team.md` | How people work together — ownership, git, the AI policy |
| `docs/coding-standards.md` | The commands, and what a tool checks vs. what a person must |
| `docs/api.md` | The frontend ↔ backend contract |
| `docs/how-it-works.md` | The whole system in plain English |
| `docs/design.md` | Colour, type, voice, accessibility |
| `docs/adr/` | Why a road was not taken |
| `docs/first-week.md` | Setup from zero; assumes no terminal experience |
| `docs/deploying.md` | Putting it on the internet; assumes you've never deployed |

If a beginner gets stuck following `docs/first-week.md`, the doc is wrong. Fix the
doc, not the person.

## Tools

Skills live in `.claude/skills/`, pinned in `skills-lock.json`. `reference/original-scaffold`
is the archived AI-generated original — useful to peek at when something is genuinely
hard, never something to build on.
