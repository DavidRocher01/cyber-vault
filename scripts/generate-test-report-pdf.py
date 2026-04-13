"""
generate-test-report-pdf.py
===========================
Génère un rapport PDF complet des tests pour une livraison.

Lit les fichiers JUnit XML produits par pytest et vitest, puis génère
un PDF structuré avec le statut de chaque test.

Usage :
    python scripts/generate-test-report-pdf.py [version]

Exemples :
    python scripts/generate-test-report-pdf.py 0.6.0
    python scripts/generate-test-report-pdf.py          # version lue depuis version.ts

Prérequis :
    pip install reportlab          (déjà présent dans backend/requirements.txt)

Entrées (générées par pytest / vitest) :
    backend/test-results/results.xml
    frontend/test-results/results.xml

Sortie :
    docs/test-reports/v<version>-test-report.pdf
"""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

# ── Import shared brand from backend package ──────────────────────────────────
_repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_repo_root / "backend"))

from app.services.pdf_brand import (  # noqa: E402
    BORDER,
    CARD_BG,
    CYAN,
    DARK_BG,
    GRAY,
    GREEN,
    RED,
    WHITE,
    YELLOW,
    DOC_COLOR,
    PAGE_W,
    PAGE_H,
    draw_page,
    get_styles,
    section_rule,
)

# ── ReportLab ─────────────────────────────────────────────────────────────────
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

DOC_TYPE = "test"
MARGIN   = 15 * mm   # left/right margin (must match pdf_brand.MARGIN mm)
HEADER   = colors.HexColor("#0c1a2e")
LGRAY    = BORDER

# ── Styles ────────────────────────────────────────────────────────────────────

def _styles():
    st = get_styles(DOC_TYPE)
    doc_hex   = DOC_COLOR[DOC_TYPE]
    doc_color = colors.HexColor(doc_hex)
    extra = {
        "pass": ParagraphStyle("pass", fontName="Helvetica",      fontSize=9, textColor=GREEN),
        "fail": ParagraphStyle("fail", fontName="Helvetica-Bold", fontSize=9, textColor=RED),
        "skip": ParagraphStyle("skip", fontName="Helvetica",      fontSize=9, textColor=YELLOW),
    }
    st.update(extra)
    return st

# ── Parsing JUnit XML ─────────────────────────────────────────────────────────

def _parse_junit(xml_path: Path) -> dict:
    """Parse a JUnit XML file and return structured data."""
    if not xml_path.exists():
        return {"suites": [], "totals": {"tests": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0}}

    tree = ET.parse(xml_path)
    root = tree.getroot()

    suites = []
    totals = {"tests": 0, "passed": 0, "failed": 0, "skipped": 0, "errors": 0}

    # Handle both <testsuites> root and <testsuite> root
    suite_elements = root.findall(".//testsuite") if root.tag != "testsuite" else [root]

    for suite in suite_elements:
        suite_name = suite.get("name", "Unknown")
        cases = []

        for case in suite.findall("testcase"):
            name      = case.get("name", "?")
            classname = case.get("classname", "")
            time_val  = float(case.get("time", "0") or "0")

            failure = case.find("failure")
            error   = case.find("error")
            skipped = case.find("skipped")

            if failure is not None:
                status  = "FAIL"
                message = (failure.get("message") or failure.text or "")[:200]
                totals["failed"] += 1
            elif error is not None:
                status  = "ERROR"
                message = (error.get("message") or error.text or "")[:200]
                totals["errors"] += 1
            elif skipped is not None:
                status  = "SKIP"
                message = skipped.get("message", "")
                totals["skipped"] += 1
            else:
                status  = "PASS"
                message = ""
                totals["passed"] += 1

            totals["tests"] += 1
            cases.append({
                "name": name,
                "classname": classname,
                "time": time_val,
                "status": status,
                "message": message,
            })

        if cases:
            suites.append({"name": suite_name, "cases": cases})

    return {"suites": suites, "totals": totals}

# ── Helpers ───────────────────────────────────────────────────────────────────

def _status_cell(status: str, styles: dict):
    labels    = {"PASS": "&#10003; PASS", "FAIL": "&#10007; FAIL", "ERROR": "&#10007; ERROR", "SKIP": "&#8212; SKIP"}
    style_map = {"PASS": "pass", "FAIL": "fail", "ERROR": "fail", "SKIP": "skip"}
    return Paragraph(labels.get(status, status), styles[style_map.get(status, "body")])

def _hr(color=None):
    return HRFlowable(
        width="100%", thickness=0.5,
        color=color if color is not None else LGRAY,
        spaceAfter=6, spaceBefore=2,
    )

