# How Nibble works

Written for someone who has never built a web app. Read it top to bottom once;
it takes about ten minutes. Everything else in the repo will make more sense
afterwards.

---

## 1. The problem in one sentence

A general chatbot answers from things it read on the internet. We want answers
from *this student's* lecture notes — so we have to hand the model the right
pages before it answers.

That technique has a name: **RAG**, short for *retrieval-augmented generation*.
Retrieve the relevant notes, then let the model generate an answer using them.

## 2. The three programs

Nibble is three separate programs that talk over the network:

| Program | What it is | Runs at |
|---|---|---|
| Frontend | The web page the student sees. React. | `localhost:5173` |
| Backend | The API. Does all the thinking. FastAPI. | `localhost:8000` |
| Database | Where everything is stored. Postgres. | `localhost:5432` |

The frontend never talks to the database or to the AI provider. It only talks to
the backend. This matters for two reasons: the API key stays secret on the
server, and there is exactly one place where rules live.

## 3. What happens when you upload a PDF

Five steps. This is the most important sequence in the project.

**Step 1 — Extract.** We open the PDF and pull out the plain text, page by page.
Code: `backend/app/services/chunking.py`, function `extract_pages`.

**Step 2 — Chunk.** We cut that text into pieces of roughly 900 characters. Two
reasons: a model has a limit on how much you can hand it at once, and searching
works far better on small focused pieces than on a whole 40-page document.

We let consecutive chunks *overlap* by about 150 characters. Without overlap, a
sentence that happens to fall across a cut gets split in half and neither piece
makes sense on its own.

**Step 3 — Embed.** We send each chunk to the AI provider and get back an
**embedding**: a list of about 1,500 numbers that represents the *meaning* of
that chunk.

> The useful mental model: imagine every possible sentence placed as a dot in an
> enormous space. Sentences about photosynthesis land near each other. Sentences
> about the French Revolution land somewhere else entirely. The embedding is just
> that dot's coordinates. Similar meaning, nearby coordinates — even when the two
> sentences share no words at all.

**Step 4 — Store.** We save each chunk's text *and* its embedding as a row in
the `chunks` table, alongside which document and which user it belongs to.

**Step 5 — Done.** We mark the document `ready` and the frontend shows it.

## 4. What happens when you ask a question

**Step 1 — Embed the question.** Same process as step 3 above. Now the question
is a dot in the same space as all the chunks.

**Step 2 — Find the nearest chunks.** We ask Postgres: *of this user's chunks,
which five have coordinates closest to the question's coordinates?* That is one
SQL query. `backend/app/services/retrieval.py`.

The word "closest" here is **cosine distance** — a standard way to measure how
far apart two of these dots are. You do not need the maths; pgvector computes it.

**Step 3 — Build the prompt.** We paste those five chunks into a message along
with the question, plus a system prompt telling the model: *answer only from
these notes, and if they do not cover it, say so.* `backend/app/services/llm.py`.

**Step 4 — Ask the model, return the answer** — together with which file and
page each chunk came from, so the UI can show "from your Ch.4 notes, p.12".

That is the entire product. Everything else is features on top.

## 5. Why the answer is trustworthy

A model on its own will confidently make things up, because it is predicting
plausible text, not looking anything up. Two things fix that here:

1. We hand it the actual source text, so it has something real to work from.
2. The system prompt forbids answering beyond that text.

It is not perfect — the model can still misread a chunk, and if retrieval fetches
the wrong pages the answer will be wrong. That is why we show the sources: the
student can check.

## 6. Things worth knowing before you start coding

**The backend is split into routes and services.** A route handles HTTP: read
the request, check it is valid, call a service, return a response. A service does
the real work and knows nothing about HTTP. Keep routes thin — it makes services
testable and stops two people conflicting in the same file.

**Everything is scoped to a user.** Every query filters on `user_id`. Forgetting
that filter once means one student sees another's notes.

**Nothing is trained.** We call somebody else's model over the internet. There is
no training, no GPU, no dataset. When someone asks at the presentation "did you
train a model?", the honest and correct answer is: no, we built a retrieval
system around a hosted model, which is how nearly all real AI products work.

## 7. Glossary

| Term | Plain meaning |
|---|---|
| API | A backend's list of URLs the frontend can call |
| Endpoint | One of those URLs, e.g. `POST /chat/ask` |
| LLM | Large language model — the thing that writes the answer |
| Embedding | A list of numbers representing a piece of text's meaning |
| Vector | Another word for that list of numbers |
| Chunk | A small slice of an uploaded document |
| RAG | Retrieve relevant text, then generate an answer from it |
| pgvector | The Postgres add-on that stores embeddings and finds nearby ones |
| Prompt | The instructions plus context we send to the model |
| Migration | A recorded change to the database's shape |
| CI | Robot that runs our tests on every pull request |
