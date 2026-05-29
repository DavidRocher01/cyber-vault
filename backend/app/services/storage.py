"""File storage — S3 in prod, local filesystem fallback in dev."""

from __future__ import annotations

import uuid
from pathlib import Path

from app.core.config import settings

_LOCAL_UPLOAD_DIR = Path("uploads") / "rssi"
_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "image/png",
    "image/jpeg",
}
_ALLOWED_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".odt",
    ".ods",
    ".png",
    ".jpg",
    ".jpeg",
}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


def validate_upload(filename: str, content_type: str, size: int) -> None:
    """Raise ValueError with a user-facing message if the file is invalid."""
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Extension non autorisée. Formats acceptés : {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
        )
    if content_type not in _ALLOWED_MIME_TYPES:
        raise ValueError("Type de fichier non autorisé.")
    if size > MAX_UPLOAD_BYTES:
        raise ValueError("Fichier trop volumineux (max 20 Mo).")


def _s3_key(user_id: int, client_id: int, original_name: str) -> str:
    safe = Path(original_name).name.replace(" ", "_")
    return f"rssi-deliverables/{user_id}/{client_id}/{uuid.uuid4().hex}_{safe}"


def upload_file(content: bytes, original_name: str, user_id: int, client_id: int) -> str:
    """Upload a file and return its storage key."""
    if settings.S3_BUCKET_NAME:
        return _upload_s3(content, original_name, user_id, client_id)
    return _upload_local(content, original_name, user_id, client_id)


def get_download_url(key: str, expires: int = 3600) -> str:
    """Return a download URL for a stored key (presigned if S3, local path if local)."""
    if settings.S3_BUCKET_NAME and key.startswith("rssi-deliverables/"):
        return _presign_s3(key, expires)
    # Local: key is a relative path like "uploads/rssi/..."
    return f"/{key}"


# ── S3 backend ─────────────────────────────────────────────────────────────────


def _upload_s3(content: bytes, original_name: str, user_id: int, client_id: int) -> str:
    import boto3  # lazy import — only needed when S3 is configured

    key = _s3_key(user_id, client_id, original_name)
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    s3.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=content,
        ContentDisposition=f'attachment; filename="{Path(original_name).name}"',
    )
    return key


def _presign_s3(key: str, expires: int) -> str:
    import boto3

    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
        ExpiresIn=expires,
    )


# ── Local filesystem backend ───────────────────────────────────────────────────


def _upload_local(content: bytes, original_name: str, user_id: int, client_id: int) -> str:
    dest_dir = _LOCAL_UPLOAD_DIR / str(user_id) / str(client_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = Path(original_name).name.replace(" ", "_")
    filename = f"{uuid.uuid4().hex}_{safe}"
    path = dest_dir / filename
    path.write_bytes(content)
    return str(Path("uploads") / "rssi" / str(user_id) / str(client_id) / filename).replace(
        "\\", "/"
    )
