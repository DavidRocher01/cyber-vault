"""PCA Light — Mini Plan de Continuité d'Activité PDF generator."""

from __future__ import annotations

import io
from datetime import UTC, datetime

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

from app.services.pdf_brand import (
    BORDER,
    CARD_BG,
    CYAN,
    DARK_BG,
    GRAY,
    MARGIN,
    PAGE_W,
    WHITE,
)

BLUE = colors.HexColor("#3b82f6")
LIGHT_BG = colors.HexColor("#1e293b")


def _styles() -> dict:
    return {
        "title": ParagraphStyle(
            "pca_title",
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=CYAN,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "pca_sub", fontName="Helvetica", fontSize=11, textColor=GRAY, spaceAfter=16
        ),
        "h2": ParagraphStyle(
            "pca_h2",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=CYAN,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "pca_body",
            fontName="Helvetica",
            fontSize=10,
            textColor=WHITE,
            leading=15,
            spaceAfter=4,
        ),
        "label": ParagraphStyle("pca_label", fontName="Helvetica-Bold", fontSize=9, textColor=GRAY),
        "value": ParagraphStyle("pca_value", fontName="Helvetica", fontSize=10, textColor=WHITE),
        "check": ParagraphStyle(
            "pca_check", fontName="Helvetica", fontSize=10, textColor=WHITE, leading=16
        ),
    }


def _section_rule(width: float) -> HRFlowable:
    return HRFlowable(width=width, thickness=1, color=BORDER, spaceAfter=8)


def _kv_table(pairs: list[tuple[str, str]], styles: dict, col_w: float) -> Table:
    data = [[Paragraph(k, styles["label"]), Paragraph(v or "—", styles["value"])] for k, v in pairs]
    t = Table(data, colWidths=[col_w * 0.35, col_w * 0.65])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [CARD_BG, DARK_BG]),
                ("TEXTCOLOR", (0, 0), (-1, -1), WHITE),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ]
        )
    )
    return t


