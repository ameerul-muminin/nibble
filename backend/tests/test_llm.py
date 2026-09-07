"""Tests for llm.py — building the prompt, and every way asking can fail.

**Nothing here calls Groq.** A test that made a real network call would be slow,
would need a key to run, would fail on CI where there is none, and would be
testing Groq rather than testing us. `requests.post` is swapped for a fake, and
what is checked is what we send and what we do with what comes back.

The one thing these tests deliberately do NOT check is whether the model obeys
the prompt. That is not something a test can assert — it is a claim about a
model's behaviour, not about our code, and the only honest way to check it is
the one written into issue #15: ask a question the notes answer, then one they
do not, and watch the second get refused. See docs/scope.md.
"""

import pytest
import requests

from app import config, llm


class _FakeResponse:
    """Just enough of a requests.Response for llm.answer to read."""

    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.text = text
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("no JSON in this response")
        return self._payload


def _reply(content: str) -> _FakeResponse:
    """A successful Groq reply carrying one message."""
    return _FakeResponse(payload={"choices": [{"message": {"content": content}}]})


@pytest.fixture(autouse=True)
def _a_key_exists(monkeypatch):
    """Every test but one wants to get past the missing-key check."""
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key-not-a-real-one")


def _capture(monkeypatch, response=None):
    """Swap requests.post for a fake, and hand back what it was called with."""
    sent = {}

    def fake_post(url, **kwargs):
        sent["url"] = url
        sent.update(kwargs)
        return response if response is not None else _reply("An answer.")

    monkeypatch.setattr(llm.requests, "post", fake_post)
    return sent


# ---------------------------------------------------------------------------
# build_context — the only reason the model can cite a page
# ---------------------------------------------------------------------------


def test_build_context_labels_every_piece_with_its_file_and_page():
    context = llm.build_context(
        [
            {"filename": "biology.pdf", "page": 4, "content": "Osmosis moves water."},
            {"filename": "biology.pdf", "page": 5, "content": "The membrane is selective."},
        ]
    )

    assert "[biology.pdf - p.4]" in context
    assert "[biology.pdf - p.5]" in context
    assert "Osmosis moves water." in context


def test_build_context_separates_pieces_with_a_blank_line():
    """Run two pages together and a model writes one sentence spanning both."""
    context = llm.build_context(
        [
            {"filename": "a.pdf", "page": 1, "content": "First."},
            {"filename": "a.pdf", "page": 2, "content": "Second."},
        ]
    )

    assert "First.\n\n[a.pdf - p.2]" in context


def test_build_context_of_nothing_is_empty():
    """The route never calls it with an empty list — it short-circuits first."""
    assert llm.build_context([]) == ""


# ---------------------------------------------------------------------------
# What we actually send
# ---------------------------------------------------------------------------


def test_the_system_prompt_and_the_notes_both_go_to_the_model(monkeypatch):
    sent = _capture(monkeypatch)

    llm.answer("what is osmosis", "[bio.pdf - p.4]\nOsmosis moves water.")

    messages = sent["json"]["messages"]
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == llm.SYSTEM_PROMPT
    assert "Osmosis moves water." in messages[1]["content"]


def test_the_question_comes_after_the_notes(monkeypatch):
    """A model weighs the last thing it read most. That should be the question."""
    sent = _capture(monkeypatch)

    llm.answer("what is osmosis", "[bio.pdf - p.4]\nOsmosis moves water.")

    user_message = sent["json"]["messages"][1]["content"]
    assert user_message.index("Osmosis moves water.") < user_message.index("what is osmosis")


def test_the_configured_model_and_key_are_used(monkeypatch):
    sent = _capture(monkeypatch)

    llm.answer("anything", "some notes")

    assert sent["json"]["model"] == config.CHAT_MODEL
    assert sent["headers"]["Authorization"] == "Bearer test-key-not-a-real-one"
    assert sent["url"].startswith(config.GROQ_BASE_URL)


