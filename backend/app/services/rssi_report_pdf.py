"""RSSI Externalisé — PDF report generator for a single client."""
from __future__ import annotations

import io
from datetime import date, datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

from app.services.pdf_brand import (
    BORDER, CARD_BG, CYAN, DARK_BG, GRAY, GREEN, ORANGE, RED, WHITE, YELLOW,
    MARGIN, PAGE_W,
)

_AMBER   = colors.HexColor("#f59e0b")
_PURPLE  = colors.HexColor("#a855f7")
_BLUE    = colors.HexColor("#3b82f6")
_COL_W   = PAGE_W - 2 * MARGIN * mm


# ── Style helpers ─────────────────────────────────────────────────────────────

def _styles() -> dict:
    return {
        "title":    ParagraphStyle("r_title",  fontName="Helvetica-Bold", fontSize=22,
                                   textColor=CYAN, spaceAfter=2),
        "subtitle": ParagraphStyle("r_sub",    fontName="Helvetica",      fontSize=11,
                                   textColor=GRAY, spaceAfter=14),
        "h2":       ParagraphStyle("r_h2",     fontName="Helvetica-Bold", fontSize=13,
                                   textColor=CYAN, spaceBefore=14, spaceAfter=6),
        "body":     ParagraphStyle("r_body",   fontName="Helvetica",      fontSize=10,
                                   textColor=WHITE, leading=15, spaceAfter=4),
        "label":    ParagraphStyle("r_label",  fontName="Helvetica-Bold", fontSize=9,
                                   textColor=GRAY),
        "value":    ParagraphStyle("r_value",  fontName="Helvetica",      fontSize=10,
                                   textColor=WHITE),
        "small":    ParagraphStyle("r_small",  fontName="Helvetica",      fontSize=8,
                                   textColor=GRAY),
        "th":       ParagraphStyle("r_th",     fontName="Helvetica-Bold", fontSize=9,
                                   textColor=CYAN),
        "td":       ParagraphStyle("r_td",     fontName="Helvetica",      fontSize=9,
                                   textColor=WHITE),
        "td_red":   ParagraphStyle("r_td_red", fontName="Helvetica-Bold", fontSize=9,
                                   textColor=RED),
        "td_grn":   ParagraphStyle("r_td_grn", fontName="Helvetica-Bold", fontSize=9,
                                   textColor=GREEN),
        "td_amb":   ParagraphStyle("r_td_amb", fontName="Helvetica-Bold", fontSize=9,
                                   textColor=_AMBER),
        "footer":   ParagraphStyle("r_footer", fontName="Helvetica",      fontSize=8,
                                   textColor=GRAY, alignment=1),
    }


def _rule() -> HRFlowable:
    return HRFlowable(width=_COL_W, thickness=1, color=BORDER, spaceAfter=8)


