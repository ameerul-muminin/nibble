# ADR 0005 — Render for the backend, after Hugging Face Spaces became paid

**Status:** accepted · **Date:** 2026-09-08 · **Decided by:** tech lead ·
**Supersedes:** the backend half of [`0003-hosting.md`](./0003-hosting.md)

## Context

[`0003-hosting.md`](./0003-hosting.md) chose a free CPU Hugging Face Space to run
the backend, and explicitly rejected Render because its free tier sleeps after 15
minutes of inactivity and takes about 50 seconds to wake, while a Space idles out
only after 48 hours.

**That decision was correct when it was made and is no longer available.** In early
July 2026 Hugging Face made the Docker SDK a paid feature: creating a Docker Space
now requires PRO on a personal account. There was no announcement, no changelog
entry and no documentation update — it was found by people watching the "Paid"
badge appear on the new-Space form. Reports differ on whether Docker Spaces created
before the change keep working.

Static Spaces remain free, and a static host cannot run Python.

The first rule of this project is that everything is free, with no card anywhere.
So PRO is not an option, and the backend needs somewhere else to live.

## Decision

- **The backend runs on Render's free tier**, as a Docker web service built from
  the existing `backend/Dockerfile`.
- **The frontend stays on Vercel.** Nothing about ADR 0003's frontend half changed.
- **`EMBED_BATCH_SIZE = 8`**, which is what makes the backend fit in 512 MB. See
  below — this is the part that is really a decision rather than a fallback.

## Why Render, given ADR 0003 turned it down

The reason it was turned down has not gone away; the thing it was compared against
has. Against the remaining free options it wins:

**It runs the `Dockerfile` we already wrote.** The image, the non-root user, and the
baked-in embedding model all carry over unchanged. That last one matters more on
Render than it did on a Space, because a free Render service sleeps after 15
minutes rather than 48 hours — so cold starts are the normal case, and a cold start
that also had to download 65 MB would be unusable.

**No card.** Checked before choosing it.

**A real filesystem while it runs**, which is the whole requirement ADR 0003 was
written around: `nibble.db` is this app's memory, not a cache.

## Why not the alternatives

**A Gradio Space wrapping FastAPI.** Gradio Spaces appear to still be free, and a
Gradio Space runs `app.py`, so it could start uvicorn on our FastAPI app instead of
a Gradio interface. Rejected on the project's own test — can the person who owns
this explain it at the demo? "This is a Gradio app that is not a Gradio app" is a
sentence nobody should have to say. It also gives up the `Dockerfile`, so the model
downloads on every rebuild, and it depends on Hugging Face not making the same
change again to a second SDK.

**A tunnel from the laptop** (`cloudflared`, free, no account). Genuinely tempting:
no memory limit, no cold start, and `nibble.db` persists for real. Rejected because
Nibble would only exist while somebody's laptop is open and on the right wifi, and
slice 7 is a classroom full of students on their phones. Worth remembering as the
fallback if Render fails on demo day.

**Paying for PRO.** Breaks the first rule of the project.

## The measurement that made this possible

Render's free tier is 512 MB of RAM. The backend did not fit, and finding out why
turned up a real defect rather than a hosting problem.

`POST /documents` embeds every piece of a document in one `embed_texts` call, and
`fastembed` batches internally with a default of 256. So peak memory grew with the
size of the upload, with no ceiling short of the 20 MB file limit. Measured on real
900-character English, embedding a 400-piece document:

| `batch_size` | Peak memory | Time |
| --- | --- | --- |
| 256 (the default) | 1275 MB | 27.8s |
| 32 | 473 MB | 29.6s |
| 16 | 341 MB | 29.5s |
| **8** | **278 MB** | 29.5s |

**The time is the same in every row.** The work is identical either way; only how
much of it is held at one moment changes. So the smaller batch costs nothing and
buys a memory ceiling that does not move — at 8, a 40-piece chapter and a 400-piece
book peak at the same number.

The idle backend with the model loaded is 227 MB, so 278 MB of working peak leaves
real headroom inside 512 MB.

This would have been a bug on any small host, and on a 16 GB laptop nobody would
ever have seen it. It is a good argument for measuring rather than assuming, and a
better one for the fact that a hosting limit found a defect in the application.

## Trade-offs accepted

- **The service sleeps after 15 minutes and takes about 50 seconds to wake.** This
  is the cost ADR 0003 refused, and we are now paying it. Open the site before a
  demo starts, not during it. It is worse than the Space's 48 hours and it is the
  main thing lost.
- **0.1 CPU.** All the timings above are from a laptop core. Embedding on a
  fractional shared CPU will be slower and nobody has measured how much yet. **This
  is the first thing to check after the first deploy** — upload a real chapter and
  time it. If it is unusable, the tunnel option above is the fallback.
- **No persistent disk on the free tier**, so `nibble.db` empties on every restart
  and every deploy. Identical to the trade ADR 0003 already accepted; re-upload
  before demoing.
- **Two hosts, two dashboards.** Unchanged from ADR 0003.
- **A hosted platform is not a decision you make once.** This is the second time an
  external provider has changed underneath this project without any of our code
  changing — Groq retired the chat model mid-slice-4, and now this. Worth saying out
  loud at the demo: the parts that run on our own machine, SQLite and `fastembed`,
  are the parts that have never broken.
