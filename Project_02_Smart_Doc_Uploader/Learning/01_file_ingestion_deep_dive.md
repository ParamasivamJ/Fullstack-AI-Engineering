# 01 — File Ingestion Deep Dive

## What Is File Ingestion?

File ingestion is the process of receiving a file from a user, validating it,
storing it safely, and preparing it for downstream processing.

It sounds simple. It is not. Every file is a potential attack vector, a source
of corrupted data, a memory bomb, or a format the user swore was a PDF but is
actually a renamed JPEG.

Production file ingestion must handle ALL of these without crashing.

---

## The Ingestion Pipeline (End to End)

```
User selects a file in the UI
            │
            ▼
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND: Pre-Upload Validation                            │
│  ├── Check file extension (.pdf, .docx, .txt only)          │
│  ├── Check file size (< 10MB — reject before uploading)     │
│  └── Show progress bar during upload                        │
└───────────────────────────┬─────────────────────────────────┘
                            │ multipart/form-data
┌───────────────────────────▼─────────────────────────────────┐
│  FASTAPI: POST /documents/upload                            │
│                                                             │
│  STEP 1: Read headers BEFORE reading the body               │
│  ├── Content-Type → must be multipart/form-data              │
│  ├── Content-Length → reject if > MAX_FILE_SIZE              │
│  └── This prevents reading a 5GB file into memory           │
│                                                             │
│  STEP 2: Read the file in chunks (streaming)                │
│  ├── async for chunk in file.stream():                      │
│  │       total += len(chunk)                                │
│  │       if total > MAX_SIZE: raise 413                     │
│  │       write chunk to temp file                           │
│  └── This handles files larger than available RAM           │
│                                                             │
│  STEP 3: Validate the file content                          │
│  ├── Read first 8 bytes (magic bytes) to confirm format     │
│  │     PDF → starts with %PDF                               │
│  │     DOCX → starts with PK (it's a ZIP)                   │
│  │     TXT → any UTF-8 text                                 │
│  ├── Reject if extension doesn't match content              │
│  │   (someone renamed virus.exe → resume.pdf)               │
│  └── Optionally: scan for malware (ClamAV in enterprise)    │
│                                                             │
│  STEP 4: Store the file                                     │
│  ├── Generate a UUID filename (never use the original name) │
│  │     Why: "../../../etc/passwd" is a valid filename        │
│  ├── LOCAL: save to uploads/{uuid}.pdf                      │
│  └── CLOUD: upload to S3/GCS with pre-signed URL            │
│                                                             │
│  STEP 5: Create a database record                           │
│  ├── filename (original), storage_path (UUID), content_type │
│  ├── file_size, status="uploaded", owner_id                 │
│  └── Return 201 with document metadata (NOT the file!)      │
│                                                             │
│  STEP 6: Trigger background processing                      │
│  └── BackgroundTasks.add_task(process_document, doc.id)      │
│       → extract text → chunk → embed → index                │
│       → update status: "uploaded" → "processing" → "indexed"│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## MIME Types vs Magic Bytes vs File Extensions

| Layer | What it checks | Trustworthy? |
|-------|---------------|-------------|
| **File extension** | `.pdf`, `.docx` | ❌ Anyone can rename a file |
| **MIME type** (Content-Type header) | `application/pdf` | ❌ Client can set any value |
| **Magic bytes** (first bytes of file) | `%PDF-1.7` | ✅ Cannot be faked without breaking the file |

### Magic Bytes Table

| Format | Magic Bytes (hex) | Magic Bytes (text) |
|--------|------------------|-------------------|
| PDF | `25 50 44 46` | `%PDF` |
| DOCX/XLSX/PPTX (ZIP) | `50 4B 03 04` | `PK..` |
| PNG | `89 50 4E 47` | `.PNG` |
| JPEG | `FF D8 FF` | `ÿØÿ` |
| ZIP | `50 4B 03 04` | `PK..` |
| GIF | `47 49 46 38` | `GIF8` |

### How to Check Magic Bytes in Python

```python
import magic  # pip install python-magic

def detect_real_type(file_path: str) -> str:
    """Reads actual file content to determine type — ignores extension."""
    mime = magic.from_file(file_path, mime=True)
    return mime  # e.g., "application/pdf"

