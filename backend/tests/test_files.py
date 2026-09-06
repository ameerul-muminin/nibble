"""Tests for file text extraction (PDF, TXT, MD)."""

from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.files import extract_text


def test_extract_text_from_plain_text():
    content = b"Hello, this is a plain text file for testing."
    result = extract_text(content, "sample.txt")

    assert len(result) == 1
    page_num, text = result[0]
    assert page_num == 1
    assert text == "Hello, this is a plain text file for testing."


def test_extract_text_from_markdown():
    content = b"# Chapter 1\n\nThis is a markdown notes file."
    result = extract_text(content, "notes.md")

    assert len(result) == 1
    page_num, text = result[0]
    assert page_num == 1
    assert text == "# Chapter 1\n\nThis is a markdown notes file."


def test_extract_text_from_pdf_structure():
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_blank_page(width=100, height=100)
    buf = BytesIO()
    writer.write(buf)
    pdf_bytes = buf.getvalue()

    result = extract_text(pdf_bytes, "document.pdf")
    assert len(result) == 2
    assert result[0][0] == 1
    assert result[1][0] == 2


def test_extract_text_unsupported_extension_raises_error():
    content = b"Some random content"
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(content, "image.png")

    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(content, "archive.zip")


def test_extract_text_case_insensitive_extension():
    content = b"Case insensitive test"
    result = extract_text(content, "DOCUMENT.TXT")
    assert len(result) == 1
    assert result[0] == (1, "Case insensitive test")


def test_extract_text_rejects_extensions_not_in_the_contract():
    """docs/api.md promises .pdf, .txt and .md — nothing else.

    These two used to be accepted here while the contract named only three
    extensions. This test is what stops that drifting apart again.
    """
    content = b"Some notes"
    for filename in ("notes.text", "notes.markdown"):
        with pytest.raises(ValueError, match="Unsupported file type"):
            extract_text(content, filename)