def _summary_table(backend: dict, frontend: dict, styles: dict):
    bt = backend["totals"]
    ft = frontend["totals"]
    total_tests  = bt["tests"]  + ft["tests"]
    total_passed = bt["passed"] + ft["passed"]
    total_failed = bt["failed"] + ft["failed"] + bt["errors"] + ft["errors"]
    total_skip   = bt["skipped"] + ft["skipped"]

    be_ok    = bt["failed"] + bt["errors"] == 0
    fe_ok    = ft["failed"] + ft["errors"] == 0
    global_ok = be_ok and fe_ok

    def cell(txt, bold=False, color=WHITE):
        style = ParagraphStyle("c", fontName="Helvetica-Bold" if bold else "Helvetica",
                               fontSize=9, textColor=color)
        return Paragraph(txt, style)

    header_style = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=9, textColor=CYAN)

    data = [
        [Paragraph("Composant", header_style), Paragraph("Tests", header_style),
         Paragraph("Réussis", header_style), Paragraph("Échoués", header_style),
         Paragraph("Ignorés", header_style), Paragraph("Statut", header_style)],
        [cell("Backend (pytest)"), cell(str(bt["tests"])),
         cell(str(bt["passed"]), color=GREEN),
         cell(str(bt["failed"] + bt["errors"]), color=RED if not be_ok else GRAY),
         cell(str(bt["skipped"]), color=YELLOW),
         cell("&#10003; OK" if be_ok else "&#10007; ÉCHEC", color=GREEN if be_ok else RED)],
        [cell("Frontend (Vitest)"), cell(str(ft["tests"])),
         cell(str(ft["passed"]), color=GREEN),
         cell(str(ft["failed"] + ft["errors"]), color=RED if not fe_ok else GRAY),
         cell(str(ft["skipped"]), color=YELLOW),
         cell("&#10003; OK" if fe_ok else "&#10007; ÉCHEC", color=GREEN if fe_ok else RED)],
        [cell("TOTAL", bold=True), cell(str(total_tests), bold=True),
         cell(str(total_passed), bold=True, color=GREEN),
         cell(str(total_failed), bold=True, color=RED if total_failed else GRAY),
         cell(str(total_skip), bold=True, color=YELLOW),
         cell("&#10003; SUCCÈS" if global_ok else "&#10007; ÉCHEC", bold=True, color=GREEN if global_ok else RED)],
    ]

    col_w = [(PAGE_W - 2 * MARGIN) * p for p in [0.28, 0.12, 0.14, 0.14, 0.14, 0.18]]
    t = Table(data, colWidths=col_w)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  HEADER),
        ("ROWBACKGROUNDS", (0, 1), (-1, 2),  [CARD_BG, DARK_BG]),
        ("BACKGROUND",     (0, 3), (-1, 3),  LGRAY),
        ("GRID",           (0, 0), (-1, -1), 0.3, LGRAY),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 6),
    ]))
    return t

def _test_table(cases: list, styles: dict):
    header_style = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=8, textColor=CYAN)
    name_style   = ParagraphStyle("n", fontName="Helvetica",      fontSize=8, textColor=WHITE)
    msg_style    = ParagraphStyle("m", fontName="Helvetica-Oblique", fontSize=7, textColor=RED)
    time_style   = ParagraphStyle("t", fontName="Helvetica",      fontSize=8, textColor=GRAY)

    data = [[Paragraph("Statut", header_style), Paragraph("Nom du test", header_style),
             Paragraph("Durée", header_style)]]

    usable_w = PAGE_W - 2 * MARGIN
    for c in cases:
        msg_cell  = Paragraph(c["message"].replace("\n", " ") if c["message"] else "", msg_style)
        name_cell = (
            Paragraph(c["name"], name_style) if not c["message"] else
            Table([[Paragraph(c["name"], name_style)], [msg_cell]],
                  colWidths=[usable_w * 0.74])
        )
        data.append([_status_cell(c["status"], styles), name_cell,
                     Paragraph(f"{c['time']:.3f}s", time_style)])

    col_w = [usable_w * p for p in [0.12, 0.74, 0.14]]
    t = Table(data, colWidths=col_w, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  HEADER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CARD_BG, DARK_BG]),
        ("GRID",           (0, 0), (-1, -1), 0.3, LGRAY),
        ("TOPPADDING",     (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
        ("LEFTPADDING",    (0, 0), (-1, -1), 5),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
    ]))
    return t

# ── Main ──────────────────────────────────────────────────────────────────────

