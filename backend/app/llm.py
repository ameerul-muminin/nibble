"""Ask the language model a question, and hold it to the notes it was given.

Alif owns this file. It is the only place in the backend that calls the chat
model, so when an answer comes out wrong there is exactly one file to read.

**The prompt is the product.** Everything before this slice — reading a PDF,
cutting it up, turning it into numbers, finding the closest pieces — exists to
put the right paragraphs in front of a model. What makes Nibble worth trusting
is the next bit: that when your notes do not answer the question, it says so
instead of writing something plausible.

That refusal is the single most important behaviour in the project, and it is
not a code path. It is the wording of ``SYSTEM_PROMPT`` below, plus the fact
that nothing except the retrieved chunks is ever put in front of the model. A
model cannot quote a page it was never shown.

Three things, in the order they are used:

    build_context(chunks)  -> the notes, as text the model can read
    answer(question, text) -> the sentence that comes back
    AnswerUnavailable      -> raised when we could not get one at all
"""

import requests

from app import config

# How long to wait for an answer before giving up.
#
# Longer than it usually takes, shorter than somebody will sit staring at a
# spinner. A 70B model on Groq answers a study question in a few seconds; if it
# has not by now, something is wrong and saying so beats waiting.
_TIMEOUT_SECONDS = 30

# The instructions the model sees before it sees anything else.
#
# Worth reading as prose rather than as configuration, because every line is
# load-bearing and each one is there to stop a specific failure:
#
#   Rule 1 is the whole point. Without it the model answers from what it learnt
#   in training — confident, fluent, often correct, and completely disconnected
#   from the student's notes. That is the exact thing this project exists not to
#   do. "You cannot answer" has to be an explicitly allowed outcome, or a model
#   treats answering as mandatory and reaches for whatever it has.
#
#   Rule 2 gives the refusal exact words. Left to itself a model hedges rather
#   than refuses — half an answer with a disclaimer on it, which reads as an
#   answer. One fixed sentence is unmistakable, and it is one somebody can act
#   on: go and add the chapter it should be in.
#
#   Rule 3 exists because rule 2 used to end "never soften this into a partial
#   answer", and that clause was wrong in a way only real use revealed. Asked to
#   name six experiments when the notes held five, Nibble answered: "That isn't
#   in your notes yet. Your notes cover Experiments 1, 3, 4, 5, and 6." It had
#   obeyed the prompt exactly and produced a refusal that contradicts itself in
#   its own second sentence — while withholding five answers the student had
#   every right to.
#
#   The distinction the prompt was missing is between *nothing* and *not
#   everything*. Nothing is a refusal, and that has not moved an inch. Not
#   everything is an answer plus an honest note about the gap, which is what a
#   good tutor does and what somebody revising actually needs. Getting five of
#   six with the sixth named as missing beats being told to go away.
#
#   Rule 4 is what makes any of this checkable. The page number is how a student
#   goes and looks, and looking is the only real defence against a wrong answer.
#
#   Rule 5 is Nibble's voice from docs/design.md: warm, brief, plain words.
#
# None of this is hidden from the person asking. The pages it cites are the same
# pages shown as chips under the answer, so every claim can be checked against
# the note it came from.
SYSTEM_PROMPT = """\
You are Nibble, a friendly study companion. A student has asked a question, and \
you have been given the pieces of their own notes that came closest to it.

1. Answer using ONLY those notes. Do not use anything you know from anywhere \
else, even if you are certain it is correct, and even if the notes look wrong.
2. If the notes contain NOTHING that answers the question, reply with exactly: \
"That isn't in your notes yet." You may add one short sentence saying what they \
do cover instead. Never guess and never fill a gap.
3. If the notes answer PART of the question, give that part and then say plainly \
what is missing — "Your notes don't have the second one." Do not refuse a \
question you can partly answer, and do not invent the rest to complete it. \
Rule 2 is for when there is nothing, not for when there is something incomplete.
4. Cite the page for anything you say, like this: (p. 4). Cite the page the \
words actually came from.
5. Be warm and brief. Short sentences, plain words, no preamble. Do not say \
"according to the notes" or "based on the provided context" — just answer.
"""


class AnswerUnavailable(RuntimeError):
    """We could not get an answer at all — no key, no network, or an unreadable reply.

    Its own type so a route can catch exactly this and turn it into one plain
    sentence, the same way ``ocr.OcrUnavailable`` and
    ``embeddings.EmbeddingUnavailable`` already work.

    This is **not** the model refusing to answer. A refusal is a successful call
    that comes back saying "That isn't in your notes yet." — that is Nibble
    working exactly as intended, and it travels home as an ordinary answer. This
    exception means we never reached the model, or could not read what it sent.
    """


def build_context(chunks: list[dict]) -> str:
    """Format the retrieved chunks as the block of notes the model reads.

    ``chunks`` is what the retrieval step hands over: dicts with ``filename``,
    ``page`` and ``content``. What comes back looks like this::

        [biology-ch4.pdf - p.4]
        Osmosis is the net movement of water across a...

        [biology-ch4.pdf - p.5]
        The membrane is described as selectively permeable...

    The label above each piece is the entire reason the model can cite a page.
    It can only write "(p. 4)" because it was shown "p.4" next to those exact
    words. Take the labels away and the citations become invention — the failure
    this slice exists to prevent, arriving through the back door.

    Blank lines between the pieces, on purpose. Run them together and a model
    reads the end of one page and the start of the next as one continuous
    passage, then writes a sentence spanning both and cites it to one page.
    """
    return "\n\n".join(
        f"[{chunk['filename']} - p.{chunk['page']}]\n{chunk['content']}" for chunk in chunks
    )


