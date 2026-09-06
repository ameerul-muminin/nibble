"""Every setting the app needs, in one place.

Nothing else in the backend should read os.getenv directly. If you need a new
setting, add it here and read it from here — then there is exactly one place to
look when something is configured wrong.
"""

import os

from dotenv import load_dotenv

# Reads the .env file sitting next to this project and puts it into os.environ.
# If there is no .env file, the defaults below are used instead.
load_dotenv()

# --- Database (slice 1 onwards) ------------------------------------------
# SQLite is just a file on disk. This is its name. No server, no password.
DATABASE_FILE = os.getenv("DATABASE_FILE", "nibble.db")

# --- Embeddings (slice 3) ------------------------------------------------
# These run on your own laptop. No API key, no internet after the first
# download, no limit on how many you make.
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384  # this model turns any text into exactly 384 numbers

# --- The language model (slice 4) ----------------------------------------
# Groq runs open-source models for free. Get a key (no card needed) at
# https://console.groq.com/keys and put it in your .env file.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
CHAT_MODEL = "llama-3.3-70b-versatile"

# --- Reading handwriting and scans (slice 1.5) ---------------------------
# A scanned or handwritten PDF has no text in it to pull out — it is a picture
# of writing. The only way to read one is to look at it, which is what a vision
# model does. This runs on the same free Groq key as the chat model above.
VISION_MODEL = "qwen/qwen3.6-27b"

# Turn the whole thing off if it is causing trouble on demo day. When this is
# false, a scanned upload is refused with a plain sentence instead.
OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() == "true"

# How wide to draw each page before sending it, in pixels. Bigger is easier to
# read and slower to send; 1600 is a good middle for handwriting.
OCR_IMAGE_WIDTH = 1600

# How many pages of a scan we will read in one upload.
#
# This is small for a real reason, found by running it. The free tier allows
# 1000 output tokens PER MINUTE, and it reserves against max_tokens below
# rather than against what actually comes back — so the real throughput is
# about two pages a minute, not two hundred. Five pages is already a two and a
# half minute upload. Twenty would look like the app had hung.
OCR_MAX_PAGES = 5

# How much text we allow back from one page.
#
# This is not a preference, it is a hard requirement. Groq's free tier caps
# OUTPUT tokens per minute at 1000, and it checks the *expected* output before
# running anything — which, with no limit set, is the model's maximum. The
# request is then rejected with a 429 before a single page is read. Asking for
# 900 keeps it under the cap.
#
# 450 tokens is roughly 300-350 words, which comfortably covers a normal page of
# handwritten notes. It is deliberately not higher: the cap is per minute and is
# reserved against this number, so doubling it halves how many pages we can read
# in a minute. A very dense page could be cut short — that trade is on purpose.
OCR_MAX_OUTPUT_TOKENS = 450

# When the per-minute allowance runs out mid-scan, wait and try that page again
# rather than failing an upload that was halfway done.
OCR_RETRY_ATTEMPTS = 3
OCR_RETRY_WAIT_SECONDS = 20

# --- Tuning knobs --------------------------------------------------------
CHUNK_SIZE = 900  # how many characters in one piece of a document
CHUNK_OVERLAP = 150  # how much each piece repeats of the one before it
TOP_K = 5  # how many pieces we hand to the model when answering

# --- Who is allowed to call us -------------------------------------------
# A browser will refuse to let a page on :5173 call :8000 unless we say so.
CORS_ORIGINS = ["http://localhost:5173"]
