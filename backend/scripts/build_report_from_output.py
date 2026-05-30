"""
Build the test report PDF from an already-captured pytest -v output file.
Usage: python scripts/build_report_from_output.py <output.txt> <report.pdf>
"""

from __future__ import annotations

import io
import re
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
    "test_ssrf_unit": "Protection SSRF (unitaire)",
    "test_stripe_service_unit": "Service Stripe (unitaire)",
    "test_subscriptions": "Abonnements",
    "test_url_scan_service": "Service — Scan URL",
    "test_url_scans": "Scans URL (API)",
    "test_users": "Utilisateurs",
    "test_vault": "Coffre-fort (Vault)",
    "test_webhooks": "Webhooks",
}

FAILURE_NOTES = {
    "test_setup_2fa_requires_auth": "Reçoit 403 au lieu de 401 (comportement FastAPI/Bearer)",
    "test_protected_route_requires_token": "Reçoit 403 au lieu de 401",
    "test_trigger_code_scan_unauthenticated_returns_403": "Reçoit 403 au lieu de 401",
    "test_upload_zip_unauthenticated_returns_403": "Reçoit 403 au lieu de 401",
    "test_get_assessment_requires_auth": "Reçoit 403 au lieu de 401",
    "test_save_assessment_requires_auth": "Reçoit 403 au lieu de 401",
    "test_export_pdf_requires_auth": "Reçoit 403 au lieu de 401",
    "test_list_notifications_unauthenticated_returns_403": "Reçoit 403 au lieu de 401",
    "test_mark_all_read_unauthenticated_returns_403": "Reçoit 403 au lieu de 401",
    "test_protected_endpoint_without_token_returns_403": "Reçoit 403 au lieu de 401",
    "test_csv_export_requires_auth": "Reçoit 403 au lieu de 401",
    "test_unauthenticated_sites_returns_401": "Reçoit 403 au lieu de 401",
    "test_get_subscription_unauthenticated_returns_403": "Reçoit 403 au lieu de 401",
    "test_checkout_unauthenticated_returns_403": "Reçoit 403 au lieu de 401",
    "test_portal_unauthenticated_returns_403": "Reçoit 403 au lieu de 401",
    "test_trigger_url_scan_requires_auth": "Reçoit 403 au lieu de 401",
    "test_list_url_scans_requires_auth": "Reçoit 403 au lieu de 401",
    "test_get_url_scan_requires_auth": "Reçoit 403 au lieu de 401",
    "test_delete_url_scan_requires_auth": "Reçoit 403 au lieu de 401",
    "test_update_email_unauthenticated_returns_403": "Reçoit 403 au lieu de 401",
    "test_update_password_unauthenticated_returns_403": "Reçoit 403 au lieu de 401",
    "test_export_my_data_unauthenticated_returns_403": "Reçoit 403 au lieu de 401",
    "test_delete_account_unauthenticated_returns_403": "Reçoit 403 au lieu de 401",
    "test_get_notification_preferences_unauthenticated_returns_403": "Reçoit 403 au lieu de 401",
    "test_update_notification_preferences_unauthenticated_returns_403": "Reçoit 403 au lieu de 401",
}

FAILURE_ROOT_CAUSE = (
    "FastAPI retourne 403 (et non 401) quand aucun token Bearer n'est fourni. "
    "Il s'agit du comportement standard de la dépendance HTTPBearer. "
    "Ces 25 tests vérifient le mauvais code HTTP — l'API se comporte correctement. "
    "Correction : remplacer assert 401 par assert 403 dans ces tests."
)


def _p(text: str, **kw) -> Paragraph:
    return Paragraph(text, ParagraphStyle("_", **kw))


