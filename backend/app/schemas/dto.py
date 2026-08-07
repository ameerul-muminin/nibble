"""Request and response shapes. These ARE the API contract.

If you change anything here, update docs/api.md and tell the frontend owner
in the PR description. Nothing else in this repo breaks the other side of
the team as fast as a silent change to this file.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    status: str  # "processing" | "ready" | "failed"
    page_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class Source(BaseModel):
    """Where an answer came from. Powers the 'from your Ch.4 notes' line in the UI."""

    document_id: uuid.UUID
    filename: str
    page: int
    excerpt: str


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    session_id: uuid.UUID | None = None


class AskResponse(BaseModel):
    session_id: uuid.UUID
    answer: str
    sources: list[Source]


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
