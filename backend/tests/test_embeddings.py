"""Tests for turning text into numbers, and comparing those numbers.

**These tests use the real model**, unlike everything else in this suite, which
stubs anything slow or networked. That is on purpose and it is worth knowing why:
the claim this file makes is that *meaning* is captured, and a stub cannot be
wrong about meaning. A fake embedder returning made-up numbers would pass every
assertion below while proving nothing at all.

The cost is that the first run downloads about 65 MB and takes a minute. Every
run after that is fast, and CI caches the download between runs. If it is not
downloaded and there is no internet, these tests fail loudly rather than being
quietly skipped — a search test that skips itself is how a broken search reaches
a demo.

The maths tests underneath need no model at all: they hand cosine_similarity
numbers directly, which is the point of it being a separate function.
"""

import numpy as np
import pytest

from app import config
from app.embeddings import cosine_similarity, embed_texts, get_model

# ---------------------------------------------------------------------------
# The real model
# ---------------------------------------------------------------------------


def test_similar_meaning_beats_matching_words():
    """The claim the whole project rests on.

    "the cat sat on the mat" and "a kitten rested on the rug" share not one
    word. They should still land closer together than either lands to a
    sentence about revenue. If this ever fails, search is not doing what the
    demo says it does, and no amount of frontend polish will hide it.
    """
    cat, kitten, revenue = embed_texts(
        [
            "the cat sat on the mat",
            "a kitten rested on the rug",
            "quarterly revenue increased by twelve percent",
        ]
    )

    like_kitten = cosine_similarity(cat, [kitten])[0]
    like_revenue = cosine_similarity(cat, [revenue])[0]

    assert like_kitten > like_revenue


def test_every_text_becomes_exactly_EMBEDDING_DIM_numbers():
    vectors = embed_texts(["osmosis", "a much longer sentence about cell membranes"])

    assert len(vectors) == 2
    assert all(len(v) == config.EMBEDDING_DIM for v in vectors)


def test_vectors_are_plain_floats_not_numpy():
    """json.dumps has to be able to write these into the embedding column.

    The model hands back numpy arrays, and json.dumps does not know what one of
    those is — it raises TypeError. So embed_texts converts, and this pins that
    conversion, because the failure would otherwise appear in slice 3's upload
    route rather than here.
    """
    import json

    vector = embed_texts(["osmosis"])[0]

    assert isinstance(vector, list)
    assert all(isinstance(number, float) for number in vector)
    json.dumps(vector)  # raises TypeError if anything above is not true


def test_no_texts_asks_the_model_nothing():
    assert embed_texts([]) == []


def test_the_model_is_loaded_once_and_reused():
    """The singleton rule, pinned.

    Loading takes seconds. Two calls returning two different objects would mean
    it is being loaded again, and a search that reloads the model every time
    looks broken to the person using it.
    """
    assert get_model() is get_model()


def test_two_threads_asking_at_once_still_build_only_one_model(monkeypatch):
    """The singleton rule again, this time under the conditions it actually meets.

    Our routes are plain `def`, so FastAPI runs them in a pool of threads and two
    requests genuinely can be inside get_model() at the same moment — two people
    uploading at once is enough. Without the lock, both see None and both build a
    model.

    This uses a fake model rather than the real one, because the point being
    tested is the locking and not the maths, and because the fake can be made
    deliberately slow. The sleep is what makes the test meaningful: it holds the
    first thread inside the constructor long enough for the others to arrive, so
    an unlocked version fails this reliably rather than once in a hundred runs.
    """
    import threading
    import time

    import app.embeddings as embeddings

    builds = []

    class SlowFakeModel:
        def __init__(self, model_name=None):
            time.sleep(0.05)
            builds.append(model_name)

    monkeypatch.setattr(embeddings, "TextEmbedding", SlowFakeModel)
    monkeypatch.setattr(embeddings, "_model", None)

    models = []
    threads = [
        threading.Thread(target=lambda: models.append(embeddings.get_model())) for _ in range(8)
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(builds) == 1, f"the model was built {len(builds)} times, not once"
    assert all(model is models[0] for model in models)


# ---------------------------------------------------------------------------
# The maths, with no model involved
# ---------------------------------------------------------------------------


def test_a_vector_is_identical_to_itself():
    """Note the approx, which is not decoration.

    Written as `== 1.0` this test fails: dividing [1, 2, 3] by its own length in
    32-bit floats and multiplying back gives 0.99999994. That is not a bug in
    anything, it is what fractions do in binary, and it is the reason nothing in
    this project ever compares two scores for exact equality.
    """
    vector = [1.0, 2.0, 3.0]

    assert cosine_similarity(vector, [vector])[0] == pytest.approx(1.0)


def test_length_is_ignored_and_only_direction_counts():
    """The reason this is cosine and not distance.

    A long paragraph and a short sentence about the same thing produce arrows of
    different lengths pointing the same way. They should score as identical.
    """
    short = [1.0, 0.0, 0.0]
    long_version = [50.0, 0.0, 0.0]

    assert cosine_similarity(short, [long_version])[0] == pytest.approx(1.0)


def test_unrelated_scores_zero_and_opposite_scores_minus_one():
    """Where the 0-to-1 promise in docs/api.md comes from.

    The raw measurement runs -1 to 1. The route clamps the negative half to 0,
    and this is the test that says the negative half is real rather than
    theoretical.
    """
    query = [1.0, 0.0]

    scores = cosine_similarity(query, [[0.0, 1.0], [-1.0, 0.0]])

    assert scores[0] == pytest.approx(0.0)
    assert scores[1] == pytest.approx(-1.0)


def test_one_score_comes_back_per_row_in_the_same_order():
    query = [1.0, 0.0]
    rows = [[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]]

    scores = cosine_similarity(query, rows)

    assert len(scores) == 3
    assert scores[0] > scores[1]
    assert scores[0] == scores[2]


def test_nothing_to_compare_against_is_an_empty_answer():
    """A fresh install with no notes in it. Ordinary, not an error."""
    assert len(cosine_similarity([1.0, 0.0], [])) == 0


def test_an_all_zero_vector_scores_zero_rather_than_nan():
    """The guard that stops a divide by zero poisoning the ranking.

    Without it numpy returns nan, which is neither greater nor less than any
    other score, so it sorts unpredictably and shows up as a blank in the UI
    rather than as an error anybody would notice.
    """
    scores = cosine_similarity([0.0, 0.0], [[1.0, 0.0]])

    assert scores[0] == pytest.approx(0.0)
    assert not np.isnan(scores).any()
