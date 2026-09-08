"""Tests for quiz.py — the prompt, and every way a reply can be unusable.

**Nothing here calls Groq**, for the reasons at the top of test_llm.py.

Most of this file is about the validator, and that weighting is deliberate.
``llm.answer`` produces a sentence a person reads and judges. A quiz is not read,
it is *used*: the browser marks answers against ``correct`` with nobody checking
it first. So a reply that is nearly right is worse here than one that fails
outright — a question with four options and ``correct: 4`` marks every answer
wrong, for one person practising or a whole class at once, and nothing on screen
looks broken.

Every rejection below is one of those.
"""

import json

import pytest
import requests

from app import config, quiz

PAGES = {1, 2, 3}


def _question(**overrides):
    """A valid question, with whatever is being tested swapped in."""
    question = {
        "prompt": "What moves water across a membrane?",
        "options": ["Osmosis", "Mitosis", "Respiration", "Diffusion"],
        "correct": 0,
        "page": 1,
    }
    question.update(overrides)
    return question


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.text = text
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no JSON in this response")
        return self._payload


def _reply(questions):
    """A successful Groq reply carrying these questions."""
    content = json.dumps({"questions": questions})
    return _FakeResponse(payload={"choices": [{"message": {"content": content}}]})


def _raw_reply(content: str):
    """A successful Groq reply carrying this exact string."""
    return _FakeResponse(payload={"choices": [{"message": {"content": content}}]})


@pytest.fixture(autouse=True)
def _a_key_exists(monkeypatch):
    """Most tests are not about the missing-key path, so give them a key."""
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")


def _capture(monkeypatch, response=None):
    sent = {}

    def fake_post(url, **kwargs):
        sent["url"] = url
        sent.update(kwargs)
        return response if response is not None else _reply([_question()])

    monkeypatch.setattr(quiz.requests, "post", fake_post)
    return sent


# ---------------------------------------------------------------------------
# build_prompt — the note, as much of it as fits
# ---------------------------------------------------------------------------


def test_build_prompt_reuses_the_same_page_labels_as_ask():
    """Those labels are why a question can name its page. One source, not two."""
    chunks = [{"filename": "bio.pdf", "page": 4, "content": "Osmosis is..."}]

    assert "[bio.pdf - p.4]" in quiz.build_prompt(chunks)


def test_build_prompt_stops_at_the_context_budget(monkeypatch):
    monkeypatch.setattr(config, "QUIZ_MAX_CONTEXT_CHARS", 100)
    chunks = [{"filename": "bio.pdf", "page": page, "content": "x" * 80} for page in range(1, 6)]

    built = quiz.build_prompt(chunks)

    assert "p.1" in built
    assert "p.5" not in built


def test_build_prompt_keeps_one_chunk_even_if_it_blows_the_budget(monkeypatch):
    """A note whose first piece is over budget should still make a quiz."""
    monkeypatch.setattr(config, "QUIZ_MAX_CONTEXT_CHARS", 10)
    chunks = [{"filename": "bio.pdf", "page": 1, "content": "x" * 900}]

    assert "p.1" in quiz.build_prompt(chunks)


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------


def test_valid_questions_come_back(monkeypatch):
    _capture(monkeypatch, _reply([_question(), _question(prompt="And another?")]))

    questions = quiz.make_questions("notes", 2, PAGES)

    assert len(questions) == 2
    assert questions[0]["prompt"] == "What moves water across a membrane?"
    assert questions[0]["correct"] == 0


def test_never_more_than_asked_for(monkeypatch):
    """A model that ignores the count must not produce a longer quiz."""
    _capture(monkeypatch, _reply([_question() for _ in range(9)]))

    assert len(quiz.make_questions("notes", 3, PAGES)) == 3


def test_fewer_than_asked_for_is_a_valid_result(monkeypatch):
    """A short note supports fewer questions. Better than invented ones."""
    _capture(monkeypatch, _reply([_question()]))

    assert len(quiz.make_questions("notes", 5, PAGES)) == 1


def test_a_bare_list_is_accepted(monkeypatch):
    """The obvious near-miss, and one line to accept."""
    content = json.dumps([_question()])
    _capture(monkeypatch, _raw_reply(content))

    assert len(quiz.make_questions("notes", 1, PAGES)) == 1


def test_the_configured_model_and_limits_are_used(monkeypatch):
    sent = _capture(monkeypatch)

    quiz.make_questions("notes", 5, PAGES)

    assert sent["json"]["model"] == config.CHAT_MODEL
    assert sent["json"]["max_tokens"] == config.QUIZ_MAX_OUTPUT_TOKENS
    assert sent["json"]["reasoning_effort"] == config.QUIZ_REASONING_EFFORT
    assert sent["json"]["response_format"] == {"type": "json_object"}


