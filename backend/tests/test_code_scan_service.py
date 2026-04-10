"""
Unit tests — app.services.code_scan_service
Tests cover pure helper functions and the main orchestration
(run_code_scan / run_code_scan_zip) with subprocess mocked.
"""

import io
import json
import os
import tempfile
import zipfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.code_scan_service import (
    _count_severities,
    _extract_repo_name,
    _run,
    _run_bandit,
    _run_pip_audit,
    _run_semgrep,
    _sanitize_repo_url,
    run_code_scan,
    run_code_scan_zip,
)


# ─── _sanitize_repo_url ────────────────────────────────────────────────────────

def test_sanitize_repo_url_without_token():
    url = "https://github.com/user/repo"
    assert _sanitize_repo_url(url, None) == url


def test_sanitize_repo_url_with_token():
    url = "https://github.com/user/repo"
    result = _sanitize_repo_url(url, "ghp_abc123")
    assert "ghp_abc123@github.com" in result


def test_sanitize_repo_url_non_http_unchanged():
    url = "git@github.com:user/repo.git"
    assert _sanitize_repo_url(url, "token") == url


# ─── _extract_repo_name ───────────────────────────────────────────────────────

def test_extract_repo_name_github_url():
    assert _extract_repo_name("https://github.com/owner/repo") == "owner/repo"


def test_extract_repo_name_strips_git_suffix():
    assert _extract_repo_name("https://github.com/owner/repo.git") == "owner/repo"


def test_extract_repo_name_strips_trailing_slash():
    assert _extract_repo_name("https://github.com/owner/repo/") == "owner/repo"


# ─── _run ─────────────────────────────────────────────────────────────────────

def test_run_success():
    with tempfile.TemporaryDirectory() as d:
        rc, stdout, stderr = _run(["python", "-c", "print('hello')"], cwd=d)
    assert rc == 0
    assert "hello" in stdout


def test_run_timeout():
    with tempfile.TemporaryDirectory() as d:
        rc, stdout, stderr = _run(["python", "-c", "import time; time.sleep(10)"], cwd=d, timeout=1)
    assert rc == 1
    assert "Timeout" in stderr


def test_run_command_not_found():
    with tempfile.TemporaryDirectory() as d:
        rc, stdout, stderr = _run(["nonexistent_tool_xyz"], cwd=d)
    assert rc == 1
    assert "not found" in stderr


# ─── _count_severities ────────────────────────────────────────────────────────

def test_count_severities_empty():
    assert _count_severities([]) == {"critical": 0, "high": 0, "medium": 0, "low": 0}


def test_count_severities_mixed():
    findings = [
        {"severity": "critical"},
        {"severity": "high"},
        {"severity": "high"},
        {"severity": "medium"},
        {"severity": "low"},
        {"severity": "unknown"},  # should not raise
    ]
    counts = _count_severities(findings)
    assert counts["critical"] == 1
    assert counts["high"] == 2
    assert counts["medium"] == 1
    assert counts["low"] == 1


def test_count_severities_all_critical():
    findings = [{"severity": "critical"}] * 5
    assert _count_severities(findings)["critical"] == 5


# ─── _run_bandit ──────────────────────────────────────────────────────────────

def test_run_bandit_parses_findings():
    bandit_output = json.dumps({
        "results": [
            {
                "test_id": "B101",
                "test_name": "assert_used",
                "issue_text": "Use of assert detected.",
                "filename": "/tmp/repo/app/main.py",
                "line_number": 10,
                "issue_severity": "LOW",
                "issue_confidence": "HIGH",
            }
        ]
    })
    with patch("app.services.code_scan_service._run", return_value=(0, bandit_output, "")):
        findings = _run_bandit("/tmp/repo")
    assert len(findings) == 1
    assert findings[0]["tool"] == "bandit"
    assert findings[0]["severity"] == "low"
    assert findings[0]["rule"] == "B101"


def test_run_bandit_maps_high_severity():
    bandit_output = json.dumps({
        "results": [{"test_id": "B602", "test_name": "subprocess_popen", "issue_text": "msg",
                      "filename": "/tmp/repo/a.py", "line_number": 1,
                      "issue_severity": "HIGH", "issue_confidence": "MEDIUM"}]
    })
    with patch("app.services.code_scan_service._run", return_value=(0, bandit_output, "")):
        findings = _run_bandit("/tmp/repo")
    assert findings[0]["severity"] == "high"


def test_run_bandit_empty_output_returns_empty():
    with patch("app.services.code_scan_service._run", return_value=(1, "", "bandit not found")):
        findings = _run_bandit("/tmp/repo")
    assert findings == []


def test_run_bandit_invalid_json_returns_empty():
    with patch("app.services.code_scan_service._run", return_value=(0, "not-json", "")):
        findings = _run_bandit("/tmp/repo")
    assert findings == []


