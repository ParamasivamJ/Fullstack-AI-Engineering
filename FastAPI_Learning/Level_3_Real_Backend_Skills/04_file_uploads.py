"""
Level 3 — File Uploads (Production Patterns)
=============================================

File uploads are common in AI apps: users upload PDFs, images, audio for processing.
This file teaches the complete production pattern:
  - Single and multiple file uploads
  - File type and size validation
  - Saving files safely (no path traversal attacks)
  - Async file reading for large files

HOW TO RUN:
  pip install python-multipart  (required for file uploads in FastAPI)
  uvicorn 04_file_uploads:app --reload

Then use the /docs UI to test uploads interactively.
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
import os
import uuid
import shutil

app = FastAPI(title="Level 3: File Uploads")


# ─────────────────────────────────────────────
# CONSTANTS — never hardcode limits inline
# ─────────────────────────────────────────────
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024  # 10 MB

# Allowed MIME types — NEVER trust file extensions alone (they can be faked)
ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "text/plain",
}
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Upload directory — in production, use cloud storage (S3, GCS)
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)  # Create folder if it doesn't exist


# ─────────────────────────────────────────────
# RESPONSE SCHEMAS
# ─────────────────────────────────────────────

class UploadResponse(BaseModel):
    file_id: str
    original_filename: str
    content_type: str
    size_bytes: int
    saved_path: str


# ─────────────────────────────────────────────
# VALIDATION DEPENDENCY
# ─────────────────────────────────────────────
# We put file validation in a dependency so it can be reused across routes.

async def validate_document(file: UploadFile = File(...)) -> UploadFile:
    """Validates that an uploaded file is an allowed document type and size."""

    # 1. Check MIME type (content_type is set by the client — also validate magic bytes in prod)
    if file.content_type not in ALLOWED_DOCUMENT_TYPES:
        raise HTTPException(
            status_code=415,  # 415 Unsupported Media Type
            detail={
                "message": f"File type '{file.content_type}' is not allowed",
                "allowed_types": list(ALLOWED_DOCUMENT_TYPES),
            },
        )

    # 2. Check file size — read the whole file into memory to measure it
    # For very large files, use streaming instead (see below)
    content = await file.read()
    size = len(content)

    if size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,  # 413 Content Too Large
            detail=f"File exceeds maximum size of {MAX_FILE_SIZE_MB}MB (got {size / 1024 / 1024:.1f}MB)",
        )

    # 3. Reset the file pointer so the route function can read it again
    # After .read(), the pointer is at the end — we must seek back to start
    await file.seek(0)

    return file


# ─────────────────────────────────────────────
# 1. SINGLE FILE UPLOAD
# ─────────────────────────────────────────────

@app.post("/upload/document", response_model=UploadResponse, tags=["Uploads"])
async def upload_document(
    # Depends(validate_document) validates the file before this function runs
    file: UploadFile = Depends(validate_document),
):
    # Generate a UUID-based filename — NEVER use the original filename directly.
    # Original filenames can contain "../" (path traversal attack) or be too long.
    file_id = str(uuid.uuid4())
    # Preserve extension for readability, but it is not trusted for type checking
    extension = os.path.splitext(file.filename or "")[-1].lower()
    safe_filename = f"{file_id}{extension}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    # Save the file to disk
    # In production: upload to S3/GCS using boto3 or google-cloud-storage
    with open(file_path, "wb") as buffer:
        # shutil.copyfileobj streams the file in chunks — memory efficient
        shutil.copyfileobj(file.file, buffer)

    content = await file.read()  # read for size calculation (file was seeked to 0 by dependency)
    # Note: in practice, size calculation and saving should be in one read pass

    return UploadResponse(
        file_id=file_id,
        original_filename=file.filename or "unknown",
        content_type=file.content_type or "unknown",
        size_bytes=os.path.getsize(file_path),
        saved_path=file_path,
    )


# ─────────────────────────────────────────────
# 2. MULTIPLE FILE UPLOAD (batch)
# ─────────────────────────────────────────────

@app.post("/upload/batch", response_model=List[UploadResponse], tags=["Uploads"])
async def upload_batch(
    # List[UploadFile] accepts multiple files in one request
    files: List[UploadFile] = File(..., description="Upload up to 5 documents"),
):
    if len(files) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 files per batch")

    results = []
    for file in files:
        # Validate each file individually
        if file.content_type not in ALLOWED_DOCUMENT_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"File '{file.filename}' has unsupported type: {file.content_type}",
            )

        file_id = str(uuid.uuid4())
        extension = os.path.splitext(file.filename or "")[-1].lower()
        safe_filename = f"{file_id}{extension}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        results.append(UploadResponse(
            file_id=file_id,
            original_filename=file.filename or "unknown",
            content_type=file.content_type or "unknown",
            size_bytes=os.path.getsize(file_path),
            saved_path=file_path,
        ))

    return results


# ─────────────────────────────────────────────
# 3. STREAMING UPLOAD (for very large files)
# ─────────────────────────────────────────────
# Reading huge files with .read() loads them entirely into RAM.
# Streaming reads them in chunks — much more memory efficient.

@app.post("/upload/large", tags=["Uploads"])
async def upload_large_file(file: UploadFile = File(...)):
    """Uploads a large file using streaming chunks to avoid RAM exhaustion."""
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, file_id)
    total_bytes = 0
    CHUNK_SIZE = 1024 * 64  # 64KB chunks

    with open(file_path, "wb") as buffer:
        while True:
            chunk = await file.read(CHUNK_SIZE)  # read 64KB at a time
            if not chunk:
                break  # no more data
            if total_bytes + len(chunk) > MAX_FILE_SIZE_BYTES:
                # Stop immediately and delete the partial file
                buffer.close()
                os.remove(file_path)
                raise HTTPException(status_code=413, detail="File too large")
            buffer.write(chunk)
            total_bytes += len(chunk)

    return {"file_id": file_id, "size_bytes": total_bytes}


# ─────────────────────────────────────────────
# 4. FILE DOWNLOAD
# ─────────────────────────────────────────────

@app.get("/files/{file_id}", tags=["Uploads"])
def download_file(file_id: str):
    """Returns a saved file for download."""
    # Validate that file_id looks like a UUID (prevents path traversal)
    try:
        uuid.UUID(file_id)  # raises ValueError if not a valid UUID
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file ID format")

    # Search for the file (any extension)
    for filename in os.listdir(UPLOAD_DIR):
        if filename.startswith(file_id):
            return FileResponse(
                path=os.path.join(UPLOAD_DIR, filename),
                filename=filename,
                # media_type tells the browser how to handle the file
                media_type="application/octet-stream",  # generic binary download
            )

    raise HTTPException(status_code=404, detail="File not found")
