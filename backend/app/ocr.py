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


def read_image(png_bytes: bytes) -> str:
    """Ask the vision model what a single picture says.

    Raises OcrUnavailable if the request fails for any reason. The caller turns
    that into a plain sentence — the user never sees a provider error.
    """
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
            },
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise OcrUnavailable(f"Could not reach the reading service: {exc}") from exc

    if response.status_code == 429:
        raise OcrUnavailable("The free daily limit for reading handwriting has run out.")

    if not response.ok:
        # Deliberately not passing the provider's message through — it is not
        # written for a student and can contain internals.
        raise OcrUnavailable(f"The reading service answered with {response.status_code}.")

    try:
        return response.json()["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError) as exc:
        raise OcrUnavailable("The reading service sent back something unexpected.") from exc


def read_pdf(pdf_bytes: bytes) -> list[tuple[int, str]]:
    """Read every page of a scanned PDF, returning the same shape as extract_text."""
    images = page_images(pdf_bytes, config.OCR_MAX_PAGES)
    return [(number, read_image(png)) for number, png in images]
