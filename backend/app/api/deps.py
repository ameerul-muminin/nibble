"""Shared route dependencies.

`DbSession` is the modern FastAPI way to inject a database session. Write
`db: DbSession` in a route signature and FastAPI opens one for that request
and closes it afterwards.

TODO(auth): current_user returns a single hardcoded demo user so the team can
build the whole pipeline before login exists. Replace in phase 2 — every route
already scopes its queries by user id, so nothing else has to change.
"""

import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import User

DbSession = Annotated[Session, Depends(get_db)]

DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def current_user(db: Session) -> User:
    user = db.get(User, DEMO_USER_ID)
    if user is None:
        user = User(id=DEMO_USER_ID, email="demo@nibble.app", display_name="Demo Student")
        db.add(user)
        db.commit()
    return user
