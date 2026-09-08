"""Tests for the database connection and schema.

Alif owns db.py, so these cover the two things about SQLite that fail quietly
rather than loudly: foreign keys being off by default, and the chunks table
having to exist before slice 2 needs it.
"""

import pytest

from app.db import get_db
from tests.conftest import TEST_USER_ID


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    """Point the database at a fresh temporary file for every single test."""
    monkeypatch.setattr("app.config.DATABASE_FILE", str(tmp_path / "test_nibble.db"))


def test_schema_creates_documents_and_chunks_tables():
    """Both tables exist from slice 1, even though chunks is not filled yet."""
    db = get_db()
    try:
        rows = db.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        names = {row["name"] for row in rows}
    finally:
        db.close()

    assert "documents" in names
    assert "chunks" in names


def test_chunks_table_has_an_embedding_column():
    """Slice 3 stores 384 numbers here as JSON. The column is created up front."""
    db = get_db()
    try:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(chunks)").fetchall()}
    finally:
        db.close()

    assert {"id", "document_id", "page", "content", "embedding"} <= columns


def test_foreign_keys_are_switched_on():
    """SQLite defaults this to OFF, per connection. Without it, cascade does nothing."""
    db = get_db()
    try:
        assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        db.close()


def test_deleting_a_document_also_deletes_its_chunks():
    """This is what DELETE /documents/{id} relies on in issue #6."""
    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO documents (user_id, filename, page_count, created_at) VALUES (?, ?, ?, ?)",
            (TEST_USER_ID, "biology.pdf", 2, "2026-09-06T10:00:00"),
        )
        doc_id = cursor.lastrowid
        db.execute(
            "INSERT INTO chunks (document_id, page, content) VALUES (?, ?, ?)",
            (doc_id, 1, "Osmosis is the net movement of water."),
        )
        db.commit()

        db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        db.commit()

        remaining = db.execute(
            "SELECT COUNT(*) AS n FROM chunks WHERE document_id = ?", (doc_id,)
        ).fetchone()["n"]
    finally:
        db.close()

    assert remaining == 0


def test_a_chunk_cannot_point_at_a_document_that_does_not_exist():
    """With foreign keys on, this raises instead of silently storing an orphan."""
    import sqlite3

    db = get_db()
    try:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO chunks (document_id, page, content) VALUES (?, ?, ?)",
                (99999, 1, "I belong to nothing."),
            )
            db.commit()
    finally:
        db.close()


def test_a_database_from_before_notes_had_owners_is_refused():
    """An old nibble.db gets a sentence, not a traceback.

    Slice 4.5 added `user_id` to `documents`, and `CREATE TABLE IF NOT EXISTS`
    will not add a column to a table that already exists — so a database made
    before that change survives, with a shape the code no longer matches.

    This is pinned because the first version of the check ran *after* the
    schema, and the schema hits the problem first: the new index on user_id
    fails with "no such column", which is exactly the raw exception the project
    promises never to show anybody. Getting the order wrong again would be
    invisible without this test, because the database is still refused either
    way — just uselessly.
    """
    import sqlite3

    from app import config

    # A `documents` table exactly as slice 1 wrote it: no user_id.
    old = sqlite3.connect(config.DATABASE_FILE)
    old.execute(
        "CREATE TABLE documents (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "filename TEXT NOT NULL, page_count INTEGER NOT NULL, created_at TEXT NOT NULL)"
    )
    old.commit()
    old.close()

    with pytest.raises(RuntimeError, match="Delete the file"):
        get_db()


def test_an_out_of_date_database_reaches_a_person_as_a_sentence(tmp_path, monkeypatch):
    """The message is only half the job; the other half is it leaving the server.

    This was a bare RuntimeError, which FastAPI turns into a 500 whose body is
    the words "Internal Server Error". The helpful sentence sat in the log while
    the person on the other end was told to check a backend that was running.

    The `signed_in` fixture in conftest.py already gets this past auth, so this
    reaches the database the way a real signed-in request would.
    """
    import sqlite3

    from fastapi.testclient import TestClient

    # A database with the pre-slice-4.5 shape: documents, but no user_id.
    old = tmp_path / "old.db"
    conn = sqlite3.connect(old)
    conn.execute(
        "CREATE TABLE documents (id INTEGER PRIMARY KEY, filename TEXT, "
        "page_count INTEGER, created_at TEXT)"
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr("app.config.DATABASE_FILE", str(old))

    from app.main import app

    response = TestClient(app).get("/documents")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "Delete the file" in detail
    assert "Internal Server Error" not in detail
