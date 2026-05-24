"""Unit tests — storage.py (validate_upload, upload_file, get_download_url, S3 paths)."""
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


# ── validate_upload ────────────────────────────────────────────────────────────

def test_validate_pdf_ok():
    from app.services.storage import validate_upload
    validate_upload("rapport.pdf", "application/pdf", 1024)  # no exception


def test_validate_docx_ok():
    from app.services.storage import validate_upload
    validate_upload("doc.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 512)


def test_validate_xlsx_ok():
    from app.services.storage import validate_upload
    validate_upload(
        "data.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        2048,
    )


def test_validate_png_ok():
    from app.services.storage import validate_upload
    validate_upload("image.png", "image/png", 500_000)


def test_validate_jpeg_ok():
    from app.services.storage import validate_upload
    validate_upload("photo.jpg", "image/jpeg", 300_000)


def test_validate_invalid_extension_raises():
    from app.services.storage import validate_upload
    with pytest.raises(ValueError, match="Extension"):
        validate_upload("script.exe", "application/octet-stream", 100)


def test_validate_invalid_mime_type_raises():
    from app.services.storage import validate_upload
    # extension ok but MIME type forbidden
    with pytest.raises(ValueError, match="non autorisé"):
        validate_upload("file.pdf", "text/html", 100)


def test_validate_too_large_raises():
    from app.services.storage import validate_upload
    big = 21 * 1024 * 1024  # 21 MB > 20 MB limit
    with pytest.raises(ValueError, match="volumineux"):
        validate_upload("big.pdf", "application/pdf", big)


def test_validate_exactly_max_size_ok():
    from app.services.storage import validate_upload
    from app.services.storage import MAX_UPLOAD_BYTES
    validate_upload("maxsize.pdf", "application/pdf", MAX_UPLOAD_BYTES)  # exactly 20 MB — ok


def test_validate_odt_ok():
    from app.services.storage import validate_upload
    validate_upload("doc.odt", "application/vnd.oasis.opendocument.text", 1024)


# ── get_download_url — local path ──────────────────────────────────────────────

def test_get_download_url_local_returns_slash_prefix():
    from app.services.storage import get_download_url
    with patch("app.services.storage.settings") as mock_settings:
        mock_settings.S3_BUCKET_NAME = ""
        url = get_download_url("uploads/rssi/1/5/abc_rapport.pdf")
    assert url.startswith("/")
    assert "uploads" in url


def test_get_download_url_non_s3_key_returns_local():
    from app.services.storage import get_download_url
    with patch("app.services.storage.settings") as mock_settings:
        mock_settings.S3_BUCKET_NAME = "my-bucket"
        # key does NOT start with rssi-deliverables/ → local path
        url = get_download_url("uploads/rssi/1/5/abc.pdf")
    assert url == "/uploads/rssi/1/5/abc.pdf"


def test_get_download_url_s3_key_calls_presign():
    from app.services.storage import get_download_url
    fake_url = "https://s3.amazonaws.com/my-bucket/rssi-deliverables/1/5/abc.pdf?X-Amz-Signature=xyz"
    with patch("app.services.storage.settings") as mock_settings:
        mock_settings.S3_BUCKET_NAME = "my-bucket"
        mock_settings.AWS_REGION = "eu-west-3"
        with patch("app.services.storage._presign_s3", return_value=fake_url) as mock_presign:
            url = get_download_url("rssi-deliverables/1/5/abc.pdf", expires=3600)
    mock_presign.assert_called_once_with("rssi-deliverables/1/5/abc.pdf", 3600)
    assert url == fake_url


# ── upload_file routing ────────────────────────────────────────────────────────

def test_upload_file_routes_to_local_when_no_s3():
    from app.services.storage import upload_file
    with patch("app.services.storage.settings") as mock_settings:
        mock_settings.S3_BUCKET_NAME = ""
        with patch("app.services.storage._upload_local", return_value="uploads/rssi/1/5/abc.pdf") as mock_local:
            key = upload_file(b"content", "doc.pdf", user_id=1, client_id=5)
    mock_local.assert_called_once_with(b"content", "doc.pdf", 1, 5)
    assert key == "uploads/rssi/1/5/abc.pdf"


def test_upload_file_routes_to_s3_when_configured():
    from app.services.storage import upload_file
    with patch("app.services.storage.settings") as mock_settings:
        mock_settings.S3_BUCKET_NAME = "my-bucket"
        with patch("app.services.storage._upload_s3", return_value="rssi-deliverables/1/5/abc.pdf") as mock_s3:
            key = upload_file(b"content", "doc.pdf", user_id=1, client_id=5)
    mock_s3.assert_called_once_with(b"content", "doc.pdf", 1, 5)
    assert key == "rssi-deliverables/1/5/abc.pdf"


# ── _upload_local ──────────────────────────────────────────────────────────────

def test_upload_local_creates_file(tmp_path):
    from app.services import storage as storage_mod
    original_dir = storage_mod._LOCAL_UPLOAD_DIR
    try:
        storage_mod._LOCAL_UPLOAD_DIR = tmp_path / "rssi"
        key = storage_mod._upload_local(b"PDF content", "rapport.pdf", user_id=42, client_id=7)
        assert key.endswith("rapport.pdf")
        assert "42" in key
        assert "7" in key
        # The file actually exists on disk
        relative = key.lstrip("/")
        # Key format: uploads/rssi/42/7/uuid_rapport.pdf — find the file
        files = list((tmp_path / "rssi" / "42" / "7").iterdir())
        assert len(files) == 1
        assert files[0].read_bytes() == b"PDF content"
    finally:
        storage_mod._LOCAL_UPLOAD_DIR = original_dir


def test_upload_local_sanitizes_spaces(tmp_path):
    from app.services import storage as storage_mod
    original_dir = storage_mod._LOCAL_UPLOAD_DIR
    try:
        storage_mod._LOCAL_UPLOAD_DIR = tmp_path / "rssi"
        key = storage_mod._upload_local(b"data", "my file name.pdf", user_id=1, client_id=1)
        assert " " not in key
    finally:
        storage_mod._LOCAL_UPLOAD_DIR = original_dir


def test_upload_local_key_uses_forward_slashes(tmp_path):
    from app.services import storage as storage_mod
    original_dir = storage_mod._LOCAL_UPLOAD_DIR
    try:
        storage_mod._LOCAL_UPLOAD_DIR = tmp_path / "rssi"
        key = storage_mod._upload_local(b"x", "test.pdf", user_id=2, client_id=3)
        assert "\\" not in key
    finally:
        storage_mod._LOCAL_UPLOAD_DIR = original_dir


# ── _upload_s3 / _presign_s3 ──────────────────────────────────────────────────

def test_upload_s3_calls_put_object():
    from app.services.storage import _upload_s3
    mock_client = MagicMock()
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client

    with patch("app.services.storage.settings") as mock_settings:
        mock_settings.S3_BUCKET_NAME = "my-bucket"
        mock_settings.AWS_REGION = "eu-west-3"
        with patch.dict("sys.modules", {"boto3": mock_boto3}):
            key = _upload_s3(b"PDF", "rapport.pdf", user_id=1, client_id=5)

    mock_client.put_object.assert_called_once()
    call_kwargs = mock_client.put_object.call_args[1]
    assert call_kwargs["Bucket"] == "my-bucket"
    assert "rssi-deliverables" in call_kwargs["Key"]
    assert key.startswith("rssi-deliverables/")


def test_presign_s3_generates_url():
    from app.services.storage import _presign_s3
    mock_client = MagicMock()
    mock_client.generate_presigned_url.return_value = "https://s3.example.com/signed"
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_client

    with patch("app.services.storage.settings") as mock_settings:
        mock_settings.S3_BUCKET_NAME = "my-bucket"
        mock_settings.AWS_REGION = "eu-west-3"
        with patch.dict("sys.modules", {"boto3": mock_boto3}):
            url = _presign_s3("rssi-deliverables/1/5/abc.pdf", 3600)

    mock_client.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": "my-bucket", "Key": "rssi-deliverables/1/5/abc.pdf"},
        ExpiresIn=3600,
    )
    assert url == "https://s3.example.com/signed"