def test_the_answer_length_is_capped_and_the_temperature_is_low(monkeypatch):
    sent = _capture(monkeypatch)

    llm.answer("anything", "some notes")

    assert sent["json"]["max_tokens"] == config.ANSWER_MAX_OUTPUT_TOKENS
    assert sent["json"]["temperature"] <= 0.3
    assert sent["timeout"] > 0


def test_the_answer_comes_back_stripped(monkeypatch):
    _capture(monkeypatch, _reply("  Water moves across the membrane (p. 4).\n\n"))

    assert llm.answer("q", "notes") == "Water moves across the membrane (p. 4)."


def test_a_refusal_is_an_ordinary_answer_not_an_error(monkeypatch):
    """The most important behaviour in the project travels home as a 200.

    A model saying it cannot answer is Nibble working. Nothing in this file may
    treat it as a failure — the route hands it straight to the frontend, which
    puts it in a bubble like any other answer.
    """
    _capture(monkeypatch, _reply("That isn't in your notes yet."))

    assert llm.answer("what is a black hole", "notes about osmosis") == (
        "That isn't in your notes yet."
    )


# ---------------------------------------------------------------------------
# Every way it can fail, and the sentence each one produces
# ---------------------------------------------------------------------------


def test_no_api_key_says_where_to_get_one(monkeypatch):
    """Somebody's first confusing failure, turned into an instruction."""
    monkeypatch.setattr(config, "GROQ_API_KEY", "")

    with pytest.raises(llm.AnswerUnavailable, match="GROQ_API_KEY"):
        llm.answer("q", "notes")


def test_no_key_means_no_request_is_made_at_all(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "")

    def explode(*args, **kwargs):
        raise AssertionError("asked Groq without a key")

    monkeypatch.setattr(llm.requests, "post", explode)

    with pytest.raises(llm.AnswerUnavailable):
        llm.answer("q", "notes")


def test_the_network_being_down_is_a_sentence_not_a_traceback(monkeypatch):
    def refuse(*args, **kwargs):
        raise requests.ConnectionError("nothing listening")

    monkeypatch.setattr(llm.requests, "post", refuse)

    with pytest.raises(llm.AnswerUnavailable, match="Could not reach"):
        llm.answer("q", "notes")


def test_being_asked_too_fast_says_to_try_again_in_a_moment(monkeypatch):
    _capture(monkeypatch, _FakeResponse(429, text="Rate limit reached for requests per minute"))

    with pytest.raises(llm.AnswerUnavailable, match="try again in a moment|Try again in a moment"):
        llm.answer("q", "notes")


def test_running_out_for_the_day_says_tomorrow_rather_than_a_moment(monkeypatch):
    """Waiting a moment does not help when the daily allowance is gone."""
    _capture(monkeypatch, _FakeResponse(429, text="Limit reached: 1000 requests per day (RPD)"))

    with pytest.raises(llm.AnswerUnavailable, match="tomorrow"):
        llm.answer("q", "notes")


def test_a_server_error_does_not_leak_the_providers_own_words(monkeypatch):
    """Their message is written for whoever is billed, and can carry internals."""
    _capture(monkeypatch, _FakeResponse(500, text="upstream connect error to 10.0.0.4:443"))

    with pytest.raises(llm.AnswerUnavailable) as raised:
        llm.answer("q", "notes")

    assert "500" in str(raised.value)
    assert "10.0.0.4" not in str(raised.value)


def test_a_reply_we_cannot_read_is_a_sentence(monkeypatch):
    _capture(monkeypatch, _FakeResponse(200, payload={"unexpected": "shape"}))

    with pytest.raises(llm.AnswerUnavailable, match="something unexpected"):
        llm.answer("q", "notes")


def test_an_empty_answer_is_a_failure_not_an_empty_bubble(monkeypatch):
    """A 200 carrying nothing would reach the screen as no answer and no error."""
    _capture(monkeypatch, _reply("   \n  "))

    with pytest.raises(llm.AnswerUnavailable, match="came back with nothing"):
        llm.answer("q", "notes")
