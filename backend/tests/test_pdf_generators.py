"""
Unit tests — PDF generators and pdf_brand helpers.
All tests are pure Python (no DB, no HTTP).
"""

import io
from datetime import datetime

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas

from app.services.pdf_brand import (
    CYAN, GRAY, GREEN, RED, YELLOW, WHITE,
    DOC_COLOR, SITE_EMAIL,
    cat_score, score_color,
    draw_compliance_cover, draw_page, draw_url_scan_cover,
    get_styles, section_rule,
)
from app.services.iso27001_pdf import generate_iso27001_pdf
from app.services.nis2_pdf import generate_nis2_pdf
from app.services.url_scan_pdf import generate_url_scan_pdf


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _minimal_canvas():
    """Return a (canvas, doc_stub) pair writing to an in-memory buffer."""
    buf = io.BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=A4)

    class _Doc:
        page = 1
        pagesize = A4

    return c, _Doc()


def _iso_categories():
    return [
        {
            "id": "cat_a",
            "label": "Contexte & Gouvernance",
            "items": [
                {"id": "a1", "label": "Politique SMSI", "desc": "Politique documentée"},
                {"id": "a2", "label": "Objectifs sécurité", "desc": "Objectifs définis"},
                {"id": "a3", "label": "Périmètre", "desc": "Périmètre délimité"},
            ],
        },
        {
            "id": "cat_b",
            "label": "Gestion des risques",
            "items": [
                {"id": "b1", "label": "Analyse des risques", "desc": "Méthode formelle"},
                {"id": "b2", "label": "Traitement des risques", "desc": "Plan de traitement"},
            ],
        },
    ]


def _nis2_categories():
    return [
        {
            "id": "gov",
            "label": "Gouvernance",
            "items": [
                {"id": "g1", "label": "Politique NIS2", "desc": "Politique appliquée"},
                {"id": "g2", "label": "Responsabilités", "desc": "Rôles définis"},
                {"id": "g3", "label": "Supervision dirigeants", "desc": "Organe dirigeant impliqué"},
                {"id": "g4", "label": "Formation sécurité", "desc": "Formations réalisées"},
            ],
        },
        {
            "id": "risk",
            "label": "Gestion des risques",
            "items": [
                {"id": "r1", "label": "Analyse risques", "desc": "Processus formalisé"},
                {"id": "r2", "label": "Traitement risques", "desc": "Plans de traitement"},
            ],
        },
    ]


# ─── pdf_brand helpers ────────────────────────────────────────────────────────

def test_score_color_green():
    assert score_color(80) == GREEN
    assert score_color(100) == GREEN


def test_score_color_yellow():
    assert score_color(50) == YELLOW
    assert score_color(79) == YELLOW


def test_score_color_red():
    assert score_color(0) == RED
    assert score_color(49) == RED


def test_cat_score_all_compliant():
    items_state = {"a1": "compliant", "a2": "compliant", "a3": "compliant"}
    cat_items = [{"id": "a1"}, {"id": "a2"}, {"id": "a3"}]
    assert cat_score(cat_items, items_state) == 100


def test_cat_score_all_non_compliant():
    items_state = {"a1": "non_compliant", "a2": "non_compliant"}
    cat_items = [{"id": "a1"}, {"id": "a2"}]
    assert cat_score(cat_items, items_state) == 0


def test_cat_score_all_na_returns_zero():
    items_state = {"a1": "na", "a2": "na"}
    cat_items = [{"id": "a1"}, {"id": "a2"}]
    assert cat_score(cat_items, items_state) == 0


def test_cat_score_mixed():
    items_state = {"a1": "compliant", "a2": "partial", "a3": "non_compliant"}
    cat_items = [{"id": "a1"}, {"id": "a2"}, {"id": "a3"}]
    pct = cat_score(cat_items, items_state)
    # compliant=2pts, partial=1pt, nc=0pts / (3*2) = 3/6 = 50%
    assert pct == 50


