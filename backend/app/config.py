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

# How short a question has to be before we treat it as a follow-up.
#
# A question that names its own subject does not need the ones before it, and is
# actively hurt by them. "for the CSE 224 lab, can you name the 6 experiments"
# is eleven words and completely self-contained; gluing two earlier questions
# about a database chapter onto it sent the search looking for something half
# about databases, and pieces of the wrong chapter came back.
#
# Six words is the line. Measured against the questions people actually asked:
#
#     "name them"                                    2   follow-up
#     "the names are there"                          4   follow-up
#     "explain the third one"                        4   follow-up
#     "what are the experiments"                     4   follow-up
#     "for the CSE 224 lab, ... 6 experiments"      11   stands alone
#     "can you summarise the DB pdf"                 6   follow-up (see below)
#
# That last one is the known hole: a SHORT question that changes the subject
# still picks up the previous ones. It is a smaller failure than gluing history
# onto everything, and word count is chosen over anything cleverer because it
# can be explained in one line and predicted without running it.
ASK_FOLLOWUP_MAX_WORDS = 6

# The most of one past turn we will read. Nothing from a browser is trusted, and
# this is the cap that makes that true here: without it a crafted transcript
# could push the actual notes out of the model's context, which is the one way
# to make Nibble answer from something other than your notes.
ASK_HISTORY_CHARS = 1000

# --- Quizzes (slice 6) ---------------------------------------------------
# How many questions a quiz has when nobody says otherwise.
QUIZ_QUESTION_COUNT = 5

# The most anybody can ask for, and this ceiling is Groq's rather than ours.
QUIZ_MAX_QUESTIONS = 10

# --- What the free tier actually allows, measured on 2026-09-09 --------------
#
# **This was written down wrong first, and the wrong version is worth naming.**
# These settings originally said "the free tier caps OUTPUT at 1,000 tokens per
# minute", copied across from OCR_MAX_OUTPUT_TOKENS below. That figure belongs
# to the VISION model. It was never checked against the chat model, and it is
# not true of it.
#
# Asking Groq directly, by reading the rate-limit headers it returns on every
# reply, for openai/gpt-oss-120b on this key:
#
#     x-ratelimit-limit-tokens: 8000      <- per minute
#     x-ratelimit-limit-requests: 1000    <- per day
#
# **8,000 tokens a minute, and it counts INPUT AND OUTPUT TOGETHER.** That
# changes which number matters. Output was never the expensive part: ten
# questions is about 800 tokens. The expensive part is the note we send, and one
# quiz used to send about 3,000 tokens of it — so a single quiz cost roughly
# 4,000 of the 8,000, and generating two in a minute, or one after a couple of
# questions to /ask, was a 429.
#
# That is exactly what happened: a 10-question quiz came back "Nibble is being
# asked a lot at once", and it was our own request that had eaten the budget.

# The ceiling on one quiz's reply.
#
# **This was 1000, and 1000 was the bug behind a 400.** A ten-question quiz came
# back as `json_validate_failed` with an empty `failed_generation`, which reads
# like the model producing nonsense and is not that at all.
#
# `max_tokens` on this model covers REASONING AS WELL AS OUTPUT, and the two
# were measured separately:
#
#     reasoning_effort  reasoning   answer   completion
#     medium                  893      621         1514
#     low                      31      615          646
#
# At medium, reasoning alone was 893 of the 1000 allowed. The JSON then ran out
# of room part-way through, Groq validated it, found it incomplete, and rejected
# the whole reply. Nothing was wrong with the questions; there was no space left
# to finish writing them.
#
# 2000 is roughly three times what a ten-question quiz actually spends at the
# effort now used, so a long question cannot truncate one again.
QUIZ_MAX_OUTPUT_TOKENS = 2000

# How much of the note the model is shown when writing questions.
#
# A quiz is made from ONE note, and unlike /ask there is no question to retrieve
# against — "write me five questions about this chapter" has no query. So the
# chunks go in from the start of the document until this budget runs out.
#
# **This was 12,000 and that was too much**, for the reason measured above: at
# roughly four characters to a token it sent about 3,000 tokens of note, and
# with the reply reserved on top, one quiz cost about half the minute's entire
# allowance. Two quizzes in a minute could not both work, and often the first
# one could not either, because /ask had already spent some of it.
#
# 6,000 characters is about 1,500 tokens, so a quiz now costs roughly a quarter
# of the budget instead of a half. Three or four in a minute, rather than one
# and a half.
#
# It is a budget rather than a whole document on purpose: a 200-page book would
# otherwise be sent in full, which is slow and large enough to be refused
# outright. Questions come from the beginning of a long note, which is honest
# and predictable — and the prompt says so, so the model does not imply it
# covered the end.
#
# The real fix for a long note is to quiz a section rather than a chapter, and
# that is a slice rather than a number. Noted in docs/scope.md.
QUIZ_MAX_CONTEXT_CHARS = 6_000

# **This said "medium", and that was asserted rather than measured.** The claim
# written here was that a question needs three wrong-but-not-obviously-wrong
# options, and that a model gets lazy about those at "low". Plausible. Untested.
#
# Tested, on the same note, asking for the same ten questions:
#
#     effort    reasoning tokens   questions returned
#     medium                 893                   10
#     low                     31                   10
#
# Twenty-nine times the reasoning for the same number of usable questions, on a
# budget of 8,000 tokens a minute shared with /ask and with reading handwriting.
# That is what was producing "Nibble is being asked a lot at once".
#
# The distractors at "low" were read by hand and are genuine — plausible, same
# kind of thing as the answer, wrong for a workable reason. **One caveat, said
# out loud because it flatters the result:** the note checked was itself a
# multiple-choice bank, so the model had real options in front of it to draw on.
# A chapter of prose is the harder case, and if distractors ever come back weak
# on one, this is the first knob to turn — with a measurement, this time, not an
# assumption.
QUIZ_REASONING_EFFORT = "low"

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
