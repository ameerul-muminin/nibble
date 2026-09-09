"""Reading pages that are pictures of writing, not text.

Alif owns this file.

A PDF made by typing carries its words inside it, and `files.py` pulls them out
with `pypdf`. A scan, a photo of a whiteboard, or a page of handwriting carries
no words at all — it is an image. There is nothing to extract, so `pypdf`
returns empty strings and the note looks fine while containing nothing.

The only way to read one is to *look* at it. That is what a vision model does:
you hand it the page as a picture and it writes back what it can see. It is the
same thing a person does, and it is the same thing Claude does when you paste a
photo of your notes into it — there is no clever text trick underneath.

Two steps, and both are ordinary:

1. `pypdfium2` draws each PDF page into a PNG. It is a normal pip install with
   no separate program to download, which is why it is here rather than
   `pdf2image` — that one needs poppler installed by hand, and on Windows that
   is exactly the kind of afternoon this project keeps avoiding.
2. The picture goes to Groq's vision model, base64-encoded, with an instruction
   to transcribe and nothing else. Same free key as the chat model in slice 4.

The result is plain text, so everything downstream — chunking, embedding,
searching, answering — carries on without knowing any of this happened.
"""

import base64
import sys
import time
from io import BytesIO

import pypdfium2
import requests

from app import config

# What we ask the model to do with the picture. Deliberately narrow: it is
# transcribing, not summarising and not explaining. A model told to "describe
# this image" will happily write "a page of handwritten biology notes", which
# is useless — we want the words themselves.
_PROMPT = (
    "Transcribe all the text in this image, exactly as written. "
    "This is a page from someone's study notes and may be handwritten. "
    "Keep the original wording, line breaks and any headings. "
    "Do not summarise, do not explain, and do not add commentary. "
    "If the page has no writing on it at all, reply with nothing."
)

# Groq is fast, but a big image still takes a few seconds. This is per page.
_TIMEOUT_SECONDS = 60


class OcrUnavailable(Exception):
    """Raised when a page could not be read. The route turns this into a sentence."""


def page_images(pdf_bytes: bytes, max_pages: int) -> list[tuple[int, bytes]]:
    """Draw each page of a PDF as a PNG.

    Returns a list of (page_number, png_bytes), page numbers starting at 1 so
    they line up with what `files.py` produces for a text PDF.
    """
    pdf = pypdfium2.PdfDocument(pdf_bytes)
    try:
        images: list[tuple[int, bytes]] = []
        for index in range(min(len(pdf), max_pages)):
            page = pdf[index]

            # `scale` is a multiplier on the page's natural size, so a wide page
            # and a narrow one both come out around the width we asked for.
            scale = config.OCR_IMAGE_WIDTH / max(page.get_size()[0], 1)
            bitmap = page.render(scale=scale)

            buffer = BytesIO()
            bitmap.to_pil().save(buffer, format="PNG")
            images.append((index + 1, buffer.getvalue()))
        return images
    finally:
        pdf.close()


class RateLimited(OcrUnavailable):
    """Out of allowance for the moment. Unlike its parent, this one is worth retrying."""


def read_image(png_bytes: bytes) -> str:
    """Ask the vision model what a single picture says, waiting out rate limits.

    The free tier allows 1000 output tokens a minute and reserves against
    max_tokens rather than what actually comes back, so roughly two pages fit
    in a minute. Reading page three of a scan therefore hits the limit as a
    matter of course, not as an error — so waiting and trying again is the
    normal path here, not an exceptional one.

    Raises OcrUnavailable if it still cannot be read. The caller turns that
    into a plain sentence; the user never sees a provider error.
    """
    for attempt in range(config.OCR_RETRY_ATTEMPTS):
        try:
            return _request_transcription(png_bytes)
        except RateLimited:
            last = attempt == config.OCR_RETRY_ATTEMPTS - 1
            if last:
                raise
            time.sleep(config.OCR_RETRY_WAIT_SECONDS)

    # Unreachable: the loop either returns or raises on its final attempt.
    raise OcrUnavailable("Nibble could not read that page.")


def _request_transcription(png_bytes: bytes) -> str:
    """One attempt at reading one picture. Raises RateLimited if it is worth retrying."""
    if not config.GROQ_API_KEY:
        raise OcrUnavailable(
            "No GROQ_API_KEY is set, so there is nothing to send the page to. "
            "Get a free key at https://console.groq.com/keys and put it in .env"
        )

    # The image travels inside the JSON as base64 text, in a data: URL. That is
    # the shape every OpenAI-compatible vision API expects, Groq included.
    encoded = base64.b64encode(png_bytes).decode("ascii")

    try:
        response = requests.post(
            f"{config.GROQ_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            json={
                "model": config.VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{encoded}"},
                            },
                        ],
                    }
                ],
                # Transcription, not invention. Low temperature keeps it copying
                # what is on the page rather than guessing plausible words.
                "temperature": 0,
                # Required, not optional — see OCR_MAX_OUTPUT_TOKENS in config.
                # Without it Groq assumes the model's maximum, decides that
                # exceeds the free tier's output-per-minute cap, and rejects the
                # request with a 429 before reading anything.
                "max_tokens": config.OCR_MAX_OUTPUT_TOKENS,
                # This model thinks out loud by default, and wraps the thinking
                # in <think> tags before the answer. Two problems: the tags end
                # up stored as if they were your notes, and the thinking burns
                # the output budget above — enough of it to truncate a real
                # page. Transcribing does not need reasoning; it needs reading.
                "reasoning_effort": "none",
            },
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        # Not `{exc}`: a requests error carries the URL it was calling and
        # whatever the network layer had to say, none of it written for a
        # student. The cause stays on the traceback via `from exc`.
        print(f"[ocr] could not reach the reading service: {exc}", file=sys.stderr)
        raise OcrUnavailable(
            "Nibble couldn't reach the service that reads handwriting. Try again in a moment."
        ) from exc

    if response.status_code == 429:
        # 429 covers both "too many just now" and "nothing left today", and the
        # two need different advice. Groq says which in the body; the wording
        # below is ours, because theirs mentions upgrading to a paid tier and
        # this project does not have one.
        body = response.text.lower()
        if "per day" in body or "rpd" in body:
            # Nothing left today. Waiting will not help, so do not retry.
            raise OcrUnavailable(
                "Nibble has read as much handwriting as it can today. Try again tomorrow."
            )
        raise RateLimited("Nibble is reading too much at once.")

    if not response.ok:
        # Deliberately not passing the provider's message through — it is not
        # written for a student and can contain internals.
        print(f"[ocr] the reading service returned {response.status_code}", file=sys.stderr)
        raise OcrUnavailable(
            "The service that reads handwriting isn't answering properly just now. "
            "Try again in a few minutes."
        )

    try:
        return _strip_thinking(response.json()["choices"][0]["message"]["content"])
    except (KeyError, IndexError, ValueError) as exc:
        raise OcrUnavailable("The reading service sent back something unexpected.") from exc


def _strip_thinking(text: str) -> str:
    """Remove a <think>...</think> block if the model produced one anyway.

    reasoning_effort="none" should stop these appearing at all. This is here
    because the cost of being wrong is silent and nasty: the thinking would be
    stored as though it were the words on the page, then chunked, embedded, and
    eventually quoted back to a student as their own notes.
    """
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


def read_pdf(pdf_bytes: bytes) -> list[tuple[int, str]]:
    """Read every page of a scanned PDF, returning the same shape as extract_text."""
    images = page_images(pdf_bytes, config.OCR_MAX_PAGES)
    return [(number, read_image(png)) for number, png in images]
