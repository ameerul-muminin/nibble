<img src="assets/mascot/nibble.svg" width="120" alt="Nibble the cat" />

# Nibble

Bite-sized answers from your own notes. Upload a chapter, ask a question, get an
answer that comes from *your* material — with the page it came from.

- **Frontend:** React + TypeScript (Vite)
- **Backend:** FastAPI (Python)
- **Database:** Postgres + pgvector (one database for everything, including embeddings)
- **AI:** a hosted LLM API — we do not train models

New to the project? Read [`docs/how-it-works.md`](docs/how-it-works.md) first. It explains
the whole system in plain English, no prior AI knowledge needed.

---

## Get it running

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/),
[Python 3.12+](https://www.python.org/downloads/) and [Node 22+](https://nodejs.org/).

**1. Start the database** (one command, from the repo root):

```bash
docker compose up -d
```

**2. Start the backend:**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env             # then open .env and paste in your LLM key
uvicorn app.main:app --reload
```

Check it worked: open <http://localhost:8000/health> — you should see `{"status":"ok"}`.
Interactive API docs are at <http://localhost:8000/docs>, generated automatically.

**3. Start the frontend** (new terminal):

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open <http://localhost:5173>.

If any step took you more than 10 minutes, that is a bug in this README — tell the
tech lead and we will fix it.

---

## Ground rules

1. **Never commit `.env`.** It holds the API key. `.gitignore` already blocks it,
   so do not force-add it.
2. **The API key lives in `backend/.env` only.** Anything in `frontend/.env`
   ships to the browser where anyone can read it.
3. **Never push straight to `main`.** Branch, open a pull request, get one review.
4. **CI must be green before merge.** If it is red, the code is not done.

---

## Everyday commands

| What you want | Command |
|---|---|
| Start the database | `docker compose up -d` |
| Stop the database | `docker compose down` |
| Wipe the database and start fresh | `docker compose down -v` |
| Run backend tests | `cd backend && pytest` |
| Fix backend formatting | `cd backend && ruff format . && ruff check --fix .` |
| Check frontend types | `cd frontend && npx tsc --noEmit` |

---

## Where things live

```
backend/app/
  api/routes/    HTTP endpoints — thin. They validate input and call a service.
  services/      The actual work: chunking, embeddings, retrieval, LLM calls.
  models/        Database tables.
  schemas/       Request and response shapes. This is the API contract.
  core/          Configuration.

frontend/src/
  components/    Reusable UI pieces (Button, Mascot, ChatBubble).
  lib/api.ts     The only file that talks to the backend.
  styles/        Design tokens. All colours and spacing come from here.
```

**Rule of thumb:** if a route handler is longer than about 30 lines, the logic
belongs in a service.

## Docs

| File | What it covers |
|---|---|
| [`docs/how-it-works.md`](docs/how-it-works.md) | How the whole thing works, explained from zero |
| [`docs/api.md`](docs/api.md) | The contract between frontend and backend |
| [`docs/team.md`](docs/team.md) | Who owns what, and how we use git |
| [`docs/design.md`](docs/design.md) | Colours, type, components, mascot |
| [`docs/adr/`](docs/adr/) | Why we made the big technical choices |
