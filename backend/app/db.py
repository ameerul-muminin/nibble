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
    conn.executescript(_SCHEMA)
    return conn
