"""Meaning as numbers, and how to measure which meanings are close.

Alif owns this file. It is the one piece of real maths in the project, and it
is the reason Nibble can answer "how does osmosis work" using a page that never
says the word "osmosis".

**The idea.** A model reads a piece of text and hands back 384 numbers. Text
about the same thing gets similar numbers, whatever words it used. So "the cat
sat on the mat" lands close to "a kitten rested on the rug" and nowhere near
"quarterly revenue increased" — three sentences, and the two that *mean* the
same thing are the two that end up near each other, even though they share no
words at all. Those 384 numbers are called an embedding, and the whole of search
is: embed the question, embed every piece of your notes, and see which pieces
landed nearest.

**"Near" needs a definition, and cosine similarity is it.** Think of each
embedding as an arrow pointing somewhere in space. Cosine similarity ignores how
long the arrows are and measures only the angle between them: 1 means pointing
the same way, 0 means unrelated, -1 means opposite. Angle rather than distance is
what we want, because a long paragraph and a short one about the same topic
should still count as close.

**This runs on your own laptop.** No API key, no rate limit, no bill. ``fastembed``
downloads about 65 MB the first time it is used and works offline afterwards —
that download is mentioned in docs/first-week.md so it reads as expected rather
than as a hang. Groq, which answers questions in slice 4, has no embeddings API
at all; that is why this one part of the project does not go through the same
provider, and it is not an oversight.
"""

import threading

import numpy as np
from fastembed import TextEmbedding

from app import config

# The loaded model, or None until something asks for it.
#
# It lives at module level on purpose. Loading it takes seconds, and a route
# that loaded it per request would look broken every single time — so it is
# built once, the first time it is needed, and reused for the life of the
# server. That is the whole of the "module-level singleton" rule in CLAUDE.md.
#
# Why lazily, rather than at import: `import app.embeddings` happens when the
# server starts, when a test collects, and every time uvicorn --reload notices a
# saved file. Paying seconds for that when nobody has searched yet is a bad
# trade. The first search after a restart is slow; every one after it is not.
_model: TextEmbedding | None = None

# Only one thread may build the model, and this is what enforces it.
#
# It is needed because our routes are plain `def`, not `async def`. FastAPI runs
# those in a pool of threads so a slow one cannot block the whole server, which
# is exactly what we want — and it means two requests really can be inside this
# module at the same moment. Two people uploading at once on demo day is enough.
#
# Without the lock both would see `_model` as None and both would build one:
# twice the memory, twice the wait, and on a machine that has never run this
# before, two threads writing into the same download directory at the same time.
# The second model then quietly replaces the first, so nothing looks wrong — it
# is just slower and heavier than it should be, which is the hardest kind of
# problem to notice.
_model_lock = threading.Lock()


class EmbeddingUnavailable(RuntimeError):
    """The model could not be loaded — no download on the first run, usually.

    Its own type so a route can catch exactly this and answer with a sentence,
    the same way ocr.OcrUnavailable works. Never show the original error to a
    person: it talks about HTTP requests to a model repository, which tells
    somebody trying to search their notes nothing at all.
    """


