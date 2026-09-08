# How the backend is built for its Hugging Face Space. Slice 4.5.
#
# **You do not need Docker to work on Nibble.** Nothing in docs/first-week.md
# mentions it and nothing here changes that: locally the backend is still
#
#     uvicorn app.main:app --reload
#
# This file is read by the Space's build servers, not by you. ADR 0003 explains
# why the backend needs a real host with a real filesystem, and why that is a
# Space rather than Vercel or Render.

FROM python:3.12-slim

# Spaces run the container as a normal user with id 1000, not as root. Building
# as that same user means every file we create is already owned by whoever runs
# the app — otherwise the app starts as user 1000 and cannot write nibble.db
# into a directory owned by root, which fails at the first upload rather than at
# startup.
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
# This is the line that makes a Space better than a serverless host for this
# app. fastembed downloads about 65 MB the first time it is asked for a model,
# and on a platform without a persistent filesystem that download happens again
# on every cold start — turning the first question after a quiet spell into a
# minute of silence.
#
# Doing it here means it happens once, on a build server, and ships inside the
# image. The first question after the Space wakes up is then just a model load.
ENV FASTEMBED_CACHE_PATH=/home/user/app/.fastembed_cache

# It calls our own get_model() rather than fastembed directly, so the model name
# comes from config.py and cannot drift away from the one the app really uses.
# CLERK_ISSUER is set to a throwaway value for this one command because
# config.py refuses to import without it — nothing here talks to Clerk, and the
# real value arrives as a Space secret at runtime.
RUN CLERK_ISSUER=https://unused-at-build-time.invalid \
    python -c "from app.embeddings import get_model; get_model()"

# 7860 is the port a Space expects to find an app on. It is not a choice.
EXPOSE 7860

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
