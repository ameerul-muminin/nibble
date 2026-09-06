"""Tests for the database connection and schema.

Alif owns db.py, so these cover the two things about SQLite that fail quietly
rather than loudly: foreign keys being off by default, and the chunks table
having to exist before slice 2 needs it.
"""

import pytest

from app.db import get_db


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
            "INSERT INTO documents (filename, page_count, created_at) VALUES (?, ?, ?)",
            ("biology.pdf", 2, "2026-09-06T10:00:00"),
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
