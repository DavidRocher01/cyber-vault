"""
pdf_brand.py — Shared visual identity for all Rocher Cybersécurité PDF reports.

Constants and helpers live here; the two large cover-page renderers have been
moved to pdf_covers.py and are re-exported below for backward compatibility.

Public API
----------
Constants  : DARK_BG, CARD_BG, BORDER, CYAN, GREEN, YELLOW, RED, ORANGE, GRAY, WHITE
             PAGE_W, PAGE_H, MARGIN, TOP_BAND, FOOTER_H
             DOC_COLOR
Functions  : score_color(pct)
             cat_score(cat_items, items)
             draw_page(canvas, doc, doc_type, title, subtitle)
             draw_compliance_cover(...)  — re-exported from pdf_covers
             draw_url_scan_cover(...)    — re-exported from pdf_covers
             section_rule(width, doc_type)
             get_styles(doc_type)
"""

from __future__ import annotations

from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import HRFlowable

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
DARK_BG = colors.HexColor("#0f172a")
CARD_BG = colors.HexColor("#1e293b")
HEADER_BG = colors.HexColor("#0c1a2e")
BORDER = colors.HexColor("#334155")

# Surfaces des pages de garde.
#
# Ces cinq teintes vivaient en LITTERAUX disperses dans pdf_covers (dix-sept
# appels a HexColor, neuf valeurs distinctes), alors meme que pdf_brand se
# presente comme « l'identite visuelle partagee ». Consequence : la palette
# n'etait pas reellement centralisee, et changer l'apparence des rapports
# revenait a traquer des valeurs a la main dans chaque fichier — ce qui rendait
# tout changement de theme illusoire.
#
# Trois des valeurs dupliquaient en plus STATUS_BG, defini quelques lignes plus
# bas dans ce meme module.
CARTE_BG = colors.HexColor("#111c30")  # fond des grandes cartes de synthese
CARTE_BORDURE = colors.HexColor("#1e2d4a")  # liseré de ces cartes
JAUGE_PISTE = colors.HexColor("#1e293b")  # piste non remplie des jauges et barres
JAUGE_CREUX = colors.HexColor("#141e30")  # disque central des jauges circulaires
TUILE_BG = colors.HexColor("#0e1623")  # fond des petites tuiles (domaines, infos)
CYAN = colors.HexColor("#06b6d4")
GREEN = colors.HexColor("#4ade80")
YELLOW = colors.HexColor("#facc15")
RED = colors.HexColor("#f87171")
ORANGE = colors.HexColor("#fb923c")
GRAY = colors.HexColor("#94a3b8")
WHITE = colors.white

# Texte pose SUR LE BANDEAU, dont le fond reste sombre quel que soit le thema.
#
# `WHITE` jouait deux roles a la fois : « couleur du texte courant » et
# « couleur du texte du bandeau ». Tant que la page etait sombre, les deux
# coincidaient. Un rendu du meme rapport sur fond clair l'a montre tout de
# suite : en inversant `WHITE` pour le texte de page, la marque devenait noire
# sur le bandeau reste sombre, donc illisible. Les deux roles sont desormais
# distincts. Valeur identique a WHITE aujourd'hui : aucun changement visuel.
TEXTE_BANDEAU = colors.white

# Per-document-type accent colour
DOC_COLOR: dict[str, str] = {
    "nis2": "#8b5cf6",
    "iso27001": "#8b5cf6",
    "url": "#f97316",
    "scan": "#3b82f6",
    "test": "#10b981",
    "darkweb": "#ef4444",
    "phishing": "#f59e0b",
}

