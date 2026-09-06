"""Cut a document's text into pieces small enough to search.

A whole chapter is the wrong unit for search. Ask "how does osmosis work" and
matching it against a 40-page document tells you the answer is *somewhere* in
those 40 pages, which you knew. Matching it against 900 characters tells you
the paragraph.

So before anything is stored, every page is cut into overlapping pieces. Two
rules make the pieces useful, and both are here for a reason:

**Pieces overlap.** Consecutive pieces repeat the last CHUNK_OVERLAP characters
of the one before. Cut a page at a fixed width and sooner or later the cut lands
mid-sentence — "water moves across a | membrane toward the solute" — and neither
half means what the whole sentence meant. With an overlap, that sentence still
sits whole inside at least one piece.

**A piece never spans two pages.** Every piece carries the page it came from, and
that number has to be true, because slice 4 shows it to a student as "p. 4". The
cheap way to keep it true is to never let a piece straddle a boundary. The cost
is that a short page produces a short piece, which is fine.

There is nothing clever in here on purpose. No sentence detection, no paragraph
splitting, no tokeniser — a character count and a step. It is six lines of real
work, and it is easy to explain, which is worth more here than the last few
percent of quality.
"""

from app import config

# The shortest a *trailing scrap* is allowed to be before it is dropped.
#
# Read that carefully, because the first version of this rule was wrong and the
# tests caught it. It applies only to a piece that is not the first piece of its
# page — never to a whole page. Applied to whole pages it silently deleted every
# title-only slide, and refused a legitimate two-line .md note outright.
#
# With the current settings it almost never fires at all: the last window of a
# page is always longer than CHUNK_OVERLAP (150), because the loop would have
# stopped a step earlier otherwise. It is a guard for a hand-edited config with
# a small overlap, where a genuine 11-character scrap can appear.
MIN_CHUNK_CHARS = 40


def chunk_pages(pages: list[tuple[int, str]]) -> list[dict]:
    """Cut every page into overlapping pieces.

    Takes exactly what ``extract_text()`` returns — a list of
    ``(page_number, text)`` — so the upload route hands one straight to the
    other with nothing in between to explain.

    Returns a list of ``{"page": int, "content": str}``, in reading order:
    every piece of page 1, then every piece of page 2. That order is what
    ``GET /documents/{id}/chunks`` shows, and it is the order they were
    inserted, so no sorting is needed anywhere downstream.

    A page with no text on it produces nothing at all. That is the normal case
    for a blank page in the middle of a scan, not an error. Every page that has
    *any* text produces at least one piece, however short — see MIN_CHUNK_CHARS.
    """
    chunks: list[dict] = []

    for page_number, text in pages:
        for piece in _cut(text):
            chunks.append({"page": page_number, "content": piece})

    return chunks


def _cut(text: str) -> list[str]:
    """Cut one page's text into overlapping pieces.

    The whole idea in one line: take CHUNK_SIZE characters, then move forward by
    less than that, so the next piece starts inside the one before it.

        CHUNK_SIZE    = 900   how long a piece is
        CHUNK_OVERLAP = 150   how much of the previous piece it repeats
        step          = 750   how far the window moves each time

    With a 2000-character page that gives pieces at 0-900, 750-1650 and
    1500-2000. The third one is 500 characters rather than 900 because the page
    ran out, which is expected — only the *last* piece is ever short.
    """
    text = text.strip()
    if not text:
        return []

    size = config.CHUNK_SIZE
    step = size - config.CHUNK_OVERLAP

    # A guard rather than a comment, because getting this wrong is silent and
    # awful: with an overlap >= the size the step is zero or negative, the loop
    # below never advances, and the server hangs building an infinite list of
    # identical pieces. Config is edited by hand, so this is reachable.
    if step <= 0:
        raise ValueError(
            f"CHUNK_OVERLAP ({config.CHUNK_OVERLAP}) must be smaller than "
            f"CHUNK_SIZE ({config.CHUNK_SIZE}), or chunking cannot move forward."
        )

    pieces: list[str] = []
    for start in range(0, len(text), step):
        piece = text[start : start + size].strip()

        # A trailing scrap, too short to be worth its own row. Only ever applied
        # to a later piece: the first piece of a page is kept however short it
        # is, because that is the whole content of the page and dropping it
        # loses a real slide title, or a real short note, and says nothing.
        if pieces and len(piece) < MIN_CHUNK_CHARS:
            continue

        pieces.append(piece)

        # This piece already reaches the end of the page, so every later
        # window is just a shorter tail of it. Without the break, a
        # 1600-character page gives 0-900, 750-1600, and then 1500-1600 — and
        # that third piece is wholly inside the second, stored twice and
        # matched twice by every search.
        if start + size >= len(text):
            break

    return pieces
