"""
darkweb_dossier_service.py — batch email breach checking + PDF report for B2B dossiers.

Flow:
  1. process_dossier()  — called in background after POST /darkweb-dossier
  2. For each target email: check_email_breaches() + enrich from local catalog
  3. Aggregate stats → update DarkwebDossier
  4. generate_dossier_pdf() — build PDF with cover + exposed table + recommendations
"""
from __future__ import annotations

import io
import json
import time
from collections import Counter
from datetime import datetime, timezone

from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.breach_catalog import BreachCatalogEntry
from app.models.darkweb_dossier import DarkwebDossier, DarkwebDossierTarget
from app.services.darkweb_service import (
    check_email_breaches,
    enrich_breaches_from_catalog,
    fetch_hibp_breach_catalog,
)
from app.services.pdf_brand import (
    CARD_BG,
    CYAN,
    DARK_BG,
    GRAY,
    GREEN,
    MARGIN,
    ORANGE,
    RED,
    WHITE,
    YELLOW,
    draw_page,
    get_styles,
    section_rule,
)

_BATCH_DELAY = 1.2  # seconds between LeakCheck calls to respect rate limit


# ── Breach catalog sync ───────────────────────────────────────────────────────

async def sync_breach_catalog(db: AsyncSession) -> int:
    """Fetch HIBP public breach list and upsert into local breach_catalog table."""
    raw = fetch_hibp_breach_catalog()
    if not raw:
        return 0
    upserted = 0
    for entry in raw:
        name = entry.get("Name", "")
        if not name:
            continue
        result = await db.execute(
            select(BreachCatalogEntry).where(BreachCatalogEntry.name == name)
        )
        existing = result.scalar_one_or_none()
        data_classes = json.dumps(entry.get("DataClasses", []))
        if existing:
            existing.title = entry.get("Title", "")
            existing.domain = entry.get("Domain", "")
            existing.breach_date = entry.get("BreachDate", "")
            existing.added_date = entry.get("AddedDate", "")
            existing.pwn_count = entry.get("PwnCount", 0)
            existing.description = entry.get("Description", "")
            existing.data_classes_json = data_classes
            existing.is_verified = entry.get("IsVerified", False)
            existing.is_sensitive = entry.get("IsSensitive", False)
            existing.is_fabricated = entry.get("IsFabricated", False)
            existing.is_spam_list = entry.get("IsSpamList", False)
            existing.updated_at = datetime.now(timezone.utc)
        else:
            db.add(BreachCatalogEntry(
                name=name,
                title=entry.get("Title", ""),
                domain=entry.get("Domain", ""),
                breach_date=entry.get("BreachDate", ""),
                added_date=entry.get("AddedDate", ""),
                pwn_count=entry.get("PwnCount", 0),
                description=entry.get("Description", ""),
                data_classes_json=data_classes,
                is_verified=entry.get("IsVerified", False),
                is_sensitive=entry.get("IsSensitive", False),
                is_fabricated=entry.get("IsFabricated", False),
                is_spam_list=entry.get("IsSpamList", False),
            ))
        upserted += 1
    await db.commit()
    return upserted


async def _build_catalog_index(db: AsyncSession) -> dict[str, dict]:
    """Return a {name.lower(): entry_dict} index from local catalog."""
    result = await db.execute(select(BreachCatalogEntry))
    entries = result.scalars().all()
    index: dict[str, dict] = {}
    for e in entries:
        try:
            dc = json.loads(e.data_classes_json or "[]")
        except Exception:
            dc = []
        index[e.name.lower()] = {
            "domain": e.domain or "",
            "breach_date": e.breach_date or "",
            "pwn_count": e.pwn_count,
            "data_classes": dc,
            "is_sensitive": e.is_sensitive,
            "is_verified": e.is_verified,
        }
    return index


# ── Background processing ─────────────────────────────────────────────────────

