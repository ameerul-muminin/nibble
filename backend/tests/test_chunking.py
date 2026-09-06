"""Tests for cutting a document into pieces.

This is the easiest thing in the project to test, and worth noticing why: no
database, no network, no server, no uploaded file. Text goes in, pieces come
out. A test is three lines and runs instantly.
"""

import pytest

from app import config
from app.chunking import MIN_CHUNK_CHARS, chunk_pages


def test_short_page_is_one_piece():
    text = "Osmosis is the net movement of water across a semipermeable membrane."
    chunks = chunk_pages([(1, text)])

    assert len(chunks) == 1
    assert chunks[0] == {"page": 1, "content": text}


def test_long_page_is_cut_into_several_pieces():
    # Comfortably longer than one piece, so this has to produce more than one.
    text = "a" * (config.CHUNK_SIZE * 3)
    chunks = chunk_pages([(1, text)])

    assert len(chunks) > 1
    assert all(len(c["content"]) <= config.CHUNK_SIZE for c in chunks)


def test_consecutive_pieces_really_do_overlap():
    """The overlap is the whole reason for the design, so pin it.

    Distinct characters rather than "aaaa..." — with repeated text every piece
    looks like every other piece and the assertion passes without meaning
    anything.
    """
    text = "".join(f"{n:04d} " for n in range(600))  # 3000 chars, all different
    chunks = chunk_pages([(1, text)])

    assert len(chunks) > 1

    first, second = chunks[0]["content"], chunks[1]["content"]

    # The definition of overlap: the second piece begins inside the first one.
    assert second[:50] in first
    assert first != second


def test_no_piece_is_lost_between_two_pieces():
    """Overlap is useless if a gap opens up somewhere else.

    Every character of the page has to appear in at least one piece, or a
    sentence could fall down the crack and never be searchable.
    """
    text = "".join(f"{n:04d} " for n in range(600))
    chunks = chunk_pages([(1, text)])

    rejoined = chunks[0]["content"]
    for chunk in chunks[1:]:
        # Each piece starts inside the previous one, so find where it picks up.
        head = chunk["content"][:50]
        assert head in rejoined, "a gap opened up between two pieces"
        rejoined = rejoined[: rejoined.index(head)] + chunk["content"]

    assert rejoined.strip() == text.strip()


def test_page_numbers_survive():
    long_page = "b" * (config.CHUNK_SIZE * 2)
    first_page = "a normal first page with enough text on it to be kept"
    chunks = chunk_pages([(1, first_page), (4, long_page)])

    assert chunks[0]["page"] == 1
    assert {c["page"] for c in chunks[1:]} == {4}


def test_a_piece_never_spans_two_pages():
    one = "the text that is written on the first page of the document"
    two = "the text that is written on the second page of the document"
    chunks = chunk_pages([(1, one), (2, two)])

    assert len(chunks) == 2
    assert chunks[0] == {"page": 1, "content": one}
    assert chunks[1] == {"page": 2, "content": two}


def test_empty_and_blank_pages_produce_nothing():
    assert chunk_pages([]) == []
    assert chunk_pages([(1, "")]) == []
    assert chunk_pages([(1, "   \n\n  \t ")]) == []


def test_a_blank_page_between_two_real_ones_is_skipped():
    """The normal shape of a scan: a blank page in the middle is not an error."""
    chunks = chunk_pages(
        [
            (1, "there is real text written here on the very first page"),
            (2, ""),
            (3, "there is real text written here on the third page too"),
        ]
    )

    assert [c["page"] for c in chunks] == [1, 3]


def test_a_short_page_is_still_kept():
    """A title-only slide, or a two-line note, is real content.

    An earlier version of this dropped any piece under MIN_CHUNK_CHARS, which
    quietly deleted every title slide in a deck and refused a legitimate small
    .md note. The minimum applies to a *trailing scrap*, never to a whole page.
    """
    assert chunk_pages([(1, "Chapter 4")]) == [{"page": 1, "content": "Chapter 4"}]
    assert len(chunk_pages([(1, "x" * (MIN_CHUNK_CHARS - 1))])) == 1


