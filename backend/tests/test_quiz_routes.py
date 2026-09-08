"""Tests for the six quiz routes.

The model is faked, for the reasons at the top of test_ask.py. What is checked
here is the route's own decisions: who is allowed to see what, what a bad patch
does, and the two rules that would otherwise put a wrong answer key in front of
a class.
"""

import pytest
from fastapi.testclient import TestClient

from app import quiz
from tests.conftest import OTHER_USER_ID, TEST_USER_ID

_OSMOSIS = [1.0, 0.0, 0.0]


def _fake_embed(texts):
    return [_OSMOSIS for _ in texts]


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.DATABASE_FILE", str(tmp_path / "test_nibble.db"))
    monkeypatch.setattr("app.routes._UPLOADS_DIR", tmp_path / "uploads")


@pytest.fixture(autouse=True)
def _fake_model(monkeypatch):
    monkeypatch.setattr("app.routes.embed_texts", _fake_embed)


def _questions(count=3):
    return [
        {
            "prompt": f"Question {n}?",
            "options": ["A", "B", "C", "D"],
            "correct": n % 4,
            "page": 1,
        }
        for n in range(count)
    ]


@pytest.fixture(autouse=True)
def written(monkeypatch):
    """Swap the question writer for a fake, and record what it was handed."""
    calls = []

    def fake_make(context, count, pages):
        calls.append({"context": context, "count": count, "pages": pages})
        return _questions(count)

    monkeypatch.setattr("app.routes.quiz.make_questions", fake_make)
    return calls


@pytest.fixture()
def client():
    from app.main import app

    return TestClient(app)


def _upload(client, filename="biology.txt", text="Osmosis moves water. " * 20):
    return client.post("/documents", files={"file": (filename, text.encode(), "text/plain")})


def _make_quiz(client, document_id, title="Chapter 4", count=3):
    return client.post(
        "/quizzes",
        json={"document_id": document_id, "title": title, "count": count},
    )


# ---------------------------------------------------------------------------
# Making one
# ---------------------------------------------------------------------------


def test_a_quiz_comes_back_matching_the_contract(client):
    doc = _upload(client).json()

    response = _make_quiz(client, doc["id"])

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "document_id", "title", "created_at", "questions"}
    assert body["title"] == "Chapter 4"
    assert len(body["questions"]) == 3

    question = body["questions"][0]
    assert set(question) == {"id", "position", "prompt", "options", "correct", "page"}
    assert len(question["options"]) == 4
    assert 0 <= question["correct"] < 4


def test_positions_are_the_order_they_were_written_in(client):
    doc = _upload(client).json()

    questions = _make_quiz(client, doc["id"]).json()["questions"]

    assert [q["position"] for q in questions] == [0, 1, 2]


def test_the_writer_is_given_the_notes_and_the_real_page_numbers(client, written):
    doc = _upload(client).json()

    _make_quiz(client, doc["id"])

    assert "[biology.txt - p.1]" in written[0]["context"]
    assert written[0]["pages"] == {1}


def test_a_note_that_is_not_yours_is_404(client, signed_in_as):
    """Otherwise a quiz is a way to read somebody else's notes back out."""
    doc = _upload(client).json()

    signed_in_as(OTHER_USER_ID)
    response = _make_quiz(client, doc["id"])

    assert response.status_code == 404


def test_a_note_that_does_not_exist_is_404(client):
    assert _make_quiz(client, 999).status_code == 404


def test_a_blank_title_is_400(client):
    doc = _upload(client).json()

    response = client.post("/quizzes", json={"document_id": doc["id"], "title": "   ", "count": 3})

    assert response.status_code == 400


@pytest.mark.parametrize("count", [0, -1, 11, 50])
def test_a_count_outside_the_range_is_400(client, count):
    doc = _upload(client).json()

    response = client.post(
        "/quizzes", json={"document_id": doc["id"], "title": "Cells", "count": count}
    )

    assert response.status_code == 400


