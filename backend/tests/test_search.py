"""Tests for POST /search.

**Every test in here uses a fake embedder, and that is deliberate.** The real
model is tested in test_embeddings.py, where the claim being made is about
meaning. The claim being made *here* is about plumbing: does the route read the
right rows, skip the right rows, sort the right way, clamp the score, and count
what it skipped. None of that needs a real model, and using one would make these
tests slow and their assertions vague — "the osmosis note scored higher" is a
much weaker statement than "the osmosis note scored exactly 1.0".

The fake is three numbers wide instead of 384. Nothing in the route or in
cosine_similarity cares how wide a vector is, as long as everything is the same
width — which is exactly what EMBEDDING_DIM guards against in the real thing.
"""

import json

import pytest
from fastapi.testclient import TestClient

from app.embeddings import EmbeddingUnavailable

# Three topics, one direction each: osmosis, databases, and everything else.
# A query about osmosis points exactly the same way as an osmosis chunk, so it
# scores 1.0, and at right angles to a database chunk, so that scores 0.0.
_OSMOSIS = [1.0, 0.0, 0.0]
_DATABASE = [0.0, 1.0, 0.0]
_NEITHER = [0.0, 0.0, 1.0]


def _fake_embed(texts: list[str]) -> list[list[float]]:
    vectors = []
    for text in texts:
        lowered = text.lower()
        if "osmosis" in lowered:
            vectors.append(_OSMOSIS)
        elif "database" in lowered:
            vectors.append(_DATABASE)
        else:
            vectors.append(_NEITHER)
    return vectors


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    """A fresh database and uploads directory for every test."""
    monkeypatch.setattr("app.config.DATABASE_FILE", str(tmp_path / "test_nibble.db"))
    monkeypatch.setattr("app.routes._UPLOADS_DIR", tmp_path / "uploads")


@pytest.fixture(autouse=True)
def _fake_model(monkeypatch):
    """Swap the real model out for the three-direction fake above."""
    monkeypatch.setattr("app.routes.embed_texts", _fake_embed)


@pytest.fixture()
def client():
    from app.main import app

    return TestClient(app)


def _upload(client, filename: str, text: str):
    return client.post("/documents", files={"file": (filename, text.encode(), "text/plain")})


# ---------------------------------------------------------------------------
# The query itself
# ---------------------------------------------------------------------------


def test_a_blank_query_is_400_with_a_sentence(client):
    response = client.post("/search", json={"query": ""})

    assert response.status_code == 400
    assert "Type something" in response.json()["detail"]


def test_a_whitespace_only_query_is_also_blank(client):
    """ "   " is empty to a person and truthy to Python. The route strips first."""
    response = client.post("/search", json={"query": "     "})

    assert response.status_code == 400


def test_a_body_with_no_query_at_all_is_422(client):
    """Pydantic rejects this before our code runs — we write no code for it."""
    assert client.post("/search", json={}).status_code == 422


# ---------------------------------------------------------------------------
# Finding things
# ---------------------------------------------------------------------------


def test_nothing_uploaded_yet_is_an_empty_list_not_an_error(client):
    response = client.post("/search", json={"query": "osmosis"})

    assert response.status_code == 200
    assert response.json() == {"results": [], "unsearchable_notes": 0}


def test_the_matching_note_comes_first_with_everything_the_contract_promises(client):
    _upload(client, "biology.txt", "Osmosis is the net movement of water across a membrane.")
    _upload(client, "systems.txt", "A database schema describes the structure of the data.")

    response = client.post("/search", json={"query": "how does osmosis work"})

    assert response.status_code == 200
    results = response.json()["results"]

    assert results[0]["filename"] == "biology.txt"
    assert results[0]["page"] == 1
    assert "Osmosis" in results[0]["content"]
    assert results[0]["score"] == 1.0
    assert isinstance(results[0]["document_id"], int)

    # The database note is still returned — it is just last, and scored 0.
    assert results[-1]["filename"] == "systems.txt"
    assert results[-1]["score"] == 0.0


def test_results_are_capped_at_TOP_K(client, monkeypatch):
    monkeypatch.setattr("app.config.TOP_K", 2)
    for n in range(5):
        _upload(client, f"note{n}.txt", f"Osmosis note number {n}, with enough words to store.")

    results = client.post("/search", json={"query": "osmosis"}).json()["results"]

    assert len(results) == 2


