"""Tests for the eight classroom routes.

The model is faked, the same way test_quiz_routes.py fakes it — nothing here is
about writing questions, it is about who is allowed to do what once they exist.

Four of these matter more than the rest, and they are the four named in
docs/scope.md before this slice was built:

  * a student never receives the answer key
  * nobody answers before Start or after End
  * nobody answers a room they did not join
  * a room that is not yours is a 404

The first one is the one that needs a test most, because its failure is
invisible: an answer key in a JSON response looks completely normal on screen
and hands the class the answers.
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
    """A room in `waiting`, owned by the default test user, around a 3-question quiz.

    Returned as the room body from POST /rooms, so a test can reach for
    ``room["code"]`` or ``room["id"]`` without repeating the setup.
    """
    client.post(
        "/documents",
        files={"file": ("biology.txt", b"Osmosis moves water. " * 20, "text/plain")},
    )
    quiz = client.post("/quizzes", json={"document_id": 1, "title": "Cells", "count": 3}).json()

    return client.post("/rooms", json={"quiz_id": quiz["id"]}).json()


def _start(client, room_id):
    return client.post(f"/rooms/{room_id}/state", json={"state": "open"})


def _end(client, room_id):
    return client.post(f"/rooms/{room_id}/state", json={"state": "closed"})


def _join(client, code):
    return client.post("/rooms/join", json={"code": code})


def _paper(client, room_id, chosen=(0, 1, 2)):
    return client.post(
        f"/rooms/{room_id}/answers",
        json={"answers": [{"question_id": n + 1, "chosen": c} for n, c in enumerate(chosen)]},
    )


# ---------------------------------------------------------------------------
# Opening a room
# ---------------------------------------------------------------------------


def test_a_new_room_matches_the_contract(room):
    assert room["state"] == "waiting"
    assert room["member_count"] == 0
    assert room["question_count"] == 3
    assert room["title"] == "Cells"
    assert len(room["code"]) == 6


def test_a_code_avoids_the_characters_people_mistype(client, room):
    """No O, 0, I or 1 — the code is read off a projector and typed by thirty people."""
    assert not set(room["code"]) & set("O0I1")
    assert room["code"] == room["code"].upper()


def test_two_rooms_do_not_share_a_code(client, room):
    second = client.post("/rooms", json={"quiz_id": 1}).json()

    assert second["code"] != room["code"]


def test_a_quiz_that_is_not_yours_cannot_be_run(client, room, signed_in_as):
    """Otherwise anybody could run somebody else's quiz and read it back out."""
    signed_in_as(OTHER_USER_ID)

    response = client.post("/rooms", json={"quiz_id": 1})

    assert response.status_code == 404


def test_a_quiz_that_does_not_exist_is_404(client):
    assert client.post("/rooms", json={"quiz_id": 999}).status_code == 404


def test_the_list_only_shows_rooms_you_run(client, room, signed_in_as):
    assert len(client.get("/rooms").json()) == 1

    signed_in_as(OTHER_USER_ID)
    assert client.get("/rooms").json() == []


def test_a_room_that_is_not_yours_is_404(client, room, signed_in_as):
    """The rule named in scope.md. Not-yours and not-found are the same answer."""
    signed_in_as(OTHER_USER_ID)

    assert client.get(f"/rooms/{room['id']}").status_code == 404
    assert _start(client, room["id"]).status_code == 404
    assert client.delete(f"/rooms/{room['id']}").status_code == 404


# ---------------------------------------------------------------------------
# The three states
# ---------------------------------------------------------------------------


def test_a_room_starts_and_ends(client, room):
    assert _start(client, room["id"]).json()["state"] == "open"
    assert _end(client, room["id"]).json()["state"] == "closed"


def test_asking_for_the_state_it_is_already_in_changes_nothing(client, room):
    """A double-tap on Start in front of a class is not an error."""
    _start(client, room["id"])

    again = _start(client, room["id"])

    assert again.status_code == 200
    assert again.json()["state"] == "open"