def test_a_note_with_no_chunks_is_422(client):
    """A note from before slice 2. The request was fine; the stored note is not."""
    from app.db import get_db

    doc = _upload(client).json()
    db = get_db()
    db.execute("DELETE FROM chunks")
    db.commit()
    db.close()

    response = _make_quiz(client, doc["id"])

    assert response.status_code == 422
    assert "upload it again" in response.json()["detail"]


def test_the_writer_failing_is_a_503_with_a_sentence(client, monkeypatch):
    doc = _upload(client).json()

    def unavailable(context, count, pages):
        raise quiz.QuizUnavailable("Nibble is being asked a lot at once.")

    monkeypatch.setattr("app.routes.quiz.make_questions", unavailable)

    response = _make_quiz(client, doc["id"])

    assert response.status_code == 503
    assert "Traceback" not in response.json()["detail"]


def test_a_failed_generation_stores_no_quiz(client, monkeypatch):
    """Half a quiz in the list is worse than none."""
    doc = _upload(client).json()

    def unavailable(context, count, pages):
        raise quiz.QuizUnavailable("nope")

    monkeypatch.setattr("app.routes.quiz.make_questions", unavailable)
    _make_quiz(client, doc["id"])

    assert client.get("/quizzes").json() == []


# ---------------------------------------------------------------------------
# Listing and reading
# ---------------------------------------------------------------------------


def test_the_list_is_newest_first_and_counts_the_questions(client):
    doc = _upload(client).json()
    _make_quiz(client, doc["id"], title="First")
    _make_quiz(client, doc["id"], title="Second")

    rows = client.get("/quizzes").json()

    assert [row["title"] for row in rows] == ["Second", "First"]
    assert rows[0]["question_count"] == 3
    assert "questions" not in rows[0]


def test_the_list_only_shows_your_own(client, signed_in_as):
    doc = _upload(client).json()
    _make_quiz(client, doc["id"])

    signed_in_as(OTHER_USER_ID)
    assert client.get("/quizzes").json() == []


def test_one_quiz_comes_back_with_its_answers(client):
    """correct is included because it is your quiz — that is the whole rule."""
    doc = _upload(client).json()
    quiz_id = _make_quiz(client, doc["id"]).json()["id"]

    body = client.get(f"/quizzes/{quiz_id}").json()

    assert len(body["questions"]) == 3
    assert all("correct" in q for q in body["questions"])


def test_somebody_elses_quiz_is_404_not_403(client, signed_in_as):
    """Saying "not yours" would confirm the id is real. It is also not there."""
    doc = _upload(client).json()
    quiz_id = _make_quiz(client, doc["id"]).json()["id"]

    signed_in_as(OTHER_USER_ID)
    assert client.get(f"/quizzes/{quiz_id}").status_code == 404


# ---------------------------------------------------------------------------
# Editing a question — the answer-key rule
# ---------------------------------------------------------------------------


def test_a_prompt_can_be_fixed_on_its_own(client):
    doc = _upload(client).json()
    body = _make_quiz(client, doc["id"]).json()
    qid = body["questions"][0]["id"]

    response = client.patch(
        f"/quizzes/{body['id']}/questions/{qid}", json={"prompt": "Better question?"}
    )

    assert response.status_code == 200
    assert response.json()["prompt"] == "Better question?"


def test_correct_may_be_sent_alone(client):
    """Fixing a mis-keyed answer stays a one-field request, on purpose."""
    doc = _upload(client).json()
    body = _make_quiz(client, doc["id"]).json()
    qid = body["questions"][0]["id"]

    response = client.patch(f"/quizzes/{body['id']}/questions/{qid}", json={"correct": 2})

    assert response.status_code == 200
    assert response.json()["correct"] == 2


