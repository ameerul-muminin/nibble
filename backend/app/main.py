"""Nibble's backend — the starting point.

Run it from the `backend` folder with:

    uvicorn app.main:app --reload

Then open http://localhost:8000/health in a browser. If you see
{"status":"ok"}, it works.

This file stays small on purpose. Its only jobs are: create the app, say who
is allowed to call it, and plug in the routes. The actual URLs live in
routes.py.
"""

import threading

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config, embeddings
from app.db import DatabaseOutOfDate
from app.routes import router

app = FastAPI(title="Nibble API", version="0.1.0")


@app.exception_handler(DatabaseOutOfDate)
def database_out_of_date(request: Request, exc: DatabaseOutOfDate):
    """Turn an out-of-date database file into a sentence the frontend can show.

    Every route that touches the database can raise this, because every one of
    them calls ``get_db()``. Handling it here rather than wrapping six routes in
    the same ``try`` is the whole reason this exists — six copies is six places
    to forget, and the one that gets forgotten is the one somebody hits.

    ``detail`` is the key on purpose: it is the same shape every ``HTTPException``
    in routes.py produces, so ``api.js`` already knows how to read it and shows
    the sentence unchanged. A new shape here would have needed a new branch there.

    503 rather than 500, because that is what this is — the server is fine, its
    database file is from an older version of Nibble, and it will work again the
    moment that is dealt with.
    """
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(exc)},
    )


@app.on_event("startup")
def warm_the_embedding_model():
    """Start loading the embedding model as soon as the server starts.

    Without this, the model loads inside whichever request needs it first — so
    the first upload after the server starts pays for the load *and* the
    embedding, one after the other. On the free host that is the difference
    between a slow upload and one somebody assumes has hung.

    **In a thread, not inline, and that is the whole subtlety here.** Loading
    takes a while, and a startup handler that blocks holds the port closed until
    it finishes. Render watches for that port to open to decide the deploy
    worked, so a slow blocking load turns "slower first upload" into "failed
    deploy" — a much worse problem than the one being fixed.

    Nothing is needed to make this safe. ``get_model()`` already takes a lock
    around loading, for the case of two uploads arriving at once, and that same
    lock covers this: a request that arrives while this thread is still working
    waits for it rather than starting a second load.

    ``daemon=True`` so this thread can never keep a stopped server alive — Ctrl-C
    should stop Nibble, not wait on it.

    Failure here is deliberately ignored. If the model cannot load, the routes
    that need it already raise ``EmbeddingUnavailable`` and turn it into a plain
    sentence for the person reading. Crashing the server at startup instead
    would take down ``/health`` too, and hide the reason.
    """

    def load():
        try:
            embeddings.get_model()
        except Exception:
            pass

    threading.Thread(target=load, daemon=True).start()


# Without this, the browser silently blocks the frontend from talking to us.
# It is the single most common "why is nothing happening" bug in this project.
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
