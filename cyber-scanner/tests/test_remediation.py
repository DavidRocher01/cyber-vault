"""
Tests for scanner/remediation.py
All file I/O uses tmp_path — no writes to the real project tree.
"""

import os

import pytest

from scanner.remediation import (
    _build_fastapi_middleware,
    _build_ssh_script,
    _build_ufw_script,
    _build_upgrade_script,
    generate_remediation,
)

DATE = "2026-01-01 00:00"
TARGET = "https://example.com"


# ---------------------------------------------------------------------------
# _build_ufw_script
# ---------------------------------------------------------------------------

def test_ufw_script_contains_deny_rules_for_critical_ports():
    script = _build_ufw_script(TARGET, DATE, [3306, 5432])
    assert "ufw deny 3306/tcp" in script
    assert "ufw deny 5432/tcp" in script


def test_ufw_script_no_deny_rules_when_no_critical_ports():
    script = _build_ufw_script(TARGET, DATE, [])
    assert "ufw deny" not in script


def test_ufw_script_includes_target_and_date():
    script = _build_ufw_script(TARGET, DATE, [])
    assert TARGET in script
    assert DATE in script


def test_ufw_script_is_bash():
    script = _build_ufw_script(TARGET, DATE, [])
    assert script.startswith("#!/usr/bin/env bash")


# ---------------------------------------------------------------------------
# _build_ssh_script
# ---------------------------------------------------------------------------

def test_ssh_script_disables_password_auth():
    script = _build_ssh_script(TARGET, DATE)
    assert "PasswordAuthentication" in script
    assert '"no"' in script


def test_ssh_script_enables_pubkey_auth():
    script = _build_ssh_script(TARGET, DATE)
    assert "PubkeyAuthentication" in script
    assert '"yes"' in script


def test_ssh_script_disables_root_login():
    script = _build_ssh_script(TARGET, DATE)
    assert "PermitRootLogin" in script


# ---------------------------------------------------------------------------
# _build_fastapi_middleware
# ---------------------------------------------------------------------------

def test_fastapi_middleware_includes_csp():
    script = _build_fastapi_middleware(TARGET, DATE, ["Content-Security-Policy"])
    assert "Content-Security-Policy" in script
    assert "default-src 'self'" in script


def test_fastapi_middleware_includes_x_frame_options():
    script = _build_fastapi_middleware(TARGET, DATE, ["X-Frame-Options"])
    assert "X-Frame-Options" in script
    assert "DENY" in script


def test_fastapi_middleware_all_headers_when_none_missing():
    script = _build_fastapi_middleware(TARGET, DATE, [])
    assert "Content-Security-Policy" in script
    assert "Strict-Transport-Security" in script


def test_fastapi_middleware_is_valid_python():
    script = _build_fastapi_middleware(TARGET, DATE, ["X-Frame-Options"])
    # Basic structural check — no syntax error would compile
    compile(script, "<string>", "exec")


# ---------------------------------------------------------------------------
# _build_upgrade_script
# ---------------------------------------------------------------------------

def test_upgrade_script_contains_pip_command():
    vulns = [{"package": "requests", "ecosystem": "PyPI", "cve_ids": ["CVE-2022-0001"]}]
    script = _build_upgrade_script(TARGET, DATE, vulns)
    assert "pip install --upgrade requests" in script


def test_upgrade_script_contains_npm_command():
    vulns = [{"package": "lodash", "ecosystem": "npm", "cve_ids": ["CVE-2021-0002"]}]
    script = _build_upgrade_script(TARGET, DATE, vulns)
    assert "npm update lodash" in script


def test_upgrade_script_deduplicates_packages():
    vulns = [
        {"package": "requests", "ecosystem": "PyPI", "cve_ids": ["CVE-2022-0001"]},
        {"package": "requests", "ecosystem": "PyPI", "cve_ids": ["CVE-2022-0002"]},
    ]
    script = _build_upgrade_script(TARGET, DATE, vulns)
    assert script.count("pip install --upgrade requests") == 1


def test_upgrade_script_no_vulns_shows_placeholder():
    script = _build_upgrade_script(TARGET, DATE, [])
    assert "No PyPI vulnerabilities found" in script
    assert "No npm vulnerabilities found" in script


# ---------------------------------------------------------------------------
# generate_remediation (integration)
# ---------------------------------------------------------------------------

def test_generate_remediation_creates_ufw_and_ssh_files(tmp_path):
    paths = generate_remediation(TARGET, output_dir=str(tmp_path))
    assert "ufw" in paths
    assert "ssh" in paths
    assert os.path.exists(paths["ufw"])
    assert os.path.exists(paths["ssh"])


def test_generate_remediation_creates_fastapi_when_headers_missing(tmp_path):
    headers_result = {
        "headers_missing": ["Content-Security-Policy", "X-Frame-Options"],
        "headers_found": [],
        "error": None,
    }
    paths = generate_remediation(TARGET, headers_result=headers_result, output_dir=str(tmp_path))
    assert "fastapi" in paths
    assert os.path.exists(paths["fastapi"])


def test_generate_remediation_creates_upgrade_when_vulns_exist(tmp_path):
    sca_result = {
        "vulns": [{"package": "flask", "ecosystem": "PyPI", "version": "2.0.0", "cve_ids": ["CVE-2023-0001"]}],
        "error": None,
    }
    paths = generate_remediation(TARGET, sca_result=sca_result, output_dir=str(tmp_path))
    assert "upgrade" in paths
    assert os.path.exists(paths["upgrade"])


def test_generate_remediation_ufw_includes_deny_rules_from_ports(tmp_path):
    port_result = {"critical_ports": [3306, 27017], "open_ports": [22, 3306, 27017], "error": None}
    paths = generate_remediation(TARGET, port_result=port_result, output_dir=str(tmp_path))
    content = open(paths["ufw"]).read()
    assert "ufw deny 3306/tcp" in content
    assert "ufw deny 27017/tcp" in content
