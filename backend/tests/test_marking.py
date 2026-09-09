"""Tests for slice 8 — the marking screen's two routes.

The fixtures here are the ones from test_rooms.py, because getting to a mark
means getting all the way through a class first: a note, a quiz, a room, a
student who joined, Start, and a paper handed in. That setup is what `marked`
below is for.

Six rules are worth a test, and they are the ones written into docs/scope.md
before this slice was built:

  * a room that is not yours has no results
  * an answer id from somebody else's room cannot be marked
  * a mark that is not 0 or 1 is refused
  * an override changes `mark` and nothing else — never `chosen`
  * the flag fires at three answers and not at two
  * a question nobody answered comes back unanswered rather than wrong

The fourth is the one this slice would break most quietly. A teacher overruling
a mark and silently rewriting what a student picked would look completely
normal on screen, and the room would have no record of what actually happened
in it.
"""

import pytest
from fastapi.testclient import TestClient

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


@pytest.fixture(autouse=True)
def _fake_writer(monkeypatch):
    """Three questions, with a known answer key: 0, 1, 2."""

    def fake_make(context, count, pages):
        return [
            {
                "prompt": f"Question {n}?",
                "options": ["A", "B", "C", "D"],
                "correct": n,
                "page": 1,
            }
            for n in range(count)
        ]

    monkeypatch.setattr("app.routes.quiz.make_questions", fake_make)


@pytest.fixture()
def client():
    from app.main import app

    return TestClient(app)


@pytest.fixture()
def room(client):
    """A room in `waiting`, owned by the default test user, around a 3-question quiz."""
    client.post(
        "/documents",
        files={"file": ("biology.txt", b"Osmosis moves water. " * 20, "text/plain")},
    )
    quiz = client.post("/quizzes", json={"document_id": 1, "title": "Cells", "count": 3}).json()

    return client.post("/rooms", json={"quiz_id": quiz["id"]}).json()


@pytest.fixture()
def marked(client, room, signed_in_as):
    """A room with one student in it who has handed in a paper.

    The paper is deliberately not perfect: question 0 right, question 1 wrong,
    question 2 not answered at all. That gives every case the marking screen has
    to draw — a right one, a wrong one, and a blank — out of one fixture.

    Ends signed in as the teacher, because that is who both routes under test
    are for.
    """
    signed_in_as(OTHER_USER_ID)
    client.post("/rooms/join", json={"code": room["code"], "name": "Amina"})

    signed_in_as(TEST_USER_ID)
    client.post(f"/rooms/{room['id']}/state", json={"state": "open"})

    signed_in_as(OTHER_USER_ID)
    client.post(
        f"/rooms/{room['id']}/answers",
        json={"answers": [{"question_id": 1, "chosen": 0}, {"question_id": 2, "chosen": 3}]},
    )

    signed_in_as(TEST_USER_ID)
    return room


# ---------------------------------------------------------------------------
# GET /rooms/{id}/results
# ---------------------------------------------------------------------------


def test_results_are_only_for_the_owner(client, marked, signed_in_as):
    """Somebody else's class is a 404, not a 403.

    The same answer as everywhere else in this project: telling a stranger the
    room exists but is not theirs confirms it exists.
    """
    signed_in_as(OTHER_USER_ID)

    response = client.get(f"/rooms/{marked['id']}/results")

    assert response.status_code == 404


def test_results_hold_the_marks_and_the_answer_key(client, marked):
    """The teacher gets `correct`, because the teacher owns the quiz.

    The exact inverse of test_rooms.py's answer-key test, and the pair is the
    point: one route must never send this column and this one must.
    """
    body = client.get(f"/rooms/{marked['id']}/results").json()

    assert [question["correct"] for question in body["questions"]] == [0, 1, 2]