def get_model() -> TextEmbedding:
    """Return the embedding model, loading it the first time and reusing it after.

    Everything in here goes through this function rather than touching ``_model``
    directly, so there is exactly one place where loading can happen and exactly
    one place that can fail.

    The lock is taken on **every** call, not only when the model is missing. You
    will see the other version of this written as "check if it is None, and only
    then take the lock" — that is called double-checked locking, it saves a few
    billionths of a second, and it is fiddly to get right for no benefit we can
    measure. Taking the lock every time is obviously correct at a glance, and the
    work waiting behind it is embedding text, which takes millions of times
    longer than the lock does.
    """
    global _model

    with _model_lock:
        if _model is None:
            try:
                # threads=1, and it is not a typo. Measured on a 16-core laptop,
                # embedding 30 pieces:
                #
                #     threads=1     2.41s      ~2.4 CPU-seconds
                #     threads=2     2.50s      ~5.0 CPU-seconds
                #     threads=4     2.57s     ~10.3 CPU-seconds
                #     threads=16    2.47s     ~39.5 CPU-seconds
                #
                # Read the first column: the extra threads buy nothing. This
                # model is small enough that one core saturates it, and the
                # threads spend their time synchronising rather than working.
                #
                # Now read the second column, because that is the one that
                # matters on the deployed backend. Render's free tier gives us
                # 0.1 CPU — ten milliseconds of CPU in every hundred. Left to
                # itself, onnxruntime counts the HOST's cores, not our share of
                # them, and starts a thread per core. Sixteen threads then queue
                # for one tenth of one core, and every one of them stalls to the
                # next scheduling window. The same work, spread across more
                # threads than we are allowed to run, takes several times longer
                # than doing it on one.
                #
                # So this line costs nothing on a laptop and is the single
                # cheapest thing that makes an upload on the free host faster.
                _model = TextEmbedding(model_name=config.EMBEDDING_MODEL, threads=1)
            except Exception as exc:  # every way this fails means the same thing to a person
                raise EmbeddingUnavailable(
                    "The search model could not be loaded. The first run downloads "
                    "about 65 MB, so check you are online and try again."
                ) from exc

    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Turn a list of texts into a list of 384-number vectors, one per text.

    Call this **once with everything**, not once per piece. The model works on a
    batch far faster than it works on the same texts one at a time, and an upload
    of a 40-page chapter is the difference between a pause and a wait.

    That is safe to do with any number of pieces: the grouping that costs memory
    happens inside, in fixed-size batches, so handing this a whole book does not
    cost more memory than handing it a chapter. See the ``batch_size`` note below.

    The order out matches the order in — vector 0 belongs to text 0 — which is
    what lets the upload route zip these straight onto the chunks it just built.
    """
    # No texts is a real, ordinary case: a document where every page was blank.
    # Ask the model for nothing and it is entitled to be unhappy about it, so
    # answer here instead.
    if not texts:
        return []

    # .embed() hands back a generator of numpy arrays, one per text. list()
    # runs it, and .tolist() turns each array into ordinary Python floats —
    # which is what json.dumps needs to write into the `embedding` column,
    # because it does not know what a numpy array is.
    #
    # batch_size is the one argument here that is not obvious, and it is load
    # bearing. `.embed()` does not run the model once per text — it groups them,
    # and its default group is 256. Hand it a 400-piece book and it builds a
    # tensor for 256 pieces at once, which measured at 1275 MB of memory. At 8
    # the same book peaks at 278 MB and takes the same thirty seconds, because
    # the work is identical either way; only how much of it is held at one
    # moment changes. See EMBED_BATCH_SIZE in config.py for the measurements.
    #
    # So memory is now flat: a short note and a long book cost the same peak.
    # Without it, the ceiling was whatever the largest file anybody uploaded.
    vectors = [
        vector.tolist() for vector in get_model().embed(texts, batch_size=config.EMBED_BATCH_SIZE)
    ]

    # A loud check on something that would otherwise be silent. Change
    # EMBEDDING_MODEL to a model with a different width and everything here
    # keeps working — right up until a query embedded by the new model is
    # compared against chunks embedded by the old one, where numpy raises
    # something about shapes that explains nothing. Say it plainly instead.
    width = len(vectors[0])
    if width != config.EMBEDDING_DIM:
        raise EmbeddingUnavailable(
            f"{config.EMBEDDING_MODEL} produced {width} numbers per piece, but "
            f"EMBEDDING_DIM in config.py says {config.EMBEDDING_DIM}. Anything "
            "already stored was embedded at the old width and cannot be compared "
            "against anything embedded at the new one."
        )

    return vectors


def cosine_similarity(query_vector: list[float], matrix: list[list[float]]) -> np.ndarray:
    """Score one vector against many, returning one number per row of ``matrix``.

    ``query_vector`` is the embedded question. ``matrix`` is every chunk's
    embedding, one per row. What comes back is an array of scores in the same
    order as the rows, each between -1 and 1, where higher means closer in
    meaning.

    This is the whole of search, and it is six lines because of one trick:
    **normalise first, then multiply.** Divide every arrow by its own length and
    they all become length 1, at which point the cosine of the angle between two
    of them is just their dot product — no division, no angles, no trigonometry.
    One matrix multiply then scores every chunk at once, which is why a few
    thousand pieces are compared in a blink without any kind of index.

    No index is deliberate, not an omission — see adr/0001-sqlite-and-numpy.md.
    """
    query = np.asarray(query_vector, dtype=np.float32)
    rows = np.asarray(matrix, dtype=np.float32)

    # Nothing to compare against. Returning an empty array rather than raising
    # keeps the caller simple: a database with no embedded chunks is an ordinary
    # state on a fresh install, not an error.
    if rows.size == 0:
        return np.zeros(0, dtype=np.float32)

    query_length = float(np.linalg.norm(query))

    # An all-zero vector has no direction, so there is no angle to measure and
    # nothing is meaningfully close to it. Dividing by its length would be a
    # divide by zero, which numpy answers with nan — a score that is neither
    # high nor low and quietly poisons any sort it lands in.
    if query_length == 0:
        return np.zeros(len(rows), dtype=np.float32)

    query = query / query_length

    row_lengths = np.linalg.norm(rows, axis=1)
    row_lengths[row_lengths == 0] = 1.0  # same divide-by-zero guard, per row
    rows = rows / row_lengths[:, np.newaxis]

    # One multiply, every score. @ is matrix multiplication: each row of `rows`
    # meets `query` and produces a single number.
    return rows @ query
