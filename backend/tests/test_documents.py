"""Tests for POST /documents and GET /documents.

Each test uses a temporary database so tests never interfere with each other
or with a real nibble.db on your machine.
"""

from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

# We need to point the database at a temporary file BEFORE importing the app,
# because importing the app imports routes.py, which imports db.py, which
# reads config.DATABASE_FILE. By setting the env var first we make sure every
# test hits a throwaway database.


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    """Point the database at a fresh temporary file for every single test."""
    db_file = str(tmp_path / "test_nibble.db")
    monkeypatch.setattr("app.config.DATABASE_FILE", db_file)

    # Also point the uploads directory into tmp so we don't litter the project
    uploads_dir = tmp_path / "uploads"
    monkeypatch.setattr("app.routes._UPLOADS_DIR", uploads_dir)


@pytest.fixture()
def client():
    """A fresh test client that uses the patched config."""
    from app.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pdf(num_pages: int = 1) -> bytes:
    """Create a tiny in-memory PDF with the given number of blank pages."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=100, height=100)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# POST /documents
# ---------------------------------------------------------------------------


def test_upload_txt_returns_201(client):
    """Uploading a .txt file should return 201 with the correct shape."""
    response = client.post(
        "/documents",
        files={"file": ("notes.txt", b"Hello, this is my notes file.", "text/plain")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["filename"] == "notes.txt"
    assert body["page_count"] == 1
    assert "id" in body
    assert "created_at" in body


def test_upload_md_returns_201(client):
    """Uploading a .md file should return 201."""
    response = client.post(
        "/documents",
        files={"file": ("chapter.md", b"# Chapter 1\n\nSome content.", "text/markdown")},
    )

    assert response.status_code == 201
    assert response.json()["filename"] == "chapter.md"
    assert response.json()["page_count"] == 1


def test_upload_pdf_returns_201_with_correct_page_count(client):
    """Uploading a 3-page PDF should return page_count == 3."""
    pdf_bytes = _make_pdf(num_pages=3)
    response = client.post(
        "/documents",
        files={"file": ("lecture.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["page_count"] == 3


def test_upload_bad_extension_returns_400(client):
    """Uploading a .png should be rejected with 400."""
    response = client.post(
        "/documents",
        files={"file": ("photo.png", b"not a real png", "image/png")},
    )

    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_upload_zip_returns_400(client):
    """Uploading a .zip should also be rejected."""
    response = client.post(
        "/documents",
        files={"file": ("archive.zip", b"not a zip", "application/zip")},
    )

    assert response.status_code == 400


def test_upload_too_large_returns_413(client):
    """A file over 20 MB should be rejected with 413."""
    big_data = b"x" * (20 * 1024 * 1024 + 1)  # just over 20 MB
    response = client.post(
        "/documents",
        files={"file": ("huge.txt", big_data, "text/plain")},
    )

    assert response.status_code == 413
    assert "too large" in response.json()["detail"]


# ---------------------------------------------------------------------------
# GET /documents
# ---------------------------------------------------------------------------


def test_get_documents_empty(client):
    """When nothing has been uploaded, GET /documents returns an empty list."""
    response = client.get("/documents")

    assert response.status_code == 200
    assert response.json() == []


def test_get_documents_returns_uploaded_file(client):
    """After uploading a file, GET /documents should include it."""
    client.post(
        "/documents",
        files={"file": ("biology.txt", b"Cell structure notes.", "text/plain")},
    )

    response = client.get("/documents")

    assert response.status_code == 200
    docs = response.json()
    assert len(docs) == 1
    assert docs[0]["filename"] == "biology.txt"
    assert docs[0]["page_count"] == 1


def test_get_documents_newest_first(client):
    """Documents should come back newest first."""
    # Upload two files — they will get slightly different timestamps
    client.post(
        "/documents",
        files={"file": ("first.txt", b"I was uploaded first.", "text/plain")},
    )
    client.post(
        "/documents",
        files={"file": ("second.txt", b"I was uploaded second.", "text/plain")},
    )

    response = client.get("/documents")
    docs = response.json()

    assert len(docs) == 2
    # The second upload should appear first in the list (newest first)
    assert docs[0]["filename"] == "second.txt"
    assert docs[1]["filename"] == "first.txt"


# ---------------------------------------------------------------------------
# Never trust a filename that came from the client
# ---------------------------------------------------------------------------


def test_upload_with_directory_traversal_filename_stays_in_uploads(client, tmp_path):
    """A filename like ../../escaped.txt must not write outside uploads/.

    The browser chooses the filename, so an attacker chooses it too. This is the
    test that proves we strip the directory part instead of trusting it.
    """
    response = client.post(
        "/documents",
        files={"file": ("../../escaped.txt", b"I should not escape.", "text/plain")},
    )

    assert response.status_code == 201
    # Only the last piece of the path survives.
    assert response.json()["filename"] == "escaped.txt"

    # And nothing was written outside the uploads directory.
    uploads_dir = tmp_path / "uploads"
    assert (uploads_dir / "escaped.txt").exists()
    assert not (tmp_path.parent / "escaped.txt").exists()
    assert not (tmp_path / "escaped.txt").exists()


def test_upload_with_windows_style_traversal_filename(client, tmp_path):
    """The same thing, written the Windows way with backslashes."""
    response = client.post(
        "/documents",
        files={"file": (r"..\..\escaped-win.txt", b"Nor should I.", "text/plain")},
    )

    assert response.status_code == 201
    assert "/" not in response.json()["filename"]
    assert "\\" not in response.json()["filename"]
