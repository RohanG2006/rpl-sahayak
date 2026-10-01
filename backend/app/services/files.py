"""Upload validation + storage. File type is decided by magic bytes, never by the client-supplied content type."""
import hashlib
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import AppError

SIGNATURES: list[tuple[bytes, int, str, str, str]] = [
    # (magic, offset, mime, kind, ext)
    (b"\xff\xd8\xff", 0, "image/jpeg", "image", "jpg"),
    (b"\x89PNG\r\n\x1a\n", 0, "image/png", "image", "png"),
    (b"WEBP", 8, "image/webp", "image", "webp"),
    (b"%PDF-", 0, "application/pdf", "document", "pdf"),
    (b"ftyp", 4, "video/mp4", "video", "mp4"),
    (b"\x1a\x45\xdf\xa3", 0, "video/webm", "video", "webm"),
    (b"ID3", 0, "audio/mpeg", "audio", "mp3"),
    (b"RIFF", 0, "audio/wav", "audio", "wav"),
]


class InvalidUpload(AppError):
    status, code = 415, "invalid_evidence"


class UploadTooLarge(AppError):
    status, code = 413, "upload_too_large"


def sniff(head: bytes) -> tuple[str, str, str] | None:
    for magic, off, mime, kind, ext in SIGNATURES:
        if head[off : off + len(magic)] == magic:
            if mime == "audio/wav" and head[8:12] != b"WAVE":
                continue
            if mime == "image/webp" and head[:4] != b"RIFF":
                continue
            return mime, kind, ext
    return None


async def read_validated(upload: UploadFile) -> tuple[bytes, str, str, str, str]:
    """Return (data, mime, kind, ext, sha256). Enforces size limit while reading."""
    s = get_settings()
    limit = s.max_upload_mb * 1024 * 1024
    chunks, size = [], 0
    while True:
        chunk = await upload.read(1024 * 256)
        if not chunk:
            break
        size += len(chunk)
        if size > limit:
            raise UploadTooLarge(f"File is larger than {s.max_upload_mb} MB.")
        chunks.append(chunk)
    data = b"".join(chunks)
    if not data:
        raise InvalidUpload("The file is empty.")
    found = sniff(data[:32])
    if not found or found[0] not in s.allowed_upload_mime:
        raise InvalidUpload("Unsupported file. Use a photo (JPG/PNG/WebP), short video (MP4/WebM), PDF or audio.")
    mime, kind, ext = found
    return data, mime, kind, ext, hashlib.sha256(data).hexdigest()


def store(worker_id: str, data: bytes, ext: str) -> str:
    root = Path(get_settings().storage_dir)
    rel = Path(worker_id) / f"{uuid.uuid4().hex}.{ext}"
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_bytes(data)
    return rel.as_posix()


def path_of(rel: str) -> Path:
    root = Path(get_settings().storage_dir).resolve()
    p = (root / rel).resolve()
    if root not in p.parents:
        raise InvalidUpload("Invalid file path.")
    return p
