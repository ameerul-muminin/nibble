"""Upload, list, and delete a student's notes."""

import uuid

from fastapi import APIRouter, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import DbSession, current_user
from app.models import Chunk, Document
from app.schemas.dto import DocumentOut
from app.services.chunking import chunk_pages, extract_pages
from app.services.embeddings import embed_texts

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_BYTES = 20 * 1024 * 1024
ALLOWED_SUFFIXES = (".pdf", ".txt", ".md")


@router.get("", response_model=list[DocumentOut])
def list_documents(db: DbSession) -> list[Document]:
    user = current_user(db)
    statement = (
        select(Document).where(Document.user_id == user.id).order_by(Document.created_at.desc())
    )
    return list(db.scalars(statement))


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile, db: DbSession) -> Document:
    filename = file.filename or "untitled"
    if not filename.lower().endswith(ALLOWED_SUFFIXES):
        raise HTTPException(400, f"Only {', '.join(ALLOWED_SUFFIXES)} files are supported.")

    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "That file is over 20 MB. Try splitting it.")

    user = current_user(db)
    document = Document(user_id=user.id, filename=filename, status="processing")
    db.add(document)
    db.commit()

    try:
        pages = extract_pages(data, filename)
        chunks = chunk_pages(pages)
        if not chunks:
            raise ValueError("No readable text found. Is this a scanned PDF?")

        vectors = await embed_texts([chunk.content for chunk in chunks])
        db.add_all(
            Chunk(
                document_id=document.id,
                user_id=user.id,
                ordinal=chunk.ordinal,
                page=chunk.page,
                content=chunk.content,
                embedding=vector,
            )
            for chunk, vector in zip(chunks, vectors, strict=True)
        )
        document.page_count = len(pages)
        document.status = "ready"
        db.commit()
    except Exception:
        document.status = "failed"
        db.commit()
        raise

    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: uuid.UUID, db: DbSession) -> None:
    user = current_user(db)
    document = db.get(Document, document_id)
    if document is None or document.user_id != user.id:
        raise HTTPException(404, "Document not found.")
    # Chunks go with it automatically — see the CASCADE on Chunk.document_id.
    db.delete(document)
    db.commit()