def test_options_without_correct_is_refused(client):
    """The important rule in this slice.

    correct is a POSITION in options. Replace the list without restating which
    entry is right and the index points at whatever now sits in that slot — the
    quiz still renders, still marks, and marks the wrong thing.
    """
    doc = _upload(client).json()
    body = _make_quiz(client, doc["id"]).json()
    qid = body["questions"][0]["id"]

    response = client.patch(
        f"/quizzes/{body['id']}/questions/{qid}",
        json={"options": ["W", "X", "Y", "Z"]},
    )

    assert response.status_code == 400
    assert "position" in response.json()["detail"]


def test_options_with_correct_is_accepted(client):
    doc = _upload(client).json()
    body = _make_quiz(client, doc["id"]).json()
    qid = body["questions"][0]["id"]

    response = client.patch(
        f"/quizzes/{body['id']}/questions/{qid}",
        json={"options": ["W", "X", "Y", "Z"], "correct": 3},
    )

    assert response.status_code == 200
    assert response.json()["options"] == ["W", "X", "Y", "Z"]
    assert response.json()["correct"] == 3


def test_a_refused_patch_changes_nothing(client):
    doc = _upload(client).json()
    body = _make_quiz(client, doc["id"]).json()
    question = body["questions"][0]

    client.patch(
        f"/quizzes/{body['id']}/questions/{question['id']}",
        json={"options": ["W", "X", "Y", "Z"]},
    )

    after = client.get(f"/quizzes/{body['id']}").json()["questions"][0]
    assert after["options"] == question["options"]


@pytest.mark.parametrize(
    "patch",
    [
        {"options": ["A", "B", "C"], "correct": 0},
        {"options": ["A", "B", "C", "D", "E"], "correct": 0},
        {"options": ["A", "", "C", "D"], "correct": 0},
        {"correct": 4},
        {"correct": -1},
        {"prompt": "   "},
    ],
)
def test_a_patch_that_would_break_the_question_is_400(client, patch):
    doc = _upload(client).json()
    body = _make_quiz(client, doc["id"]).json()
    qid = body["questions"][0]["id"]

    response = client.patch(f"/quizzes/{body['id']}/questions/{qid}", json=patch)

    assert response.status_code == 400


def test_patching_somebody_elses_question_is_404(client, signed_in_as):
    doc = _upload(client).json()
    body = _make_quiz(client, doc["id"]).json()
    qid = body["questions"][0]["id"]

    signed_in_as(OTHER_USER_ID)
    response = client.patch(f"/quizzes/{body['id']}/questions/{qid}", json={"correct": 1})

    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Deleting
# ---------------------------------------------------------------------------


def test_a_question_can_be_dropped(client):
    doc = _upload(client).json()
    body = _make_quiz(client, doc["id"]).json()
    qid = body["questions"][0]["id"]

    assert client.delete(f"/quizzes/{body['id']}/questions/{qid}").status_code == 204
    assert len(client.get(f"/quizzes/{body['id']}").json()["questions"]) == 2


def test_the_remaining_questions_keep_their_positions(client):
    """Nothing reads position as a count, so renumbering could only add a bug."""
    doc = _upload(client).json()
    body = _make_quiz(client, doc["id"]).json()
    client.delete(f"/quizzes/{body['id']}/questions/{body['questions'][0]['id']}")

    positions = [q["position"] for q in client.get(f"/quizzes/{body['id']}").json()["questions"]]

    assert positions == [1, 2]


def test_deleting_the_last_question_is_refused(client):
    """An empty quiz would sit in the list looking takeable."""
    doc = _upload(client).json()
    body = _make_quiz(client, doc["id"], count=1).json()
    qid = body["questions"][0]["id"]

    response = client.delete(f"/quizzes/{body['id']}/questions/{qid}")

    assert response.status_code == 400
    assert len(client.get(f"/quizzes/{body['id']}").json()["questions"]) == 1