def test_a_negative_score_is_reported_as_zero(client, monkeypatch):
    """docs/api.md promises 0 to 1, and a cosine can go to -1.

    The clamp lives in the route rather than in cosine_similarity, so this is
    where it has to be pinned. The fake points the query in exactly the opposite
    direction to the stored piece, which is the -1 case.
    """
    _upload(client, "biology.txt", "Osmosis is the net movement of water across a membrane.")

    monkeypatch.setattr("app.routes.embed_texts", lambda texts: [[-1.0, 0.0, 0.0] for _ in texts])
    results = client.post("/search", json={"query": "the opposite of osmosis"}).json()["results"]

    assert results[0]["score"] == 0.0


# ---------------------------------------------------------------------------
# Notes stored before search existed
# ---------------------------------------------------------------------------


def _insert_note_with_no_embedding(filename: str = "old.pdf"):
    """Write a document the way slice 2 would have — chunks, but no vectors."""
    from app.db import get_db

    db = get_db()
    try:
        cursor = db.execute(
            "INSERT INTO documents (filename, page_count, created_at) VALUES (?, ?, ?)",
            (filename, 1, "2026-09-01T10:00:00"),
        )
        db.execute(
            "INSERT INTO chunks (document_id, page, content) VALUES (?, ?, ?)",
            (cursor.lastrowid, 1, "Osmosis, written down before search existed."),
        )
        db.commit()
    finally:
        db.close()


def test_a_note_with_no_embedding_is_skipped_and_counted(client):
    """The decision in docs/scope.md: skip them, but never silently.

    Without the count this is the failure the project keeps meeting — a note
    sitting in the list, looking perfectly normal, that no search can ever find.
    """
    _insert_note_with_no_embedding()
    _upload(client, "new.txt", "Osmosis is the net movement of water across a membrane.")

    body = client.post("/search", json={"query": "osmosis"}).json()

    assert [r["filename"] for r in body["results"]] == ["new.txt"]
    assert body["unsearchable_notes"] == 1


def test_only_old_notes_means_no_results_but_still_a_count(client):
    _insert_note_with_no_embedding()

    body = client.post("/search", json={"query": "osmosis"}).json()

    assert body["results"] == []
    assert body["unsearchable_notes"] == 1


# ---------------------------------------------------------------------------
# When the model is not there
# ---------------------------------------------------------------------------


def test_the_model_failing_is_503_and_a_plain_sentence(client, monkeypatch):
    def _explode(texts):
        raise EmbeddingUnavailable("The search model could not be loaded.")

    monkeypatch.setattr("app.routes.embed_texts", _explode)

    response = client.post("/search", json={"query": "osmosis"})

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "Nibble couldn't search" in detail
    assert "Traceback" not in detail


# ---------------------------------------------------------------------------
# What the upload stored — issue #12, seen from the other side
# ---------------------------------------------------------------------------


def test_every_chunk_is_stored_with_an_embedding(client):
    from app.db import get_db

    _upload(client, "biology.txt", "Osmosis is the net movement of water across a membrane.")

    db = get_db()
    try:
        rows = db.execute("SELECT embedding FROM chunks").fetchall()
    finally:
        db.close()

    assert rows
    for row in rows:
        assert row["embedding"] is not None
        assert json.loads(row["embedding"]) == _OSMOSIS


def test_an_upload_that_cannot_be_embedded_stores_nothing(client, monkeypatch):
    """The single-transaction promise, from slice 2, extended to vectors.

    A document stored without its vectors would list perfectly and never match
    a search. So the embedding happens before the insert, and a failure means
    the whole upload fails — not a half-stored note.
    """
    from app.db import get_db

    def _explode(texts):
        raise EmbeddingUnavailable("The search model could not be loaded.")

    monkeypatch.setattr("app.routes.embed_texts", _explode)

    response = _upload(client, "biology.txt", "Osmosis is the net movement of water.")

    assert response.status_code == 503
    assert "Nibble couldn't get that note ready to search" in response.json()["detail"]

    db = get_db()
    try:
        assert db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 0
    finally:
        db.close()
