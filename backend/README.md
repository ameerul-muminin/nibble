---
title: Nibble API
emoji: 🐹
colorFrom: yellow
colorTo: pink
sdk: docker
app_port: 7860
pinned: false
---

# Nibble's backend

FastAPI, SQLite, and a small embedding model that runs on the machine rather
than through an API. It reads uploaded notes, cuts them into pieces, and answers
questions using only those pieces.

Start it locally from this folder:

```bash
uvicorn app.main:app --reload
```

Then open <http://localhost:8000/health>. Full setup, from nothing, is in
[`../docs/first-week.md`](../docs/first-week.md).

## Why this file starts with all that `---` stuff

That block at the top is not documentation, it is configuration. This folder is
also a [Hugging Face Space](https://huggingface.co/spaces), which is where the
backend runs once it is deployed, and a Space reads its settings out of the
front of its README: which SDK to use (`docker`, so it builds our
[`Dockerfile`](./Dockerfile)) and which port the app listens on.

It looks odd and it is genuinely load-bearing — a Space with no `app_port` waits
for an app on the wrong port and shows a build that never finishes starting.

[`../docs/deploying.md`](../docs/deploying.md) is the step-by-step, and
[`../docs/adr/0003-hosting.md`](../docs/adr/0003-hosting.md) is why a Space and
not somewhere else.
