"""Tests for slice 4.5: your notes are yours.

Two separate claims live in here, and they fail in different ways, so keep them
apart when reading:

1. **A request with no valid sign-in is refused.** These turn OFF the override
   in conftest.py and hit the real dependency. Without them, nothing in the
   suite would notice if auth.py were deleted — every other test file installs
   a fake signed-in user and would go on passing.

2. **Two signed-in people cannot see each other's notes.** These keep the
   override and simply switch who it returns. That is the part that actually
   makes a deployed, shared backend safe, and it is checked on all four routes
   that touch somebody's data, because getting it right on three of them and
   forgetting the fourth is exactly how this goes wrong.
"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import OTHER_USER_ID, TEST_USER_ID


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    """A fresh throwaway database and uploads folder for every test."""
    monkeypatch.setattr("app.config.DATABASE_FILE", str(tmp_path / "test_nibble.db"))
    monkeypatch.setattr("app.routes._UPLOADS_DIR", tmp_path / "uploads")


@pytest.fixture(autouse=True)
def _fake_embeddings(monkeypatch):
    """One fixed vector for everything.

    These tests are about who can see what, not about meaning, so every piece
    of text pointing the same way is fine — it means everything matches
    everything, which is the *hardest* case for an ownership filter. If a note
    of somebody else's is going to leak into a search, this is the setup that
    finds it.
    """
    monkeypatch.setattr("app.routes.embed_texts", lambda texts: [[0.1, 0.2, 0.3] for _ in texts])


@pytest.fixture()
def client():
    from app.main import app

    return TestClient(app)


@pytest.fixture()
def signed_out():
    """Turn off the fake sign-in, so the real token check runs.

    conftest.py installs an override for every test in the suite. Clearing it
    here is what makes these particular tests meaningful: the request now goes
    through current_user_id in auth.py for real, finds no Authorization header,
    and refuses.
    """
    from app.main import app

    app.dependency_overrides.clear()


def _upload(client: TestClient, filename: str, text: str) -> int:
    """Upload a text note as whoever is currently signed in, and return its id."""
    response = client.post(
        "/documents",
        files={"file": (filename, text.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


# ---------------------------------------------------------------------------
# 1. No sign-in, no answer
# ---------------------------------------------------------------------------

# Every route that touches somebody's notes, as (method, path, body).
PROTECTED = [
    ("GET", "/documents", None),
    ("DELETE", "/documents/1", None),
    ("GET", "/documents/1/chunks", None),
    ("POST", "/search", {"query": "osmosis"}),
    ("POST", "/ask", {"question": "what is osmosis"}),
    # Slice 6. A quiz is made from your notes and carries their answers, so
    # every one of these is as private as the note it came from.
    ("POST", "/quizzes", {"document_id": 1, "title": "Cells", "count": 5}),
    ("GET", "/quizzes", None),
    ("GET", "/quizzes/1", None),
    ("PATCH", "/quizzes/1/questions/1", {"correct": 1}),
    ("DELETE", "/quizzes/1/questions/1", None),
    ("DELETE", "/quizzes/1", None),
    # Slice 7. The teacher's five are as private as the quiz they run. The
    # student's three are here for a different reason: without a verified token
    # there is no `sub`, so there is nobody to be a member of a room — anonymous
    # answering would be a paper with no name on it.
    ("POST", "/rooms", {"quiz_id": 1}),
    ("GET", "/rooms", None),
    ("GET", "/rooms/1", None),
    ("POST", "/rooms/1/state", {"state": "open"}),
    ("DELETE", "/rooms/1", None),
    ("POST", "/rooms/join", {"code": "K7M2QP"}),
    ("GET", "/rooms/code/K7M2QP", None),
    ("POST", "/rooms/1/answers", {"answers": [{"question_id": 1, "chosen": 0}]}),
    # Slice 8. Both of these are the teacher's, and the first is the only
    # response in the whole API that contains an answer key — a 401 here is the
    # difference between a marking screen and a way to read somebody's quiz.
    ("GET", "/rooms/1/results", None),
    ("PATCH", "/rooms/1/answers/1", {"mark": 1}),
]


@pytest.mark.parametrize(("method", "path", "body"), PROTECTED)
def test_no_token_is_refused(client, signed_out, method, path, body):
    """Without a sign-in, every route about notes answers 401 and does nothing.

    Parametrised rather than written out five times so that adding a route to
    the list above is all it takes to cover it. A new route that forgets
    Depends(current_user_id) will not be caught by this — nothing can catch
    that automatically — but a route that has it stays covered for free.
    """
    response = client.request(method, path, json=body)

    assert response.status_code == 401
    # A person reads this. It should tell them what to do, not name a header.
    assert "signed in" in response.json()["detail"].lower()


def test_upload_with_no_token_is_refused(client, signed_out):
    """Kept separate from the list above because it sends a file, not JSON."""
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", b"Osmosis is the movement of water.", "text/plain")},
    )

    assert response.status_code == 401


def test_a_nonsense_token_is_refused(client, signed_out):
    """A header that is present but not a real Clerk token is still a 401.

    This is the case that matters most, because it is the one an attacker
    actually tries. It must never reach the route, and it must never show the
    JWT library's own wording — "Not enough segments" tells a student nothing
    and an attacker something.
    """
    response = client.get("/documents", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_health_needs_no_sign_in(client, signed_out):
    """/health stays open on purpose — the host's health check calls it."""
    response = client.get("/health")

    assert response.status_code == 200


