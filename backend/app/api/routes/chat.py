"""Ask a question, get an answer grounded in the student's own notes."""

from fastapi import APIRouter

from app.api.deps import DbSession, current_user
from app.models import ChatSession, Message
from app.schemas.dto import AskRequest, AskResponse, Source
from app.services.llm import answer_question, build_context
from app.services.retrieval import find_relevant_chunks

router = APIRouter(prefix="/chat", tags=["chat"])

NO_NOTES = (
    "I could not find anything about that in your notes yet. "
    "Upload the chapter it comes from and ask me again."
)


@router.post("/ask", response_model=AskResponse)
async def ask(body: AskRequest, db: DbSession) -> AskResponse:
    user = current_user(db)

    session = db.get(ChatSession, body.session_id) if body.session_id else None
    if session is None or session.user_id != user.id:
        session = ChatSession(user_id=user.id, title=body.question[:80])
        db.add(session)
        db.commit()

    db.add(Message(session_id=session.id, role="user", content=body.question))
    db.commit()

    hits = await find_relevant_chunks(db, user.id, body.question)

    if not hits:
        answer, sources = NO_NOTES, []
    else:
        context = build_context(
            [(doc.filename, chunk.content, chunk.page) for chunk, doc, _ in hits]
        )
        answer = await answer_question(body.question, context)
        sources = [
            Source(
                document_id=doc.id,
                filename=doc.filename,
                page=chunk.page,
                excerpt=chunk.content[:200],
            )
            for chunk, doc, _ in hits
        ]

    db.add(Message(session_id=session.id, role="assistant", content=answer))
    db.commit()

    return AskResponse(session_id=session.id, answer=answer, sources=sources)
