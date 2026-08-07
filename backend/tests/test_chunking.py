from app.services.chunking import chunk_pages


def test_splits_long_text_with_overlap():
    page = "word " * 500
    chunks = chunk_pages([page])
    assert len(chunks) > 1
    assert all(chunk.page == 1 for chunk in chunks)
    assert [chunk.ordinal for chunk in chunks] == list(range(len(chunks)))


def test_skips_empty_pages():
    assert chunk_pages(["", "   ", "\n"]) == []


def test_keeps_page_numbers():
    chunks = chunk_pages(["a" * 200, "b" * 200])
    assert {chunk.page for chunk in chunks} == {1, 2}