def generate(version: str, repo_root: Path):
    backend_xml  = repo_root / "backend"  / "test-results" / "results.xml"
    frontend_xml = repo_root / "frontend" / "test-results" / "results.xml"
    out_dir      = repo_root / "docs" / "test-reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path     = out_dir / f"v{version}-test-report.pdf"

    backend  = _parse_junit(backend_xml)
    frontend = _parse_junit(frontend_xml)
    styles   = _styles()

    date_str = datetime.now().strftime("%d/%m/%Y à %Hh%M")
    bt = backend["totals"]
    ft = frontend["totals"]
    total_tests  = bt["tests"]  + ft["tests"]
    total_passed = bt["passed"] + ft["passed"]
    total_failed = bt["failed"] + ft["failed"] + bt["errors"] + ft["errors"]
    global_ok    = total_failed == 0

    doc = SimpleDocTemplate(
        str(out_path), pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=25 * mm, bottomMargin=20 * mm,
    )

    story = []

    # ── Page de garde ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("CyberScan", styles["title"]))
    story.append(Paragraph(f"Rapport de tests — v{version}", styles["section"]))
    story.append(Paragraph(f"Généré le {date_str}", styles["subtitle"]))
    story.append(section_rule(PAGE_W - 2 * MARGIN, DOC_TYPE))
    story.append(Spacer(1, 6 * mm))

    # Badge résultat global
    badge_text  = "&#10003;  TOUS LES TESTS PASSENT" if global_ok else "&#10007;  DES TESTS ÉCHOUENT"
    badge_color = GREEN if global_ok else RED
    badge_style = ParagraphStyle("badge", fontName="Helvetica-Bold",
                                 fontSize=16, textColor=badge_color, spaceAfter=10)
    story.append(Paragraph(badge_text, badge_style))
    story.append(Spacer(1, 4 * mm))

    # Résumé chiffré
    doc_hex     = DOC_COLOR[DOC_TYPE]
    summary_style = ParagraphStyle("sum", fontName="Helvetica", fontSize=10, textColor=GRAY)
    story.append(Paragraph(
        f"<b><font color='{doc_hex}'>{total_tests}</font></b> tests exécutés  ·  "
        f"<b><font color='#4ade80'>{total_passed}</font></b> réussis  ·  "
        f"<b><font color='#f87171'>{total_failed}</font></b> échoués",
        summary_style,
    ))
    story.append(Spacer(1, 8 * mm))
    story.append(_summary_table(backend, frontend, styles))
    story.append(Spacer(1, 8 * mm))

    # Infos
    info_data = [
        ["Version",      f"v{version}"],
        ["Date",         date_str],
        ["Backend XML",  str(backend_xml)  if backend_xml.exists()  else "non trouvé"],
        ["Frontend XML", str(frontend_xml) if frontend_xml.exists() else "non trouvé"],
    ]
    info_style = ParagraphStyle("i",  fontName="Helvetica",      fontSize=8, textColor=GRAY)
    info_bold  = ParagraphStyle("ib", fontName="Helvetica-Bold", fontSize=8, textColor=WHITE)
    info_rows  = [[Paragraph(k, info_bold), Paragraph(v, info_style)] for k, v in info_data]
    usable_w   = PAGE_W - 2 * MARGIN
    info_table = Table(info_rows, colWidths=[usable_w * 0.25, usable_w * 0.75])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
        ("GRID",       (0, 0), (-1, -1), 0.3, LGRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]))
    story.append(info_table)

    # ── Détail Backend ─────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Détail — Backend (pytest)", styles["section"]))
    story.append(_hr())

    if not backend["suites"]:
        story.append(Paragraph("Aucun résultat trouvé (lancer pytest depuis backend/)", styles["body"]))
    else:
        for suite in backend["suites"]:
            story.append(Paragraph(suite["name"], styles["subsection"]))
            story.append(_test_table(suite["cases"], styles))
            story.append(Spacer(1, 4 * mm))

    # ── Détail Frontend ────────────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Détail — Frontend (Vitest)", styles["section"]))
    story.append(_hr())

    if not frontend["suites"]:
        story.append(Paragraph("Aucun résultat trouvé (lancer npm test depuis frontend/)", styles["body"]))
    else:
        for suite in frontend["suites"]:
            story.append(Paragraph(suite["name"], styles["subsection"]))
            story.append(_test_table(suite["cases"], styles))
            story.append(Spacer(1, 4 * mm))

    doc.build(
        story,
        onFirstPage=lambda c, d: draw_page(c, d, DOC_TYPE, "Rapport de Tests"),
        onLaterPages=lambda c, d: draw_page(c, d, DOC_TYPE, "Rapport de Tests"),
    )
    return out_path


if __name__ == "__main__":
    repo_root = Path(__file__).resolve().parent.parent

    # Version : argument CLI ou lue depuis version.ts
    if len(sys.argv) > 1:
        version = sys.argv[1]
    else:
        version_file = repo_root / "frontend" / "src" / "app" / "core" / "version.ts"
        m = re.search(r"APP_VERSION = '([^']+)'", version_file.read_text())
        version = m.group(1) if m else "0.0.0"

    out = generate(version, repo_root)
    print(f"[OK] PDF genere : {out}")
