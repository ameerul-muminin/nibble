# ADR 0001 — Postgres with pgvector, not a separate vector database

**Status:** accepted · **Date:** 2026-08-07 · **Decided by:** tech lead

## Context

Nibble stores two kinds of data: ordinary relational records (users, documents,
chat history) and embeddings that need similarity search. The common tutorial
setup pairs Postgres with a dedicated vector database such as Pinecone, Qdrant
or Chroma.

Our constraints: a three-person team, two members new to programming, a fixed
presentation deadline, and a realistic dataset of a few hundred PDFs — on the
order of tens of thousands of chunks.

## Decision

Use a single Postgres instance with the `pgvector` extension for everything,
including embeddings.

## Why

**Consistency for free.** Deleting a document must delete its chunks. In one
database that is an `ON DELETE CASCADE` in a single transaction. Across two, it
is an application-level two-phase delete, and a failure in the second half
leaves orphaned chunks that surface in answers for a document the user removed.

**Filtering is a `WHERE` clause.** "Search only this user's notes" is a join and
a predicate in the same query. Across two stores it means querying the vector
database, collecting ids, then a second round trip to Postgres.

**One thing to learn and run.** One connection string, one Docker service, one
set of credentials, one backup. For teammates learning from scratch, halving the
infrastructure roughly halves the surface area of confusion.

**Scale is not a factor here.** Dedicated vector databases earn their complexity
in the millions-to-billions of vectors range. pgvector is comfortable well past
where we will land.

## Trade-offs accepted

- pgvector's index tuning options are narrower than a specialised engine's.
- Very large scale would eventually mean migrating. Acceptable: migration is
  re-inserting rows we can regenerate, and we are nowhere near that point.

## Revisit if

Chunk count passes roughly one million, or p95 retrieval latency exceeds 300 ms
after adding an HNSW index.