def test_a_trailing_scrap_is_dropped(monkeypatch):
    """The rule it does still apply to: a stub left at the end of a long page.

    It takes a small overlap to produce one at all. With the real settings the
    loop stops a step early and the last piece is always over 150 characters,
    which is why this has to reach for the config to show the rule working.
    """
    monkeypatch.setattr(config, "CHUNK_SIZE", 100)
    monkeypatch.setattr(config, "CHUNK_OVERLAP", 5)

    # 195 characters: windows at 0-100 and 95-195, then a 5-character scrap.
    chunks = chunk_pages([(1, "x" * 195 + "y" * 5)])

    assert all(len(c["content"]) >= MIN_CHUNK_CHARS for c in chunks)


def test_the_tail_of_a_page_is_not_stored_twice():
    """The last window must not be a piece already wholly inside the one before.

    Without the break in _cut, a page a little longer than two steps produces a
    final piece that is a tail of its predecessor — duplicated in the database
    and matched twice by every search.
    """
    text = "".join(f"{n:04d} " for n in range(320))  # 1600 chars
    chunks = chunk_pages([(1, text)])

    contents = [c["content"] for c in chunks]
    for i, piece in enumerate(contents):
        for other in contents[i + 1 :]:
            assert other not in piece, "a piece was stored twice"


def test_pieces_come_back_in_reading_order():
    """The route inserts in this order and never sorts, so the order is the contract."""
    pages = [(1, "x" * 2000), (2, "y" * 2000), (3, "z" * 2000)]
    chunks = chunk_pages(pages)

    page_numbers = [c["page"] for c in chunks]
    assert page_numbers == sorted(page_numbers)


def test_an_overlap_bigger_than_the_size_is_refused(monkeypatch):
    """A hand-edited config must fail loudly rather than hang the server.

    With CHUNK_OVERLAP >= CHUNK_SIZE the step is zero, the window never moves,
    and the loop builds identical pieces until the process dies.
    """
    monkeypatch.setattr(config, "CHUNK_OVERLAP", config.CHUNK_SIZE)

    with pytest.raises(ValueError, match="must be smaller than"):
        chunk_pages([(1, "some text that is long enough to be chunked at all")])


def test_whitespace_on_a_boundary_never_splits_a_word():
    """What the overlap actually guarantees, pinned against the trimming.

    Each window is stripped of leading and trailing whitespace, so the overlap
    between two pieces is shorter than CHUNK_OVERLAP by however much whitespace
    sat on the boundary — and where a boundary lands inside a long run of blank
    space, the overlap disappears completely.

    That is harmless, and this test is what says so rather than leaving it to be
    rediscovered. Trimming only ever removes whitespace, so a boundary with no
    overlap left is a boundary with nothing but blank space on it: no word is
    being cut, so there is nothing for an overlap to rescue. The promise worth
    testing is about words, not about a character count.
    """
    left = " ".join(f"alpha{n:03d}" for n in range(80))
    right = " ".join(f"omega{n:03d}" for n in range(120))

    # 200 spaces, wider than CHUNK_OVERLAP, so the overlap really does vanish.
    chunks = chunk_pages([(1, left + " " * 200 + right)])
    contents = [c["content"] for c in chunks]

    for word in set((left + " " + right).split()):
        assert any(word in piece for piece in contents), f"{word} was split in two"


def test_ordinary_prose_keeps_very_nearly_the_whole_overlap():
    """The trimming costs a character or two on real text, not the whole overlap."""
    text = " ".join(f"word{n:04d}" for n in range(400))
    contents = [c["content"] for c in chunk_pages([(1, text)])]

    for first, second in zip(contents, contents[1:], strict=False):
        shared = next(
            (n for n in range(min(len(first), len(second)), 0, -1) if first.endswith(second[:n])),
            0,
        )
        assert shared >= config.CHUNK_OVERLAP - 2
