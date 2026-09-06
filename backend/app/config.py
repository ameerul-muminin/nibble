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

# A scan of a whole textbook would eat the daily free allowance in one upload,
# so refuse politely past this many pages rather than silently burning it.
OCR_MAX_PAGES = 20

# --- Tuning knobs --------------------------------------------------------
CHUNK_SIZE = 900  # how many characters in one piece of a document
CHUNK_OVERLAP = 150  # how much each piece repeats of the one before it
TOP_K = 5  # how many pieces we hand to the model when answering

# --- Who is allowed to call us -------------------------------------------
# A browser will refuse to let a page on :5173 call :8000 unless we say so.
CORS_ORIGINS = ["http://localhost:5173"]
