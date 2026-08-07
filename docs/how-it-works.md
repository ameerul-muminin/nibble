# How Nibble works

Written for someone who has never built a web app. Ten minutes, top to bottom.
Everything else in the repo makes more sense afterwards.

---

## 1. The problem in one sentence

A general chatbot answers from things it read on the internet. We want answers
from *this student's* lecture notes — so we have to find the right pages and
hand them to the model before it answers.

That technique is called **RAG**: *retrieval-augmented generation*. Retrieve the
relevant notes, then generate an answer from them.

## 2. The two programs and one file

| Part | What it is | Where |
|---|---|---|
| Frontend | The web page the student sees. React. | `localhost:5173` |
| Backend | The API. Does all the thinking. FastAPI. | `localhost:8000` |
| Database | A single file on disk. SQLite. | `backend/nibble.db` |

The frontend never talks to the database or to the AI provider — only to the
backend. That means the API key stays on the server, and there is exactly one
place where the rules live.

There is no database *server* to install or start. SQLite is just a file. If you
delete it, you get an empty app back.

## 3. What happens when you upload a PDF

**Step 1 — Extract.** Open the PDF, pull out the plain text, page by page.

**Step 2 — Chunk.** Cut that text into pieces of roughly 900 characters. Two
reasons: a model has a limit on how much you can hand it, and searching works
far better on small focused pieces than on a whole 40-page document.

Consecutive chunks *overlap* by about 150 characters, so a sentence that falls
across a cut still lands whole inside at least one piece.

**Step 3 — Embed.** Turn each chunk into an **embedding**: a list of exactly 384
numbers standing for the *meaning* of that chunk.

> The mental model: imagine every possible sentence as a dot in an enormous
> space. Sentences about photosynthesis land near each other. Sentences about
> the French Revolution land somewhere else entirely. The embedding is that
> dot's coordinates. Similar meaning, nearby coordinates — even when the two
> sentences share no words at all.

This runs **on your own laptop**, using a small model called
`bge-small-en-v1.5`. No API key, no internet (after the first download), no
limit on how many you make.

**Step 4 — Store.** Save each chunk's text and its 384 numbers as a row in the
`chunks` table.

## 4. What happens when you ask a question

**Step 1 — Embed the question**, exactly as in step 3. The question is now a dot
in the same space as every chunk.

**Step 2 — Find the nearest chunks.** Load the chunks' numbers and measure which
five sit closest to the question's numbers. The measure is **cosine
similarity**, and it is about six lines of arithmetic — no magic, and you can
read it.

**Step 3 — Build the prompt.** Paste those five chunks into a message with the
question, plus a system prompt saying: *answer only from these notes, and if
they don't cover it, say so.*

**Step 4 — Ask the model.** We send that to **Groq**, which runs open-source
models (Llama) for free. Back comes an answer, which we return along with which
file and page each chunk came from — so the UI can say "from your Ch.4 notes,
p.12".

That is the entire product. Everything else is decoration.

## 5. Why the answer is trustworthy

A model on its own will confidently make things up, because it is predicting
plausible text, not looking anything up. Two things fix that:

1. We hand it the actual source text, so it has something real to work from.
2. The system prompt forbids answering beyond that text.

It isn't perfect — the model can misread a chunk, and if the search fetches the
wrong pages the answer will be wrong. That's exactly why we show the sources:
the student can check.

## 6. Things worth knowing before you code

**Routes stay thin.** A route reads the request, calls something that does the
real work, and returns a result. When a route starts doing real thinking, that
logic moves to its own file — which makes it testable without a running server.

**Nothing is trained.** We call somebody else's model over the internet, and run
a small open-source embedding model locally. There is no training, no GPU, no
dataset. When someone asks at the presentation "did you train a model?", the
honest and correct answer is: no, we built a retrieval system around existing
open models, which is how nearly all real AI products work.

**We started simple on purpose.** SQLite and a few lines of numpy instead of a
vector database. See `docs/adr/0001-sqlite-and-numpy.md` — knowing *why* you
chose the simple thing is worth more marks than using the complicated one.

## 7. Glossary

| Term | Plain meaning |
|---|---|
| API | A backend's list of URLs the frontend can call |
| Endpoint | One of those URLs, e.g. `POST /ask` |
| LLM | Large language model — the thing that writes the answer |
| Embedding | A list of numbers representing a piece of text's meaning |
| Vector | Another word for that list of numbers |
| Chunk | A small slice of an uploaded document |
| RAG | Retrieve relevant text, then generate an answer from it |
| Cosine similarity | How we measure "these two meanings are close" |
| Prompt | The instructions plus context we send to the model |
| SQLite | A whole database that is just one file |
| CI | The robot that checks our code on every pull request |