def test_a_closed_room_cannot_be_reopened(client, room):
    """Reopening would let a second paper land against a class that is over."""
    _start(client, room["id"])
    _end(client, room["id"])

    response = _start(client, room["id"])

    assert response.status_code == 400
    assert "reopened" in response.json()["detail"]
    assert client.get(f"/rooms/{room['id']}").json()["state"] == "closed"


def test_an_open_room_cannot_go_back_to_waiting(client, room):
    _start(client, room["id"])

    assert client.post(f"/rooms/{room['id']}/state", json={"state": "waiting"}).status_code == 400


def test_a_state_that_is_not_a_state_is_400(client, room):
    assert client.post(f"/rooms/{room['id']}/state", json={"state": "paused"}).status_code == 400


# ---------------------------------------------------------------------------
# Joining
# ---------------------------------------------------------------------------


def test_a_student_joins_with_the_code(client, room, signed_in_as):
    signed_in_as(OTHER_USER_ID)

    response = _join(client, room["code"])

    assert response.status_code == 200
    assert response.json()["title"] == "Cells"
    assert response.json()["state"] == "waiting"


def test_the_code_is_forgiving_about_case_and_spaces(client, room, signed_in_as):
    """It is typed off a projector by somebody in a hurry."""
    signed_in_as(OTHER_USER_ID)

    response = _join(client, f"  {room['code'].lower()}  ")

    assert response.status_code == 200
    assert response.json()["code"] == room["code"]


def test_joining_twice_is_still_one_student(client, room, signed_in_as):
    """The teacher is watching that count while deciding whether to start."""
    signed_in_as(OTHER_USER_ID)
    _join(client, room["code"])
    _join(client, room["code"])

    signed_in_as(TEST_USER_ID)
    assert client.get(f"/rooms/{room['id']}").json()["member_count"] == 1


def test_a_latecomer_can_still_join_an_open_room(client, room, signed_in_as):
    _start(client, room["id"])
    signed_in_as(OTHER_USER_ID)

    assert _join(client, room["code"]).status_code == 200


def test_a_closed_room_cannot_be_joined(client, room, signed_in_as):
    _end(client, room["id"])
    signed_in_as(OTHER_USER_ID)

    response = _join(client, room["code"])

    assert response.status_code == 400
    assert "ended" in response.json()["detail"]


def test_a_code_nobody_has_is_404(client, room, signed_in_as):
    signed_in_as(OTHER_USER_ID)

    assert _join(client, "ZZZZZZ").status_code == 404


def test_an_empty_code_is_400(client, room, signed_in_as):
    signed_in_as(OTHER_USER_ID)

    assert _join(client, "   ").status_code == 400


# ---------------------------------------------------------------------------
# The student's poll — and the answer key that must never be in it
# ---------------------------------------------------------------------------


def test_a_student_never_receives_the_answer_key(client, room, signed_in_as):
    """The rule whose failure is invisible.

    Asserted on the KEYS of the response rather than on a value, because the way
    this breaks is a field arriving that nobody meant to send — a `dict(row)` or
    a `SELECT *` somebody wrote in a hurry. Checking `correct != 1` would not
    catch that; checking that no question has a `correct` at all does.

    `page` is checked the same way and for a smaller reason: it is a page of the
    teacher's note, which the student does not have and cannot check.
    """
    signed_in_as(OTHER_USER_ID)
    _join(client, room["code"])

    signed_in_as(TEST_USER_ID)
    _start(client, room["id"])

    signed_in_as(OTHER_USER_ID)
    body = client.get(f"/rooms/code/{room['code']}").json()

    assert len(body["questions"]) == 3
    for question in body["questions"]:
        assert set(question) == {"id", "position", "prompt", "options"}

    assert "correct" not in client.get(f"/rooms/code/{room['code']}").text


