"""doctemplate.py — AuditDocTemplate (page frames + branded footer)."""

from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageTemplate,
)

from .theme import (
    COLOR_BG,
    COLOR_BORDER,
    COLOR_PRIMARY,
    COLOR_WHITE,
)


# ---------------------------------------------------------------------------
# Page template with footer
# ---------------------------------------------------------------------------
class AuditDocTemplate(BaseDocTemplate):
    """Custom doc template that renders a footer on every page."""

    def __init__(self, filename: str, report_date: str, **kwargs):
        super().__init__(filename, **kwargs)
        self.report_date = report_date
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="main",
        )
        template = PageTemplate(id="main", frames=[frame], onPage=self._draw_footer)
        self.addPageTemplates([template])

    def _draw_footer(self, canvas, doc):
        """Render dark background, top band (scan blue) and footer on every page."""
        page_w, page_h = A4

        canvas.saveState()

        # ── Full-page dark background ─────────────────────────────────────────
        canvas.setFillColor(COLOR_BG)  # DARK_BG #0f172a
        canvas.rect(0, 0, page_w, page_h, fill=1, stroke=0)

        # ── Top band (scan blue, #3b82f6 at 30 % opacity) ────────────────────
        scan_color = colors.HexColor("#3b82f6")
        r, g, b = scan_color.red, scan_color.green, scan_color.blue
        band_h = 10 * mm
        band_y = page_h - band_h

        canvas.setFillColorRGB(r, g, b, alpha=0.30)
        canvas.rect(0, band_y, page_w, band_h, fill=1, stroke=0)

        # Top edge line (2 px)
        canvas.setStrokeColor(scan_color)
        canvas.setLineWidth(2)
        canvas.line(0, page_h - 1, page_w, page_h - 1)

        # "CS" logo mark
        left_margin = doc.leftMargin
        logo_size = 6 * mm
        logo_x = left_margin
        logo_y = band_y + (band_h - logo_size) / 2
        canvas.setFillColor(COLOR_PRIMARY)  # CYAN
        canvas.roundRect(
            logo_x, logo_y, logo_size, logo_size, radius=1.5 * mm, fill=1, stroke=0
        )
        canvas.setFillColor(COLOR_WHITE)
        canvas.setFont("Helvetica-Bold", 6)
        canvas.drawCentredString(logo_x + logo_size / 2, logo_y + 1.5 * mm, "CS")

        # "Rocher Cybersécurité" label
        text_x = logo_x + logo_size + 3 * mm
        mid_y = band_y + band_h / 2 - 1.5 * mm
        canvas.setFillColor(COLOR_WHITE)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(text_x, mid_y, "Rocher Cybersécurité")

        # Pipe separator
        sep_x = text_x + 60
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.setFont("Helvetica", 9)
        canvas.drawString(sep_x, mid_y, "|")

        # Document title
        canvas.setFillColor(scan_color)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(sep_x + 8, mid_y, "Rapport d'Audit")

        # Date right-aligned in band
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(
            page_w - left_margin, mid_y, self.report_date.split(" ")[0]
        )

        # ── Footer ────────────────────────────────────────────────────────────
        footer_y = 8 * mm
        canvas.setStrokeColor(COLOR_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(left_margin, footer_y, left_margin + doc.width, footer_y)

        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.setFont("Helvetica", 7)

        canvas.drawString(
            left_margin, footer_y - 5 * mm, "Rocher Cybersécurité \u2014 confidentiel"
        )
        canvas.drawCentredString(page_w / 2, footer_y - 5 * mm, f"Page {doc.page}")
        canvas.drawRightString(
            left_margin + doc.width, footer_y - 5 * mm, self.report_date
        )

        canvas.restoreState()