# Cover accent triples: (main, mid, dark-bg) hex strings
_COVER_ACCENT: dict[str, tuple[str, str, str]] = {
    "nis2": ("#8b5cf6", "#5b21b6", "#13102a"),
    "iso27001": ("#8b5cf6", "#5b21b6", "#13102a"),
    "url": ("#f97316", "#c2410c", "#1a0700"),
    "scan": ("#3b82f6", "#1d4ed8", "#0c1a2e"),
    "darkweb": ("#ef4444", "#b91c1c", "#1a0505"),
    "phishing": ("#f59e0b", "#b45309", "#1a1000"),
}

# Lighter header-title colour per doc type (right-zone text in band)
_BAND_TITLE_COLOR: dict[str, str] = {
    "nis2": "#c4b5fd",
    "iso27001": "#c4b5fd",
    "url": "#fed7aa",
    "scan": "#bae6fd",
    "darkweb": "#fca5a5",
    "phishing": "#fde68a",
}

# Short label shown in the band right zone for compliance covers
_BAND_COVER_LABEL: dict[str, str] = {
    "nis2": "DIRECTIVE NIS2",
    "iso27001": "ISO 27001:2022",
}

# Status badge styling (shared by compliance generators)
STATUS_COLOR = {"compliant": GREEN, "partial": YELLOW, "non_compliant": RED, "na": GRAY}
STATUS_LABEL = {
    "compliant": "Conforme",
    "partial": "Partiel",
    "non_compliant": "Non conforme",
    "na": "N/A",
}
STATUS_BG = {
    "compliant": colors.HexColor("#052e16"),
    "partial": colors.HexColor("#1c1400"),
    "non_compliant": colors.HexColor("#2d0a0a"),
    "na": colors.HexColor("#111827"),
}

# Layout constants
PAGE_W, PAGE_H = A4
MARGIN = 15  # mm (integer — multiply by `mm` to get points)
TOP_BAND = 14  # mm — content-page band height
FOOTER_H = 8  # mm — footer area height

SITE_EMAIL = "contact@rochercybersecurite.com"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _accent_cols(doc_type: str) -> tuple:
    """Return (main, mid, bg) as Color objects for the given doc type."""
    if doc_type in _COVER_ACCENT:
        m, mid, bg = _COVER_ACCENT[doc_type]
        return colors.HexColor(m), colors.HexColor(mid), colors.HexColor(bg)
    h = DOC_COLOR.get(doc_type, "#06b6d4")
    return colors.HexColor(h), colors.HexColor(h), DARK_BG


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def score_color(pct: int):
    """Return GREEN / YELLOW / RED based on score percentage."""
    if pct >= 80:
        return GREEN
    if pct >= 50:
        return YELLOW
    return RED


def cat_score(cat_items: list, items: dict) -> int:
    """Compute a category compliance score as a 0-100 integer."""
    scorable = [it for it in cat_items if items.get(it["id"], "non_compliant") != "na"]
    if not scorable:
        return 0
    pts = sum(
        2
        if items.get(it["id"], "non_compliant") == "compliant"
        else 1
        if items.get(it["id"], "non_compliant") == "partial"
        else 0
        for it in scorable
    )
    return round(pts / (len(scorable) * 2) * 100)


# ---------------------------------------------------------------------------
# Shared band drawing helper (used by draw_page and cover renderers)
# ---------------------------------------------------------------------------


def ajuster_texte(
    canvas,
    texte: str,
    police: str,
    taille: float,
    largeur_max: float,
    *,
    taille_mini: float = 5.5,
) -> tuple[str, float]:
    """Fait tenir `texte` dans `largeur_max` : reduit la police, tronque en dernier recours.

    Renvoie (texte a dessiner, taille de police a utiliser).

    Remplace les troncatures au NOMBRE DE CARACTERES qui trainaient dans les
    generateurs (`lbl if len(lbl) <= 26 else lbl[:25] + "…"`). Un compte de
    caracteres ignore la largeur reelle des glyphes : « Formation &
    sensibilisation » etait coupe alors qu'il tenait, et un libelle de 26
    caracteres larges aurait deborde sans etre coupe.
    """
    if not texte:
        return texte, taille
    while taille > taille_mini and canvas.stringWidth(texte, police, taille) > largeur_max:
        taille -= 0.25
    if canvas.stringWidth(texte, police, taille) <= largeur_max:
        return texte, taille
    # Toujours trop long a la taille plancher : on coupe, en mesurant.
    coupe = texte
    while coupe and canvas.stringWidth(coupe + "…", police, taille) > largeur_max:
        coupe = coupe[:-1]
    return (coupe + "…") if coupe else texte[:1], taille


