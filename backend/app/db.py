"""SQLite database connection and schema.

Alif owns this file. It sets up the database tables and gives the rest of the
app a simple way to get a connection.

The database is just a file on disk (nibble.db by default). Delete it to start
over with an empty app. There is no server to install or run.
"""

import sqlite3
from pathlib import Path

from app import config

# ---------------------------------------------------------------------------
# Schema — what the tables look like
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    filename   TEXT    NOT NULL,
    page_count INTEGER NOT NULL,
    created_at TEXT    NOT NULL   -- ISO 8601, e.g. '2026-08-07T09:14:22'
);

-- Slice 2 fills this in and slice 3 fills in the embedding. It is created now,
-- with slice 1, because changing the shape of a table that already has rows in
-- it is a genuine chore, and designing it once up front costs nothing.
CREATE TABLE IF NOT EXISTS chunks (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    page        INTEGER NOT NULL,
    content     TEXT    NOT NULL,

    -- 384 numbers describing what this chunk means, stored as a JSON string.
    -- SQLite has no array type, and json.dumps / json.loads is the whole
    -- conversion. NULL until slice 3 starts filling it in.
    embedding   TEXT,

    -- ON DELETE CASCADE means deleting a document deletes its chunks too, so
    -- DELETE /documents/{id} does not leave orphans behind. It only works when
    -- foreign keys are switched on — see get_db below.
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Every chunk lookup is "the chunks belonging to this document", so the
-- database should be able to find them without reading every row.
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
"""


def get_db() -> sqlite3.Connection:
    """Return a connection to the SQLite database.

    The connection uses ``sqlite3.Row`` as its row factory, so every row
    behaves like a dict — you can write ``row["filename"]`` instead of
    remembering column positions.

    The schema is created automatically on the first call (or whenever the
    database file is missing).
    """
    db_path = Path(config.DATABASE_FILE)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # safer for concurrent reads

    # SQLite has foreign keys switched OFF by default, and it is per connection,
    # not per database — so this line has to run on every single connection. Miss
    # it and ON DELETE CASCADE above does nothing at all, silently: no error, the
    # chunks just quietly stay behind. Worth knowing about before slice 2.
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript(_SCHEMA)
    return conn
