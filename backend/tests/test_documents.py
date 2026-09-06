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
    """A PDF of BLANK pages — no text layer, which is what a scan looks like."""
    writer = PdfWriter()
    for _ in range(num_pages):
        writer.add_blank_page(width=100, height=100)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_text_pdf(page_texts: list[str]) -> bytes:
    """A minimal but genuinely valid PDF that really contains a text layer.

    pypdf's PdfWriter can add blank pages but cannot put words on them, and a
    blank page is now indistinguishable from a scan — which is the whole point
    of has_no_text(). So these tests build a real one: a catalog, a page tree,
    one Helvetica font, and a content stream per page that draws the text.
    """
    objects = []
    n_pages = len(page_texts)
    page_ids = [4 + i * 2 for i in range(n_pages)]

    objects.append((1, b"<< /Type /Catalog /Pages 2 0 R >>"))
    kids = b" ".join(b"%d 0 R" % pid for pid in page_ids)
    objects.append((2, b"<< /Type /Pages /Kids [" + kids + b"] /Count %d >>" % n_pages))
    objects.append((3, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"))

    for i, text in enumerate(page_texts):
        pid = page_ids[i]
        stream = b"BT /F1 12 Tf 20 100 Td (" + text.encode("ascii") + b") Tj ET"
        objects.append(
            (
                pid,
                (
                    b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
                    b"/Resources << /Font << /F1 3 0 R >> >> /Contents %d 0 R >>" % (pid + 1)
                ),
            )
        )
        objects.append(
            (pid + 1, b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        )

    objects.sort()
    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for num, body in objects:
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num + body + b"\nendobj\n"

    xref_at = len(out)
    highest = max(offsets)
    out += b"xref\n0 %d\n" % (highest + 1)
    out += b"0000000000 65535 f \n"
    for num in range(1, highest + 1):
        out += (b"%010d 00000 n \n" % offsets[num]) if num in offsets else b"0000000000 65535 f \n"
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (highest + 1, xref_at)
    return bytes(out)


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
    """Uploading a 3-page typed PDF should return page_count == 3."""
    pdf_bytes = _make_text_pdf(["Page one text", "Page two text", "Page three text"])
    response = client.post(
        "/documents",
        files={"file": ("lecture.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["page_count"] == 3


def test_upload_bad_extension_returns_400(client):
    """An .exe is rejected. (.png is now supported — it goes to the vision model.)"""
    response = client.post(
        "/documents",
        files={"file": ("virus.exe", b"not a real exe", "application/octet-stream")},
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
    """The same thing, written the Windows way with backslashes.

    This one is why the cleaning does not just call Path(...).name: on Linux a
    backslash is an ordinary character in a filename, so Path would hand the
    whole string straight back and the upload would be stored inside uploads/
    under that literal name. Not an escape on Linux — but not the same answer
    the same upload gets on Windows either, which is reason enough to normalise.
    """
    response = client.post(
        "/documents",
        files={"file": (r"..\..\escaped-win.txt", b"Nor should I.", "text/plain")},
    )

    assert response.status_code == 201
    assert response.json()["filename"] == "escaped-win.txt"
    assert (tmp_path / "uploads" / "escaped-win.txt").exists()


def test_safe_filename_strips_directories_on_either_separator():
    """The helper on its own, without going through HTTP.

    Every one of these has to give the same answer on Windows and on Linux,
    which is the whole reason the helper exists.
    """
    from app.routes import _safe_filename

    assert _safe_filename("notes.txt") == "notes.txt"
    assert _safe_filename("../../escaped.txt") == "escaped.txt"
    assert _safe_filename(r"..\..\escaped.txt") == "escaped.txt"
    assert _safe_filename("/etc/passwd") == "passwd"
    assert _safe_filename(r"C:\Windows\System32\evil.dll") == "evil.dll"
    assert _safe_filename("a/b/c/notes.md") == "notes.md"


def test_safe_filename_falls_back_when_nothing_usable_is_left():
    """ "../.." and friends leave no name behind at all."""
    from app.routes import _safe_filename

    assert _safe_filename(None) == "unnamed"
    assert _safe_filename("") == "unnamed"
    assert _safe_filename("../..") == "unnamed"
    assert _safe_filename("...") == "..."  # a real, if odd, filename
    assert _safe_filename("/") == "unnamed"


# ---------------------------------------------------------------------------
# DELETE /documents/{id} — issue #6
# ---------------------------------------------------------------------------


def test_delete_document_returns_204(client):
    """Deleting a document that exists returns 204 and an empty body."""
    created = client.post(
        "/documents",
        files={"file": ("notes.txt", b"Delete me.", "text/plain")},
    ).json()

    response = client.delete(f"/documents/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""


def test_delete_document_actually_removes_it_from_the_list(client):
    """After deleting, GET /documents no longer includes it.

    This is the test that catches a route returning 204 while deleting nothing.
    """
    keep = client.post("/documents", files={"file": ("keep.txt", b"Keep me.", "text/plain")}).json()
    remove = client.post(
        "/documents", files={"file": ("remove.txt", b"Not me.", "text/plain")}
    ).json()

    client.delete(f"/documents/{remove['id']}")

    docs = client.get("/documents").json()
    assert [d["id"] for d in docs] == [keep["id"]]


def test_delete_missing_document_returns_404(client):
    """Deleting an id that was never there is a 404, not a quiet 204.

    Worth writing first: DELETE on a missing row succeeds silently in SQL, so
    without an existence check this comes back 204 and looks like it worked.
    """
    response = client.delete("/documents/99999")

    assert response.status_code == 404
    # A plain sentence, not SQL and not a stack trace.
    assert "isn't here" in response.json()["detail"]


def test_delete_document_twice_is_a_404_the_second_time(client):
    """The same delete repeated stops being a success."""
    created = client.post("/documents", files={"file": ("once.txt", b"Once.", "text/plain")}).json()

    assert client.delete(f"/documents/{created['id']}").status_code == 204
    assert client.delete(f"/documents/{created['id']}").status_code == 404


def test_delete_document_also_deletes_its_chunks(client):
    """The chunks belonging to a document go with it.

    test_db.py proves the cascade at the database level. This is the same thing
    through the real HTTP route, which is where a dropped PRAGMA would show up.
    """
    from app.db import get_db

    created = client.post(
        "/documents", files={"file": ("biology.txt", b"Osmosis.", "text/plain")}
    ).json()

    db = get_db()
    try:
        db.execute(
            "INSERT INTO chunks (document_id, page, content) VALUES (?, ?, ?)",
            (created["id"], 1, "Osmosis is the net movement of water."),
        )
        db.commit()
    finally:
        db.close()

    client.delete(f"/documents/{created['id']}")

    db = get_db()
    try:
        remaining = db.execute(
            "SELECT COUNT(*) AS n FROM chunks WHERE document_id = ?", (created["id"],)
        ).fetchone()["n"]
    finally:
        db.close()

    assert remaining == 0


def test_delete_with_a_non_numeric_id_is_rejected(client):
    """FastAPI converts the path parameter, so /documents/abc never reaches us."""
    assert client.delete("/documents/abc").status_code == 422


def test_two_concurrent_deletes_give_one_204_and_one_404(client):
    """Exactly one caller wins when the same note is deleted twice at once.

    The obvious way to write this route is SELECT to check it exists, then
    DELETE. Both requests would pass that check, both would call DELETE, and
    the loser would remove nothing while still answering 204 — reporting a
    success for something it did not do. Asking the DELETE how many rows it
    removed closes the gap, because it is a single statement.
    """
    from concurrent.futures import ThreadPoolExecutor

    created = client.post(
        "/documents", files={"file": ("race.txt", b"Delete me once.", "text/plain")}
    ).json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        both = [pool.submit(client.delete, f"/documents/{created['id']}") for _ in range(2)]
        codes = sorted(f.result().status_code for f in both)

    assert codes == [204, 404]
    assert client.get("/documents").json() == []