def test_cat_score_with_na_excluded():
    # na items excluded from denominator
    items_state = {"a1": "compliant", "a2": "na"}
    cat_items = [{"id": "a1"}, {"id": "a2"}]
    assert cat_score(cat_items, items_state) == 100


def test_cat_score_empty_items():
    assert cat_score([], {}) == 0


def test_doc_color_contains_expected_types():
    assert "nis2" in DOC_COLOR
    assert "iso27001" in DOC_COLOR
    assert "url" in DOC_COLOR


def test_site_email_format():
    assert "@" in SITE_EMAIL
    assert "cyberscanapp" in SITE_EMAIL


def test_section_rule_returns_hrflowable():
    from reportlab.platypus import HRFlowable
    rule = section_rule(400, "nis2")
    assert isinstance(rule, HRFlowable)


def test_get_styles_returns_expected_keys():
    styles = get_styles("nis2")
    for key in ("title", "subtitle", "section", "body", "small", "mono"):
        assert key in styles


def test_get_styles_fallback_doc_type():
    styles = get_styles("unknown_type")
    assert "section" in styles


# ─── draw_page (canvas smoke test) ────────────────────────────────────────────

@pytest.mark.parametrize("doc_type", ["nis2", "iso27001", "url", "scan"])
def test_draw_page_does_not_raise(doc_type):
    c, doc = _minimal_canvas()
    draw_page(c, doc, doc_type, "Test Title", "Subtitle")
    c.save()


# ─── draw_compliance_cover ────────────────────────────────────────────────────

def test_draw_compliance_cover_score_zero():
    c, doc = _minimal_canvas()
    draw_compliance_cover(
        c, doc,
        doc_type="nis2",
        title_line1="Rapport de conformite",
        title_line2="Directive NIS2",
        score=0, score_label="Non conforme",
        total=10, compliant=0, partial=0, nc=10, na=0,
        date_str="15/04/2026 à 10:00",
        domain_scores=[("Gouvernance", 0), ("Risques", 0)],
    )
    c.save()


def test_draw_compliance_cover_score_full():
    c, doc = _minimal_canvas()
    draw_compliance_cover(
        c, doc,
        doc_type="iso27001",
        title_line1="Rapport de conformite",
        title_line2="ISO/IEC 27001:2022",
        score=100, score_label="Conforme",
        total=38, compliant=38, partial=0, nc=0, na=0,
        date_str="15/04/2026 à 10:00",
        domain_scores=[("Dom A", 100), ("Dom B", 80), ("Dom C", 55), ("Dom D", 30)],
    )
    c.save()


def test_draw_compliance_cover_many_domains():
    c, doc = _minimal_canvas()
    domain_scores = [(f"Domaine {i}", i * 10) for i in range(10)]
    draw_compliance_cover(
        c, doc,
        doc_type="nis2",
        title_line1="Rapport",
        title_line2="NIS2",
        score=45, score_label="En cours",
        total=34, compliant=5, partial=8, nc=21, na=0,
        date_str="15/04/2026",
        domain_scores=domain_scores,
    )
    c.save()


def test_draw_compliance_cover_empty_domains():
    c, doc = _minimal_canvas()
    draw_compliance_cover(
        c, doc,
        doc_type="iso27001",
        title_line1="Rapport",
        title_line2="ISO",
        score=50, score_label="En cours",
        total=5, compliant=2, partial=1, nc=2, na=0,
        date_str="15/04/2026",
        domain_scores=[],
    )
    c.save()


def test_draw_compliance_cover_with_na():
    c, doc = _minimal_canvas()
    draw_compliance_cover(
        c, doc,
        doc_type="nis2",
        title_line1="Rapport",
        title_line2="NIS2",
        score=60, score_label="En cours",
        total=20, compliant=8, partial=4, nc=4, na=4,
        date_str="15/04/2026",
        domain_scores=[("Cat A", 80), ("Cat B", 40)],
    )
    c.save()


# ─── draw_url_scan_cover ──────────────────────────────────────────────────────