def test_no_questions_are_handed_out_before_the_teacher_starts(client, room, signed_in_as):
    signed_in_as(OTHER_USER_ID)
    _join(client, room["code"])

    body = client.get(f"/rooms/code/{room['code']}").json()

    assert body["state"] == "waiting"
    assert body["questions"] == []


def test_no_questions_come_back_once_the_class_has_ended(client, room, signed_in_as):
    signed_in_as(OTHER_USER_ID)
    _join(client, room["code"])

    signed_in_as(TEST_USER_ID)
    _start(client, room["id"])
    _end(client, room["id"])

    signed_in_as(OTHER_USER_ID)
    body = client.get(f"/rooms/code/{room['code']}").json()

    assert body["state"] == "closed"
    assert body["questions"] == []


def test_polling_a_room_you_did_not_join_is_404(client, room, signed_in_as):
    signed_in_as(OTHER_USER_ID)

    assert client.get(f"/rooms/code/{room['code']}").status_code == 404


def test_submitted_is_what_stops_a_refresh_offering_the_quiz_twice(client, room, signed_in_as):
    signed_in_as(OTHER_USER_ID)
    _join(client, room["code"])

    signed_in_as(TEST_USER_ID)
    _start(client, room["id"])

    signed_in_as(OTHER_USER_ID)
    assert client.get(f"/rooms/code/{room['code']}").json()["submitted"] is False

    _paper(client, room["id"])

    assert client.get(f"/rooms/code/{room['code']}").json()["submitted"] is True


# ---------------------------------------------------------------------------
# Handing the paper in
# ---------------------------------------------------------------------------


@pytest.fixture()
def sat(client, room, signed_in_as):
    """A second person, joined to the room, with the room open. Returns the room."""
    signed_in_as(OTHER_USER_ID)
    _join(client, room["code"])

    signed_in_as(TEST_USER_ID)
    _start(client, room["id"])

    signed_in_as(OTHER_USER_ID)
    return room


def test_a_paper_is_accepted_and_no_score_comes_back(client, sat):
    """The teacher can change a mark in slice 8, so a number now would later move."""
    response = _paper(client, sat["id"])

    assert response.status_code == 200
    assert response.json() == {"submitted": True, "answered": 3}


def test_the_mark_is_written_at_submit_time(client, sat, tmp_path):
    """Stored, not derived — see the comment over answers.mark in db.py.

    The key from the fake writer is 0, 1, 2, so this paper gets two right and
    one wrong.
    """
    import sqlite3

    _paper(client, sat["id"], chosen=(0, 1, 3))

    db = sqlite3.connect(str(tmp_path / "test_nibble.db"))
    marks = [row[0] for row in db.execute("SELECT mark FROM answers ORDER BY question_id")]
    db.close()

    assert marks == [1, 1, 0]


def test_a_partial_paper_is_accepted(client, sat):
    """Somebody who ran out of time answered three of five, not nothing."""
    response = client.post(
        f"/rooms/{sat['id']}/answers",
        json={"answers": [{"question_id": 1, "chosen": 0}]},
    )

    assert response.status_code == 200
    assert response.json()["answered"] == 1


def test_nobody_answers_before_the_teacher_starts(client, room, signed_in_as):
    """One of the four rules named in scope.md."""
    signed_in_as(OTHER_USER_ID)
    _join(client, room["code"])

    response = _paper(client, room["id"])

    assert response.status_code == 400
    assert "started" in response.json()["detail"]


def test_nobody_answers_after_the_teacher_ends(client, sat, signed_in_as):
    """The other half of the same rule."""
    signed_in_as(TEST_USER_ID)
    _end(client, sat["id"])

    signed_in_as(OTHER_USER_ID)
    response = _paper(client, sat["id"])

    assert response.status_code == 400
    assert "ended" in response.json()["detail"]


