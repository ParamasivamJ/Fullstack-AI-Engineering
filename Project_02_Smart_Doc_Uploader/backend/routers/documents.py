"""
Project 02 — Router: Documents
================================
Handles file upload, listing, status checks, and deletion.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from uuid import UUID
from pathlib import Path
import os
import aiofiles
from uuid import uuid4
import logging

from database import DB
from config import get_settings
import crud
import schemas

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# MIME type mapping
MIME_MAP = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


# ─── Background Processing Task ─────────────────────────────────

async def process_document(doc_id: str):
    """
    Background task: extract → chunk → embed → store.
    Runs after the upload response is sent to the user.
    """
    from database import AsyncSessionLocal
    from services.extraction import extract_text
    from services.chunking import chunk_pages
    from services.embedding import embed_texts

    async with AsyncSessionLocal() as db:
        doc = await crud.get_document(db, UUID(doc_id))
        if not doc:
            logger.error(f"Document not found: {doc_id}")
            return

        try:
            # Step 1: Mark as processing
            await crud.update_document_status(db, doc.id, "processing")

            # Step 2: Extract text
            pages = extract_text(doc.storage_path, doc.content_type)
            if not pages:
                await crud.update_document_status(
                    db, doc.id, "failed",
                    error_message="No text could be extracted from this document"
                )
                return

            # Step 3: Chunk text
            chunks = chunk_pages(
                pages,
                max_chunk_size=settings.CHUNK_SIZE,
                overlap_sentences=settings.CHUNK_OVERLAP_SENTENCES,
            )

            # Step 4: Generate embeddings (batch)
            texts = [c["content"] for c in chunks]
            embeddings = embed_texts(texts)

            # Step 5: Attach embeddings to chunks
            for chunk, embedding in zip(chunks, embeddings):
                chunk["embedding"] = embedding

            # Step 6: Delete old chunks (idempotent reprocessing)
            await crud.delete_chunks_by_document(db, doc.id)

            # Step 7: Batch insert chunks
            await crud.create_chunks_batch(db, doc.id, chunks)

            # Step 8: Update status
            await crud.update_document_status(
                db, doc.id, "indexed",
                chunk_count=len(chunks),
                page_count=len(pages),
            )
            logger.info(f"✅ Document indexed: {doc.filename} ({len(chunks)} chunks)")

        except Exception as e:
            logger.error(f"❌ Processing failed for {doc.filename}: {e}", exc_info=True)
            await crud.update_document_status(
                db, doc.id, "failed",
                error_message=str(e)[:500]
            )


# ─── Routes ──────────────────────────────────────────────────────

@router.post("/upload", response_model=schemas.DocumentOut, status_code=201,
             summary="Upload a document for indexing")
async def upload_document(
    db: DB,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    """
    Uploads a file, validates it, stores it, and triggers background processing.
    Returns immediately with status='uploaded'.
    """
    # Validate file extension
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    ext = Path(file.filename).suffix.lower()
    if ext not in settings.allowed_extensions_list:
        raise HTTPException(
            400,
            f"Unsupported file type: {ext}. Allowed: {settings.allowed_extensions_list}"
        )

    # Determine content type
    content_type = MIME_MAP.get(ext, file.content_type or "application/octet-stream")

    # Generate safe filename (UUID-based)
    safe_name = f"{uuid4()}{ext}"
    save_path = os.path.join(settings.UPLOAD_DIR, safe_name)

    # Stream upload to disk (never load full file into RAM)
    total_size = 0
    async with aiofiles.open(save_path, "wb") as out:
        while chunk := await file.read(64 * 1024):  # 64KB chunks
            total_size += len(chunk)
            if total_size > settings.max_file_size_bytes:
                os.remove(save_path)
                raise HTTPException(
                    413,
                    f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB} MB"
                )
            await out.write(chunk)

    # Create database record
    doc = await crud.create_document(
        db=db,
        filename=file.filename,
        content_type=content_type,
        file_size_bytes=total_size,
        storage_path=save_path,
    )

    # Trigger background processing (extract → chunk → embed → index)
    background_tasks.add_task(process_document, str(doc.id))

    return doc


@router.get("/", response_model=schemas.DocumentListOut,
            summary="List all uploaded documents")
async def list_documents(db: DB):
    docs, total = await crud.get_documents(db)
    return schemas.DocumentListOut(total=total, items=docs)


@router.get("/{doc_id}", response_model=schemas.DocumentOut,
            summary="Get document details")
async def get_document(doc_id: UUID, db: DB):
    doc = await crud.get_document(db, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.get("/{doc_id}/status", response_model=schemas.DocumentStatus,
            summary="Check document processing status")
async def get_document_status(doc_id: UUID, db: DB):
    doc = await crud.get_document(db, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return schemas.DocumentStatus(
        id=doc.id,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
    )


@router.delete("/{doc_id}", status_code=204,
               summary="Delete a document and all its chunks")
async def delete_document(doc_id: UUID, db: DB):
    doc = await crud.get_document(db, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    # Delete the stored file
    if os.path.exists(doc.storage_path):
        os.remove(doc.storage_path)

    # Delete from DB (cascades to chunks)
    await crud.delete_document(db, doc_id)