def ajuster_paire(
    canvas,
    gauche: str,
    droite: str,
    police: str,
    taille_gauche: float,
    taille_droite: float,
    largeur_dispo: float,
    *,
    ecart_min: float,
    facteur_mini: float = 0.55,
) -> tuple[float, float, float, float]:
    """Fait cohabiter deux textes opposes sur une meme ligne sans chevauchement.

    Renvoie (taille_gauche, taille_droite, largeur_gauche, largeur_droite) apres
    reduction PROPORTIONNELLE si l'ensemble deborde — l'equilibre visuel entre
    les deux est ainsi conserve.

    Extrait pour etre partage : le bandeau de `_draw_band` et celui du rapport en
    marque blanche etaient deux copies du meme dessin. Seule la premiere avait
    ete corrigee, et le rapport marque blanche — celui qu'un consultant presente
    a SON client sous SA marque — restait illisible, d'autant que la longueur du
    nom de societe y est arbitraire.
    """
    lg = canvas.stringWidth(gauche, police, taille_gauche)
    ld = canvas.stringWidth(droite, police, taille_droite)
    budget = largeur_dispo - ecart_min
    if lg + ld > budget and lg + ld > 0:
        facteur = max(budget / (lg + ld), facteur_mini)
        taille_gauche *= facteur
        taille_droite *= facteur
        lg = canvas.stringWidth(gauche, police, taille_gauche)
        ld = canvas.stringWidth(droite, police, taille_droite)
    return taille_gauche, taille_droite, lg, ld


def base_sous_plafond(base: float, taille: float, police: str, plafond: float) -> float:
    """Abaisse `base` jusqu'a ce que l'ascendante de la police tienne sous `plafond`.

    Sans cela, un titre en capitales ACCENTUEES voit son accent rogne par le bord
    du bandeau — defaut invisible tant que les chaines etaient saisies sans
    accents, flagrant une fois celles-ci corrigees.
    """
    ascendante = pdfmetrics.getAscent(police, taille)
    return min(base, plafond - ascendante)