def test_nobody_answers_a_room_they_did_not_join(client, room, signed_in_as):
    """The third rule. A 404, not a 403 — being told you are not in a class
    confirms the class exists."""
    _start(client, room["id"])
    signed_in_as(OTHER_USER_ID)

    response = _paper(client, room["id"])

    assert response.status_code == 404


def test_a_paper_can_only_be_handed_in_once(client, sat):
    _paper(client, sat["id"])

    response = _paper(client, sat["id"])

    assert response.status_code == 400
    assert "already" in response.json()["detail"]


def test_a_refused_second_paper_does_not_change_the_first(client, sat, tmp_path):
    import sqlite3

    _paper(client, sat["id"], chosen=(0, 1, 2))
    _paper(client, sat["id"], chosen=(3, 3, 3))

    db = sqlite3.connect(str(tmp_path / "test_nibble.db"))
    chosen = [row[0] for row in db.execute("SELECT chosen FROM answers ORDER BY question_id")]
    db.close()

    assert chosen == [0, 1, 2]


def test_an_empty_paper_is_400(client, sat):
    assert client.post(f"/rooms/{sat['id']}/answers", json={"answers": []}).status_code == 400


def test_a_question_from_another_quiz_is_refused(client, sat, signed_in_as):
    """The room's quiz is the only source of question ids this route will take."""
    signed_in_as(TEST_USER_ID)
    other = client.post("/quizzes", json={"document_id": 1, "title": "Other", "count": 3}).json()

    signed_in_as(OTHER_USER_ID)
    response = client.post(
        f"/rooms/{sat['id']}/answers",
        json={"answers": [{"question_id": other["questions"][0]["id"], "chosen": 0}]},
    )

    assert response.status_code == 400


@pytest.mark.parametrize("chosen", [-1, 4])
def test_an_option_that_is_not_on_the_paper_is_refused(client, sat, chosen):
    response = client.post(
        f"/rooms/{sat['id']}/answers",
        json={"answers": [{"question_id": 1, "chosen": chosen}]},
    )

    assert response.status_code == 400


def test_the_same_question_answered_twice_is_refused(client, sat, tmp_path):
    """Caught here rather than by the UNIQUE in db.py, which would be a 500 and
    half a paper already stored."""
    import sqlite3

    response = client.post(
        f"/rooms/{sat['id']}/answers",
        json={
            "answers": [
                {"question_id": 1, "chosen": 0},
                {"question_id": 1, "chosen": 2},
            ]
        },
    )

    assert response.status_code == 400

    db = sqlite3.connect(str(tmp_path / "test_nibble.db"))
    assert db.execute("SELECT COUNT(*) FROM answers").fetchone()[0] == 0
    db.close()


# ---------------------------------------------------------------------------
# Deleting, and what cascades with it
# ---------------------------------------------------------------------------


def test_deleting_a_room_takes_its_members_and_answers(client, sat, signed_in_as, tmp_path):
    import sqlite3

    _paper(client, sat["id"])

    signed_in_as(TEST_USER_ID)
    assert client.delete(f"/rooms/{sat['id']}").status_code == 204

    db = sqlite3.connect(str(tmp_path / "test_nibble.db"))
    assert db.execute("SELECT COUNT(*) FROM answers").fetchone()[0] == 0
    assert db.execute("SELECT COUNT(*) FROM room_members").fetchone()[0] == 0
    db.close()


def test_deleting_the_quiz_takes_the_rooms_made_from_it(client, room):
    """Worth knowing before somebody tidies up the morning of a lesson."""
    assert client.delete("/quizzes/1").status_code == 204

    assert client.get("/rooms").json() == []


def test_deleting_the_note_takes_the_rooms_too(client, room):
    """Two cascades deep: note to quiz to room."""
    assert client.delete("/documents/1").status_code == 204

    assert client.get("/rooms").json() == []


