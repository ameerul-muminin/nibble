"""Ask the model to write questions from a note, and check what comes back.

Alif owns this file. It is the second place in the backend that calls the chat
model, and it is deliberately shaped like the first: a prompt, one function that
sends it, and one exception type for every way it can fail. If you have read
llm.py, you have already read most of this.

**The difference from llm.py is what happens to the reply.** ``llm.answer``
takes a sentence and hands it straight to a person, who can read it and judge
it. A quiz is not read, it is *used* — the browser marks answers against
``correct`` without anybody checking it first. So a reply that is nearly right
is worse here than a reply that fails: a question with ``correct: 4`` and four
options marks every answer wrong, for one person practising alone or for a whole
class at once, and nothing on screen looks broken.

That is why the second half of this file is a validator rather than a
``json.loads``. **Every field is checked before a single row is written.** A
model returning almost-right JSON is the realistic failure here, not a model
returning nonsense.

Three things, in the order they are used:

    build_prompt(chunks)     -> the note, as much of it as fits
    make_questions(...)      -> validated questions, ready to store
    QuizUnavailable          -> raised when we could not get usable ones
"""

import json

import requests

from app import config, llm

# Longer than llm.py's 30 seconds, and for a plain reason: this writes ten
# questions where that writes one sentence, at a higher reasoning effort. The
# route warns the browser it takes a few seconds; this is the ceiling before we
# stop waiting and say so.
_TIMEOUT_SECONDS = 60

# How many options every question has. Four is not configurable, and that is on
# purpose rather than an oversight: `correct` is an index into this list, the
# frontend renders exactly four buttons, and the validator below rejects
# anything else. Making it a setting would mean three places that can disagree.
OPTION_COUNT = 4

QUIZ_SYSTEM_PROMPT = """\
You write multiple-choice questions from a student's own notes, so they can \
test themselves on what they actually studied.

1. Every question must be answerable from the notes alone. Do not use anything \
you know from elsewhere, and do not write a question the notes do not answer.
2. Give exactly four options. Exactly one is correct.
3. The three wrong options must be plausible — the same kind of thing as the \
right answer, and wrong for a reason a student could work out. Never pad with \
options that are obviously silly; a question anybody can guess teaches nothing.
4. Say which page each question came from. Use the page numbers shown in the \
notes, and only those.
5. Ask about what the notes explain, not about how they are laid out. Never \
write a question about a page number, a heading, an answer key, or how many \
sections there are.
6. Vary what you ask about. Do not write four questions about one paragraph \
while the rest of the notes go untouched.

Reply with JSON only, in exactly this shape, and nothing else:

{"questions": [
  {"prompt": "...", "options": ["...", "...", "...", "..."], "correct": 0, "page": 4}
]}

`correct` is the index of the right option, 0 to 3.

If the notes cannot support the number of questions asked for, return fewer. \
Never invent material to reach the count.
"""


class QuizUnavailable(RuntimeError):
    """We could not get a usable quiz — no key, no network, or an unusable reply.

    Its own type for the same reason ``llm.AnswerUnavailable``,
    ``ocr.OcrUnavailable`` and ``embeddings.EmbeddingUnavailable`` have one: so
    the route can catch exactly this and turn it into one plain sentence.

    **"Unusable" covers more here than in llm.py**, and deliberately. There, a
    reply we could read was a success. Here a reply we can read but cannot trust
    — three options instead of four, a `correct` of 7, a page that is not in the
    note — is also this exception, because storing it would put a broken
    question in front of a class.
    """


def build_prompt(chunks: list[dict]) -> str:
    """Format as much of the note as fits into the model's context budget.

    ``chunks`` is what the route reads out of the database: dicts with
    ``filename``, ``page`` and ``content``, in reading order.

    **This reuses ``llm.build_context`` rather than formatting chunks a second
    time.** Those page labels are the entire reason a question can name the page
    it came from, exactly as they are the reason an answer can cite one — and
    two functions that both have to produce ``[file - p.4]`` is one of them
    quietly drifting later.

    Unlike ``/ask`` there is no query to retrieve against: "write five questions
    about this chapter" has no question to match chunks to. So this takes the
    note from the beginning until ``QUIZ_MAX_CONTEXT_CHARS`` runs out. For most
    chapters that is all of it; for a very long one the questions come from the
    start, which is predictable, and the prompt says so rather than letting the
    model imply it covered the end.
    """
    kept: list[dict] = []
    budget = config.QUIZ_MAX_CONTEXT_CHARS

    for chunk in chunks:
        cost = len(chunk["content"])
        if kept and cost > budget:
            break
        kept.append(chunk)
        budget -= cost

    return llm.build_context(kept)


