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
    _build_ssl_nginx,
    _build_cors_fastapi,
    _build_cors_nginx,
    _build_cookies_script,
    _build_http_methods_nginx,
    _build_clickjacking_nginx,
    _build_clickjacking_fastapi,
    _build_directory_listing_nginx,
    _build_open_redirect_fastapi,
    _build_robots_txt,
    _build_email_security,
    _build_waf_nginx,
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


def test_generate_remediation_always_creates_robots_and_waf(tmp_path):
    paths = generate_remediation(TARGET, output_dir=str(tmp_path))
    assert "robots" in paths
    assert "nginx_waf" in paths
    assert os.path.exists(paths["robots"])
    assert os.path.exists(paths["nginx_waf"])


# ---------------------------------------------------------------------------
# _build_ssl_nginx
# ---------------------------------------------------------------------------

def test_ssl_nginx_contains_tls_directive():
    script = _build_ssl_nginx(TARGET, DATE)
    assert "ssl_protocols" in script
    assert "TLSv1.2" in script
    assert "TLSv1.3" in script


def test_ssl_nginx_contains_hsts():
    script = _build_ssl_nginx(TARGET, DATE)
    assert "Strict-Transport-Security" in script


# ---------------------------------------------------------------------------
# _build_cors_fastapi
# ---------------------------------------------------------------------------

def test_cors_fastapi_includes_allow_origins():
    issues = ["Wildcard origin detected"]
    script = _build_cors_fastapi(TARGET, DATE, issues)
    assert "allow_origins" in script
    assert "CORSMiddleware" in script


def test_cors_fastapi_is_valid_python():
    compile(_build_cors_fastapi(TARGET, DATE, []), "<string>", "exec")


# ---------------------------------------------------------------------------
# _build_cors_nginx
# ---------------------------------------------------------------------------

def test_cors_nginx_contains_access_control_header():
    script = _build_cors_nginx(TARGET, DATE)
    assert "Access-Control-Allow-Origin" in script


# ---------------------------------------------------------------------------
# _build_cookies_script
# ---------------------------------------------------------------------------

def test_cookies_script_sets_httponly():
    issues = [{"name": "session", "missing_flags": ["HttpOnly"]}]
    script = _build_cookies_script(TARGET, DATE, issues)
    assert "httponly" in script.lower()


def test_cookies_script_is_valid_python():
    compile(_build_cookies_script(TARGET, DATE, []), "<string>", "exec")


# ---------------------------------------------------------------------------
# _build_http_methods_nginx
# ---------------------------------------------------------------------------

def test_http_methods_nginx_blocks_delete():
    script = _build_http_methods_nginx(TARGET, DATE, ["DELETE", "TRACE"])
    assert "DELETE" in script
    assert "405" in script


def test_http_methods_nginx_contains_method_check():
    script = _build_http_methods_nginx(TARGET, DATE, ["TRACE"])
    assert "$request_method" in script


# ---------------------------------------------------------------------------
# _build_clickjacking_nginx
# ---------------------------------------------------------------------------

def test_clickjacking_nginx_sets_x_frame_options():
    script = _build_clickjacking_nginx(TARGET, DATE)
    assert "X-Frame-Options" in script
    assert "DENY" in script


# ---------------------------------------------------------------------------
# _build_clickjacking_fastapi
# ---------------------------------------------------------------------------

def test_clickjacking_fastapi_is_valid_python():
    compile(_build_clickjacking_fastapi(TARGET, DATE), "<string>", "exec")


def test_clickjacking_fastapi_sets_header():
    script = _build_clickjacking_fastapi(TARGET, DATE)
    assert "X-Frame-Options" in script


# ---------------------------------------------------------------------------
# _build_directory_listing_nginx
# ---------------------------------------------------------------------------

def test_directory_listing_nginx_disables_autoindex():
    script = _build_directory_listing_nginx(TARGET, DATE, ["/backup/", "/.git/"])
    assert "autoindex off" in script


# ---------------------------------------------------------------------------
# _build_open_redirect_fastapi
# ---------------------------------------------------------------------------

def test_open_redirect_fastapi_is_valid_python():
    compile(_build_open_redirect_fastapi(TARGET, DATE), "<string>", "exec")


def test_open_redirect_fastapi_validates_url():
    script = _build_open_redirect_fastapi(TARGET, DATE)
    assert "netloc" in script or "urlparse" in script or "allowed" in script.lower()