def generate_pca_pdf(data: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )
    styles = _styles()
    col_w = PAGE_W - 2 * MARGIN
    story = []
    now = datetime.now(UTC)

    company = data.get("company", {})
    systems = data.get("critical_systems", [])
    team = data.get("response_team", [])

    # ── Cover / Title ─────────────────────────────────────────────────────────
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Plan de Continuité d'Activité", styles["title"]))
    story.append(
        Paragraph(
            f"Version légère — {company.get('name', 'Entreprise')} — {now.strftime('%d/%m/%Y')}",
            styles["subtitle"],
        )
    )
    story.append(_section_rule(col_w))
    story.append(Spacer(1, 4 * mm))

    # ── Section 1 : Informations générales ───────────────────────────────────
    story.append(Paragraph("1. Informations générales", styles["h2"]))
    story.append(
        _kv_table(
            [
                ("Entreprise", company.get("name", "")),
                ("Secteur d'activité", company.get("sector", "")),
                ("Responsable PCA", company.get("contact", "")),
                ("Email", company.get("email", "")),
                ("Téléphone", company.get("phone", "")),
                ("Date de création", now.strftime("%d/%m/%Y")),
            ],
            styles,
            col_w,
        )
    )
    story.append(Spacer(1, 6 * mm))

    # ── Section 2 : Systèmes critiques ────────────────────────────────────────
    story.append(Paragraph("2. Systèmes critiques", styles["h2"]))
    story.append(
        Paragraph(
            "RTO = Recovery Time Objective (durée max d'interruption acceptable). "
            "RPO = Recovery Point Objective (perte de données maximale acceptable).",
            styles["body"],
        )
    )
    story.append(Spacer(1, 3 * mm))

    if systems:
        headers = [
            Paragraph("Système", styles["label"]),
            Paragraph("Description", styles["label"]),
            Paragraph("RTO (h)", styles["label"]),
            Paragraph("RPO (h)", styles["label"]),
            Paragraph("Responsable", styles["label"]),
        ]
        rows = [headers]
        for s in systems:
            rows.append(
                [
                    Paragraph(s.get("name", ""), styles["value"]),
                    Paragraph(s.get("description", ""), styles["value"]),
                    Paragraph(str(s.get("rto_hours", "—")), styles["value"]),
                    Paragraph(str(s.get("rpo_hours", "—")), styles["value"]),
                    Paragraph(s.get("responsible", ""), styles["value"]),
                ]
            )
        t = Table(
            rows,
            colWidths=[
                col_w * 0.20,
                col_w * 0.30,
                col_w * 0.10,
                col_w * 0.10,
                col_w * 0.30,
            ],
        )
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CARD_BG, DARK_BG]),
                    ("TEXTCOLOR", (0, 0), (-1, -1), WHITE),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ]
            )
        )
        story.append(t)
    else:
        story.append(Paragraph("Aucun système critique renseigné.", styles["body"]))

    story.append(Spacer(1, 6 * mm))

    # ── Section 3 : Équipe de réponse ─────────────────────────────────────────
    story.append(Paragraph("3. Équipe de réponse aux incidents", styles["h2"]))

    if team:
        headers = [
            Paragraph("Nom", styles["label"]),
            Paragraph("Rôle", styles["label"]),
            Paragraph("Téléphone", styles["label"]),
            Paragraph("Email", styles["label"]),
        ]
        rows = [headers]
        for m in team:
            rows.append(
                [
                    Paragraph(m.get("name", ""), styles["value"]),
                    Paragraph(m.get("role", ""), styles["value"]),
                    Paragraph(m.get("phone", ""), styles["value"]),
                    Paragraph(m.get("email", ""), styles["value"]),
                ]
            )
        t = Table(rows, colWidths=[col_w * 0.25, col_w * 0.25, col_w * 0.20, col_w * 0.30])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BG),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CARD_BG, DARK_BG]),
                    ("TEXTCOLOR", (0, 0), (-1, -1), WHITE),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ]
            )
        )
        story.append(t)
    else:
        story.append(Paragraph("Aucun membre d'équipe renseigné.", styles["body"]))

    story.append(Spacer(1, 6 * mm))

    # ── Section 4 : Procédures de continuité ──────────────────────────────────
    story.append(Paragraph("4. Procédures de continuité", styles["h2"]))

    checklist = [
        "□  Déclarer l'incident au responsable PCA et à la direction",
        "□  Activer la cellule de crise (équipe de réponse)",
        "□  Évaluer l'impact (systèmes touchés, données compromises ?)",
        "□  Isoler les systèmes affectés du réseau",
        "□  Restaurer à partir des dernières sauvegardes validées",
        "□  Communiquer aux parties prenantes internes (selon plan de communication)",
        "□  Notifier les autorités si nécessaire (CNIL si données personnelles, ANSSI si OIV/OSE)",
        "□  Tester la restauration avant remise en production",
        "□  Documenter l'incident et les actions prises",
        "□  Organiser un retour d'expérience (REX) dans les 7 jours",
    ]
    for item in checklist:
        story.append(Paragraph(item, styles["check"]))

    story.append(Spacer(1, 6 * mm))

    # ── Section 5 : Plan de communication ────────────────────────────────────
    story.append(Paragraph("5. Plan de communication", styles["h2"]))
    comm = data.get("communication_plan", "")
    story.append(
        Paragraph(
            comm if comm else "À définir par l'entreprise selon les parties prenantes concernées.",
            styles["body"],
        )
    )

    story.append(Spacer(1, 4 * mm))
    story.append(_section_rule(col_w))
    story.append(
        Paragraph(
            f"Document généré le {now.strftime('%d/%m/%Y à %H:%M')} UTC — Rocher Cybersécurité PCA Light",
            ParagraphStyle("footer", fontName="Helvetica", fontSize=8, textColor=GRAY),
        )
    )

    doc.build(story)
    return buf.getvalue()