# ---------------------------------------------------------------------------
# The validator — a bad question is dropped, never repaired
# ---------------------------------------------------------------------------
#
# There is no sensible way to guess what a model meant by `correct: 7`, and a
# guess would put a wrong answer key in front of a class — worse than one fewer
# question, because nothing about it looks wrong.


@pytest.mark.parametrize(
    "bad, why",
    [
        ({"options": ["A", "B", "C"]}, "three options"),
        ({"options": ["A", "B", "C", "D", "E"]}, "five options"),
        ({"correct": 4}, "correct past the end — marks everything wrong"),
        ({"correct": -1}, "negative index"),
        ({"correct": "Osmosis"}, "the text instead of the position"),
        ({"correct": True}, "a bool, which is an int in Python"),
        ({"prompt": "   "}, "nothing actually asked"),
        ({"options": ["A", "", "C", "D"]}, "a blank option"),
        ({"options": ["A", "A", "C", "D"]}, "two identical options"),
        ({"page": 99}, "a page the note does not have"),
        ({"page": "4"}, "a page as a string"),
        ({"page": True}, "a page as a bool"),
    ],
)
def test_an_unusable_question_is_dropped(monkeypatch, bad, why):
    _capture(monkeypatch, _reply([_question(), _question(**bad)]))

    questions = quiz.make_questions("notes", 5, PAGES)

    assert len(questions) == 1, f"should have dropped the one with {why}"


def test_a_question_that_is_not_even_a_dict_is_dropped(monkeypatch):
    _capture(monkeypatch, _raw_reply(json.dumps({"questions": [_question(), "nonsense"]})))

    assert len(quiz.make_questions("notes", 5, PAGES)) == 1


def test_every_question_being_unusable_is_a_failure_not_an_empty_quiz(monkeypatch):
    """An empty quiz is a non-result that would sit in the list looking takeable."""
    _capture(monkeypatch, _reply([_question(correct=9), _question(page=99)]))

    with pytest.raises(quiz.QuizUnavailable, match="could not write questions"):
        quiz.make_questions("notes", 5, PAGES)


def test_a_reply_that_is_not_json_is_a_sentence(monkeypatch):
    _capture(monkeypatch, _raw_reply("Here are your questions!"))

    with pytest.raises(quiz.QuizUnavailable, match="usable questions"):
        quiz.make_questions("notes", 5, PAGES)


def test_json_of_the_wrong_shape_is_a_sentence(monkeypatch):
    _capture(monkeypatch, _raw_reply(json.dumps({"questions": "not a list"})))

    with pytest.raises(quiz.QuizUnavailable, match="usable questions"):
        quiz.make_questions("notes", 5, PAGES)


def test_options_are_stripped_not_just_accepted(monkeypatch):
    _capture(monkeypatch, _reply([_question(options=[" A ", "B", "C", "D"])]))

    assert quiz.make_questions("notes", 1, PAGES)[0]["options"][0] == "A"


# ---------------------------------------------------------------------------
# When something goes wrong, a person gets a sentence
# ---------------------------------------------------------------------------


def test_no_api_key_says_where_to_get_one(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "")

    with pytest.raises(quiz.QuizUnavailable, match="console.groq.com"):
        quiz.make_questions("notes", 5, PAGES)


def test_no_key_means_no_request_is_made_at_all(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "")

    def explode(*args, **kwargs):
        raise AssertionError("called Groq with no key")

    monkeypatch.setattr(quiz.requests, "post", explode)

    with pytest.raises(quiz.QuizUnavailable):
        quiz.make_questions("notes", 5, PAGES)


def test_the_network_being_down_is_a_sentence_not_a_traceback(monkeypatch):
    def boom(*args, **kwargs):
        raise requests.ConnectionError("no route to host")

    monkeypatch.setattr(quiz.requests, "post", boom)

    with pytest.raises(quiz.QuizUnavailable, match="Could not reach"):
        quiz.make_questions("notes", 5, PAGES)


def test_being_asked_too_fast_says_to_try_again_in_a_moment(monkeypatch):
    _capture(monkeypatch, _FakeResponse(status_code=429, text="rate limit"))

    with pytest.raises(quiz.QuizUnavailable, match="in a moment"):
        quiz.make_questions("notes", 5, PAGES)


def test_running_out_for_the_day_says_tomorrow(monkeypatch):
    _capture(monkeypatch, _FakeResponse(status_code=429, text="limit per day exceeded"))

    with pytest.raises(quiz.QuizUnavailable, match="tomorrow"):
        quiz.make_questions("notes", 5, PAGES)


def test_a_server_error_does_not_leak_the_providers_own_words(monkeypatch):
    _capture(monkeypatch, _FakeResponse(status_code=500, text="upstream billing failure"))

    with pytest.raises(quiz.QuizUnavailable) as caught:
        quiz.make_questions("notes", 5, PAGES)

    assert "billing" not in str(caught.value)