def test_a_partial_paper_reads_as_unanswered_not_wrong(client, marked):
    """The question nobody answered has no answer row, and is not counted wrong.

    A blank scoring zero and a wrong answer scoring zero look the same on a
    total. They are not the same thing to a teacher, and the difference has to
    survive as far as the screen.
    """
    body = client.get(f"/rooms/{marked['id']}/results").json()
    student = body["students"][0]

    assert student["submitted"] is True
    assert [answer["question_id"] for answer in student["answers"]] == [1, 2]

    # One right, one wrong, one never reached.
    assert student["score"] == 1

    third = next(q for q in body["questions"] if q["id"] == 3)
    assert third["answered"] == 0
    assert third["right"] == 0


def test_a_student_with_no_name_is_numbered_by_join_order(client, room, signed_in_as):
    """Clerk allows an account with no name. That is normal, not an error."""
    signed_in_as(OTHER_USER_ID)
    client.post("/rooms/join", json={"code": room["code"]})

    signed_in_as(TEST_USER_ID)
    body = client.get(f"/rooms/{room['id']}/results").json()

    assert body["students"][0]["name"] == "Student 1"


def test_a_name_is_stored_and_shown(client, marked):
    """And a student who has one is called it."""
    body = client.get(f"/rooms/{marked['id']}/results").json()

    assert body["students"][0]["name"] == "Amina"


def test_a_very_long_name_is_capped(client, room, signed_in_as):
    """Nothing stops a browser sending a megabyte in that field.

    The cap is about a table staying readable rather than about safety — the
    name is only ever displayed — but a screen with one row a mile wide is a
    broken screen.
    """
    signed_in_as(OTHER_USER_ID)
    client.post("/rooms/join", json={"code": room["code"], "name": "A" * 500})

    signed_in_as(TEST_USER_ID)
    body = client.get(f"/rooms/{room['id']}/results").json()

    assert len(body["students"][0]["name"]) == 60


def test_the_first_join_wins_the_name(client, room, signed_in_as):
    """Coming back after a phone locked does not rename anybody.

    The same INSERT OR IGNORE that stops a refresh becoming a second student.
    """
    signed_in_as(OTHER_USER_ID)
    client.post("/rooms/join", json={"code": room["code"], "name": "Amina"})
    client.post("/rooms/join", json={"code": room["code"], "name": "Someone Else"})

    signed_in_as(TEST_USER_ID)
    body = client.get(f"/rooms/{room['id']}/results").json()

    assert len(body["students"]) == 1
    assert body["students"][0]["name"] == "Amina"


# ---------------------------------------------------------------------------
# The flag
# ---------------------------------------------------------------------------


def _class_of(client, signed_in_as, room, chosen_by_student):
    """Put several students through one class, each answering question 1.

    ``chosen_by_student`` is one `chosen` per student, so a test can say "three
    answered and one of them was right" in a line.
    """
    # Everybody joins first, because a room only takes answers once it is open
    # and latecomers would otherwise be answering a class they are not in.
    for n in range(len(chosen_by_student)):
        signed_in_as(f"user_test_student_{n}")
        client.post("/rooms/join", json={"code": room["code"], "name": f"Student {n}"})

    signed_in_as(TEST_USER_ID)
    client.post(f"/rooms/{room['id']}/state", json={"state": "open"})

    for n, chosen in enumerate(chosen_by_student):
        signed_in_as(f"user_test_student_{n}")
        client.post(
            f"/rooms/{room['id']}/answers",
            json={"answers": [{"question_id": 1, "chosen": chosen}]},
        )

    signed_in_as(TEST_USER_ID)
    body = client.get(f"/rooms/{room['id']}/results").json()

    return next(q for q in body["questions"] if q["id"] == 1)


def test_the_flag_fires_when_most_of_the_class_got_it_wrong(client, room, signed_in_as):
    """Three answered, one right. Fewer than half, and enough of them to mean it."""
    # Question 1's answer is 0. Two of these are wrong.
    question = _class_of(client, signed_in_as, room, [0, 1, 2])

    assert question["answered"] == 3
    assert question["right"] == 1
    assert question["flagged"] is True


def test_the_flag_does_not_fire_on_two_answers(client, room, signed_in_as):
    """Half of two is a coin flip, and a flag that fires on noise gets ignored."""
    question = _class_of(client, signed_in_as, room, [1, 2])

    assert question["answered"] == 2
    assert question["right"] == 0
    assert question["flagged"] is False


