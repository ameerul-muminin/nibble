"""Tests for reading pages that are pictures of writing.

The vision model itself is never called here. These tests replace it with a
stub, because a test that needs a network, an API key and somebody's free daily
allowance is a test that fails for reasons that have nothing to do with the code.

What is worth testing is everything around it: that a scan is recognised as a
scan, that a photo goes to the model at all, that a failure becomes a plain
sentence rather than a traceback, and that a typed PDF never touches it.
"""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app import config, ocr
from app.files import has_no_text
from tests.test_documents import _make_text_pdf


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr("app.config.DATABASE_FILE", str(tmp_path / "test_nibble.db"))
    monkeypatch.setattr("app.routes._UPLOADS_DIR", tmp_path / "uploads")
    monkeypatch.setattr("app.config.OCR_ENABLED", True)


@pytest.fixture()
def client():
    from app.main import app

    return TestClient(app)


def _scanned_pdf(pages: int = 2) -> bytes:
    """A PDF with no text layer — exactly what a scan or a phone photo produces."""
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Telling a scan apart from a typed document
# ---------------------------------------------------------------------------


def test_has_no_text_is_true_for_a_scan():
    from app.files import extract_text

    assert has_no_text(extract_text(_scanned_pdf(3), "scan.pdf")) is True


def test_has_no_text_is_false_for_a_typed_pdf():
    from app.files import extract_text

    pages = extract_text(_make_text_pdf(["Osmosis is water movement"]), "typed.pdf")
    assert has_no_text(pages) is False


# ---------------------------------------------------------------------------
# The upload route's fallback
# ---------------------------------------------------------------------------