def _draw_band(
    canvas,
    *,
    band_y: float,
    band_h: float,
    band_cy: float,
    doc_type: str,
    doc_color,
    right_text: str,
    right_sub: str,
) -> None:
    """Draw the top accent band (flat dark bg, stripe, logo, wordmark, right text)."""
    M = MARGIN * mm
    W = PAGE_W

    # Band background
    canvas.setFillColor(colors.HexColor("#0f0a28"))
    canvas.rect(0, band_y, W, band_h, fill=1, stroke=0)

    # Left stripe (2 mm)
    canvas.setFillColor(doc_color)
    canvas.rect(0, band_y, 2 * mm, band_h, fill=1, stroke=0)

    # Bottom border
    canvas.setStrokeColor(doc_color)
    canvas.setLineWidth(2.5)
    canvas.line(0, band_y, W, band_y)

    # Circle logo "CS"
    logo_cx = M + 5 * mm
    logo_r = band_h * 0.22
    canvas.setFillColor(CYAN)
    canvas.circle(logo_cx, band_cy, logo_r, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#22d3ee"))
    canvas.circle(
        logo_cx - logo_r * 0.14,
        band_cy + logo_r * 0.14,
        logo_r * 0.55,
        fill=1,
        stroke=0,
    )
    canvas.setFillColor(colors.HexColor("#083344"))
    canvas.setFont("Helvetica-Bold", band_h * 0.33)
    canvas.drawCentredString(logo_cx, band_cy - band_h * 0.07, "CS")

    # ── Marque a gauche, type de document a droite ────────────────────────────
    #
    # Les deux textes etaient dessines a taille fixe, sans qu'aucun ne mesure sa
    # largeur : ils se chevauchaient sur TOUTES les pages de TOUS les rapports
    # (« Rocher Cybersécurité » recouvrant « DIRECTIVE NIS2 », « CONFORMITÉ
    # NIS2 », « RAPPORT D'ANALYSE D'URL »...). Le `rule_x0 = wm_x + 52` etait une
    # estimation en dur de la largeur du nom, tres en dessous du reel.
    #
    # On mesure desormais, et si l'ensemble deborde on reduit les deux polices
    # PROPORTIONNELLEMENT : l'equilibre visuel est conserve, et aucun texte
    # n'est tronque ni recouvert.
    wm_x = logo_cx + logo_r + 2.5 * mm
    wm_texte = "Rocher Cybersécurité"

    taille_wm, taille_rt, largeur_wm, largeur_rt = ajuster_paire(
        canvas,
        wm_texte,
        right_text,
        "Helvetica-Bold",
        band_h * 0.62,
        band_h * 0.50,
        (W - M) - wm_x,
        ecart_min=6 * mm,
    )

    canvas.setFillColor(TEXTE_BANDEAU)
    canvas.setFont("Helvetica-Bold", taille_wm)
    canvas.drawString(wm_x, band_cy - band_h * 0.12, wm_texte)

    # Filet de liaison, borne par les largeurs REELLES des deux textes.
    rule_x0 = wm_x + largeur_wm + 2 * mm
    rule_x1 = (W - M) - largeur_rt - 2 * mm
    if rule_x1 > rule_x0 + 8:
        canvas.setStrokeColor(colors.HexColor("#2d1b69"))
        canvas.setLineWidth(0.5)
        canvas.line(rule_x0, band_cy, rule_x1, band_cy)

    # Right zone: stacked title + sub
    #
    # La ligne de base est abaissee jusqu'a ce que l'ASCENDANTE de la police
    # tienne sous le bord du bandeau. Sans ca, un titre en capitales accentuees
    # (« CONFORMITÉ NIS2 ») voyait son accent rogne par le bord : invisible tant
    # que les chaines etaient saisies sans accents, flagrant une fois corrigees.
    base_titre = base_sous_plafond(
        band_cy + band_h * 0.10,
        taille_rt,
        "Helvetica-Bold",
        band_y + band_h - 1.2 * mm,
    )

    right_col = colors.HexColor(_BAND_TITLE_COLOR.get(doc_type, "#e2e8f0"))
    canvas.setFillColor(right_col)
    canvas.setFont("Helvetica-Bold", taille_rt)
    canvas.drawRightString(W - M, base_titre, right_text)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.setFont("Helvetica", band_h * 0.38)
    canvas.drawRightString(W - M, band_cy - band_h * 0.28, right_sub)


# ---------------------------------------------------------------------------
# Content-page template
# ---------------------------------------------------------------------------


def draw_page(canvas, doc, doc_type: str, title: str, subtitle: str = "") -> None:
    """
    Render the common dark page background, top band, and footer.
    Call as onFirstPage / onLaterPages in SimpleDocTemplate.build().
    """
    doc_color = colors.HexColor(DOC_COLOR.get(doc_type, "#06b6d4"))
    today_str = datetime.now().strftime("%d/%m/%Y")
    M = MARGIN * mm
    BAND_H = TOP_BAND * mm
    band_y = PAGE_H - BAND_H
    band_cy = PAGE_H - BAND_H / 2

    canvas.saveState()

    # Full-page dark background
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    _draw_band(
        canvas,
        band_y=band_y,
        band_h=BAND_H,
        band_cy=band_cy,
        doc_type=doc_type,
        doc_color=doc_color,
        right_text=title.upper(),
        right_sub=today_str,
    )

    # Footer
    footer_y = FOOTER_H * mm
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(M, footer_y, PAGE_W - M, footer_y)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(M, footer_y - 5 * mm, "Rocher Cybersécurité — confidentiel")
    canvas.drawCentredString(PAGE_W / 2, footer_y - 5 * mm, f"Page {doc.page}")
    canvas.drawRightString(PAGE_W - M, footer_y - 5 * mm, today_str)

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Cover-page renderers — moved to pdf_covers.py, re-exported for compat
# ---------------------------------------------------------------------------
# These imports must come AFTER all constants above are defined (pdf_covers
# imports from this module).
from app.services.pdf_covers import (  # noqa: E402, F401
    draw_compliance_cover,
    draw_url_scan_cover,
)

# ---------------------------------------------------------------------------
# Section rule helper
# ---------------------------------------------------------------------------


def section_rule(width, doc_type: str) -> HRFlowable:
    """Return a coloured HRFlowable matching the document type."""
    hex_color = DOC_COLOR.get(doc_type, "#06b6d4")
    base = colors.HexColor(hex_color)
    r, g, b = base.red, base.green, base.blue
    bg_r, bg_g, bg_b = DARK_BG.red, DARK_BG.green, DARK_BG.blue
    alpha = 0.6
    blended = colors.Color(
        r * alpha + bg_r * (1 - alpha),
        g * alpha + bg_g * (1 - alpha),
        b * alpha + bg_b * (1 - alpha),
    )
    return HRFlowable(width=width, thickness=0.8, color=blended, spaceAfter=4, spaceBefore=2)


# ---------------------------------------------------------------------------
# Shared paragraph styles
# ---------------------------------------------------------------------------


def get_styles(doc_type: str) -> dict[str, ParagraphStyle]:
    doc_hex = DOC_COLOR.get(doc_type, "#06b6d4")
    doc_color = colors.HexColor(doc_hex)

    def _s(name: str, **kw) -> ParagraphStyle:
        defaults = dict(fontName="Helvetica", textColor=WHITE, fontSize=9, spaceAfter=2)
        defaults.update(kw)
        return ParagraphStyle(name, **defaults)

    return {
        "title": _s(
            f"brand_title_{doc_type}",
            fontSize=20,
            fontName="Helvetica-Bold",
            textColor=WHITE,
        ),
        "subtitle": _s(f"brand_subtitle_{doc_type}", fontSize=10, textColor=GRAY),
        "section": _s(
            f"brand_section_{doc_type}",
            fontSize=12,
            fontName="Helvetica-Bold",
            textColor=doc_color,
            spaceBefore=12,
            spaceAfter=4,
        ),
        "subsection": _s(
            f"brand_subsection_{doc_type}",
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=WHITE,
            spaceBefore=8,
            spaceAfter=3,
        ),
        "body": _s(f"brand_body_{doc_type}", fontSize=9, textColor=colors.HexColor("#cbd5e1")),
        "small": _s(f"brand_small_{doc_type}", fontSize=7, textColor=GRAY),
        "mono": _s(f"brand_mono_{doc_type}", fontSize=8, fontName="Courier", textColor=CYAN),
        "label": _s(
            f"brand_label_{doc_type}",
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=WHITE,
        ),
        "badge_pass": _s(
            f"brand_badge_pass_{doc_type}",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=GREEN,
        ),
        "badge_fail": _s(
            f"brand_badge_fail_{doc_type}",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=RED,
        ),
        "badge_warn": _s(
            f"brand_badge_warn_{doc_type}",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=YELLOW,
        ),
        "badge_gray": _s(
            f"brand_badge_gray_{doc_type}",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=GRAY,
        ),
    }