def _kv_table(pairs: list[tuple[str, str]], styles: dict) -> Table:
    data = [[Paragraph(k, styles["label"]), Paragraph(v or "—", styles["value"])] for k, v in pairs]
    t = Table(data, colWidths=[_COL_W * 0.32, _COL_W * 0.68])
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [CARD_BG, DARK_BG]),
        ("TOPPADDING",     (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("GRID",           (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    return t


def _fmt_date(d: str | date | None) -> str:
    if not d:
        return "—"
    if isinstance(d, str):
        try:
            return datetime.fromisoformat(d).strftime("%d/%m/%Y")
        except ValueError:
            return d
    return d.strftime("%d/%m/%Y")


def _priority_style(priority: str, styles: dict) -> ParagraphStyle:
    return {
        "critical": styles["td_red"],
        "high":     styles["td_amb"],
        "medium":   styles["td"],
        "low":      styles["small"],
    }.get(priority, styles["td"])


def _status_style(status: str, styles: dict) -> ParagraphStyle:
    return {
        "done":        styles["td_grn"],
        "in_progress": ParagraphStyle("r_td_blue", fontName="Helvetica-Bold",
                                      fontSize=9, textColor=_BLUE),
        "cancelled":   styles["small"],
        "postponed":   styles["td_amb"],
    }.get(status, styles["td"])


# ── Main generator ────────────────────────────────────────────────────────────

def generate_rssi_report(
    client: dict,
    actions: list[dict],
    visits: list[dict],
    deliverables: list[dict] | None = None,
    consultant: dict | None = None,
) -> bytes:
    """Return PDF bytes for a full RSSI client report."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN * mm, rightMargin=MARGIN * mm,
        topMargin=MARGIN * mm,  bottomMargin=MARGIN * mm,
    )
    styles = _styles()
    story: list = []
    now = datetime.now(timezone.utc)

    _formula_labels = {"essentiel": "Essentiel", "premium": "Premium", "excellence": "Excellence"}
    _status_labels  = {"active": "Actif", "inactive": "Inactif", "churned": "Churné"}

    today_str = now.date().isoformat()

    # ── Cover ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("Rapport RSSI Externalisé", styles["title"]))
    story.append(Paragraph(
        f"{client.get('name', '—')} — Généré le {now.strftime('%d/%m/%Y à %H:%M')} UTC",
        styles["subtitle"],
    ))

    if consultant:
        parts: list[str] = []
        if consultant.get("display_name"):
            parts.append(consultant["display_name"])
        if consultant.get("company_name"):
            parts.append(consultant["company_name"])
        if consultant.get("email"):
            parts.append(consultant["email"])
        if consultant.get("phone"):
            parts.append(consultant["phone"])
        if parts:
            story.append(Paragraph("RSSI : " + " · ".join(parts), styles["small"]))

    story.append(_rule())
    story.append(Spacer(1, 2 * mm))

    # ── Section 1 : Informations client ──────────────────────────────────────
    story.append(Paragraph("1. Informations client", styles["h2"]))

    formula     = client.get("formula") or ""
    monthly     = client.get("monthly_amount")
    monthly_str = f"{monthly:,.0f} €/mois".replace(",", " ") if monthly else "—"
    renewal     = _fmt_date(client.get("contract_renewal_at"))
    status      = _status_labels.get(client.get("status", ""), client.get("status", "—"))

    story.append(_kv_table([
        ("Nom",               client.get("name", "—")),
        ("Email",             client.get("email") or "—"),
        ("Formule",           _formula_labels.get(formula, "—")),
        ("Montant mensuel",   monthly_str),
        ("Statut",            status),
        ("Renouvellement",    renewal),
        ("Description",       client.get("description") or "—"),
    ], styles))
    story.append(Spacer(1, 4 * mm))

    # Optional integrations
    notion = client.get("notion_workspace_url")
    pipedrive = client.get("pipedrive_deal_id")
    pennylane = client.get("pennylane_customer_id")
    if notion or pipedrive or pennylane:
        story.append(Paragraph("Intégrations", styles["h2"]))
        story.append(_kv_table([
            ("Notion workspace", notion or "—"),
            ("Pipedrive deal",   pipedrive or "—"),
            ("Pennylane client", pennylane or "—"),
        ], styles))
        story.append(Spacer(1, 4 * mm))

    # ── Section 2 : Plan d'actions ────────────────────────────────────────────
    story.append(Paragraph("2. Plan d'actions", styles["h2"]))

    open_actions = [a for a in actions if a.get("status") not in ("done", "cancelled")]
    overdue = [a for a in open_actions if a.get("due_date") and a["due_date"] < today_str]

    story.append(_kv_table([
        ("Actions ouvertes",  str(len(open_actions))),
        ("Actions en retard", str(len(overdue))),
        ("Actions terminées", str(len([a for a in actions if a.get("status") == "done"]))),
        ("Total actions",     str(len(actions))),
    ], styles))
    story.append(Spacer(1, 3 * mm))

    if actions:
        _priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        sorted_actions = sorted(actions, key=lambda a: _priority_order.get(a.get("priority", ""), 9))

        _priority_fr = {"critical": "Critique", "high": "Haute", "medium": "Moyenne", "low": "Basse"}
        _status_fr   = {
            "open": "Ouverte", "in_progress": "En cours", "done": "Terminée",
            "cancelled": "Annulée", "postponed": "Reportée",
        }

        header = [
            Paragraph("Titre", styles["th"]),
            Paragraph("Priorité", styles["th"]),
            Paragraph("Statut", styles["th"]),
            Paragraph("Échéance", styles["th"]),
            Paragraph("Responsable", styles["th"]),
        ]
        rows = [header]
        for a in sorted_actions:
            is_overdue = (
                a.get("due_date") and a["due_date"] < today_str
                and a.get("status") not in ("done", "cancelled")
            )
            title_style = styles["td_red"] if is_overdue else styles["td"]
            rows.append([
                Paragraph(a.get("title", "—"), title_style),
                Paragraph(_priority_fr.get(a.get("priority", ""), "—"), _priority_style(a.get("priority", ""), styles)),
                Paragraph(_status_fr.get(a.get("status", ""), "—"),    _status_style(a.get("status", ""), styles)),
                Paragraph(_fmt_date(a.get("due_date")), styles["td_red"] if is_overdue else styles["small"]),
                Paragraph(a.get("assigned_to") or "—", styles["small"]),
            ])

        col_widths = [_COL_W * 0.35, _COL_W * 0.13, _COL_W * 0.14, _COL_W * 0.16, _COL_W * 0.22]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  CARD_BG),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [DARK_BG, CARD_BG]),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("GRID",          (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("Aucune action enregistrée.", styles["body"]))

    story.append(Spacer(1, 4 * mm))

    # ── Section 3 : Historique des visites ────────────────────────────────────
    story.append(Paragraph("3. Historique des visites", styles["h2"]))

    _visit_type_fr   = {"monthly": "Mensuelle", "quarterly": "Trimestrielle",
                        "annual": "Annuelle", "urgent": "Urgente"}
    _visit_status_fr = {"planned": "Planifiée", "completed": "Complétée",
                        "cancelled": "Annulée", "postponed": "Reportée"}
    _location_fr     = {"onsite": "Sur site", "remote": "À distance"}

    if visits:
        recent = sorted(visits, key=lambda v: v.get("scheduled_date", ""), reverse=True)[:10]
        header = [
            Paragraph("Date", styles["th"]),
            Paragraph("Type", styles["th"]),
            Paragraph("Lieu", styles["th"]),
            Paragraph("Statut", styles["th"]),
            Paragraph("Durée", styles["th"]),
        ]
        rows = [header]
        for v in recent:
            vst = v.get("status", "planned")
            rows.append([
                Paragraph(_fmt_date(v.get("scheduled_date")), styles["td"]),
                Paragraph(_visit_type_fr.get(v.get("visit_type", ""), "—"),   styles["td"]),
                Paragraph(_location_fr.get(v.get("location", ""), "—"),       styles["td"]),
                Paragraph(_visit_status_fr.get(vst, vst),
                          styles["td_grn"] if vst == "completed" else
                          styles["td_red"] if vst == "cancelled" else styles["td"]),
                Paragraph(f"{v['duration_hours']}h" if v.get("duration_hours") else "—", styles["small"]),
            ])

        col_widths = [_COL_W * 0.22, _COL_W * 0.20, _COL_W * 0.18, _COL_W * 0.22, _COL_W * 0.18]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  CARD_BG),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [DARK_BG, CARD_BG]),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("GRID",          (0, 0), (-1, -1), 0.5, BORDER),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("Aucune visite enregistrée.", styles["body"]))

    story.append(Spacer(1, 4 * mm))

    # ── Section 4 : Livrables envoyés ────────────────────────────────────────
    story.append(Paragraph("4. Livrables envoyés", styles["h2"]))

    _doc_type_fr = {
        "compte_rendu": "Compte-rendu", "rapport": "Rapport",
        "recommandation": "Recommandation", "contrat": "Contrat", "autre": "Autre",
    }

    if deliverables:
        recent_deliverables = sorted(
            deliverables, key=lambda d: d.get("delivered_at", ""), reverse=True
        )[:20]
        header = [
            Paragraph("Date", styles["th"]),
            Paragraph("Type", styles["th"]),
            Paragraph("Titre", styles["th"]),
            Paragraph("Fichier", styles["th"]),
        ]
        rows = [header]
        for d in recent_deliverables:
            rows.append([
                Paragraph(_fmt_date(d.get("delivered_at")), styles["td"]),
                Paragraph(_doc_type_fr.get(d.get("doc_type", ""), "—"), styles["td"]),
                Paragraph(d.get("title", "—"), styles["td"]),
                Paragraph(d.get("file_url") or "—", styles["small"]),
            ])

        col_widths = [_COL_W * 0.18, _COL_W * 0.20, _COL_W * 0.38, _COL_W * 0.24]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0),  CARD_BG),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [DARK_BG, CARD_BG]),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("GRID",          (0, 0), (-1, -1), 0.5, BORDER),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("Aucun livrable enregistré.", styles["body"]))

    story.append(Spacer(1, 8 * mm))
    story.append(_rule())
    story.append(Paragraph(
        f"Rapport généré par CyberScan — RSSI Externalisé — {now.strftime('%d/%m/%Y')}",
        styles["footer"],
    ))

    doc.build(story)
    return buf.getvalue()