def test_a_scanned_pdf_is_read_by_the_vision_model(client, monkeypatch):
    """The whole point: a scan uploads and ends up with real text in it."""
    monkeypatch.setattr(ocr, "read_image", lambda png: "Osmosis is the movement of water.")

    response = client.post(
        "/documents",
        files={"file": ("handwritten.pdf", _scanned_pdf(2), "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["page_count"] == 2


def test_a_typed_pdf_never_touches_the_vision_model(client, monkeypatch):
    """Typed PDFs must stay instant and free — no API call, no daily allowance."""

    def _explode(png):
        raise AssertionError("the vision model was called for a PDF that had text in it")

    monkeypatch.setattr(ocr, "read_image", _explode)

    response = client.post(
        "/documents",
        files={"file": ("typed.pdf", _make_text_pdf(["Real text here"]), "application/pdf")},
    )

    assert response.status_code == 201


def test_a_photo_of_notes_is_accepted(client, monkeypatch):
    """A .png goes straight to the model — there is no text in it to try first."""
    monkeypatch.setattr(ocr, "read_image", lambda png: "Cell structure, chapter 4.")

    response = client.post(
        "/documents",
        files={"file": ("notes.png", b"pretend png bytes", "image/png")},
    )

    assert response.status_code == 201
    assert response.json()["page_count"] == 1


def test_a_reading_failure_becomes_a_plain_sentence(client, monkeypatch):
    """The user never sees a provider error or a traceback."""

    def _fail(png):
        raise ocr.OcrUnavailable("The free daily limit for reading handwriting has run out.")

    monkeypatch.setattr(ocr, "read_image", _fail)

    response = client.post(
        "/documents",
        files={"file": ("scan.pdf", _scanned_pdf(1), "application/pdf")},
    )

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert "couldn't read" in detail
    assert "Traceback" not in detail


def test_a_scan_is_refused_politely_when_ocr_is_switched_off(client, monkeypatch):
    monkeypatch.setattr(config, "OCR_ENABLED", False)

    response = client.post(
        "/documents",
        files={"file": ("scan.pdf", _scanned_pdf(1), "application/pdf")},
    )

    assert response.status_code == 400
    assert "scan" in response.json()["detail"]


def test_a_very_long_scan_is_refused_rather_than_eating_the_daily_limit(client, monkeypatch):
    monkeypatch.setattr(config, "OCR_MAX_PAGES", 3)

    response = client.post(
        "/documents",
        files={"file": ("book.pdf", _scanned_pdf(10), "application/pdf")},
    )

    assert response.status_code == 400
    assert "splitting it up" in response.json()["detail"]


def test_a_blank_photo_is_refused_rather_than_stored_empty(client, monkeypatch):
    """An empty note would look fine in the list and never match anything."""
    monkeypatch.setattr(ocr, "read_image", lambda png: "")

    response = client.post(
        "/documents",
        files={"file": ("blank.png", b"pretend png bytes", "image/png")},
    )

    assert response.status_code == 400
    assert "couldn't find any writing" in response.json()["detail"]


# ---------------------------------------------------------------------------
# The module on its own
# ---------------------------------------------------------------------------


def test_read_image_says_so_when_there_is_no_api_key(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "")

    with pytest.raises(ocr.OcrUnavailable, match="GROQ_API_KEY"):
        ocr.read_image(b"pretend png")


def test_page_images_draws_one_png_per_page():
    """pypdfium2 turns each PDF page into a real PNG, capped at max_pages."""
    images = ocr.page_images(_scanned_pdf(4), max_pages=2)

    assert len(images) == 2
    assert [number for number, _ in images] == [1, 2]
    for _, png in images:
        assert png.startswith(b"\x89PNG"), "not a PNG"


# ---------------------------------------------------------------------------
# Waiting out the per-minute limit
# ---------------------------------------------------------------------------


def test_a_rate_limited_page_is_retried_rather_than_failing(monkeypatch):
    """Hitting the per-minute cap mid-scan is normal, not exceptional.

    The free tier reserves against max_tokens, so roughly two pages fit in a
    minute. Page three of a scan therefore hits the limit as a matter of
    course — failing the whole upload there would be wrong.
    """
    monkeypatch.setattr(config, "OCR_RETRY_WAIT_SECONDS", 0)
    monkeypatch.setattr(config, "OCR_RETRY_ATTEMPTS", 3)

    attempts = []

    def _limited_twice(png):
        attempts.append(1)
        if len(attempts) < 3:
            raise ocr.RateLimited("Nibble is reading too much at once.")
        return "Osmosis moves water."

    monkeypatch.setattr(ocr, "_request_transcription", _limited_twice)

    assert ocr.read_image(b"png") == "Osmosis moves water."
    assert len(attempts) == 3


def test_giving_up_after_the_last_retry(monkeypatch):
    monkeypatch.setattr(config, "OCR_RETRY_WAIT_SECONDS", 0)
    monkeypatch.setattr(config, "OCR_RETRY_ATTEMPTS", 2)

    def _always_limited(png):
        raise ocr.RateLimited("Nibble is reading too much at once.")

    monkeypatch.setattr(ocr, "_request_transcription", _always_limited)

    with pytest.raises(ocr.OcrUnavailable):
        ocr.read_image(b"png")


def test_the_daily_limit_is_not_retried(monkeypatch):
    """Waiting cannot fix "nothing left today", so it must not sit there retrying."""
    monkeypatch.setattr(config, "OCR_RETRY_WAIT_SECONDS", 0)
    calls = []

    def _out_for_the_day(png):
        calls.append(1)
        raise ocr.OcrUnavailable("Nibble has read as much handwriting as it can today.")

    monkeypatch.setattr(ocr, "_request_transcription", _out_for_the_day)

    with pytest.raises(ocr.OcrUnavailable, match="today"):
        ocr.read_image(b"png")
    assert len(calls) == 1, "a daily limit must not be retried"


def test_thinking_tags_never_reach_the_stored_text():
    """If the model thinks out loud anyway, that must not be stored as your notes."""
    thought = "<think>The user wants the text. Let me look.</think>\nOsmosis moves water."

    assert ocr._strip_thinking(thought) == "Osmosis moves water."
    assert ocr._strip_thinking("Just the answer.") == "Just the answer."
