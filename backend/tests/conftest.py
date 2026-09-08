"""Setup that every test file gets for free.

pytest imports this file before it imports any test, and before anything here
imports the app — which is what makes the environment variable below work.

Two problems are solved here, and both arrived with slice 4.5.
"""

import os

import pytest

# --- Problem one: the app refuses to start without a Clerk issuer ----------
#
# config.py raises at import if CLERK_ISSUER is missing, on purpose: a backend
# that starts fine and then answers 401 to everything is the exact silent
# failure this project keeps trying to design out.
#
# Tests still have to import the app, and CI has no Clerk account. So we set a
# fake issuer here. Nothing ever calls it, because the tests below replace the
# token check itself — this only has to exist for the import to succeed.
#
# setdefault rather than assignment, so a real value in your own .env wins and
# you can point the tests at a real Clerk application if you ever want to.
os.environ.setdefault("CLERK_ISSUER", "https://test-issuer.clerk.accounts.dev")

# Who the tests are signed in as, unless they say otherwise.
TEST_USER_ID = "user_test_alif"

# A second person, for the tests that are about two people not seeing each
# other's notes. There is nothing special about the string beyond being
# different.
OTHER_USER_ID = "user_test_someone_else"


@pytest.fixture(autouse=True)
def signed_in():
    """Run every test as a signed-in person, without a real Clerk token.

    Problem two. From slice 4.5 every route except /health demands a verified
    Clerk token, so ninety-odd tests written before that would all answer 401 —
    and none of them is about signing in.

    Making a real token would mean a real Clerk account, a private key, and a
    network call, in tests that are supposed to be about chunking and page
    numbers. So we replace the check instead.

    ``app.dependency_overrides`` is FastAPI's own hook for this: it says "when a
    route asks for current_user_id, call this instead". The route code is
    completely unchanged and still asks for the id the same way — only where the
    id comes from is different. That is exactly what a test double should swap,
    and no more.

    What this deliberately does NOT prove is that the real token check works.
    Nothing here would notice if auth.py were deleted. That claim belongs to
    test_auth.py, which turns this override off and checks the real thing.

    yield rather than return, so the override is removed afterwards. Without
    that, `app` is a module-level object shared by every test file and the
    override would leak into the ones that are meant to see a 401.
    """
    from app.auth import current_user_id
    from app.main import app

    app.dependency_overrides[current_user_id] = lambda: TEST_USER_ID
    yield TEST_USER_ID
    app.dependency_overrides.clear()


@pytest.fixture()
def signed_in_as():
    """Switch who the current test is signed in as.

    Used by the tests about one person not seeing another's notes::

        signed_in_as(OTHER_USER_ID)
        response = client.get("/documents")

    It overwrites the override the autouse fixture above installed, and the
    same clean-up covers it.
    """
    from app.auth import current_user_id
    from app.main import app

    def _switch(user_id: str) -> str:
        app.dependency_overrides[current_user_id] = lambda: user_id
        return user_id

    return _switch
