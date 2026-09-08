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

# How many pieces the model is given at once.
#
# This is a memory setting, not a speed one, and it is the difference between
# the backend fitting on a free host and being killed by it. `fastembed`
# defaults to 256, and the whole upload is handed over in one call — so peak
# memory grows with the size of the document rather than staying put.
#
# Measured on real 900-character English, embedding a 400-piece document:
#
#     batch_size=256 (the default)   1275 MB
#     batch_size=32                   473 MB
#     batch_size=16                   341 MB
#     batch_size=8                    278 MB
#
# Every one of those took the same ~30 seconds, so the smaller batch is free.
# 8 was chosen because the deploy target has 512 MB and the idle backend with
# the model loaded is already 227 MB of it.
#
# The thing worth understanding: this makes memory *flat*. At 8, a 40-piece
# chapter and a 400-piece book both peak at the same number. Without it, the
# ceiling is whatever the biggest file anybody uploads happens to be.
EMBED_BATCH_SIZE = 8

# --- The language model (slice 4) ----------------------------------------
# Groq runs open-source models for free. Get a key (no card needed) at
# https://console.groq.com/keys and put it in your .env file.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
#
# This was `llama-3.3-70b-versatile` until slice 4 was actually run against
# Groq, at which point every question came back as a 404: Groq had retired it.
# A hosted model is not a decision you make once — the provider can withdraw it
# and your app breaks without a line of your code changing. `GET /models` on the
# same key lists what is really there, and that is the thing to check first when
# answering suddenly stops working.
CHAT_MODEL = "openai/gpt-oss-120b"

# How hard the model thinks before it answers.
#
# It lives next to CHAT_MODEL because it belongs to it: this setting only means
# anything to a model that reasons, and the two have to be changed together.
#
# "low" was chosen by running both. On the same questions, "medium" produced
# answers no better and spent two to four times the tokens getting there — and
# on a free tier shared with reading handwriting, tokens are the budget. It is
# not zero, because deciding "is this actually in the notes?" is the one piece
# of thinking this project genuinely wants the model to do.
ANSWER_REASONING_EFFORT = "low"

# How long an answer is allowed to be.
#
# A ceiling, not a target — most answers come back far shorter, because the
# prompt asks for brief ones. It is here for the case where the model decides to
# write an essay: that turns a five-second wait into a thirty-second one, and
# spends a free-tier allowance this project shares with reading handwriting.
#
# 700 tokens is roughly 500 words, which is a long answer to a study question
# and a short one to anything else. Raise it if answers start getting cut off
# mid-sentence; that is the symptom to watch for.
ANSWER_MAX_OUTPUT_TOKENS = 700

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

# How many pieces we hand to the model when answering.
#
# **This was 5, and 5 was measurably too few.** The number was picked before
# anybody had asked a real question of a real document, and the first person who
# did found it immediately: asked to name the six experiments in an 11-page lab
# PDF, Nibble named one. It was not making things up — it had been shown five
# pieces, and four of the six headings were not among them. Retrieval starved it
# and the model answered from what it had.
#
# Measured on that PDF: reaching every one of the six experiment headings needed
# 11 of its 12 pieces. So full coverage is not what this number can buy, and
# chasing it is the wrong instinct. What it can buy is enough room that a
# document-wide question ("what is this about", "what does it cover") sees more
# than one corner of the file.
#
# 12 rather than more, and this is the real tension: every extra piece is more
# text that is only loosely related to the question, and the most important
# behaviour in this project is that Nibble REFUSES when your notes do not cover
# something. Pile in enough weakly-matching text and a model starts finding
# something to say in it. 12 is roughly 11,000 characters — a big enough view of
# a chapter to answer "what is this about", small enough that a genuine miss
# still looks like a miss.
#
# Raise it and re-check the refusal, not just the answers. That is the thing
# that breaks first, and it breaks quietly.
TOP_K = 12

# How much of the conversation is used to shape the next question. Slice 4 fix.
#
# The frontend draws a chat, so people write follow-ups — "name them", "why?",
# "explain the third one". Every one of those is meaningless on its own, and
# before this the backend embedded it on its own and searched for it. "name
# them" matched nothing in particular, returned near-random pieces, and the
# answer built from them read as the model inventing things. It was not. It was
# a search handed a question with the meaning taken out.
#
# 4 turns is two exchanges, which covers "what are the experiments" -> "name
# them" -> "explain the third one" without letting a long session drag the
# search back toward whatever was being discussed ten questions ago. A follow-up
# is about what was JUST said; older turns are noise dressed as context.
ASK_HISTORY_TURNS = 4

# The most of one past turn we will read. Nothing from a browser is trusted, and
# this is the cap that makes that true here: without it a crafted transcript
# could push the actual notes out of the model's context, which is the one way
# to make Nibble answer from something other than your notes.
ASK_HISTORY_CHARS = 1000

# --- Who is allowed to call us -------------------------------------------
# A browser will refuse to let a page on :5173 call :8000 unless we say so.
#
# This is a list because the deployed frontend lives somewhere else entirely —
# a vercel.app address — and both have to work: the same backend serves your
# laptop while you develop and the real site once it is up. Set it in the
# environment as one line of comma-separated addresses, e.g.
#
#     CORS_ORIGINS=http://localhost:5173,https://nibble.vercel.app
#
# No trailing slash on any of them. An origin is scheme + host + port and
# nothing else; "https://nibble.vercel.app/" does not match and the browser
# will block the call with a message that does not mention the slash.
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]

# --- Who is calling us (slice 4.5) ---------------------------------------
# Clerk already puts the sign-in button on the page. From slice 4.5 it also
# tells the backend who is asking, so your notes are yours.
#
# The frontend sends Clerk's session token on every request. We verify that
# token's signature against Clerk's public keys and read the `sub` claim out of
# it, which is that person's id. See auth.py — it is about fifteen lines.
#
# This is the issuer, and it is what Clerk calls your "Frontend API URL": it
# looks like https://something-something-12.clerk.accounts.dev and it is in the
# Clerk dashboard under API keys. It is NOT a secret — it is in every token any
# browser holds — but it is different for every Clerk application, so it cannot
# have a useful default.
CLERK_ISSUER = os.getenv("CLERK_ISSUER", "")

# Where Clerk publishes the public half of the keys it signs tokens with.
# Standard location, derived rather than configured, so there is one fewer
# setting to get wrong.
CLERK_JWKS_URL = f"{CLERK_ISSUER.rstrip('/')}/.well-known/jwks.json"

# Fail now, loudly, rather than at the first upload with a confusing 500.
#
# Without this the app starts perfectly happily and every single protected route
# answers 401, which looks like "my login is broken" and is actually "nobody
# filled in a setting". That is the exact failure this rule exists to stop —
# see CLAUDE.md, "fail loudly on a missing setting at startup".
if not CLERK_ISSUER:
    raise RuntimeError(
        "CLERK_ISSUER is not set, so the backend cannot check who is signed in. "
        "Copy backend/.env.example to backend/.env and fill it in — the value is "
        "the Frontend API URL in your Clerk dashboard, under API keys."
    )