# ---------------------------------------------------------------------------
# The four windows between a check and the write that follows it
# ---------------------------------------------------------------------------
#
# Every route here reads before it writes, and the read is not inside the write.
# Something else can commit in the gap. None of these can be provoked by timing
# a real request — the window is a millisecond wide — so each test forces the
# interleaving instead, by making the second look at the world return what it
# would have returned had the race actually happened.
#
# What that does and does not prove: it proves the handling is right and, for
# two of them, that the rollback really does undo the write. It does not prove
# the window is as narrow as the comments in routes.py say. Nothing in a test
# suite can.


def _count(tmp_path, table):
    import sqlite3

    db = sqlite3.connect(str(tmp_path / "test_nibble.db"))
    total = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    db.close()
    return total


def test_a_paper_handed_in_as_the_class_ends_is_not_stored(client, sat, monkeypatch, tmp_path):
    """The teacher presses End between the state check and the insert.

    The paper must not survive it, or a class that has finished collects one
    more submission and the teacher marks something that arrived too late.
    """
    monkeypatch.setattr("app.routes._state_now", lambda db, room_id: "closed")

    response = _paper(client, sat["id"])

    assert response.status_code == 400
    assert "ended" in response.json()["detail"]
    # The rollback is the half worth asserting: the INSERT had already run.
    assert _count(tmp_path, "answers") == 0


def test_a_second_paper_racing_the_first_is_a_sentence_not_a_500(
    client, sat, monkeypatch, tmp_path
):
    """Two submissions at once both get past the friendly check.

    The UNIQUE in db.py refuses the second. Uncaught that is a 500 and an
    "Internal Server Error" on the one action a student cares about.
    """
    _paper(client, sat["id"])

    # What the second request would have seen: no paper in yet, because the
    # first had not committed when it looked.
    monkeypatch.setattr("app.routes._has_handed_in", lambda db, room_id, user_id: False)

    response = _paper(client, sat["id"])

    assert response.status_code == 400
    assert "already" in response.json()["detail"]
    # The first paper is untouched — three answers, not six and not none.
    assert _count(tmp_path, "answers") == 3


def test_joining_as_the_class_ends_leaves_no_member(
    client, room, monkeypatch, signed_in_as, tmp_path
):
    """The teacher presses End between the state check and the member insert.

    Left alone this puts a student in a class that is over, and the teacher's
    joiner count goes up after the class has finished.
    """
    monkeypatch.setattr("app.routes._state_now", lambda db, room_id: "closed")
    signed_in_as(OTHER_USER_ID)

    response = _join(client, room["code"])

    assert response.status_code == 400
    assert "ended" in response.json()["detail"]
    assert _count(tmp_path, "room_members") == 0


def test_two_classes_opened_on_the_same_code_is_a_sentence_not_a_500(client, room, monkeypatch):
    """Two rooms are told the same code is free before either takes it.

    It needs two of a billion inside a one-millisecond window, so it will very
    likely never happen. What it must not do is hand a teacher a traceback.
    """
    monkeypatch.setattr("app.routes._new_code", lambda db: room["code"])

    response = client.post("/rooms", json={"quiz_id": 1})

    assert response.status_code == 503
    assert "try again" in response.json()["detail"].lower()


def test_the_quiz_being_deleted_as_the_class_opens_is_a_404(client, room, monkeypatch):
    """The other thing that can break that same INSERT, told apart from it.

    A quiz deleted from another tab between the ownership check and the insert
    trips the foreign key, which raises the same error a duplicate code does.
    They are told apart by asking the database again — never by reading
    SQLite's message text, which is not ours and can be reworded.
    """

    def delete_it_first(db):
        db.execute("DELETE FROM quizzes WHERE id = 1")
        db.commit()
        return "ZZZZ99"

    monkeypatch.setattr("app.routes._new_code", delete_it_first)

    response = client.post("/rooms", json={"quiz_id": 1})

    assert response.status_code == 404
    assert "deleted" in response.json()["detail"]