def test_run_bandit_strips_repo_dir_from_filename():
    bandit_output = json.dumps({
        "results": [{"test_id": "B1", "test_name": "test", "issue_text": "msg",
                      "filename": "/tmp/repo/src/app.py", "line_number": 5,
                      "issue_severity": "MEDIUM", "issue_confidence": "LOW"}]
    })
    with patch("app.services.code_scan_service._run", return_value=(0, bandit_output, "")):
        findings = _run_bandit("/tmp/repo")
    assert findings[0]["file"] == "src/app.py"


# ─── _run_semgrep ─────────────────────────────────────────────────────────────

def test_run_semgrep_parses_findings():
    semgrep_output = json.dumps({
        "results": [
            {
                "check_id": "python.lang.security.audit.insecure-hash.insecure-md5",
                "path": "/tmp/repo/utils/crypto.py",
                "start": {"line": 42},
                "extra": {"severity": "WARNING", "message": "MD5 is insecure"},
            }
        ]
    })
    with patch("app.services.code_scan_service._run", return_value=(0, semgrep_output, "")):
        findings = _run_semgrep("/tmp/repo")
    assert len(findings) == 1
    assert findings[0]["tool"] == "semgrep"
    assert findings[0]["severity"] == "medium"
    assert findings[0]["line"] == 42


def test_run_semgrep_critical_severity():
    semgrep_output = json.dumps({
        "results": [
            {
                "check_id": "rule.critical",
                "path": "/tmp/repo/app.py",
                "start": {"line": 1},
                "extra": {"severity": "CRITICAL", "message": "Critical issue"},
            }
        ]
    })
    with patch("app.services.code_scan_service._run", return_value=(0, semgrep_output, "")):
        findings = _run_semgrep("/tmp/repo")
    assert findings[0]["severity"] == "critical"


def test_run_semgrep_empty_output_returns_empty():
    with patch("app.services.code_scan_service._run", return_value=(1, "", "semgrep not found")):
        findings = _run_semgrep("/tmp/repo")
    assert findings == []


def test_run_semgrep_invalid_json_returns_empty():
    with patch("app.services.code_scan_service._run", return_value=(0, "broken{json", "")):
        findings = _run_semgrep("/tmp/repo")
    assert findings == []


# ─── _run_pip_audit ───────────────────────────────────────────────────────────

def test_run_pip_audit_no_requirements_file(tmp_path):
    findings = _run_pip_audit(str(tmp_path))
    assert findings == []


