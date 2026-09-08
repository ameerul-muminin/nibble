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

    -- Whose note this is: Clerk's id for a person, straight from the `sub`
    -- claim of their session token. See auth.py. Added in slice 4.5, when
    -- Nibble got a public URL and "every note belongs to everybody" stopped
    -- being an acceptable trade.
    --
    -- There is no `users` table and no foreign key to one. Clerk owns the
    -- people; we only ever hold the id, so a second table would be a copy of
    -- someone else's data that we would then have to keep in step.
    user_id    TEXT    NOT NULL,

    filename   TEXT    NOT NULL,
    page_count INTEGER NOT NULL,
    created_at TEXT    NOT NULL   -- ISO 8601, e.g. '2026-08-07T09:14:22'
);

-- Every list, search and delete now starts with "the documents belonging to this
-- person", so the database should find them without reading every row.
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id);

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

-- Slice 6 — quizzes.
--
-- New TABLES rather than new columns, and that is forced rather than tidy.
-- `CREATE TABLE IF NOT EXISTS` does nothing at all to a table that already
-- exists, including adding a column to it — which is exactly how slice 4.5
-- produced a database the code no longer matched, and why _check_shape below
-- exists at all. A new table costs an existing install nothing. A new column
-- would make everybody delete their nibble.db.
CREATE TABLE IF NOT EXISTS quizzes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Whose quiz this is, exactly as documents.user_id holds it: Clerk's `sub`.
    -- This is the sixth thing in the codebase owned this way, not a new idea.
    -- It is stored here as well as being reachable through the document because
    -- ownership questions should be answerable without a join — every quiz
    -- route starts with "is this yours".
    user_id     TEXT    NOT NULL,

    -- The note it was made from. ON DELETE CASCADE, so deleting a note takes
    -- its quizzes with it the same way it already takes its chunks. Worth
    -- knowing before somebody tidies up their notes the morning of a lesson.
    document_id INTEGER NOT NULL,

    title       TEXT    NOT NULL,
    created_at  TEXT    NOT NULL,   -- ISO 8601, like documents.created_at

    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_quizzes_user_id ON quizzes(user_id);

CREATE TABLE IF NOT EXISTS questions (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id  INTEGER NOT NULL,

    -- What order the questions are asked in. Deliberately NOT a count and never
    -- renumbered: delete question 2 of 5 and the rest keep 0, 2, 3, 4. Nothing
    -- reads these as "how many", only as "in what order", so renumbering would
    -- be work that could only ever introduce a bug.
    position INTEGER NOT NULL,

    prompt   TEXT    NOT NULL,

    -- The four answers, as a JSON array of strings. Same trick as
    -- chunks.embedding: SQLite has no array type and json.dumps/json.loads is
    -- the whole conversion. A separate options table would be a join and a
    -- second insert for something that is always read all at once and always
    -- has exactly four entries.
    options  TEXT    NOT NULL,

    -- Which entry of `options` is right, 0 to 3. An index rather than the text,
    -- so a question can have two identically worded options without the answer
    -- key becoming ambiguous.
    correct  INTEGER NOT NULL,

    -- The page of the note this question came from, so it can be checked
    -- against what the page actually says while editing — the same claim
    -- POST /ask makes with its sources.
    page     INTEGER NOT NULL,

    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_questions_quiz_id ON questions(quiz_id);
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

    # Before the schema, not after. Running _SCHEMA against a database from
    # before slice 4.5 fails on its own — the new index names a column that is
    # not there — and it fails as a raw sqlite3.OperationalError reading "no
    # such column: user_id", which is a traceback rather than an answer. Asking
    # first is what lets the sentence below be the thing anybody sees.
    _check_shape(conn)

    conn.executescript(_SCHEMA)
    return conn


class DatabaseOutOfDate(RuntimeError):
    """The database file predates slice 4.5, so notes in it have no owner.

    Its own type for exactly the reason ``ocr.OcrUnavailable``,
    ``embeddings.EmbeddingUnavailable`` and ``llm.AnswerUnavailable`` have one:
    so something upstream can catch precisely this and turn it into a sentence
    somebody can act on.

    **It was a bare RuntimeError until 2026-09-09, and that cost real time.**
    The message below is a good one — it names the file and says exactly what to
    do — but a bare RuntimeError becomes a FastAPI 500 whose body is the words
    "Internal Server Error", so the sentence never left the server. It sat in
    the log while the person on the other end was told to check whether the
    backend was running, which it was. Writing a helpful message is only half of
    it; the other half is making sure it can reach somebody.

    Still a RuntimeError underneath, so anything already catching that keeps
    working.
    """


def _check_shape(conn: sqlite3.Connection) -> None:
    """Refuse to run against a database from before notes had owners.

    ``CREATE TABLE IF NOT EXISTS`` does exactly what it says: if `documents`
    already exists, the statement above does nothing at all — including nothing
    about the `user_id` column added in slice 4.5. So a database created before
    that change keeps working, silently, with a schema the code no longer
    matches. Every insert would fail on a column that is not there, and every
    query would be filtering on one either.

    A migration system is the grown-up answer to this and a whole new idea to
    explain. What this project does instead is fail loudly and say what to do,
    which is the same trade as everywhere else: the data is a handful of
    uploaded chapters, and re-uploading them costs a minute.

    Raises:
        RuntimeError: the `documents` table exists but predates `user_id`.
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(documents)").fetchall()}

    # An empty answer means the table does not exist at all, which is a brand
    # new database and completely fine — the schema is about to create it. Only
    # a `documents` that exists *without* user_id is the bad case, and telling
    # those two apart is the whole reason this looks at the columns rather than
    # just asking whether user_id is missing.
    if not columns:
        return

    if "user_id" not in columns:
        conn.close()
        raise DatabaseOutOfDate(
            f"The database file '{config.DATABASE_FILE}' was made before notes "
            "had owners, so Nibble cannot tell whose notes are whose in it. "
            "Delete the file and start the backend again — it will build a fresh "
            "one, and you can re-upload your notes."
        )