def test_exactly_half_right_is_not_flagged(client, room, signed_in_as):
    """The rule is *fewer* than half, so a straight split is not a bad question."""
    question = _class_of(client, signed_in_as, room, [0, 0, 1, 2])

    assert question["answered"] == 4
    assert question["right"] == 2
    assert question["flagged"] is False


# ---------------------------------------------------------------------------
# PATCH /rooms/{id}/answers/{aid}
# ---------------------------------------------------------------------------


def _first_answer(client, room_id):
    body = client.get(f"/rooms/{room_id}/results").json()

    return body["students"][0]["answers"][0]


def test_an_override_changes_the_mark_and_nothing_else(client, marked):
    """The teacher overrules the judgement, not what the student picked.

    **The rule this slice would break most quietly.** A screen that silently
    rewrote `chosen` would look completely normal, and the room would lose its
    record of what actually happened in it — so this asserts on `chosen` as
    hard as it asserts on `mark`.
    """
    answer = _first_answer(client, marked["id"])
    assert answer["mark"] == 1
    assert answer["chosen"] == 0

    response = client.patch(f"/rooms/{marked['id']}/answers/{answer['id']}", json={"mark": 0})

    assert response.status_code == 200
    assert response.json()["mark"] == 0
    assert response.json()["chosen"] == 0
    assert response.json()["overridden"] is True

    # And it is actually stored, not just returned.
    assert _first_answer(client, marked["id"])["mark"] == 0


def test_the_score_follows_an_override(client, marked):
    """`score` is summed from the stored marks, so it moves the moment one does."""
    answer = _first_answer(client, marked["id"])
    client.patch(f"/rooms/{marked['id']}/answers/{answer['id']}", json={"mark": 0})

    body = client.get(f"/rooms/{marked['id']}/results").json()

    assert body["students"][0]["score"] == 0


def test_marking_it_back_clears_overridden(client, marked):
    """`overridden` is derived, so undo is just marking it back.

    If it were a stored flag this would stay true forever, and the screen would
    keep saying a teacher had changed something they had changed back.
    """
    answer = _first_answer(client, marked["id"])
    client.patch(f"/rooms/{marked['id']}/answers/{answer['id']}", json={"mark": 0})
    response = client.patch(f"/rooms/{marked['id']}/answers/{answer['id']}", json={"mark": 1})

    assert response.json()["overridden"] is False


def test_a_mark_that_is_not_zero_or_one_is_refused(client, marked):
    """`mark` is summed into a score, so a 2 would quietly make a total wrong."""
    answer = _first_answer(client, marked["id"])

    response = client.patch(f"/rooms/{marked['id']}/answers/{answer['id']}", json={"mark": 2})

    assert response.status_code == 400
    assert _first_answer(client, marked["id"])["mark"] == 1


def test_only_the_owner_can_change_a_mark(client, marked, signed_in_as):
    """The student whose answer it is cannot mark their own paper."""
    answer = _first_answer(client, marked["id"])

    signed_in_as(OTHER_USER_ID)
    response = client.patch(f"/rooms/{marked['id']}/answers/{answer['id']}", json={"mark": 0})

    assert response.status_code == 404

    signed_in_as(TEST_USER_ID)
    assert _first_answer(client, marked["id"])["mark"] == 1


def test_an_answer_from_another_room_is_a_404(client, marked, signed_in_as):
    """The answer id is real and yours; the room in the URL is not the one it is in.

    The ownership test lives inside the UPDATE, so this is refused by the same
    statement that would have done the work — there is no window between
    checking and writing for anything to change.
    """
    answer = _first_answer(client, marked["id"])
    other = client.post("/rooms", json={"quiz_id": 1}).json()

    response = client.patch(f"/rooms/{other['id']}/answers/{answer['id']}", json={"mark": 0})

    assert response.status_code == 404
    assert _first_answer(client, marked["id"])["mark"] == 1


def test_an_answer_that_does_not_exist_is_a_404(client, marked):
    response = client.patch(f"/rooms/{marked['id']}/answers/9999", json={"mark": 0})

    assert response.status_code == 404
