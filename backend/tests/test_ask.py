"""Tests for POST /ask — Slice 4.

Every test mocks the Groq API call so tests run without a real key and
without hitting the network. The search_chunks function is also mocked so
these tests do not depend on Slices 2/3 being merged.
"""

import sys
import types

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    """Point the database at a fresh temporary file for every single test."""
    db_file = str(tmp_path / "test_nibble.db")
    monkeypatch.setattr("app.config.DATABASE_FILE", db_file)

    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr("app.routes._UPLOADS_DIR", uploads_dir)


@pytest.fixture(autouse=True)
def _fake_embeddings_module(monkeypatch):
    """Inject a fake app.embeddings module so the late import in routes works.

    Your friend's Slices 2/3 will provide the real module. For testing Slice 4
    in isolation we create a stand-in that returns whatever _FAKE_CHUNKS holds.
    """
    fake_mod = types.ModuleType("app.embeddings")
    fake_mod.search_chunks = lambda _query, **_kw: list(_FAKE_CHUNKS)
    monkeypatch.setitem(sys.modules, "app.embeddings", fake_mod)


@pytest.fixture()
def client():
    """A fresh test client that uses the patched config."""
    from app.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

# A fake set of search results, as search_chunks would return.
_FAKE_CHUNKS = [
    {
        "document_id": 1,
        "filename": "biology-ch4.pdf",
        "page": 4,
        "content": (
            "Osmosis is the net movement of water molecules through a "
            "selectively permeable membrane from a region of lower solute "
            "concentration to a region of higher solute concentration."
        ),
        "score": 0.87,
    },
    {
        "document_id": 1,
        "filename": "biology-ch4.pdf",
        "page": 5,
        "content": (
            "This process does not require energy and is driven by the "
            "difference in concentration across the membrane."
        ),
        "score": 0.74,
    },
]

# A fake Groq API response shaped like OpenAI's chat completions response.
_FAKE_GROQ_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": (
                    "Water moves across a membrane toward the side "
                    "with more solute (p. 4). This process does not "
                    "require energy (p. 5)."
                )
            }
        }
    ]
}


def _mock_groq_post(monkeypatch, response_json=None, raise_exc=None):
    """Replace requests.post so it returns a fake Groq response."""
    if response_json is None:
        response_json = _FAKE_GROQ_RESPONSE

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return response_json

    def fake_post(*_args, **_kwargs):
        if raise_exc:
            raise raise_exc
        return FakeResponse()

    monkeypatch.setattr("requests.post", fake_post)


def _set_search_returns(monkeypatch, results):
    """Override what the fake app.embeddings.search_chunks returns."""
    fake_mod = sys.modules["app.embeddings"]
    monkeypatch.setattr(fake_mod, "search_chunks", lambda _query, **_kw: list(results))


# ---------------------------------------------------------------------------
# POST /ask — happy path
# ---------------------------------------------------------------------------


def test_ask_returns_answer_and_sources(client, monkeypatch):
    """A valid question returns an answer with sources."""
    monkeypatch.setattr("app.config.GROQ_API_KEY", "fake-key-for-testing")
    _mock_groq_post(monkeypatch)

    response = client.post("/ask", json={"question": "explain osmosis simply"})

    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert "sources" in body
    assert isinstance(body["sources"], list)
    assert len(body["sources"]) == 2
    assert body["sources"][0]["filename"] == "biology-ch4.pdf"
    assert body["sources"][0]["page"] == 4
    assert "document_id" in body["sources"][0]
    assert "excerpt" in body["sources"][0]


def test_ask_answer_contains_text(client, monkeypatch):
    """The answer should contain the model's generated text."""
    monkeypatch.setattr("app.config.GROQ_API_KEY", "fake-key-for-testing")
    _mock_groq_post(monkeypatch)

    response = client.post("/ask", json={"question": "how does osmosis work"})

    body = response.json()
    assert "Water moves" in body["answer"]


# ---------------------------------------------------------------------------
# POST /ask — no documents / empty results
# ---------------------------------------------------------------------------


def test_ask_no_documents_returns_answer_with_empty_sources(client, monkeypatch):
    """When no chunks are found, the model still gets called but sources is empty."""
    monkeypatch.setattr("app.config.GROQ_API_KEY", "fake-key-for-testing")
    _set_search_returns(monkeypatch, [])

    no_info_response = {
        "choices": [
            {
                "message": {
                    "content": "I don't have enough information in your notes to answer that."
                }
            }
        ]
    }
    _mock_groq_post(monkeypatch, response_json=no_info_response)

    response = client.post("/ask", json={"question": "what is quantum physics"})

    assert response.status_code == 200
    body = response.json()
    assert body["sources"] == []
    assert "don't have enough" in body["answer"]


# ---------------------------------------------------------------------------
# POST /ask — missing API key
# ---------------------------------------------------------------------------


def test_ask_missing_api_key_returns_503(client, monkeypatch):
    """Without a GROQ_API_KEY, the endpoint returns 503."""
    monkeypatch.setattr("app.config.GROQ_API_KEY", "")

    response = client.post("/ask", json={"question": "explain osmosis"})

    assert response.status_code == 503
    assert "GROQ_API_KEY" in response.json()["detail"]


# ---------------------------------------------------------------------------
# POST /ask — validation
# ---------------------------------------------------------------------------


def test_ask_empty_question_returns_400(client, monkeypatch):
    """An empty question should be rejected."""
    monkeypatch.setattr("app.config.GROQ_API_KEY", "fake-key-for-testing")

    response = client.post("/ask", json={"question": "   "})

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_ask_missing_question_returns_422(client):
    """A request body without a 'question' field should be rejected."""
    response = client.post("/ask", json={})

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /ask — Groq API failure
# ---------------------------------------------------------------------------


def test_ask_groq_failure_returns_503(client, monkeypatch):
    """When the Groq API call fails, return 503 with the error message."""
    import requests

    monkeypatch.setattr("app.config.GROQ_API_KEY", "fake-key-for-testing")
    _mock_groq_post(
        monkeypatch,
        raise_exc=requests.ConnectionError("Network unreachable"),
    )

    response = client.post("/ask", json={"question": "explain osmosis"})

    assert response.status_code == 503
    assert "failed" in response.json()["detail"].lower()
