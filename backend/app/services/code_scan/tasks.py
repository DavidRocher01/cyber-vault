"""
tasks.py — Async entry-point tasks: run_code_scan and run_code_scan_zip.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code_scan import CodeScan

from .runner import _run_all_tools
from .utils import _redact_url


def _run_subprocess(cmd: list[str], cwd: str, timeout: int = 120):
    """Thin wrapper around subprocess for git clone (avoids circular import)."""
    import subprocess

    try:
        proc = subprocess.run(  # nosec B603
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Timeout after {timeout}s"
    except FileNotFoundError:
        return -2, "", f"Command not found: {cmd[0]}"


async def run_code_scan(scan_id: int, db: AsyncSession, clone_url: str | None = None) -> None:
    """
    Background task: clone repo, run tools, persist results.
    clone_url — URL with embedded token if provided; never stored in DB.
    """
    from sqlalchemy import select

    result = await db.execute(select(CodeScan).where(CodeScan.id == scan_id))
    scan: CodeScan | None = result.scalar_one_or_none()
    if not scan:
        logger.error(f"CodeScan {scan_id} not found")
        return

    scan.status = "running"
    scan.started_at = datetime.now(UTC)
    await db.commit()

    tmp_dir = tempfile.mkdtemp(prefix="rochercybersecurite_code_")
    try:
        effective_clone_url = clone_url or scan.repo_url
        logger.info(f"CodeScan {scan_id}: cloning {scan.repo_url}")
        rc, _, stderr = _run_subprocess(
            ["git", "clone", "--depth=1", effective_clone_url, "repo"],
            cwd=tmp_dir,
            timeout=120,
        )
        if rc != 0:
            raise RuntimeError(f"git clone failed: {_redact_url(stderr[:300])}")

        repo_dir = os.path.join(tmp_dir, "repo")

        all_findings, counts, unavailable = await asyncio.to_thread(
            _run_all_tools, scan_id, repo_dir
        )
        total = sum(counts.values())

        results = {
            "findings": all_findings,
            "summary": {
                "total": total,
                **counts,
            },
            "tool_errors": unavailable,
        }

        scan.status = "done"
        scan.critical_count = counts["critical"]
        scan.high_count = counts["high"]
        scan.medium_count = counts["medium"]
        scan.low_count = counts["low"]
        scan.results_json = json.dumps(results)
        scan.finished_at = datetime.now(UTC)
        logger.info(f"CodeScan {scan_id}: done — {total} findings")

    except Exception as exc:
        logger.exception(f"CodeScan {scan_id} failed: {exc}")
        scan.status = "failed"
        scan.error_message = str(exc)[:512]
        scan.finished_at = datetime.now(UTC)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        await db.commit()


async def run_code_scan_zip(scan_id: int, zip_path: str, db: AsyncSession) -> None:
    """Background task: extract ZIP archive, run tools, persist results."""
    from sqlalchemy import select

    result = await db.execute(select(CodeScan).where(CodeScan.id == scan_id))
    scan: CodeScan | None = result.scalar_one_or_none()
    if not scan:
        logger.error(f"CodeScan {scan_id} not found")
        return

    scan.status = "running"
    scan.started_at = datetime.now(UTC)
    await db.commit()

    tmp_dir = tempfile.mkdtemp(prefix="rochercybersecurite_code_")
    try:
        logger.info(f"CodeScan {scan_id}: extracting ZIP")
        repo_dir = os.path.join(tmp_dir, "repo")
        os.makedirs(repo_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as z:
            total_size = sum(info.file_size for info in z.infolist())
            if total_size > 200 * 1024 * 1024:
                raise RuntimeError("Archive trop volumineuse après extraction (max 200 MB)")
            real_repo = os.path.realpath(repo_dir)
            for member in z.infolist():
                dest = os.path.realpath(os.path.join(repo_dir, member.filename))
                if not dest.startswith(real_repo + os.sep) and dest != real_repo:
                    raise RuntimeError("Archive contient des chemins invalides (path traversal)")
            z.extractall(repo_dir)

        entries = list(Path(repo_dir).iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            repo_dir = str(entries[0])

        all_findings, counts, unavailable = await asyncio.to_thread(
            _run_all_tools, scan_id, repo_dir
        )
        total = sum(counts.values())
        results = {
            "findings": all_findings,
            "summary": {"total": total, **counts},
            "tool_errors": unavailable,
        }

        scan.status = "done"
        scan.critical_count = counts["critical"]
        scan.high_count = counts["high"]
        scan.medium_count = counts["medium"]
        scan.low_count = counts["low"]
        scan.results_json = json.dumps(results)
        scan.finished_at = datetime.now(UTC)
        logger.info(f"CodeScan {scan_id}: done — {total} findings")

    except Exception as exc:
        logger.exception(f"CodeScan {scan_id} (ZIP) failed: {exc}")
        scan.status = "failed"
        scan.error_message = str(exc)[:512]
        scan.finished_at = datetime.now(UTC)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        try:
            os.unlink(zip_path)
        except OSError as exc:
            logger.debug("Nettoyage du zip temporaire echoue : {}", exc)
        await db.commit()