def test_draw_url_scan_cover_safe():
    c, doc = _minimal_canvas()
    draw_url_scan_cover(
        c, doc,
        url="https://example.com/path?q=1",
        verdict_label="SÛR",
        verdict_color_hex="#4ade80",
        threat_score=5,
        findings_count=0,
        redirect_count=1,
        ssl_valid=True,
        date_str="15/04/2026",
    )
    c.save()


def test_draw_url_scan_cover_malicious():
    c, doc = _minimal_canvas()
    draw_url_scan_cover(
        c, doc,
        url="http://malicious-site.ru/payload",
        verdict_label="MALVEILLANT",
        verdict_color_hex="#f87171",
        threat_score=95,
        findings_count=7,
        redirect_count=3,
        ssl_valid=False,
        date_str="15/04/2026",
    )
    c.save()


def test_draw_url_scan_cover_long_url():
    c, doc = _minimal_canvas()
    long_url = "https://example.com/" + "a" * 120
    draw_url_scan_cover(
        c, doc,
        url=long_url,
        verdict_label="SUSPECT",
        verdict_color_hex="#facc15",
        threat_score=50,
        findings_count=2,
        redirect_count=0,
        ssl_valid=True,
        date_str="15/04/2026",
    )
    c.save()


# ─── generate_nis2_pdf ────────────────────────────────────────────────────────

def test_generate_nis2_pdf_returns_pdf_bytes():
    cats = _nis2_categories()
    items = {it["id"]: "non_compliant" for cat in cats for it in cat["items"]}
    result = generate_nis2_pdf(cats, items, 0, datetime.now(), "test@test.com")
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_generate_nis2_pdf_all_compliant():
    cats = _nis2_categories()
    items = {it["id"]: "compliant" for cat in cats for it in cat["items"]}
    result = generate_nis2_pdf(cats, items, 100, datetime.now(), "test@test.com")
    assert result[:4] == b"%PDF"


def test_generate_nis2_pdf_mixed_statuses():
    cats = _nis2_categories()
    statuses = ["compliant", "partial", "non_compliant", "na",
                "compliant", "non_compliant"]
    all_ids = [it["id"] for cat in cats for it in cat["items"]]
    items = {i: s for i, s in zip(all_ids, statuses)}
    result = generate_nis2_pdf(cats, items, 50, datetime.now(), "user@example.com")
    assert result[:4] == b"%PDF"


def test_generate_nis2_pdf_no_updated_at():
    cats = _nis2_categories()
    items = {}
    result = generate_nis2_pdf(cats, items, 0, None, "x@x.com")
    assert result[:4] == b"%PDF"


def test_generate_nis2_pdf_many_categories():
    cats = [
        {"id": f"cat{i}", "label": f"Catégorie {i}",
         "items": [{"id": f"c{i}_{j}", "label": f"Item {j}", "desc": "Desc"} for j in range(4)]}
        for i in range(8)
    ]
    items = {it["id"]: "partial" for cat in cats for it in cat["items"]}
    result = generate_nis2_pdf(cats, items, 40, datetime.now(), "x@x.com")
    assert result[:4] == b"%PDF"


# ─── generate_iso27001_pdf ────────────────────────────────────────────────────

def test_generate_iso27001_pdf_returns_pdf_bytes():
    cats = _iso_categories()
    items = {it["id"]: "non_compliant" for cat in cats for it in cat["items"]}
    result = generate_iso27001_pdf(cats, items, 0, datetime.now(), "test@test.com")
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_generate_iso27001_pdf_all_compliant():
    cats = _iso_categories()
    items = {it["id"]: "compliant" for cat in cats for it in cat["items"]}
    result = generate_iso27001_pdf(cats, items, 100, datetime.now(), "test@test.com")
    assert result[:4] == b"%PDF"


def test_generate_iso27001_pdf_mixed():
    cats = _iso_categories()
    all_ids = [it["id"] for cat in cats for it in cat["items"]]
    statuses = ["compliant", "partial", "non_compliant", "na", "compliant"]
    items = {i: statuses[idx % len(statuses)] for idx, i in enumerate(all_ids)}
    result = generate_iso27001_pdf(cats, items, 55, datetime.now(), "u@u.com")
    assert result[:4] == b"%PDF"