def _as_messages(history: list[dict] | None) -> list[dict]:
    """Turn Nibble's own record of the conversation into what the API expects.

    We say "nibble"; the API says "assistant". Translating here, in one place,
    means the rest of the project never has to hold the provider's vocabulary in
    its head — routes.py and the frontend both talk about turns being from the
    person or from Nibble, which is what they are.

    Anything with an unexpected role is dropped rather than passed through. The
    route already rejects those with a 422, so reaching this is a bug rather
    than a user; dropping keeps a bug from turning into a malformed request that
    fails with something unreadable from the provider.
    """
    if not history:
        return []

    roles = {"user": "user", "nibble": "assistant"}

    return [
        {"role": roles[turn["role"]], "content": turn["content"]}
        for turn in history
        if turn.get("role") in roles and turn.get("content")
    ]


def answer(question: str, context: str, history: list[dict] | None = None) -> str:
    """Send one question and its notes to the model, and return what it says.

    ``context`` is the string from ``build_context``. This function does not
    search, does not decide what counts as relevant, and does not build the
    sources list. It asks about the notes it is handed and nothing else, which
    is what keeps it short enough to read and testable with a fake.

    ``history`` is the recent conversation, oldest first, as
    ``{"role": "user" | "nibble", "content": ...}``. It defaults to nothing, so
    every existing caller and test keeps working unchanged.

    **The history is context, not evidence, and the difference is the whole
    point of this project.** Past turns are replayed so "explain the third one"
    knows what "the third one" is. They are not notes, and rule 1 in the prompt
    still binds the answer to the pieces in ``context`` — otherwise Nibble could
    answer a follow-up out of something it said earlier, which is exactly the
    "confident and disconnected from your notes" failure this file exists to
    prevent, arriving one turn later than usual.

    Raises ``AnswerUnavailable`` for every way this can fail, and never lets the
    provider's own error text out to a person: it is written for whoever is
    being billed, not for somebody trying to revise, and it can carry internals.
    """
    if not config.GROQ_API_KEY:
        raise AnswerUnavailable(
            "No GROQ_API_KEY is set, so there is nothing to ask. Get a free key at "
            "https://console.groq.com/keys and put it in backend/.env"
        )

    try:
        response = requests.post(
            f"{config.GROQ_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            json={
                "model": config.CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    # The conversation so far, between the rules and this
                    # question. It sits here rather than being pasted into the
                    # message below so the model reads it as things that were
                    # said, not as more notes to answer from — the notes are the
                    # labelled block below, and only that block gets cited.
                    *_as_messages(history),
                    # Notes first, question last, in one user message. The order
                    # matters more than it looks: a model weighs the last thing
                    # it read most heavily, and the last thing it should read is
                    # the question it has to answer.
                    {
                        "role": "user",
                        "content": (
                            f"Here are the pieces of my notes that matched:\n\n{context}\n\n"
                            f"My question: {question}"
                        ),
                    },
                ],
                # Low, not zero. Zero is for transcription, where there is one
                # right answer and copying it exactly is the job — which is why
                # ocr.py uses it. Explaining something has more than one good
                # phrasing, and a little room produces a sentence that reads
                # like a person wrote it. It does not license invention; rule 1
                # in the prompt does that work.
                "temperature": 0.2,
                # A ceiling on the answer, not a target. It stops a model that
                # has decided to write an essay from turning a five-second wait
                # into a thirty-second one, and it bounds what a single question
                # can spend of a free-tier allowance shared with reading scans.
                "max_tokens": config.ANSWER_MAX_OUTPUT_TOKENS,
                # How much the model thinks before answering — see config.py for
                # why it is "low" rather than off or higher.
                #
                # Unlike the vision model in ocr.py, this one keeps its thinking
                # in a separate `reasoning` field instead of wrapping it in
                # <think> tags inside the answer, so there is nothing to strip
                # out here. Worth knowing before swapping the model: a model
                # that inlines its thinking would put it straight on screen.
                "reasoning_effort": config.ANSWER_REASONING_EFFORT,
            },
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise AnswerUnavailable(f"Could not reach the answering service: {exc}") from exc

    if response.status_code == 429:
        # The same split as ocr.py: 429 covers both "too fast just now" and
        # "nothing left today", and those need different advice. Unlike reading
        # a scan, this one is not retried here — somebody is waiting on this
        # answer, and a silent twenty-second pause looks exactly like the app
        # having hung.
        body = response.text.lower()
        if "per day" in body or "rpd" in body:
            raise AnswerUnavailable(
                "Nibble has answered as many questions as it can today. Try again tomorrow."
            )
        raise AnswerUnavailable("Nibble is being asked a lot at once. Try again in a moment.")

    if not response.ok:
        # Deliberately not passing the provider's message through, for the same
        # reason ocr.py does not.
        raise AnswerUnavailable(f"The answering service answered with {response.status_code}.")

    try:
        text = response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise AnswerUnavailable("The answering service sent back something unexpected.") from exc

    text = text.strip()

    # A successful call that returns nothing is the quiet failure in this file.
    # It would arrive on screen as an empty bubble: no answer, no error, nothing
    # to try. Rare, and it costs one line to turn into a sentence.
    if not text:
        raise AnswerUnavailable(
            "Nibble read your notes but came back with nothing. Try asking again."
        )

    return text