# ---------------------------------------------------------------------------
# _build_robots_txt
# ---------------------------------------------------------------------------

def test_robots_txt_disallows_admin():
    script = _build_robots_txt(TARGET, DATE)
    assert "Disallow" in script
    assert "/admin" in script


# ---------------------------------------------------------------------------
# _build_email_security
# ---------------------------------------------------------------------------

def test_email_security_contains_spf():
    email_result = {"spf": False, "dkim": False, "dmarc": False, "domain": "example.com", "issues": []}
    script = _build_email_security(TARGET, DATE, email_result)
    assert "SPF" in script
    assert "TXT" in script


def test_email_security_contains_dmarc():
    email_result = {"spf": True, "dkim": True, "dmarc": False, "domain": "example.com", "issues": []}
    script = _build_email_security(TARGET, DATE, email_result)
    assert "DMARC" in script


# ---------------------------------------------------------------------------
# _build_waf_nginx
# ---------------------------------------------------------------------------

def test_waf_nginx_contains_rate_limit():
    script = _build_waf_nginx(TARGET, DATE)
    assert "limit_req" in script


def test_waf_nginx_blocks_attack_patterns():
    script = _build_waf_nginx(TARGET, DATE)
    assert "403" in script or "union" in script.lower() or "select" in script.lower()


# ---------------------------------------------------------------------------
# generate_remediation — conditional scripts
# ---------------------------------------------------------------------------

def test_generate_remediation_ssl_script_when_ssl_critical(tmp_path):
    ssl_result = {"status": "CRITICAL", "tls_ok": False, "error": None}
    paths = generate_remediation(TARGET, ssl_result=ssl_result, output_dir=str(tmp_path))
    assert "nginx_ssl" in paths
    assert os.path.exists(paths["nginx_ssl"])


def test_generate_remediation_cors_scripts_when_cors_issues(tmp_path):
    cors_result = {"status": "CRITICAL", "issues": ["Wildcard origin detected"], "error": None}
    paths = generate_remediation(TARGET, cors_result=cors_result, output_dir=str(tmp_path))
    assert "fastapi_cors" in paths
    assert "nginx_cors" in paths


def test_generate_remediation_cookie_script_when_cookie_issues(tmp_path):
    cookie_result = {"status": "WARNING", "issues": [{"name": "session", "missing_flags": ["HttpOnly"]}], "error": None}
    paths = generate_remediation(TARGET, cookie_result=cookie_result, output_dir=str(tmp_path))
    assert "fastapi_cookie" in paths


def test_generate_remediation_http_methods_when_dangerous(tmp_path):
    methods_result = {"status": "WARNING", "dangerous_methods": ["DELETE", "TRACE"], "error": None}
    paths = generate_remediation(TARGET, http_methods_result=methods_result, output_dir=str(tmp_path))
    assert "nginx_methods" in paths


def test_generate_remediation_clickjacking_scripts(tmp_path):
    clickjacking_result = {"status": "CRITICAL", "error": None}
    paths = generate_remediation(TARGET, clickjacking_result=clickjacking_result, output_dir=str(tmp_path))
    assert "nginx_clickjacking" in paths
    assert "fastapi_clickjacking" in paths


def test_generate_remediation_dirlist_script(tmp_path):
    dirlist_result = {"status": "CRITICAL", "exposed_paths": ["/backup/"], "error": None}
    paths = generate_remediation(TARGET, directory_listing_result=dirlist_result, output_dir=str(tmp_path))
    assert "nginx_dirlist" in paths


def test_generate_remediation_open_redirect_script(tmp_path):
    redirect_result = {"status": "CRITICAL", "error": None}
    paths = generate_remediation(TARGET, open_redirect_result=redirect_result, output_dir=str(tmp_path))
    assert "fastapi_open_redirect" in paths


def test_generate_remediation_email_script_when_missing_records(tmp_path):
    email_result = {"status": "WARNING", "spf": False, "dkim": False, "dmarc": False, "domain": "example.com", "issues": [], "error": None}
    paths = generate_remediation(TARGET, email_result=email_result, output_dir=str(tmp_path))
    assert "dns_email" in paths


def test_generate_remediation_no_ssl_script_when_ssl_ok(tmp_path):
    ssl_result = {"status": "OK", "tls_ok": True, "error": None}
    paths = generate_remediation(TARGET, ssl_result=ssl_result, output_dir=str(tmp_path))
    assert "nginx_ssl" not in paths
