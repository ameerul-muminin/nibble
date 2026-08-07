-- Runs once, the first time the database container is created.
-- Turns on pgvector so we can store embeddings in a normal Postgres table.
CREATE EXTENSION IF NOT EXISTS vector;