# ---------------------------------------------------------------------------
# 2. Two people, one backend
# ---------------------------------------------------------------------------


def test_the_notes_list_only_shows_your_own(client, signed_in_as):
    _upload(client, "alifs-notes.txt", "Osmosis is the net movement of water.")

    signed_in_as(OTHER_USER_ID)
    _upload(client, "someone-elses-notes.txt", "Osmosis, written by somebody else.")

    assert [d["filename"] for d in client.get("/documents").json()] == ["someone-elses-notes.txt"]

    signed_in_as(TEST_USER_ID)
    assert [d["filename"] for d in client.get("/documents").json()] == ["alifs-notes.txt"]


def test_you_cannot_delete_someone_elses_note(client, signed_in_as):
    """And the refusal is a 404, so it does not confirm the note exists."""
    document_id = _upload(client, "alifs-notes.txt", "Osmosis is the net movement of water.")

    signed_in_as(OTHER_USER_ID)
    response = client.delete(f"/documents/{document_id}")

    assert response.status_code == 404

    # The note is still there afterwards. Without this, a 404 that deleted the
    # row anyway would pass the assertion above.
    signed_in_as(TEST_USER_ID)
    assert [d["id"] for d in client.get("/documents").json()] == [document_id]


def test_you_cannot_read_the_pieces_of_someone_elses_note(client, signed_in_as):
    document_id = _upload(client, "alifs-notes.txt", "Osmosis is the net movement of water.")

    signed_in_as(OTHER_USER_ID)
    response = client.get(f"/documents/{document_id}/chunks")

    assert response.status_code == 404


def test_search_never_reaches_someone_elses_notes(client, signed_in_as):
    """The one that would be worst to get wrong.

    Every vector in this test is identical, so a missing ownership filter does
    not merely *risk* leaking the other note — it guarantees it comes back as a
    perfect match.
    """
    _upload(client, "alifs-notes.txt", "Osmosis is the net movement of water.")

    signed_in_as(OTHER_USER_ID)
    body = client.post("/search", json={"query": "osmosis"}).json()

    assert body["results"] == []
    assert body["unsearchable_note_ids"] == []


def test_asking_never_reaches_someone_elses_notes(client, signed_in_as, monkeypatch):
    """/ask must not answer from notes you cannot see.

    The model is not stubbed here and does not need to be: with no notes of
    their own, the route returns its "nothing in your notes" answer *without
    calling the model at all*. Failing this test would mean the model was
    called — with somebody else's notes in the prompt — so a stub that raises
    is the clearest possible tripwire.
    """

    def _must_not_be_called(*args, **kwargs):
        raise AssertionError("the model was called with notes belonging to somebody else")

    monkeypatch.setattr("app.routes.llm.answer", _must_not_be_called)

    _upload(client, "alifs-notes.txt", "Osmosis is the net movement of water.")

    signed_in_as(OTHER_USER_ID)
    body = client.post("/ask", json={"question": "what is osmosis"}).json()

    assert body["sources"] == []
    assert "nothing in your notes" in body["answer"].lower()


def test_two_people_can_upload_the_same_filename(client, signed_in_as):
    """Both notes exist, separately, and each person sees exactly one.

    Worth pinning because slice 1 accepted that two uploads with the same name
    share one file on disk. That is still true and still fine — the *rows* are
    what the app reads from, and they are separate.
    """
    _upload(client, "biology.txt", "Alif's osmosis notes.")

    signed_in_as(OTHER_USER_ID)
    _upload(client, "biology.txt", "Somebody else's osmosis notes.")

    assert len(client.get("/documents").json()) == 1

    signed_in_as(TEST_USER_ID)
    assert len(client.get("/documents").json()) == 1
