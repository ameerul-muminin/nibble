"""Nibble's backend — the starting point.

Run it from the `backend` folder with:

    uvicorn app.main:app --reload

Then open http://localhost:8000/health in a browser. If you see
{"status":"ok"}, it works.

This file stays small on purpose. Its only jobs are: create the app, say who
is allowed to call it, and plug in the routes. The actual URLs live in
routes.py.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routes import router

app = FastAPI(title="Nibble API", version="0.1.0")

# Without this, the browser silently blocks the frontend from talking to us.
# It is the single most common "why is nothing happening" bug in this project.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
