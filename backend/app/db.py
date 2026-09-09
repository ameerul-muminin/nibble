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

-- Slice 7 — the classroom.
--
-- Three tables, and not one of them is a `users` table or a `roles` table. A
-- teacher is somebody who owns a room; a student is somebody with a row in
-- room_members. That is the whole of it, and the three roads not taken are in
-- adr/0004-teacher-is-an-owner.md.
CREATE TABLE IF NOT EXISTS rooms (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,

    -- The teacher. Clerk's `sub` again, the same string documents.user_id and
    -- quizzes.user_id hold. Named owner_id rather than user_id on purpose: a
    -- room has two kinds of person in it, and "user" would not say which.
    owner_id   TEXT    NOT NULL,

    -- The quiz being run. ON DELETE CASCADE, so deleting a quiz takes its rooms
    -- and — through the cascades below — their members and answers. Worth
    -- knowing before somebody tidies up the morning of a lesson.
    quiz_id    INTEGER NOT NULL,

    -- What students type off the projector. Six characters, and UNIQUE because
    -- the whole point of a code is that it names exactly one room. See
    -- _new_code in routes.py for the alphabet and why O, 0, I and 1 are not in
    -- it.
    code       TEXT    NOT NULL UNIQUE,

    -- waiting -> open -> closed, and never backwards. The CHECK is the only
    -- constraint of its kind in this schema, and it earns its place: every
    -- screen in this slice decides what to draw from this one value, so a
    -- fourth string appearing in this column would break both of them at once
    -- in a way no test would necessarily catch. The database refusing it is
    -- cheaper than remembering to.
    state      TEXT    NOT NULL DEFAULT 'waiting'
               CHECK (state IN ('waiting', 'open', 'closed')),

    created_at TEXT    NOT NULL,   -- ISO 8601, like every other created_at here

    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rooms_owner_id ON rooms(owner_id);

CREATE TABLE IF NOT EXISTS room_members (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id   INTEGER NOT NULL,

    -- The student. Clerk's `sub`, same as everywhere.
    user_id   TEXT    NOT NULL,

    -- What to call them on the teacher's marking screen. Added in slice 8, and
    -- it is the first human-readable thing about a person this project stores —
    -- auth.py's docstring used to say the Clerk id was the only one, and was
    -- amended when this landed rather than left to quietly go false.
    --
    -- It comes from the student's Clerk profile, sent by the frontend at join
    -- time so that nobody has to type it. That makes it a value the client
    -- chose, so it is trimmed, length-capped, and **only ever displayed** — it
    -- never decides anything, which is the line between a value you show and a
    -- value you trust. A student can call themselves whatever they like.
    --
    -- DEFAULT '' because Clerk allows an account with no name at all, and an
    -- empty one is normal rather than an error: the results route turns it into
    -- 'Student 1', 'Student 2' by join order when somebody looks.
    name      TEXT    NOT NULL DEFAULT '',

    joined_at TEXT    NOT NULL,

    -- One row per person per room, enforced here rather than remembered in the
    -- route. A student who refreshes the page, or comes back after their phone
    -- locked, joins again — and must not become a second student, because the
    -- teacher is watching that number on a projector while deciding whether to
    -- start. The route inserts with OR IGNORE and this line is what makes that
    -- mean something.
    UNIQUE (room_id, user_id),

    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_room_members_room_id ON room_members(room_id);

CREATE TABLE IF NOT EXISTS answers (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id     INTEGER NOT NULL,

    -- Who answered. Clerk's `sub`. There is no foreign key to room_members and
    -- there does not need to be: the route checks membership before it writes,
    -- and the pair (room_id, user_id) says the same thing a members row would.
    user_id     TEXT    NOT NULL,

    question_id INTEGER NOT NULL,

    -- Which entry of the question's options they picked, 0 to 3. An index, for
    -- exactly the reason questions.correct is one.
    chosen      INTEGER NOT NULL,

    -- 1 if right, 0 if wrong, written HERE at submit time rather than worked
    -- out when somebody looks.
    --
    -- **It is stored in slice 7 even though nothing reads it until slice 8**,
    -- and that is deliberate rather than premature. Slice 8 lets a teacher
    -- override a mark, and the moment they can, `chosen == correct` is no
    -- longer the answer — there would be two rules for one number and every
    -- screen would have to know which applies. Writing it once at submit time
    -- makes an override an ordinary UPDATE, and "was this changed?" is still
    -- answerable by comparing it with chosen == correct at read time.
    --
    -- Adding it later would have been the expensive move: CREATE TABLE IF NOT
    -- EXISTS silently will not add a column to a table that already exists,
    -- which is the whole reason _check_shape below exists.
    mark        INTEGER NOT NULL,

    answered_at TEXT    NOT NULL,

    -- One answer per person per question. The route refuses a second
    -- submission outright, so this is the belt to that pair of braces: if a
    -- double-tapped Submit ever gets past the route, the database still ends up
    -- with one paper per student rather than two overlapping ones.
    UNIQUE (room_id, user_id, question_id),

    FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- Slice 8 reads this two ways: everything one student answered, and everything
-- answered for one question. Both start with the room.
CREATE INDEX IF NOT EXISTS idx_answers_room_id ON answers(room_id);
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


def _columns_of(conn: sqlite3.Connection, table: str) -> set[str]:
    """The column names of a table, or an empty set if it does not exist.

    The empty set is the interesting half. It means "no such table", which is a
    brand new database and completely fine — the schema is about to create it.
    A table that exists *without* the column we need is the bad case, and telling
    those two apart is the whole reason this looks at the columns rather than
    just asking whether one is missing.
    """
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _check_shape(conn: sqlite3.Connection) -> None:
    """Refuse to run against a database whose tables predate the code.

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

    **There are two of these now, and the second one proves the first was not a
    one-off.** Slice 4.5 added `documents.user_id`; slice 8 added
    `room_members.name`, to a table slice 7 had already created on `main`. Both
    times the new column landed on a table that existing databases already had,
    and both times `CREATE TABLE IF NOT EXISTS` did exactly nothing about it. The
    check below is the same shape twice for that reason, and adding a third is
    two lines rather than a new idea.

    Raises:
        DatabaseOutOfDate: a table exists but is missing a column added later.
    """
    # Slice 4.5. Without user_id, every insert fails on a column that is not
    # there and every query filters on one either.
    documents = _columns_of(conn, "documents")

    if documents and "user_id" not in documents:
        conn.close()
        raise DatabaseOutOfDate(
            f"The database file '{config.DATABASE_FILE}' was made before notes "
            "had owners, so Nibble cannot tell whose notes are whose in it. "
            "Delete the file and start the backend again — it will build a fresh "
            "one, and you can re-upload your notes."
        )

    # Slice 8. A room_members from slice 7 has no name column, so the first
    # student to join a class would hit an OperationalError from the INSERT —
    # a traceback, mid-lesson, instead of a sentence at startup.
    members = _columns_of(conn, "room_members")

    if members and "name" not in members:
        conn.close()
        raise DatabaseOutOfDate(
            f"The database file '{config.DATABASE_FILE}' was made before students "
            "had names, so Nibble cannot tell you who handed in what. Delete the "
            "file and start the backend again — it will build a fresh one, and you "
            "can re-upload your notes."
        )