async def process_dossier(dossier_id: int, api_key: str) -> None:
    """Process all targets for a dossier — runs in background with its own DB session."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DarkwebDossier).where(DarkwebDossier.id == dossier_id)
        )
        dossier = result.scalar_one_or_none()
        if not dossier:
            return

        dossier.status = "processing"
        dossier.started_at = datetime.now(timezone.utc)
        await db.commit()

        catalog = await _build_catalog_index(db)

        try:
            result = await db.execute(
                select(DarkwebDossierTarget).where(DarkwebDossierTarget.dossier_id == dossier_id)
            )
            targets = result.scalars().all()

            exposed = 0
            total_instances = 0

            for i, target in enumerate(targets):
                if i > 0:
                    time.sleep(_BATCH_DELAY)
                data = check_email_breaches(target.email, api_key)
                breaches = enrich_breaches_from_catalog(data.get("breaches", []), catalog)
                count = data.get("total", 0)

                target.total_breaches = count
                target.status = "clean" if count == 0 else "exposed"
                target.breach_sources_json = json.dumps(breaches)
                target.checked_at = datetime.now(timezone.utc)

                if count > 0:
                    exposed += 1
                    total_instances += count

            # Compute risk score: weighted exposure rate
            total = len(targets)
            if total > 0:
                heavy = sum(1 for t in targets if t.total_breaches >= 3)
                weighted = (exposed + heavy * 0.5) / (total + heavy * 0.5)
                risk_score = min(100, round(weighted * 100))
            else:
                risk_score = 0

            # Top breach sources
            all_sources: list[str] = []
            for target in targets:
                try:
                    src = json.loads(target.breach_sources_json or "[]")
                    all_sources.extend(b.get("name", "") for b in src if b.get("name"))
                except Exception:
                    pass
            top_sources = [{"name": n, "count": c}
                           for n, c in Counter(all_sources).most_common(10)]

            dossier.exposed_emails = exposed
            dossier.total_breach_instances = total_instances
            dossier.risk_score = risk_score
            dossier.top_sources_json = json.dumps(top_sources)
            dossier.status = "completed"
            dossier.finished_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as exc:
            dossier.status = "failed"
            dossier.error_message = str(exc)
            dossier.finished_at = datetime.now(timezone.utc)
            await db.commit()


# ── PDF generation ────────────────────────────────────────────────────────────

def _risk_color(score: int):
    if score >= 50:
        return RED
    if score >= 20:
        return YELLOW
    return GREEN


def _risk_label(score: int) -> str:
    if score >= 50:
        return "RISQUE ÉLEVÉ"
    if score >= 20:
        return "RISQUE MODÉRÉ"
    return "RISQUE FAIBLE"


def _draw_dossier_cover(canvas, doc, *, company_name: str, domain: str,
                        risk_score: int, total_emails: int,
                        exposed_emails: int, total_instances: int,
                        date_str: str) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from app.services.pdf_brand import (DARK_BG, GRAY, WHITE, BORDER,
                                         MARGIN, FOOTER_H, PAGE_W, PAGE_H)

    W, H = A4
    M = MARGIN * mm
    rc = _risk_color(risk_score)

    canvas.saveState()

    # Background
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)

    # Top band
    BAND_H = 18 * mm
    band_y = H - BAND_H
    band_cy = H - BAND_H / 2
    from app.services.pdf_brand import _draw_band, DOC_COLOR
    doc_color = colors.HexColor(DOC_COLOR.get("darkweb", "#ef4444"))
    _draw_band(canvas, band_y=band_y, band_h=BAND_H, band_cy=band_cy,
               doc_type="darkweb", doc_color=doc_color,
               right_text="DOSSIER DARKWEB", right_sub=date_str[:10])

    # Title block
    tx = M + 7 * mm
    ty = H - 26 * mm
    canvas.setFillColor(rc)
    canvas.roundRect(M, H - 56 * mm, 3 * mm, 22 * mm, radius=1 * mm, fill=1, stroke=0)
    canvas.setFillColor(rc)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawString(tx, ty, "Dossier d'exposition")
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 17)
    canvas.drawString(tx, ty - 9 * mm, "Dark Web — Fuites de données")
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(tx, ty - 16 * mm, f"Généré le {date_str}  •  contact@cyberscanapp.com")

    # Company card
    card_y = H - 120 * mm
    card_h = 30 * mm
    card_w = W - 2 * M
    canvas.setFillColor(colors.HexColor("#111c30"))
    canvas.roundRect(M, card_y, card_w, card_h, radius=4 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(rc)
    canvas.setLineWidth(2 * mm)
    canvas.setLineCap(0)
    canvas.line(M + 4 * mm, card_y + card_h - 1 * mm,
                M + card_w - 4 * mm, card_y + card_h - 1 * mm)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 14)
    canvas.drawString(M + 6 * mm, card_y + card_h * 0.55, company_name)
    canvas.setFillColor(GRAY)
    canvas.setFont("Courier", 9)
    canvas.drawString(M + 6 * mm, card_y + 6 * mm, f"@{domain}")

    # Risk score + KPIs
    kpi_y = card_y - 55 * mm
    kpi_h = 50 * mm
    kpi_w = card_w

    canvas.setFillColor(colors.HexColor("#111c30"))
    canvas.roundRect(M, kpi_y, kpi_w, kpi_h, radius=4 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#1e2d4a"))
    canvas.setLineWidth(0.8)
    canvas.roundRect(M, kpi_y, kpi_w, kpi_h, radius=4 * mm, fill=0, stroke=1)

    left_w = kpi_w * 0.35
    cx = M + left_w / 2
    cy = kpi_y + kpi_h / 2 + 4 * mm
    r = 16 * mm

    canvas.setStrokeColor(colors.HexColor("#1e293b"))
    canvas.setLineWidth(11)
    canvas.setLineCap(0)
    p = canvas.beginPath()
    p.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)
    canvas.drawPath(p, stroke=1, fill=0)

    if risk_score > 0:
        fill_ext = min(risk_score / 100 * 180, 180)
        canvas.setStrokeColor(rc)
        canvas.setLineWidth(11)
        p2 = canvas.beginPath()
        p2.arc(cx - r, cy - r, cx + r, cy + r,
               startAng=180 - fill_ext, extent=fill_ext)
        canvas.drawPath(p2, stroke=1, fill=0)

    canvas.setFillColor(colors.HexColor("#141e30"))
    canvas.circle(cx, cy, r - 5.5 * mm, fill=1, stroke=0)
    canvas.setFillColor(rc)
    canvas.setFont("Helvetica-Bold", 26)
    canvas.drawCentredString(cx, cy - 4 * mm, f"{risk_score}%")
    canvas.setFillColor(rc)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawCentredString(cx, kpi_y + 9 * mm, _risk_label(risk_score))
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawCentredString(cx, kpi_y + 4.5 * mm, "Score de risque global")

    sep_x = M + left_w + 4 * mm
    canvas.setStrokeColor(colors.HexColor("#1e293b"))
    canvas.setLineWidth(0.8)
    canvas.line(sep_x, kpi_y + 8 * mm, sep_x, kpi_y + kpi_h - 8 * mm)

    clean = total_emails - exposed_emails
    kpis = [
        (str(total_emails), "Emails analysés", GRAY),
        (str(exposed_emails), "Emails exposés", RED if exposed_emails > 0 else GREEN),
        (str(clean), "Emails sains", GREEN),
        (str(total_instances), "Fuites cumulées", ORANGE if total_instances > 0 else GREEN),
    ]
    gx0 = sep_x + 4 * mm
    gw = kpi_w - left_w - 12 * mm
    cell_w = gw / 4 - 2 * mm
    cell_h = kpi_h - 10 * mm

    for i, (val, lbl, k_col) in enumerate(kpis):
        kx = gx0 + i * (cell_w + 2.5 * mm)
        ky = kpi_y + 5 * mm
        canvas.setFillColor(colors.HexColor("#1e293b"))
        canvas.roundRect(kx, ky, cell_w, cell_h, radius=2.5 * mm, fill=1, stroke=0)
        canvas.setStrokeColor(k_col)
        canvas.setLineWidth(2 * mm)
        canvas.setLineCap(0)
        canvas.line(kx + 2.5 * mm, ky + cell_h - 1 * mm,
                    kx + cell_w - 2.5 * mm, ky + cell_h - 1 * mm)
        canvas.setFillColor(k_col)
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawCentredString(kx + cell_w / 2, ky + cell_h * 0.50, val)
        canvas.setFillColor(GRAY)
        canvas.setFont("Helvetica", 6.5)
        canvas.drawCentredString(kx + cell_w / 2, ky + 3.5 * mm, lbl)

    # Footer
    from app.services.pdf_brand import FOOTER_H
    footer_y = FOOTER_H * mm
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(M, footer_y + 4 * mm, W - M, footer_y + 4 * mm)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(M, footer_y - 1 * mm, "CyberScan — confidentiel")
    canvas.drawCentredString(W / 2, footer_y - 1 * mm, "Page 1")
    canvas.drawRightString(W - M, footer_y - 1 * mm, date_str[:10])

    canvas.restoreState()


def generate_dossier_pdf(
    dossier: DarkwebDossier,
    targets: list[DarkwebDossierTarget],
) -> bytes:
    from reportlab.lib import colors

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=(210 * mm, 297 * mm),
        leftMargin=MARGIN * mm, rightMargin=MARGIN * mm,
        topMargin=(14 + 6) * mm, bottomMargin=(8 + 6) * mm,
    )
    styles = get_styles("darkweb")
    date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    risk_score = dossier.risk_score or 0

    exposed_targets = [t for t in targets if t.status == "exposed"]
    clean_targets = [t for t in targets if t.status == "clean"]

    try:
        top_sources = json.loads(dossier.top_sources_json or "[]")
    except Exception:
        top_sources = []

    def on_cover(canvas, doc):
        _draw_dossier_cover(
            canvas, doc,
            company_name=dossier.company_name,
            domain=dossier.domain,
            risk_score=risk_score,
            total_emails=dossier.total_emails,
            exposed_emails=dossier.exposed_emails,
            total_instances=dossier.total_breach_instances,
            date_str=date_str,
        )

    def on_page(canvas, doc):
        draw_page(canvas, doc, "darkweb", "DOSSIER DARKWEB", date_str)

    story = []

    # ── Section 1 : Emails exposés ────────────────────────────────────────────
    story.append(Paragraph("Emails exposés", styles["section"]))
    story.append(section_rule(doc.width, "darkweb"))

    if exposed_targets:
        table_data = [["Email", "Fuites", "Sources principales", "Données exposées"]]
        for t in exposed_targets:
            try:
                breaches = json.loads(t.breach_sources_json or "[]")
            except Exception:
                breaches = []
            sources_str = ", ".join(b.get("name", "") for b in breaches[:4])
            if len(breaches) > 4:
                sources_str += f" +{len(breaches) - 4}"
            all_dc: list[str] = []
            for b in breaches:
                all_dc.extend(b.get("data_classes", []))
            unique_dc = list(dict.fromkeys(all_dc))[:4]
            dc_str = ", ".join(unique_dc) if unique_dc else "—"
            row_color = RED if t.total_breaches >= 3 else YELLOW
            table_data.append([
                Paragraph(f'<font color="#{row_color.hexval()[1:]}">{t.email}</font>', styles["mono"]),
                Paragraph(f'<b>{t.total_breaches}</b>', styles["label"]),
                Paragraph(sources_str or "—", styles["small"]),
                Paragraph(dc_str, styles["small"]),
            ])
        tbl = Table(table_data, colWidths=[60 * mm, 18 * mm, 55 * mm, 45 * mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111c30")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#06b6d4")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.HexColor("#0f172a"), colors.HexColor("#111827")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#1e293b")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph("Aucun email exposé détecté.", styles["body"]))

    story.append(Spacer(1, 6 * mm))

    # ── Section 2 : Top sources de fuites ─────────────────────────────────────
    if top_sources:
        story.append(Paragraph("Sources de fuites les plus fréquentes", styles["section"]))
        story.append(section_rule(doc.width, "darkweb"))
        src_data = [["Source", "Occurrences"]]
        for s in top_sources[:8]:
            src_data.append([
                Paragraph(s["name"], styles["body"]),
                Paragraph(str(s["count"]), styles["label"]),
            ])
        src_tbl = Table(src_data, colWidths=[120 * mm, 30 * mm])
        src_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111c30")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#ef4444")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 7),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [colors.HexColor("#0f172a"), colors.HexColor("#111827")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#1e293b")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(src_tbl)
        story.append(Spacer(1, 6 * mm))

    # ── Section 3 : Recommandations ───────────────────────────────────────────
    story.append(Paragraph("Recommandations", styles["section"]))
    story.append(section_rule(doc.width, "darkweb"))

    recs = [
        ("Réinitialisation des mots de passe exposés",
         "Forcer un changement de mot de passe pour tous les comptes identifiés comme exposés. "
         "Prioriser les comptes avec 3 fuites ou plus."),
        ("Activation de l'authentification multi-facteur (MFA)",
         "Déployer le MFA sur tous les accès critiques (messagerie, VPN, outils métiers). "
         "Un mot de passe volé seul ne suffit plus à compromettre le compte."),
        ("Vérification des réutilisations de mots de passe",
         "Sensibiliser les collaborateurs concernés à ne pas réutiliser leurs mots de passe "
         "personnels sur les outils professionnels."),
        ("Surveillance continue",
         "Programmer une nouvelle analyse dans 30 jours pour détecter d'éventuelles nouvelles "
         "fuites. Mettre en place une alerte sur les adresses email critiques."),
        ("Formation et sensibilisation",
         "Intégrer les résultats de cette analyse dans le programme de sensibilisation à la "
         "cybersécurité de l'entreprise."),
    ]

    for title, body in recs:
        story.append(Paragraph(f"• {title}", styles["subsection"]))
        story.append(Paragraph(body, styles["body"]))
        story.append(Spacer(1, 2 * mm))

    doc.build(story, onFirstPage=on_cover, onLaterPages=on_page)
    return buf.getvalue()