# Manual check without python-magic:
def check_magic_bytes(file_path: str) -> str:
    with open(file_path, "rb") as f:
        header = f.read(8)

    if header[:4] == b"%PDF":
        return "application/pdf"
    elif header[:4] == b"PK\x03\x04":
        return "application/zip"  # DOCX is a ZIP
    elif header[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    else:
        return "application/octet-stream"  # unknown
```

---

## Streaming Uploads (Large Files)

**The problem:** `await file.read()` loads the entire file into RAM.
A 500MB PDF will eat 500MB of server memory. With 10 concurrent uploads,
that's 5GB — your server crashes.

**The fix:** Read in chunks, write to disk, never hold the full file in memory.

```python
import aiofiles
from uuid import uuid4

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

async def save_uploaded_file(file: UploadFile) -> str:
    """
    Saves an upload to disk by reading it in 64KB chunks.
    Returns the storage path.
    Raises HTTPException if file exceeds MAX_FILE_SIZE.
    """
    ext = file.filename.rsplit(".", 1)[-1].lower() if file.filename else "bin"
    safe_name = f"{uuid4()}.{ext}"
    save_path = f"{UPLOAD_DIR}/{safe_name}"

    total_size = 0

    async with aiofiles.open(save_path, "wb") as out:
        while chunk := await file.read(64 * 1024):  # 64 KB chunks
            total_size += len(chunk)
            if total_size > MAX_FILE_SIZE:
                # Clean up the partially written file
                import os
                os.remove(save_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum size of {MAX_FILE_SIZE // (1024*1024)} MB"
                )
            await out.write(chunk)

    return save_path
```

---

## Storage: Local Disk vs Cloud (S3/GCS)

| Factor | Local Disk | S3/GCS |
|--------|-----------|--------|
| **Setup** | Zero (just a directory) | Need AWS/GCP account, SDK |
| **Cost** | Free (your server's disk) | ~$0.023/GB/month |
| **Scalability** | Limited by disk size | Unlimited |
| **Redundancy** | None (disk dies = files gone) | 99.999999999% durability |
| **Multi-instance** | ❌ Each server has its own copy | ✅ All instances share one bucket |
| **CDN** | ❌ | ✅ Built-in with CloudFront/CDN |
| **Use for** | Learning, local dev | Staging, production |

### S3 Upload Pattern (Production)

```python
import boto3
from botocore.config import Config

s3 = boto3.client(
    "s3",
    region_name="ap-south-1",
    config=Config(retries={"max_attempts": 3}),
)

async def upload_to_s3(file_path: str, key: str, bucket: str) -> str:
    """Uploads a local file to S3 and returns the URL."""
    s3.upload_file(
        file_path,
        bucket,
        key,
        ExtraArgs={
            "ContentType": "application/pdf",
            "ServerSideEncryption": "AES256",
        },
    )
    return f"s3://{bucket}/{key}"


# Pre-signed URL for downloads (temporary, secure link):
def generate_download_url(key: str, bucket: str, expires: int = 3600) -> str:
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires,  # link valid for 1 hour
    )
```

---

## Document Status Lifecycle

```
"uploaded"
    │
    │  Background task starts
    ▼
"processing"
    │
    ├── Text extraction succeeds
    ├── Chunking completes
    ├── Embeddings generated
    │
    ├── SUCCESS ──► "indexed"  ← document is now searchable
    │
    └── FAILURE ──► "failed"   ← log the error, let user retry
                     │
                     └── Store error message in DB for debugging
```

Always let the user check status: `GET /documents/{id}/status`

---

## Security Checklist for File Ingestion

| # | Check | Why |
|---|-------|-----|
| 1 | Validate magic bytes, not just extension | Prevents renamed malware |
| 2 | Limit file size BEFORE reading | Prevents memory exhaustion |
| 3 | Use UUID filenames | Prevents path traversal attacks |
| 4 | Store outside web root | Files aren't directly URL-accessible |
| 5 | Set Content-Disposition on download | Forces "Save As" instead of rendering |
| 6 | Filter allowed MIME types | Only accept PDF, DOCX, TXT |
| 7 | Scan for malware (enterprise) | ClamAV or cloud-based scanning |
| 8 | Enforce per-user upload limits | Prevents storage abuse |
| 9 | Never trust `file.filename` | Use it only for display, never for disk paths |
| 10 | Clean up failed uploads | Don't leave orphan files on disk |

---

## Tools and Libraries

| Tool | Purpose | Install |
|------|---------|---------|
| `python-magic` | Detect real MIME type from file content | `pip install python-magic` |
| `aiofiles` | Async file I/O (streaming writes) | `pip install aiofiles` |
| `boto3` | AWS S3 upload/download | `pip install boto3` |
| `google-cloud-storage` | GCS upload/download | `pip install google-cloud-storage` |
| `filetype` | Lightweight magic byte detection | `pip install filetype` |
| `python-multipart` | Required for FastAPI file uploads | `pip install python-multipart` |