def test_a_quiz_can_be_deleted(client):
    doc = _upload(client).json()
    quiz_id = _make_quiz(client, doc["id"]).json()["id"]

    assert client.delete(f"/quizzes/{quiz_id}").status_code == 204
    assert client.get(f"/quizzes/{quiz_id}").status_code == 404


def test_deleting_a_quiz_takes_its_questions(client):
    """Through ON DELETE CASCADE, which only works with the foreign_keys PRAGMA."""
    from app.db import get_db

    doc = _upload(client).json()
    quiz_id = _make_quiz(client, doc["id"]).json()["id"]
    client.delete(f"/quizzes/{quiz_id}")

    db = get_db()
    left = db.execute("SELECT COUNT(*) AS n FROM questions WHERE quiz_id = ?", (quiz_id,))
    remaining = left.fetchone()["n"]
    db.close()

    assert remaining == 0


def test_deleting_a_note_takes_the_quizzes_made_from_it(client):
    """Worth knowing before somebody tidies up the morning of a lesson."""
    doc = _upload(client).json()
    _make_quiz(client, doc["id"])

    client.delete(f"/documents/{doc['id']}")

    assert client.get("/quizzes").json() == []


def test_deleting_somebody_elses_quiz_is_404(client, signed_in_as):
    doc = _upload(client).json()
    quiz_id = _make_quiz(client, doc["id"]).json()["id"]

    signed_in_as(OTHER_USER_ID)
    assert client.delete(f"/quizzes/{quiz_id}").status_code == 404

    # Back as the owner: the quiz survived somebody else's delete.
    signed_in_as(TEST_USER_ID)
    assert client.get(f"/quizzes/{quiz_id}").status_code == 200


def test_the_note_being_deleted_mid_generation_is_a_sentence_not_a_500(client, monkeypatch):
    """Generation takes seconds with no connection open. A tab can delete the
    note in that window, and the foreign key then refuses the insert. Uncaught
    that is a 500 with a traceback for something somebody did deliberately."""
    doc = _upload(client).json()

    def delete_it_mid_flight(context, count, pages):
        client.delete(f"/documents/{doc['id']}")
        return _questions(3)

    monkeypatch.setattr("app.routes.quiz.make_questions", delete_it_mid_flight)

    response = _make_quiz(client, doc["id"])

    assert response.status_code == 404
    assert "deleted while" in response.json()["detail"]


def test_a_note_deleted_mid_generation_leaves_no_half_quiz(client, monkeypatch):
    doc = _upload(client).json()

    def delete_it_mid_flight(context, count, pages):
        client.delete(f"/documents/{doc['id']}")
        return _questions(3)

    monkeypatch.setattr("app.routes.quiz.make_questions", delete_it_mid_flight)
    _make_quiz(client, doc["id"])

    assert client.get("/quizzes").json() == []


def test_duplicate_options_are_refused_on_an_edit(client):
    """quiz._validate_one already refuses these when the model writes them.

    An edit must not be able to produce a question that generation would have
    thrown away: two identical buttons where only one scores is unanswerable,
    and reads as the app being broken rather than the question being bad.
    """
    doc = _upload(client).json()
    body = _make_quiz(client, doc["id"]).json()
    qid = body["questions"][0]["id"]

    response = client.patch(
        f"/quizzes/{body['id']}/questions/{qid}",
        json={"options": ["Same", "Same", "C", "D"], "correct": 0},
    )

    assert response.status_code == 400
    assert "different" in response.json()["detail"]


def test_duplicate_options_that_differ_only_in_spacing_are_also_refused(client):
    """They are stored stripped, so these would land as duplicates."""
    doc = _upload(client).json()
    body = _make_quiz(client, doc["id"]).json()
    qid = body["questions"][0]["id"]

    response = client.patch(
        f"/quizzes/{body['id']}/questions/{qid}",
        json={"options": ["Osmosis", "  Osmosis  ", "C", "D"], "correct": 0},
    )

    assert response.status_code == 400
