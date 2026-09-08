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

## Where this runs when it is deployed

On [Render](https://render.com), as a Docker web service built from the
[`Dockerfile`](./Dockerfile) next to this file. **You do not need Docker to work
on Nibble** — that file is read by Render's build servers, not by you.

This README used to begin with a block of `---` YAML, which was configuration
for a Hugging Face Space. That is gone, because Hugging Face made Docker Spaces
a paid feature in July 2026 and everything in this project is free.
[`../docs/adr/0005-render.md`](../docs/adr/0005-render.md) is the replacement
decision, [`../docs/adr/0003-hosting.md`](../docs/adr/0003-hosting.md) is why the
backend needs a real container at all, and
[`../docs/deploying.md`](../docs/deploying.md) is the step-by-step.
