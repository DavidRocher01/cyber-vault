"""
Generate a PDF test report from pytest verbose output.
Usage: python scripts/generate_test_report_pdf.py [output.pdf]
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Palette ────────────────────────────────────────────────────────────────────
NAVY = colors.HexColor("#0f172a")
CYAN = colors.HexColor("#06b6d4")
GREEN = colors.HexColor("#22c55e")
RED = colors.HexColor("#ef4444")
YELLOW = colors.HexColor("#f59e0b")
GRAY = colors.HexColor("#64748b")
LGRAY = colors.HexColor("#f1f5f9")
BORDER = colors.HexColor("#cbd5e1")
WHITE = colors.white
BLACK = colors.HexColor("#1e293b")

MODULE_LABELS = {
    "test_2fa": "Authentification 2FA",
    "test_admin_scans": "Admin — Scans",
    "test_admin_stats": "Admin — Statistiques",
    "test_admin_users": "Admin — Utilisateurs",
    "test_auth": "Authentification (base)",
    "test_auth_advanced": "Authentification (avancé)",
    "test_blog": "Blog",
    "test_bookings": "Réservations",
    "test_code_scan_service": "Service — Analyse de code",
    "test_code_scans": "Scans de code (API)",
    "test_contact": "Formulaire de contact",
    "test_input_validation": "Validation des entrées",
    "test_invoices": "Facturation",
    "test_iso27001_unit": "ISO 27001 (unitaire)",
    "test_limiter": "Rate limiter",
    "test_newsletter": "Newsletter",
    "test_nis2": "NIS2",
    "test_nis2_direct": "NIS2 (direct)",
    "test_nis2_integration": "NIS2 (intégration)",
    "test_nis2_unit": "NIS2 (unitaire)",
    "test_notif_prefs_unit": "Préférences notifications (unitaire)",
    "test_notifications": "Notifications",
    "test_notifications_unit": "Notifications (unitaire)",
    "test_password_reset": "Réinitialisation mot de passe",
    "test_pdf_generators": "Générateurs PDF",
    "test_plans": "Plans & abonnements",
    "test_plans_unit": "Plans (unitaire)",
    "test_port_scanner": "Scanner de ports",
    "test_public_scan_unit": "Scan public (unitaire)",
    "test_rate_limiting": "Rate limiting",
    "test_regression": "Tests de régression",
    "test_remediation": "Remédiation",
    "test_scan_service": "Service de scan",
    "test_scans": "Scans (API)",
    "test_scans_unit": "Scans (unitaire)",
    "test_security": "Sécurité",
    "test_sites": "Sites surveillés",
    "test_sites_unit": "Sites (unitaire)",
    "test_ssl_alerts_unit": "Alertes SSL (unitaire)",
    "test_ssl_email_unit": "Emails SSL (unitaire)",
    "test_ssrf_unit": "SSRF (unitaire)",
    "test_stripe_service_unit": "Service Stripe (unitaire)",
    "test_subscriptions": "Abonnements",
    "test_url_scan_service": "Service — Scan URL",
    "test_url_scans": "Scans URL (API)",
    "test_users": "Utilisateurs",
    "test_vault": "Coffre-fort (Vault)",
    "test_webhooks": "Webhooks",
}


def _p(text: str, **kw) -> Paragraph:
    return Paragraph(text, ParagraphStyle("_", **kw))


def run_pytest() -> str:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-v", "--tb=line", "-q"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )
    return result.stdout + result.stderr


def parse_results(output: str) -> dict:
    """Parse pytest -v output into structured data."""
    tests: list[dict] = []
    pattern = re.compile(
        r"^tests/(\w+)\.py::(\S+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)",
        re.MULTILINE,
    )
    for m in pattern.finditer(output):
        tests.append(
            {
                "module": m.group(1),
                "name": m.group(2),
                "status": m.group(3),
            }
        )

    summary_m = re.search(
        r"(\d+) passed(?:.*?(\d+) failed)?(?:.*?(\d+) error)?(?:.*?(\d+) skipped)?",
        output,
    )
    passed = int(summary_m.group(1)) if summary_m and summary_m.group(1) else 0
    failed = int(summary_m.group(2)) if summary_m and summary_m.group(2) else 0
    errors = int(summary_m.group(3)) if summary_m and summary_m.group(3) else 0
    skipped = int(summary_m.group(4)) if summary_m and summary_m.group(4) else 0

    by_module: dict[str, list] = defaultdict(list)
    for t in tests:
        by_module[t["module"]].append(t)

    return {
        "tests": tests,
        "by_module": dict(by_module),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "total": passed + failed + errors + skipped,
    }


def status_color(status: str) -> colors.Color:
    return {
        "PASSED": GREEN,
        "FAILED": RED,
        "ERROR": RED,
        "SKIPPED": YELLOW,
        "XFAIL": YELLOW,
        "XPASS": CYAN,
    }.get(status, GRAY)


def status_label(status: str) -> str:
    return {
        "PASSED": "✓ PASSÉ",
        "FAILED": "✗ ÉCHOUÉ",
        "ERROR": "✗ ERREUR",
        "SKIPPED": "○ IGNORÉ",
        "XFAIL": "○ XFAIL",
        "XPASS": "✓ XPASS",
    }.get(status, status)


def build_pdf(data: dict, out_path: str) -> None:
    buf = io.BytesIO()
    W, H = A4
    mg = 16 * mm

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=mg,
        rightMargin=mg,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
    )
    cw = W - 2 * mg
    s = []

    # ── Cover / Header ──────────────────────────────────────────────────────
    half = cw / 2 - 3 * mm
    gap = 6 * mm

    brand_box = Table(
        [
            [
                _p(
                    "<b>CyberScan</b>",
                    fontSize=18,
                    fontName="Helvetica-Bold",
                    textColor=WHITE,
                    leading=22,
                ),
                _p(
                    "<font color='#06b6d4'>●</font>",
                    fontSize=24,
                    fontName="Helvetica-Bold",
                    textColor=CYAN,
                    alignment=2,
                ),
            ]
        ],
        colWidths=[half * 0.7, half * 0.3],
    )
    brand_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    title_box = Table(
        [
            [
                _p(
                    "<b>RAPPORT DE TESTS</b>",
                    fontSize=16,
                    fontName="Helvetica-Bold",
                    textColor=NAVY,
                    alignment=2,
                ),
            ]
        ],
        colWidths=[half],
    )
    title_box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 11),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    top_row = Table([[brand_box, "", title_box]], colWidths=[half, gap, half])
    top_row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    s.append(top_row)
    s.append(Spacer(1, 4 * mm))

    now = datetime.now().strftime("%d/%m/%Y à %H:%M")
    s.append(
        _p(
            f"<font color='#64748b'>Généré le</font> <b>{now}</b>",
            fontSize=8.5,
            fontName="Helvetica",
            textColor=BLACK,
            alignment=2,
        )
    )
    s.append(Spacer(1, 5 * mm))
    s.append(HRFlowable(width=cw, thickness=0.6, color=BORDER, spaceAfter=5 * mm))

    # ── Summary boxes ────────────────────────────────────────────────────────
    rate = round(data["passed"] / data["total"] * 100) if data["total"] else 0
    rate_color = GREEN if rate >= 95 else YELLOW if rate >= 80 else RED

    def _stat_cell(value: str, label: str, val_color=NAVY):
        return Table(
            [
                [
                    _p(
                        f"<b>{value}</b>",
                        fontSize=22,
                        fontName="Helvetica-Bold",
                        textColor=val_color,
                        alignment=1,
                    ),
                ],
                [
                    _p(
                        label,
                        fontSize=7.5,
                        fontName="Helvetica",
                        textColor=GRAY,
                        alignment=1,
                    ),
                ],
            ],
            colWidths=[(cw - 3 * gap) / 4],
        )

    w4 = (cw - 3 * gap) / 4
    stats_row = Table(
        [
            [
                _stat_cell(str(data["total"]), "Total"),
                _stat_cell(str(data["passed"]), "Passés", GREEN),
                _stat_cell(
                    str(data["failed"] + data["errors"]),
                    "Échoués",
                    RED if data["failed"] + data["errors"] else GRAY,
                ),
                _stat_cell(f"{rate}%", "Taux de succès", rate_color),
            ]
        ],
        colWidths=[w4, w4, w4, w4],
    )
    stats_row.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LINEBEFORE", (1, 0), (-1, -1), 0.5, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), LGRAY),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("LINEABOVE", (0, 0), (-1, 0), 2, CYAN),
            ]
        )
    )
    s.append(stats_row)
    s.append(Spacer(1, 7 * mm))

    # ── Module summary table ─────────────────────────────────────────────────
    s.append(
        _p(
            "<b>Résumé par module</b>",
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=NAVY,
        )
    )
    s.append(Spacer(1, 3 * mm))

    summary_rows = [
        [
            _p("Module", fontSize=8, fontName="Helvetica-Bold", textColor=BLACK),
            _p(
                "Total",
                fontSize=8,
                fontName="Helvetica-Bold",
                textColor=BLACK,
                alignment=1,
            ),
            _p(
                "Passés",
                fontSize=8,
                fontName="Helvetica-Bold",
                textColor=BLACK,
                alignment=1,
            ),
            _p(
                "Échoués",
                fontSize=8,
                fontName="Helvetica-Bold",
                textColor=BLACK,
                alignment=1,
            ),
            _p(
                "Statut",
                fontSize=8,
                fontName="Helvetica-Bold",
                textColor=BLACK,
                alignment=1,
            ),
        ]
    ]
    col_mod = cw * 0.52
    col_num = cw * 0.12
    col_sta = cw * 0.12

    module_style = [
        ("BACKGROUND", (0, 0), (-1, 0), LGRAY),
        ("LINEBELOW", (0, 0), (-1, 0), 1, NAVY),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]

    for i, (mod, tests) in enumerate(sorted(data["by_module"].items()), 1):
        total_m = len(tests)
        passed_m = sum(1 for t in tests if t["status"] == "PASSED")
        failed_m = total_m - passed_m
        label = MODULE_LABELS.get(mod, mod.replace("test_", "").replace("_", " ").title())
        ok = failed_m == 0
        row_bg = WHITE if i % 2 == 0 else colors.HexColor("#f8fafc")
        module_style.append(("BACKGROUND", (0, i), (-1, i), row_bg))

        summary_rows.append(
            [
                _p(label, fontSize=8, fontName="Helvetica", textColor=BLACK),
                _p(
                    str(total_m),
                    fontSize=8,
                    fontName="Helvetica",
                    textColor=GRAY,
                    alignment=1,
                ),
                _p(
                    str(passed_m),
                    fontSize=8,
                    fontName="Helvetica",
                    textColor=GREEN,
                    alignment=1,
                ),
                _p(
                    str(failed_m) if failed_m else "—",
                    fontSize=8,
                    fontName="Helvetica",
                    textColor=RED if failed_m else GRAY,
                    alignment=1,
                ),
                _p(
                    "✓" if ok else f"✗ {failed_m}",
                    fontSize=8,
                    fontName="Helvetica-Bold",
                    textColor=GREEN if ok else RED,
                    alignment=1,
                ),
            ]
        )

    summary_table = Table(
        summary_rows,
        colWidths=[col_mod, col_num, col_num, col_num, col_sta],
    )
    summary_table.setStyle(TableStyle(module_style))
    s.append(summary_table)
    s.append(Spacer(1, 8 * mm))

    # ── Detail per module ────────────────────────────────────────────────────
    for mod, tests in sorted(data["by_module"].items()):
        label = MODULE_LABELS.get(mod, mod.replace("test_", "").replace("_", " ").title())
        failed_in_mod = [t for t in tests if t["status"] not in ("PASSED", "XFAIL")]

        s.append(
            _p(
                f"<b>{label}</b>  "
                f"<font color='#64748b' size='7.5'>{mod}.py — {len(tests)} tests</font>",
                fontSize=9.5,
                fontName="Helvetica-Bold",
                textColor=NAVY,
            )
        )
        s.append(Spacer(1, 2 * mm))

        col_n = cw * 0.78
        col_s = cw * 0.22
        rows = [
            [
                _p(
                    "Nom du test",
                    fontSize=7.5,
                    fontName="Helvetica-Bold",
                    textColor=BLACK,
                ),
                _p(
                    "Statut",
                    fontSize=7.5,
                    fontName="Helvetica-Bold",
                    textColor=BLACK,
                    alignment=2,
                ),
            ]
        ]
        tstyle = [
            ("BACKGROUND", (0, 0), (-1, 0), LGRAY),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        for i, t in enumerate(tests, 1):
            bg = WHITE if i % 2 == 0 else colors.HexColor("#f8fafc")
            tstyle.append(("BACKGROUND", (0, i), (-1, i), bg))
            readable = t["name"].replace("test_", "").replace("_", " ")
            rows.append(
                [
                    _p(readable, fontSize=7, fontName="Helvetica", textColor=BLACK),
                    _p(
                        f"<b>{status_label(t['status'])}</b>",
                        fontSize=7,
                        fontName="Helvetica-Bold",
                        textColor=status_color(t["status"]),
                        alignment=2,
                    ),
                ]
            )

        tbl = Table(rows, colWidths=[col_n, col_s])
        tbl.setStyle(TableStyle(tstyle))
        s.append(tbl)
        s.append(Spacer(1, 6 * mm))

    # ── Footer ───────────────────────────────────────────────────────────────
    s.append(HRFlowable(width=cw, thickness=0.5, color=BORDER, spaceAfter=3 * mm))
    s.append(
        _p(
            f"CyberScan — Rapport de tests automatisés — {now} — cyberscanapp.com",
            fontSize=7,
            fontName="Helvetica",
            textColor=GRAY,
            alignment=1,
        )
    )

    doc.build(s)
    with open(out_path, "wb") as f:
        f.write(buf.getvalue())
    print(f"PDF généré : {out_path}")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "test_report.pdf"
    print("Lancement des tests…")
    output = run_pytest()
    print("Parsing des résultats…")
    data = parse_results(output)
    print(
        f"  {data['total']} tests — {data['passed']} passés, {data['failed'] + data['errors']} échoués"
    )
    print("Génération du PDF…")
    build_pdf(data, out)
