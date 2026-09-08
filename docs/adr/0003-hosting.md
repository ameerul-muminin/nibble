# ADR 0003 — Vercel for the frontend, a Hugging Face Space for the backend

**Status:** accepted · **Date:** 2026-09-08 · **Decided by:** tech lead

## Context

The question was "can we host Nibble on Vercel's free tier?" Vercel is the
obvious answer for a Vite app, and the assumption underneath the question was
that it would host the whole project.

It cannot host the backend. Not "with some configuration" — the three reasons are
structural, and each one on its own is fatal.

## Decision

- **Frontend → Vercel Hobby.** Root directory `frontend`, Vite preset.
- **Backend → a free CPU Hugging Face Space, running our own `Dockerfile`.**
- **Everything stays free.** No card, on either.

## Why not Vercel for the backend

**No disk.** A Vercel function's filesystem is read-only except `/tmp`, which is
per-instance and does not survive between invocations. `nibble.db` is not a cache
in this project, it is the entire memory of the app — see
[`0001-sqlite-and-numpy.md`](./0001-sqlite-and-numpy.md). Upload a chapter and
the next request can land on an instance that has never seen it. Keeping SQLite
means keeping a real filesystem, and that rules out serverless generally, not
just Vercel.

**Too big.** The Hobby plan caps a Python function at 250 MB unzipped.
`fastembed` pulls in `onnxruntime` and a tokenizer stack; with numpy and
pypdfium2 alongside it, the limit is gone before the 65 MB model file is counted.

**Too slow.** Hobby functions cap at 60 seconds. The first search after a cold
start downloads and loads the embedding model — so the platform re-pays a cost
that `embeddings.py` is specifically built to pay once, on every cold start. OCR
cannot fit at all: `OCR_MAX_PAGES = 5` at `OCR_RETRY_WAIT_SECONDS = 20` is a
deliberately multi-minute upload, and that pacing exists because of Groq's free
tier, not because it is tunable.

## Why a Space rather than Render

Render's free web service was the other real candidate, and it is a closer fit
than Vercel: a real process, a real filesystem, free, no card.

It loses on one thing that matters more than it sounds. **Render's free tier
sleeps after 15 minutes of no traffic**, and waking it takes roughly 50 seconds —
after which the first question also loads the embedding model. The demo is the
one moment this project is judged, and "the first question takes a minute and a
half" is a bad thing to discover in front of an audience.

A free Space idles out after 48 hours instead of 15 minutes, has considerably
more memory than fastembed needs, and — because we supply a `Dockerfile` — lets
us **bake the model into the image at build time**, which removes the cold-start
download completely. The model is also hosted on Hugging Face, so that build-time
download is a short trip.

## Trade-offs accepted

- **The database resets.** Free Spaces have no persistent disk, so `nibble.db`
  empties on any restart or rebuild. Re-upload before demoing. Persistent
  storage on a Space is paid, which the "everything is free" rule forbids, and
  reaching for a hosted Postgres to fix it would undo ADR 0001 for a
  demo-day inconvenience.
- **Two hosts, two dashboards, two sets of environment variables.** More places
  for a setting to be wrong than a single host would have. `deploying.md` exists
  because of this.
- **The backend is a Docker image now**, which is a tool ADR 0001 deliberately
  kept out of local development. It stays out: nobody needs Docker installed to
  work on Nibble. The `Dockerfile` is read by the Space's build, not by the team,
  and local development is still `uvicorn app.main:app --reload`.
- **A public URL required real auth first**, which was a slice of its own. That
  is recorded under Slice 4.5 in `scope.md` rather than here, because it is a
  consequence of deploying at all rather than of choosing these two hosts.