def parse_output(text: str) -> dict:
    tests = []
    pattern = re.compile(
        r"^tests/(\w+)\.py::(\S+)\s+(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)",
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        tests.append({"module": m.group(1), "name": m.group(2), "status": m.group(3)})

    sm = re.search(r"(\d+) failed.*?(\d+) passed|(\d+) passed", text)
    summary = re.search(r"=+ (.*?) =+\s*$", text, re.MULTILINE)

    passed = sum(1 for t in tests if t["status"] == "PASSED")
    failed = sum(1 for t in tests if t["status"] in ("FAILED", "ERROR"))
    skipped = sum(1 for t in tests if t["status"] in ("SKIPPED", "XFAIL"))

    by_module: dict[str, list] = defaultdict(list)
    for t in tests:
        by_module[t["module"]].append(t)

    return {
        "tests": tests,
        "by_module": dict(by_module),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "total": len(tests),
    }


def status_color(s: str) -> colors.Color:
    return {
        "PASSED": GREEN,
        "FAILED": RED,
        "ERROR": RED,
        "SKIPPED": YELLOW,
        "XFAIL": YELLOW,
    }.get(s, GRAY)


def status_label(s: str) -> str:
    return {
        "PASSED": "✓  PASSÉ",
        "FAILED": "✗  ÉCHOUÉ",
        "ERROR": "✗  ERREUR",
        "SKIPPED": "○  IGNORÉ",
        "XFAIL": "○  XFAIL",
    }.get(s, s)


def build_pdf(data: dict, out_path: str) -> None:
    buf = io.BytesIO()
    W, _ = A4
    mg = 16 * mm
    cw = W - 2 * mg

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=mg,
        rightMargin=mg,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
    )
    s = []
    half = cw / 2 - 3 * mm
    gap = 6 * mm
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")

    # ── En-tête ──────────────────────────────────────────────────────────────
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
                ("BOX", (0, 0), (-1, -1), 1.5, NAVY),
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
    s.append(Spacer(1, 3 * mm))
    s.append(
        _p(
            f"<font color='#64748b'>Généré le</font> <b>{now}</b>  —  "
            f"<font color='#64748b'>Backend FastAPI + pytest</font>",
            fontSize=8,
            fontName="Helvetica",
            textColor=BLACK,
            alignment=2,
        )
    )
    s.append(Spacer(1, 5 * mm))
    s.append(HRFlowable(width=cw, thickness=0.6, color=BORDER, spaceAfter=5 * mm))

    # ── Indicateurs ──────────────────────────────────────────────────────────
    rate = round(data["passed"] / data["total"] * 100) if data["total"] else 0
    rate_col = GREEN if rate >= 95 else YELLOW if rate >= 80 else RED

    w4 = (cw - 3 * gap) / 4

    def _kpi(val: str, label: str, vc=NAVY):
        t = Table(
            [
                [
                    _p(
                        f"<b>{val}</b>",
                        fontSize=24,
                        fontName="Helvetica-Bold",
                        textColor=vc,
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
            colWidths=[w4],
        )
        t.setStyle(
            TableStyle(
                [
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return t

    kpi_row = Table(
        [
            [
                _kpi(str(data["total"]), "Total"),
                _kpi(str(data["passed"]), "Passés", GREEN),
                _kpi(str(data["failed"]), "Échoués", RED if data["failed"] else GRAY),
                _kpi(f"{rate}%", "Réussite", rate_col),
            ]
        ],
        colWidths=[w4, w4, w4, w4],
    )
    kpi_row.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LINEBEFORE", (1, 0), (-1, -1), 0.5, BORDER),
                ("BACKGROUND", (0, 0), (-1, -1), LGRAY),
                ("LINEABOVE", (0, 0), (-1, 0), 2.5, CYAN),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    s.append(kpi_row)
    s.append(Spacer(1, 6 * mm))

    # ── Note sur les 25 échecs ───────────────────────────────────────────────
    if data["failed"]:
        note = Table(
            [
                [
                    _p(
                        f"<b>Note sur les {data['failed']} échecs</b>",
                        fontSize=8.5,
                        fontName="Helvetica-Bold",
                        textColor=YELLOW,
                    ),
                ],
                [
                    _p(
                        FAILURE_ROOT_CAUSE,
                        fontSize=7.5,
                        fontName="Helvetica",
                        textColor=BLACK,
                        leading=11,
                    ),
                ],
            ],
            colWidths=[cw],
        )
        note.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, YELLOW),
                    ("LINEABOVE", (0, 0), (-1, 0), 2, YELLOW),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        s.append(note)
        s.append(Spacer(1, 6 * mm))

    # ── Résumé par module ────────────────────────────────────────────────────
    s.append(
        _p(
            "<b>Résumé par module</b>",
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=NAVY,
        )
    )
    s.append(Spacer(1, 3 * mm))

    cm = cw * 0.50
    cn = cw * 0.12
    cs = cw * 0.14

    hdr = [
        [
            _p("Module", fontSize=7.5, fontName="Helvetica-Bold", textColor=BLACK),
            _p(
                "Total",
                fontSize=7.5,
                fontName="Helvetica-Bold",
                textColor=BLACK,
                alignment=1,
            ),
            _p(
                "Passés",
                fontSize=7.5,
                fontName="Helvetica-Bold",
                textColor=BLACK,
                alignment=1,
            ),
            _p(
                "Échoués",
                fontSize=7.5,
                fontName="Helvetica-Bold",
                textColor=BLACK,
                alignment=1,
            ),
            _p(
                "Statut",
                fontSize=7.5,
                fontName="Helvetica-Bold",
                textColor=BLACK,
                alignment=1,
            ),
        ]
    ]
    mod_style = [
        ("BACKGROUND", (0, 0), (-1, 0), LGRAY),
        ("LINEBELOW", (0, 0), (-1, 0), 1, NAVY),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    rows = list(hdr)
    for i, (mod, tests) in enumerate(sorted(data["by_module"].items()), 1):
        tot = len(tests)
        ok = sum(1 for t in tests if t["status"] == "PASSED")
        ko = tot - ok
        lbl = MODULE_LABELS.get(mod, mod.replace("test_", "").replace("_", " ").title())
        bg = WHITE if i % 2 == 0 else colors.HexColor("#f8fafc")
        mod_style.append(("BACKGROUND", (0, i), (-1, i), bg))
        rows.append(
            [
                _p(lbl, fontSize=7.5, fontName="Helvetica", textColor=BLACK),
                _p(
                    str(tot),
                    fontSize=7.5,
                    fontName="Helvetica",
                    textColor=GRAY,
                    alignment=1,
                ),
                _p(
                    str(ok),
                    fontSize=7.5,
                    fontName="Helvetica",
                    textColor=GREEN,
                    alignment=1,
                ),
                _p(
                    str(ko) if ko else "—",
                    fontSize=7.5,
                    fontName="Helvetica",
                    textColor=RED if ko else GRAY,
                    alignment=1,
                ),
                _p(
                    "✓" if not ko else f"✗ {ko}",
                    fontSize=7.5,
                    fontName="Helvetica-Bold",
                    textColor=GREEN if not ko else RED,
                    alignment=1,
                ),
            ]
        )

    mod_tbl = Table(rows, colWidths=[cm, cn, cn, cn, cs])
    mod_tbl.setStyle(TableStyle(mod_style))
    s.append(mod_tbl)
    s.append(Spacer(1, 8 * mm))

    # ── Détail par module ────────────────────────────────────────────────────
    for mod, tests in sorted(data["by_module"].items()):
        lbl = MODULE_LABELS.get(mod, mod.replace("test_", "").replace("_", " ").title())
        s.append(
            _p(
                f"<b>{lbl}</b>  "
                f"<font color='#64748b' size='7'>{mod}.py — {len(tests)} tests</font>",
                fontSize=9.5,
                fontName="Helvetica-Bold",
                textColor=NAVY,
            )
        )
        s.append(Spacer(1, 2 * mm))

        cn2 = cw * 0.63
        cs2 = cw * 0.22
        cn3 = cw * 0.15
        rows2 = [
            [
                _p(
                    "Nom du test",
                    fontSize=7,
                    fontName="Helvetica-Bold",
                    textColor=BLACK,
                ),
                _p("Note", fontSize=7, fontName="Helvetica-Bold", textColor=BLACK),
                _p(
                    "Statut",
                    fontSize=7,
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
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]
        for i, t in enumerate(tests, 1):
            bg = WHITE if i % 2 == 0 else colors.HexColor("#f8fafc")
            tstyle.append(("BACKGROUND", (0, i), (-1, i), bg))
            readable = t["name"].replace("test_", "").replace("_", " ")
            note = ""
            if t["status"] == "FAILED":
                note = FAILURE_NOTES.get(t["name"], "Voir sortie pytest")
            rows2.append(
                [
                    _p(readable, fontSize=6.5, fontName="Helvetica", textColor=BLACK),
                    _p(
                        note,
                        fontSize=6,
                        fontName="Helvetica-Oblique",
                        textColor=YELLOW if note else GRAY,
                    ),
                    _p(
                        f"<b>{status_label(t['status'])}</b>",
                        fontSize=6.5,
                        fontName="Helvetica-Bold",
                        textColor=status_color(t["status"]),
                        alignment=2,
                    ),
                ]
            )

        tbl = Table(rows2, colWidths=[cn2, cs2, cn3])
        tbl.setStyle(TableStyle(tstyle))
        s.append(tbl)
        s.append(Spacer(1, 5 * mm))

    # ── Pied de page ─────────────────────────────────────────────────────────
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
    input_file = sys.argv[1]
    output_pdf = sys.argv[2] if len(sys.argv) > 2 else "test_report.pdf"
    text = Path(input_file).read_text(encoding="utf-8", errors="replace")
    data = parse_output(text)
    print(f"  {data['total']} tests — {data['passed']} passés, {data['failed']} échoués")
    build_pdf(data, output_pdf)
