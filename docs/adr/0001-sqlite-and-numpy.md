# ADR 0001 — SQLite and numpy now, a vector database later

**Status:** accepted · **Date:** 2026-08-07 · **Decided by:** tech lead

## Context

Nibble has to store text chunks along with their embeddings, and find the chunks
whose embeddings sit closest to a question's embedding.

The usual answers are a dedicated vector database (Pinecone, Qdrant, Chroma) or
Postgres with the pgvector extension. An earlier version of this project used
Postgres + pgvector.

Two facts about *this* project shaped the decision differently:

1. Two of the three developers are learning to program on this project. Every
   piece of infrastructure is something they must install, understand and debug
   before they can write a line of their own code.
2. The realistic upper bound on data is a few thousand chunks — a handful of
   students uploading a handful of chapters each.

## Decision

Store everything in **SQLite**, a single file on disk, using plain SQL through
Python's built-in `sqlite3`. Store each embedding alongside its chunk. Do
similarity search **in Python with numpy**: load the vectors, compute cosine
similarity against the question, take the top five.

Revisit if we ever exceed roughly 50,000 chunks or search takes over 200ms.

## Why

**Nothing to install.** No Docker, no database server, no connection string, no
port, no password. `pip install` and the app runs. Setting up Docker Desktop on
Windows was the single largest predictable time-sink for a beginner, and it
bought us nothing at this data size.

**The search is readable.** Cosine similarity in numpy is about six lines. A
beginner can read them, and can explain at the presentation what the system
actually does. `ORDER BY embedding <=> query` is shorter, but it is a black box
to someone who has been programming for two weeks — and being able to explain
our own system is a graded outcome here.

**It is genuinely fast enough.** Comparing a question against a few thousand
384-dimension vectors is a single small matrix multiply — a millisecond or two.
An index only starts to matter several orders of magnitude above where we are.

**Deleting data is trivial.** Delete the file. For a team repeatedly wiping test
uploads while building, that matters more than it sounds.

## Trade-offs accepted

- **It does not scale.** Every search loads every vector into memory. That is
  fine at a few thousand chunks and hopeless at a million. We know exactly which
  wall we will hit, and roughly when.
- **One writer at a time.** SQLite locks on write. Irrelevant for a single-user
  demo; a real problem for a deployed multi-user service.
- **No index on the vectors.** We do the full comparison every time. Deliberate:
  an approximate index adds a tuning parameter and a failure mode we do not need.
- **We will have to migrate eventually.** Accepted. The migration is contained,
  because all database access lives in `backend/app/db.py` and all searching in
  `backend/app/embeddings.py`. Keeping those two files as the only places that
  know how storage works is what makes this decision reversible.

## What "later" looks like

Postgres with pgvector, most likely — one database for both the rows and the
vectors, so a similarity search and a `WHERE user_id = ...` filter stay in a
single query. That becomes the right answer as soon as there are real users and
real data volumes. It is the wrong answer for week one of three people learning.