def make_questions(context: str, count: int, pages: set[int]) -> list[dict]:
    """Ask for ``count`` questions about ``context``, and return only valid ones.

    ``pages`` is every page number that really exists in the note. It is passed
    in rather than parsed back out of ``context`` because the route already knows
    it, and because a question citing a page the note does not have is one of the
    things worth refusing.

    Returns a list of ``{"prompt", "options", "correct", "page"}``, already
    checked. Raises ``QuizUnavailable`` if the model could not be reached, or if
    nothing usable came back.

    Fewer than ``count`` is a valid result — the note may not support that many,
    and the prompt asks for fewer rather than invented ones. Zero is not: that is
    a failure that would otherwise look like an empty quiz.
    """
    if not config.GROQ_API_KEY:
        raise QuizUnavailable(
            "No GROQ_API_KEY is set, so Nibble cannot write questions. Get a free key "
            "at https://console.groq.com/keys and put it in backend/.env"
        )

    try:
        response = requests.post(
            f"{config.GROQ_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            json={
                "model": config.CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": QUIZ_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Here are my notes:\n\n{context}\n\n"
                            f"Write {count} multiple-choice questions from them."
                        ),
                    },
                ],
                # Asking the API itself to guarantee JSON, rather than hoping the
                # prompt is obeyed. It removes the most common failure — a model
                # wrapping perfectly good JSON in ```json fences or a sentence of
                # preamble — without removing the need for the validator below,
                # which is about the SHAPE being right, not the syntax.
                "response_format": {"type": "json_object"},
                # Lower than llm.py's 0.2. A quiz has no voice to get right, and
                # the variation that makes an answer read naturally makes a
                # question's distractors wander.
                "temperature": 0.1,
                "max_tokens": config.QUIZ_MAX_OUTPUT_TOKENS,
                "reasoning_effort": config.QUIZ_REASONING_EFFORT,
            },
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise QuizUnavailable(f"Could not reach the question writer: {exc}") from exc

    if response.status_code == 429:
        # The same split as llm.py and ocr.py: "too fast just now" and "nothing
        # left today" need different advice, and somebody is waiting on this.
        body = response.text.lower()
        if "per day" in body or "rpd" in body:
            raise QuizUnavailable(
                "Nibble has written as many questions as it can today. Try again tomorrow."
            )
        raise QuizUnavailable("Nibble is being asked a lot at once. Try again in a moment.")

    if not response.ok:
        raise QuizUnavailable(f"The question writer answered with {response.status_code}.")

    try:
        raw = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise QuizUnavailable("The question writer sent back something unexpected.") from exc

    questions = _validate(raw, pages)

    if not questions:
        raise QuizUnavailable(
            "Nibble read that note but could not write questions from it. "
            "It may be too short, or mostly pictures."
        )

    return questions[:count]


def _validate(raw: str, pages: set[int]) -> list[dict]:
    """Turn the model's JSON into questions we are willing to store.

    **A bad question is dropped, not repaired.** There is no sensible way to
    guess what a model meant by ``correct: 7``, and a guess would put a question
    with the wrong answer key in front of a class — which is worse than one
    fewer question, because nothing about it looks wrong.

    A reply where *every* question is bad ends up as an empty list, which
    ``make_questions`` turns into ``QuizUnavailable``. So "the model ignored the
    format entirely" and "the model wrote nothing usable" arrive at the same
    place, which is the same sentence to whoever is waiting.
    """
    try:
        payload = json.loads(raw)
    except ValueError as exc:
        raise QuizUnavailable("The question writer did not send back usable questions.") from exc

    # A dict with "questions" is what was asked for. A bare list is the obvious
    # near-miss and costs one line to accept, so it is accepted.
    if isinstance(payload, dict):
        candidates = payload.get("questions")
    elif isinstance(payload, list):
        candidates = payload
    else:
        candidates = None

    if not isinstance(candidates, list):
        raise QuizUnavailable("The question writer did not send back usable questions.")

    valid: list[dict] = []

    for item in candidates:
        question = _validate_one(item, pages)
        if question is not None:
            valid.append(question)

    return valid


def _validate_one(item: object, pages: set[int]) -> dict | None:
    """Check one question. Returns it cleaned up, or None if it cannot be used.

    Every rule here maps to something that would otherwise reach a student:

    - not four options, or an out-of-range ``correct``: the quiz marks every
      answer wrong and looks fine doing it
    - a blank prompt or option: an unanswerable question
    - duplicate options: two identical buttons where only one of them scores
    - a page the note does not have: the "check it against the page" promise
      breaks, and that promise is why anybody trusts this
    """
    if not isinstance(item, dict):
        return None

    prompt = item.get("prompt")
    options = item.get("options")
    correct = item.get("correct")
    page = item.get("page")

    if not isinstance(prompt, str) or not prompt.strip():
        return None

    if not isinstance(options, list) or len(options) != OPTION_COUNT:
        return None

    if not all(isinstance(option, str) and option.strip() for option in options):
        return None

    cleaned = [option.strip() for option in options]

    # Two identical options means one right answer and one that looks identical
    # and scores zero. Unanswerable, and infuriating in a way that reads as the
    # app being broken rather than the question being bad.
    if len(set(cleaned)) != OPTION_COUNT:
        return None

    # `bool` is a subclass of `int` in Python, so True would otherwise sail
    # through as the index 1. Worth one clause: a model that answers `correct:
    # true` is exactly the almost-right reply this validator exists for.
    if isinstance(correct, bool) or not isinstance(correct, int):
        return None

    if not 0 <= correct < OPTION_COUNT:
        return None

    if isinstance(page, bool) or not isinstance(page, int) or page not in pages:
        return None

    return {
        "prompt": prompt.strip(),
        "options": cleaned,
        "correct": correct,
        "page": page,
    }