def test_generate_iso27001_pdf_no_updated_at():
    cats = _iso_categories()
    items = {}
    result = generate_iso27001_pdf(cats, items, 0, None, "x@x.com")
    assert result[:4] == b"%PDF"


def test_generate_iso27001_pdf_ten_domains():
    cats = [
        {"id": f"d{i}", "label": f"Domaine {'A' * min(i+1, 26)}", "items": [
            {"id": f"d{i}_1", "label": "Control 1", "desc": "Desc"},
            {"id": f"d{i}_2", "label": "Control 2", "desc": "Desc"},
        ]}
        for i in range(10)
    ]
    items = {it["id"]: "compliant" if i % 3 == 0 else "non_compliant"
             for i, (cat, it) in enumerate((cat, it) for cat in cats for it in cat["items"])}
    result = generate_iso27001_pdf(cats, items, 33, datetime.now(), "x@x.com")
    assert result[:4] == b"%PDF"


# ─── generate_url_scan_pdf ────────────────────────────────────────────────────

def _url_scan_data(**overrides):
    base = {
        "url": "https://example.com",
        "verdict": "safe",
        "threat_type": "",
        "threat_score": 5,
        "ssl_valid": True,
        "original_domain": "example.com",
        "final_domain": "example.com",
        "redirect_count": 0,
        "redirect_chain": [],
        "findings": [],
        "created_at": "2026-04-15T10:00:00Z",
    }
    base.update(overrides)
    return base


def test_generate_url_scan_pdf_safe():
    result = generate_url_scan_pdf(_url_scan_data())
    assert isinstance(result, bytes)
    assert result[:4] == b"%PDF"


def test_generate_url_scan_pdf_malicious():
    data = _url_scan_data(
        verdict="malicious",
        threat_type="phishing",
        threat_score=95,
        ssl_valid=False,
        final_domain="evil.ru",
        redirect_count=3,
        redirect_chain=["https://example.com", "https://redir.io", "http://evil.ru"],
        findings=[
            {"severity": "critical", "detail": "Phishing page detected"},
            {"severity": "high", "detail": "Malicious domain"},
        ],
    )
    result = generate_url_scan_pdf(data)
    assert result[:4] == b"%PDF"


def test_generate_url_scan_pdf_suspicious():
    data = _url_scan_data(
        verdict="suspicious",
        threat_type="tracker",
        threat_score=45,
        findings=[{"severity": "medium", "detail": "Tracker detected"}],
    )
    result = generate_url_scan_pdf(data)
    assert result[:4] == b"%PDF"


def test_generate_url_scan_pdf_unknown_verdict():
    data = _url_scan_data(verdict="unknown", threat_score=0)
    result = generate_url_scan_pdf(data)
    assert result[:4] == b"%PDF"


def test_generate_url_scan_pdf_datetime_object():
    data = _url_scan_data(created_at=datetime(2026, 4, 15, 10, 0, 0))
    result = generate_url_scan_pdf(data)
    assert result[:4] == b"%PDF"


def test_generate_url_scan_pdf_no_created_at():
    data = _url_scan_data(created_at=None)
    result = generate_url_scan_pdf(data)
    assert result[:4] == b"%PDF"


def test_generate_url_scan_pdf_many_findings():
    findings = [{"severity": s, "detail": f"Finding {i}"}
                for i, s in enumerate(["critical", "high", "medium", "low"] * 5)]
    data = _url_scan_data(verdict="malicious", findings=findings, threat_score=90)
    result = generate_url_scan_pdf(data)
    assert result[:4] == b"%PDF"


def test_generate_url_scan_pdf_domain_redirect():
    data = _url_scan_data(
        original_domain="legit.com",
        final_domain="phish.ru",
        redirect_chain=["https://legit.com/click", "https://phish.ru/steal"],
    )
    result = generate_url_scan_pdf(data)
    assert result[:4] == b"%PDF"
