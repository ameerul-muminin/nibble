# How the backend is built for Render. Slice 4.5.
#
# **You do not need Docker to work on Nibble.** Nothing in docs/first-week.md
# mentions it and nothing here changes that: locally the backend is still
#
#     uvicorn app.main:app --reload
#
# This file is read by Render's build servers, not by you. ADR 0003 explains why
# the backend needs a real host with a real filesystem rather than a serverless
# one, and ADR 0005 explains why that host is Render — the Hugging Face Space
# this was originally written for became a paid feature in July 2026.

FROM python:3.12-slim

# Run as a normal user rather than root. Building as the same user that runs the
# app means every file we create is already owned by it — otherwise the app
# cannot write nibble.db into a directory owned by root, which fails at the first
# upload rather than at startup. Nothing here needs root, and a container that
# does not run as root is one fewer thing to explain if anybody asks.
RUN useradd --create-home --uid 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /home/user/app

# Dependencies before application code, on purpose. Docker caches each step and
# reuses it while the files that step read have not changed — so with the code
# copied after this, editing routes.py rebuilds in seconds instead of
# reinstalling onnxruntime every time.
COPY --chown=user pyproject.toml ./
COPY --chown=user app ./app
RUN pip install --no-cache-dir --user .

# --- The embedding model, baked in at build time -------------------------
#
# This is the line that makes a real container better than a serverless host for
# this app. fastembed downloads about 65 MB the first time it is asked for a
# model, and on a platform without a persistent filesystem that download happens
# again on every cold start — turning the first question after a quiet spell into
# a minute of silence.
#
# Doing it here means it happens once, on a build server, and ships inside the
# image. The first question after the service wakes up is then just a model load,
# which matters on Render because a free service sleeps after 15 minutes.
ENV FASTEMBED_CACHE_PATH=/home/user/app/.fastembed_cache

# --- One thread, on purpose ----------------------------------------------
#
# Render's free tier gives this container 0.1 CPU: ten milliseconds of CPU time
# in every hundred. The maths libraries underneath onnxruntime do not know that.
# They count the cores on the HOST machine — many — and start a thread for each
# one, which then all queue for our one tenth of one core and spend most of
# their time stalled waiting for the next scheduling window.
#
# embeddings.py already passes threads=1 to fastembed, and that is the setting
# that matters. These two are the belt to its braces: they cover the libraries
# that read the environment directly rather than being told by onnxruntime, and
# they apply to the build step below as well as to the running server.
#
# Measured: on a 16-core laptop, one thread embeds 30 pieces in 2.41s and
# sixteen threads take 2.47s. The parallelism was never buying anything; it was
# only ever spending CPU we do not have here.
ENV OMP_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV MKL_NUM_THREADS=1

# It calls our own get_model() rather than fastembed directly, so the model name
# comes from config.py and cannot drift away from the one the app really uses.
# CLERK_ISSUER is set to a throwaway value for this one command because
# config.py refuses to import without it — nothing here talks to Clerk, and the
# real value arrives as an environment variable at runtime.
RUN CLERK_ISSUER=https://unused-at-build-time.invalid \
    python -c "from app.embeddings import get_model; get_model()"

# Render sets PORT in the environment and expects the app to listen on it. It
# defaults to 10000, and it can usually detect a different port, but relying on
# that detection is how a deploy fails with "no open ports" for no visible
# reason. Reading the variable is the supported way, so we read it.
#
# EXPOSE is documentation and nothing else — it opens no port and Render does
# not act on it. It is here so anybody reading this file learns the same number
# the CMD below uses.
EXPOSE 10000

# Shell form, not the ["exec", "list"] form, and that is the whole point: the
# list form passes ${PORT} to uvicorn as four literal characters, because there
# is no shell present to substitute it. uvicorn then fails to parse a port
# called "${PORT}" and the container dies at startup.
#
# ${PORT:-10000} means "PORT, or 10000 if it is not set", so this still runs
# under a plain `docker run` with nothing configured.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}
