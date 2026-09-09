"""Who is calling? Verifying Clerk's token, and getting an id out of it.

Alif owns this file. It is small on purpose, because the interesting part is not
the code — it is understanding what a token actually proves.

**The problem.** Anyone can type our backend's address into a browser. Until
slice 4.5, anyone who did could read and delete everybody's notes, because no
route ever asked who was calling. The sign-in button on the frontend decided what
to *draw*; it never decided what the backend would *do*.

**Why we can trust a string the browser sent us.** The frontend attaches a Clerk
session token to every request. That token is three chunks of base64 with dots
between them: who it is about, when it expires, and a signature. The signature is
the whole point. Clerk made it with a private key nobody else has, and it can be
checked with a public key anybody can fetch — so we can prove the token came from
Clerk without ever talking to Clerk about this particular request. Change one
character of the token and the signature stops matching.

So: no shared password with Clerk, no database of sessions on our side, and no
network call in the hot path once the keys are cached.

**What we learn from the token, and deliberately nothing more.** The `sub` claim
— Clerk's opaque id for a person, something like ``user_2abc...``. Not their
email, not their name: this file never asks for a claim beyond the subject, so
there is nothing else here to leak or to keep in step with Clerk. A `documents`
row belongs to that string, and that is the whole of "your notes are yours".

**One thing about a human being is stored elsewhere, since slice 8.** This
docstring used to say the Clerk id was the only one, and that stopped being true
the day the marking screen needed to say *who* handed in what:
``room_members.name`` holds a student's display name, sent by the frontend from
their Clerk profile when they join a class. It does not come through this file
and nothing here verifies it — it is a label the client chose, only ever shown,
never used to decide anything. See the comment on that column in ``db.py``.

The sentence is amended rather than left alone because a comment that has quietly
gone false is worse than no comment: the next person reads it and believes it.
"""

import jwt
from fastapi import Header, HTTPException, status
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError

from app import config

# Clerk's public keys, fetched once and kept.
#
# Module level for the same reason the embedding model is: building this fetches
# over the network, and doing that per request would put an internet round trip
# in front of every single call. PyJWKClient caches the keys it downloads, so the
# first verified request pays for it and the rest do not.
#
# Built at import rather than lazily, unlike the embedding model — no network
# happens until something actually asks it for a key, so there is nothing to
# defer.
_jwk_client = PyJWKClient(config.CLERK_JWKS_URL)


def current_user_id(authorization: str | None = Header(default=None)) -> str:
    """Return the id of whoever is signed in, or refuse the request.

    Use it on a route by asking for it as an argument::

        @router.get("/documents")
        def list_documents(user_id: str = Depends(current_user_id)):

    FastAPI sees ``Depends`` and runs this function first, then hands the route
    whatever it returned. If this raises instead, the route never runs at all —
    which is the property that matters: there is no way to forget the check
    inside a route body, because the route body is not reached.

    ``authorization`` is the HTTP header of that name, which FastAPI hands us
    because of the ``Header`` default above. It looks like
    ``Bearer eyJhbGciOi...``, and "Bearer" is just a convention meaning "whoever
    bears this token is who it says". That is why a token is short-lived and why
    it must never be logged.

    Raises:
        HTTPException 401: no header, a malformed one, or a token that is
            expired, tampered with, or not signed by our Clerk application.
        HTTPException 503: Clerk's keys could not be fetched, so the token can
            neither be trusted nor fairly rejected.
    """
    # --- Get the token out of the header ----------------------------------
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You need to be signed in to do that. Sign in and try again.",
        )

    token = authorization.removeprefix("Bearer ").strip()

    # --- Check the signature, and only then believe anything in it --------
    try:
        # Every Clerk token names which key signed it, so this picks the right
        # public key out of the set rather than trying them all.
        signing_key = _jwk_client.get_signing_key_from_jwt(token)

        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=config.CLERK_ISSUER,
            # Clerk's default session token has no audience claim, so there is
            # nothing to check. Saying so explicitly beats letting the library
            # decide, because the day a token does carry one, this line is where
            # somebody looks.
            options={"verify_aud": False},
        )
    except PyJWKClientConnectionError as e:
        # Clerk itself is unreachable. This is NOT the user's fault and must not
        # be reported as a bad sign-in, or everybody sees "your session expired"
        # during an outage and starts re-logging in for no reason.
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nibble can’t check your sign-in right now. Try again in a moment.",
        ) from e
    except jwt.PyJWTError as e:
        # Expired, tampered with, signed by a different Clerk application, or not
        # a token at all. All of them mean the same thing to the person reading
        # it, and none of them should show the library's wording.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your sign-in has expired. Sign in again and try once more.",
        ) from e

    # --- The id itself -----------------------------------------------------
    user_id = claims.get("sub")
    if not user_id:
        # A signed token with no subject should be impossible. If it ever
        # happens, failing is the only safe move — the alternative is a
        # document row owned by None, which every other user's query would then
        # have to be careful about forever.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your sign-in has expired. Sign in again and try once more.",
        )

    return user_id
