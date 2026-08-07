"""Find the chunks most relevant to a question.

This is the payoff for keeping embeddings in Postgres: similarity search and
the "only this user's notes" filter happen in ONE query. No syncing, no second
round trip to another database.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Chunk, Document
from app.services.embeddings import embed_query


async def find_relevant_chunks(
    db: Session, user_id: uuid.UUID, question: str
) -> list[tuple[Chunk, Document, float]]:
    query_vector = await embed_query(question)
    distance = Chunk.embedding.cosine_distance(query_vector)

    statement = (
        select(Chunk, Document, distance.label("distance"))
        .join(Document, Chunk.document_id == Document.id)
        .where(Chunk.user_id == user_id)
        .order_by(distance)
        .limit(get_settings().top_k)
    )
    return list(db.execute(statement).all())
