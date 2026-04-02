"""
Tests for scanner/report_generator.py
PDF generation uses tmp_path — no writes to the real project tree.
Internal builders are tested by inspecting the returned flowable lists.
"""

import os

import pytest
from reportlab.lib import colors
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table

from scanner.report_generator import (
    COLOR_CRITICAL,
    COLOR_OK,
    COLOR_WARNING,
    _build_cover,
    _build_executive_summary,
    _build_headers_section,
    _build_ports_section,
    _build_recommendations,
    _build_sca_section,
    _build_ssl_section,
    _build_styles,
    _build_toc,
    _status_color,
    generate_report,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

PAGE_W = 21 * 2.835  # A4 width in points ≈ 595
DATE = "01/01/2026 à 00:00"
TARGET = "https://example.com"

SSL_OK = {
    "valid": True,
    "expiry_date": "01/01/2027",
    "days_remaining": 365,
    "protocol": "TLSv1.3",
    "tls_ok": True,
    "status": "OK",
    "error": None,
}
SSL_ERROR = {"status": "CRITICAL", "error": "Connection refused", "valid": False,
             "expiry_date": None, "days_remaining": None, "protocol": None, "tls_ok": False}

HEADERS_OK = {
    "status": "OK", "status_code": 200, "score": 6,
    "headers_found": ["Content-Security-Policy", "X-Frame-Options",
                      "X-Content-Type-Options", "Strict-Transport-Security",
                      "Referrer-Policy", "Permissions-Policy"],
    "headers_missing": [], "error": None,
}
HEADERS_MISSING = {
    "status": "WARNING", "status_code": 200, "score": 4,
    "headers_found": ["X-Frame-Options", "X-Content-Type-Options",
                      "Strict-Transport-Security", "Referrer-Policy"],
    "headers_missing": ["Content-Security-Policy", "Permissions-Policy"],
    "error": None,
}

PORTS_OK = {"open_ports": [], "critical_ports": [], "status": "OK", "error": None}
PORTS_CRIT = {"open_ports": [22, 3306, 5432], "critical_ports": [3306, 5432], "status": "CRITICAL", "error": None}

SCA_OK = {"vulns": [], "total_packages": 5, "total_vulns": 0, "status": "OK", "error": None}
SCA_VULN = {
    "vulns": [{"package": "requests", "version": "2.25.0", "ecosystem": "PyPI",
               "cve_ids": ["CVE-2022-0001"], "severity": "HIGH",
               "summary": "Remote code execution"}],
    "total_packages": 3, "total_vulns": 1, "status": "CRITICAL", "error": None,
}


@pytest.fixture
def styles():
    return _build_styles()


# ---------------------------------------------------------------------------
# _build_styles
# ---------------------------------------------------------------------------

def test_build_styles_returns_all_required_keys(styles):
    for key in ("section_title", "body", "bullet", "toc_entry", "cell", "label"):
        assert key in styles


def test_build_styles_values_are_paragraph_styles(styles):
    from reportlab.lib.styles import ParagraphStyle
    for value in styles.values():
        assert isinstance(value, ParagraphStyle)


# ---------------------------------------------------------------------------
# _status_color
# ---------------------------------------------------------------------------

def test_status_color_ok_returns_green():
    assert _status_color("OK") == COLOR_OK


def test_status_color_critical_returns_red():
    assert _status_color("CRITICAL") == COLOR_CRITICAL


def test_status_color_warning_returns_orange():
    assert _status_color("WARNING") == COLOR_WARNING


def test_status_color_unknown_returns_grey():
    c = _status_color("UNKNOWN")
    assert c is not None  # falls back to a colour, not an error


# ---------------------------------------------------------------------------
# _build_cover
# ---------------------------------------------------------------------------

def test_build_cover_returns_non_empty_list(styles):
    story = _build_cover(TARGET, DATE, styles, PAGE_W, 842)
    assert len(story) > 0


def test_build_cover_ends_with_page_break(styles):
    story = _build_cover(TARGET, DATE, styles, PAGE_W, 842)
    assert isinstance(story[-1], PageBreak)


# ---------------------------------------------------------------------------
# _build_toc
# ---------------------------------------------------------------------------

def test_build_toc_contains_six_sections(styles):
    story = _build_toc(styles)
    text = " ".join(
        e.text if hasattr(e, "text") else ""
        for e in story
        if isinstance(e, Paragraph)
    )
    for section in ("SSL", "Headers", "Ports", "SCA", "Recommandations"):
        assert section in text


def test_build_toc_ends_with_page_break(styles):
    story = _build_toc(styles)
    assert isinstance(story[-1], PageBreak)


# ---------------------------------------------------------------------------
# _build_executive_summary
# ---------------------------------------------------------------------------

def test_executive_summary_contains_table(styles):
    statuses = {"ssl": "OK", "headers": "WARNING", "ports": "OK"}
    story = _build_executive_summary("WARNING", statuses, styles, PAGE_W)
    assert any(isinstance(e, Table) for e in story)


def test_executive_summary_reflects_all_modules(styles):
    statuses = {"ssl": "OK", "headers": "CRITICAL", "ports": "OK", "sca": "WARNING"}
    story = _build_executive_summary("CRITICAL", statuses, styles, PAGE_W)
    assert len(story) > 0


# ---------------------------------------------------------------------------
# _build_ssl_section
# ---------------------------------------------------------------------------

def test_ssl_section_ok_result_contains_table(styles):
    story = _build_ssl_section(SSL_OK, styles, PAGE_W)
    assert any(isinstance(e, Table) for e in story)


def test_ssl_section_error_result_contains_table(styles):
    story = _build_ssl_section(SSL_ERROR, styles, PAGE_W)
    assert any(isinstance(e, Table) for e in story)


def test_ssl_section_empty_result_does_not_raise(styles):
    story = _build_ssl_section({}, styles, PAGE_W)
    assert isinstance(story, list)


# ---------------------------------------------------------------------------
# _build_headers_section
# ---------------------------------------------------------------------------

def test_headers_section_ok_shows_found_headers(styles):
    story = _build_headers_section(HEADERS_OK, styles, PAGE_W)
    assert any(isinstance(e, Table) for e in story)


def test_headers_section_missing_headers_shows_table(styles):
    story = _build_headers_section(HEADERS_MISSING, styles, PAGE_W)
    assert any(isinstance(e, Table) for e in story)


def test_headers_section_error_result_does_not_raise(styles):
    err = {"error": "timeout", "status": "CRITICAL"}
    story = _build_headers_section(err, styles, PAGE_W)
    assert isinstance(story, list)


# ---------------------------------------------------------------------------
# _build_ports_section
# ---------------------------------------------------------------------------

def test_ports_section_skipped_shows_table(styles):
    story = _build_ports_section({}, styles, PAGE_W, skipped=True)
    assert any(isinstance(e, Table) for e in story)


def test_ports_section_open_ports_shows_table(styles):
    story = _build_ports_section(PORTS_CRIT, styles, PAGE_W, skipped=False)
    assert any(isinstance(e, Table) for e in story)


def test_ports_section_no_open_ports_shows_table(styles):
    story = _build_ports_section(PORTS_OK, styles, PAGE_W, skipped=False)
    assert any(isinstance(e, Table) for e in story)


# ---------------------------------------------------------------------------
# _build_sca_section
# ---------------------------------------------------------------------------

def test_sca_section_skipped_shows_table(styles):
    story = _build_sca_section({}, styles, PAGE_W, skipped=True)
    assert any(isinstance(e, Table) for e in story)


def test_sca_section_with_vulns_shows_two_tables(styles):
    story = _build_sca_section(SCA_VULN, styles, PAGE_W, skipped=False)
    tables = [e for e in story if isinstance(e, Table)]
    assert len(tables) >= 2  # summary table + vuln table


def test_sca_section_ok_no_vulns_shows_summary_only(styles):
    story = _build_sca_section(SCA_OK, styles, PAGE_W, skipped=False)
    assert any(isinstance(e, Table) for e in story)


# ---------------------------------------------------------------------------
# _build_recommendations
# ---------------------------------------------------------------------------

def test_recommendations_empty_when_all_ok(styles):
    story = _build_recommendations(SSL_OK, HEADERS_OK, PORTS_OK, styles, PAGE_W)
    # Should contain a "no issues" paragraph
    assert any(isinstance(e, Paragraph) for e in story)


def test_recommendations_generates_items_for_missing_headers(styles):
    story = _build_recommendations(SSL_OK, HEADERS_MISSING, PORTS_OK, styles, PAGE_W)
    tables = [e for e in story if isinstance(e, Table)]
    assert len(tables) >= 2  # one per missing header rec


def test_recommendations_generates_item_for_critical_ports(styles):
    story = _build_recommendations(SSL_OK, HEADERS_OK, PORTS_CRIT, styles, PAGE_W)
    tables = [e for e in story if isinstance(e, Table)]
    assert len(tables) >= 1


def test_recommendations_includes_sca_vuln(styles):
    story = _build_recommendations(
        SSL_OK, HEADERS_OK, PORTS_OK, styles, PAGE_W,
        sca_result=SCA_VULN, sca_skipped=False,
    )
    tables = [e for e in story if isinstance(e, Table)]
    assert len(tables) >= 1


# ---------------------------------------------------------------------------
# generate_report (integration)
# ---------------------------------------------------------------------------

def test_generate_report_creates_pdf_file(tmp_path):
    out = str(tmp_path / "report.pdf")
    path = generate_report(
        target_url=TARGET,
        ssl_result=SSL_OK,
        headers_result=HEADERS_OK,
        port_result=PORTS_OK,
        output_path=out,
    )
    assert os.path.exists(path)
    assert path.endswith(".pdf")


def test_generate_report_pdf_is_non_empty(tmp_path):
    out = str(tmp_path / "report.pdf")
    generate_report(
        target_url=TARGET,
        ssl_result=SSL_OK,
        headers_result=HEADERS_OK,
        port_result=PORTS_OK,
        output_path=out,
    )
    assert os.path.getsize(out) > 1024  # at least 1 KB


def test_generate_report_with_all_modules(tmp_path):
    out = str(tmp_path / "full.pdf")
    path = generate_report(
        target_url=TARGET,
        ssl_result=SSL_ERROR,
        headers_result=HEADERS_MISSING,
        port_result=PORTS_CRIT,
        output_path=out,
        ports_skipped=False,
        sca_result=SCA_VULN,
        sca_skipped=False,
    )
    assert os.path.exists(path)


def test_generate_report_with_ports_skipped(tmp_path):
    out = str(tmp_path / "noportscan.pdf")
    path = generate_report(
        target_url=TARGET,
        ssl_result=SSL_OK,
        headers_result=HEADERS_OK,
        port_result={},
        output_path=out,
        ports_skipped=True,
    )
    assert os.path.exists(path)


def test_generate_report_creates_output_directory(tmp_path):
    out = str(tmp_path / "nested" / "dir" / "report.pdf")
    generate_report(
        target_url=TARGET,
        ssl_result=SSL_OK,
        headers_result=HEADERS_OK,
        port_result=PORTS_OK,
        output_path=out,
    )
    assert os.path.exists(out)