def test_run_pip_audit_parses_vulnerabilities(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("flask==1.0.0\n")

    audit_output = json.dumps({
        "dependencies": [
            {
                "name": "flask",
                "version": "1.0.0",
                "vulns": [
                    {
                        "id": "PYSEC-2021-1",
                        "description": "XSS vulnerability in Flask",
                        "fix_versions": ["2.0.0"],
                        "aliases": [],
                    }
                ],
            }
        ]
    })
    with patch("app.services.code_scan_service._run", return_value=(0, audit_output, "")):
        findings = _run_pip_audit(str(tmp_path))
    assert len(findings) == 1
    assert findings[0]["tool"] == "pip-audit"
    assert findings[0]["rule"] == "PYSEC-2021-1"
    assert findings[0]["severity"] == "high"
    assert "2.0.0" in findings[0]["fix_versions"]


def test_run_pip_audit_empty_output_returns_empty(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("django==3.2\n")
    with patch("app.services.code_scan_service._run", return_value=(1, "", "pip-audit not found")):
        findings = _run_pip_audit(str(tmp_path))
    assert findings == []


def test_run_pip_audit_invalid_json_returns_empty(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("django==3.2\n")
    with patch("app.services.code_scan_service._run", return_value=(0, "not-json", "")):
        findings = _run_pip_audit(str(tmp_path))
    assert findings == []


def test_run_pip_audit_no_vulns_returns_empty(tmp_path):
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.28.0\n")
    audit_output = json.dumps({"dependencies": [{"name": "requests", "version": "2.28.0", "vulns": []}]})
    with patch("app.services.code_scan_service._run", return_value=(0, audit_output, "")):
        findings = _run_pip_audit(str(tmp_path))
    assert findings == []


# ─── run_code_scan (async, mocked DB) ─────────────────────────────────────────

def _make_mock_scan(scan_id: int = 1) -> MagicMock:
    scan = MagicMock()
    scan.id = scan_id
    scan.repo_url = "https://github.com/user/repo"
    return scan


def _make_mock_db(scan: MagicMock | None):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = scan
    db.execute = AsyncMock(return_value=result)
    return db


@pytest.mark.asyncio
async def test_run_code_scan_scan_not_found():
    """Should return early without error when scan_id doesn't exist."""
    db = _make_mock_db(None)
    # Should not raise
    await run_code_scan(999, db)
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_run_code_scan_success():
    scan = _make_mock_scan()
    db = _make_mock_db(scan)

    with patch("app.services.code_scan_service._run", return_value=(0, "", "")):
        with patch("app.services.code_scan_service._run_bandit", return_value=[
            {"tool": "bandit", "severity": "high", "rule": "B1", "title": "t",
             "message": "m", "file": "a.py", "line": 1, "confidence": "HIGH"}
        ]):
            with patch("app.services.code_scan_service._run_semgrep", return_value=[]):
                with patch("app.services.code_scan_service._run_pip_audit", return_value=[]):
                    with patch("shutil.rmtree"):
                        await run_code_scan(1, db)

    assert scan.status == "done"
    assert scan.high_count == 1
    assert scan.critical_count == 0
    assert scan.results_json is not None
    results = json.loads(scan.results_json)
    assert results["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_run_code_scan_git_clone_failure():
    scan = _make_mock_scan()
    db = _make_mock_db(scan)

    # git clone returns non-zero exit code
    with patch("app.services.code_scan_service._run", return_value=(1, "", "fatal: not found")):
        with patch("shutil.rmtree"):
            await run_code_scan(1, db)

    assert scan.status == "failed"
    assert "git clone failed" in scan.error_message


@pytest.mark.asyncio
async def test_run_code_scan_sets_started_at():
    scan = _make_mock_scan()
    db = _make_mock_db(scan)

    with patch("app.services.code_scan_service._run", return_value=(1, "", "error")):
        with patch("shutil.rmtree"):
            await run_code_scan(1, db)

    assert scan.started_at is not None


# ─── run_code_scan_zip (async, mocked DB) ─────────────────────────────────────

def _make_zip_bytes(filename: str = "main.py", content: str = "print('hello')") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, content)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_run_code_scan_zip_scan_not_found():
    db = _make_mock_db(None)
    await run_code_scan_zip(999, "/tmp/fake.zip", db)
    db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_run_code_scan_zip_success(tmp_path):
    # Write a real zip to disk
    zip_path = str(tmp_path / "upload.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("app/main.py", "import os")

    scan = _make_mock_scan()
    db = _make_mock_db(scan)

    with patch("app.services.code_scan_service._run_bandit", return_value=[]):
        with patch("app.services.code_scan_service._run_semgrep", return_value=[]):
            with patch("app.services.code_scan_service._run_pip_audit", return_value=[]):
                with patch("shutil.rmtree"):
                    await run_code_scan_zip(1, zip_path, db)

    assert scan.status == "done"
    assert scan.results_json is not None


@pytest.mark.asyncio
async def test_run_code_scan_zip_path_traversal(tmp_path):
    zip_path = str(tmp_path / "evil.zip")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../../../etc/passwd", "root:x:0:0")
    with open(zip_path, "wb") as f:
        f.write(buf.getvalue())

    scan = _make_mock_scan()
    db = _make_mock_db(scan)

    with patch("shutil.rmtree"):
        await run_code_scan_zip(1, zip_path, db)

    assert scan.status == "failed"
    assert "path traversal" in scan.error_message.lower()


@pytest.mark.asyncio
async def test_run_code_scan_zip_cleans_up_zip_file(tmp_path):
    zip_path = str(tmp_path / "upload.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("main.py", "pass")

    scan = _make_mock_scan()
    db = _make_mock_db(scan)

    with patch("app.services.code_scan_service._run_bandit", return_value=[]):
        with patch("app.services.code_scan_service._run_semgrep", return_value=[]):
            with patch("app.services.code_scan_service._run_pip_audit", return_value=[]):
                with patch("shutil.rmtree"):
                    await run_code_scan_zip(1, zip_path, db)

    # ZIP file should be deleted after processing
    assert not os.path.exists(zip_path)


@pytest.mark.asyncio
async def test_run_code_scan_zip_descends_single_top_level_folder(tmp_path):
    """ZIP with a single top-level folder should unwrap it."""
    zip_path = str(tmp_path / "wrapped.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("myproject/main.py", "pass")
        zf.writestr("myproject/requirements.txt", "flask==2.0.0")

    scan = _make_mock_scan()
    db = _make_mock_db(scan)

    called_dirs = []

    def capture_bandit(repo_dir):
        called_dirs.append(repo_dir)
        return []

    with patch("app.services.code_scan_service._run_bandit", side_effect=capture_bandit):
        with patch("app.services.code_scan_service._run_semgrep", return_value=[]):
            with patch("app.services.code_scan_service._run_pip_audit", return_value=[]):
                with patch("shutil.rmtree"):
                    await run_code_scan_zip(1, zip_path, db)

    # The bandit should have been called on the inner folder, not the outer wrapper
    assert any("myproject" in d for d in called_dirs)
