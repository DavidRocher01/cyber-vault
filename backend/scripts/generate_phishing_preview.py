#!/usr/bin/env python3
"""Generate a combined HTML preview of all 13 phishing email templates."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.phishing_service import (  # noqa: E402
    _dynamic_ctx,
    _tpl_bank,
    _tpl_ceo_fraud,
    _tpl_fake_invoice,
    _tpl_hr_document,
    _tpl_invoice_pdf,
    _tpl_it_password,
    _tpl_it_ticket,
    _tpl_o365,
    _tpl_parcel,
    _tpl_prize,
    _tpl_sharepoint,
    _tpl_teams,
    _tpl_vpn_update,
)

TEMPLATES = [
    ("CEO Fraud — Virement urgent",           "ceo-fraud",         _tpl_ceo_fraud),
    ("Microsoft 365 — Connexion suspecte",    "o365-credentials",  _tpl_o365),
    ("Facture impayée — Relance comptabilité","fake-invoice",       _tpl_fake_invoice),
    ("Alerte bancaire — Transaction suspecte","bank-phishing",      _tpl_bank),
    ("Colis non livré — Réexpédition",        "parcel-tracking",   _tpl_parcel),
    ("DSI — Renouvellement mot de passe",     "it-password",       _tpl_it_password),
    ("RH — Carte cadeau gagnée",              "prize",             _tpl_prize),
    ("Signature électronique requise",        "invoice-pdf",       _tpl_invoice_pdf),
    ("Vulnérabilité VPN critique",            "vpn-update",        _tpl_vpn_update),
    ("Document RH confidentiel",              "hr-document",       _tpl_hr_document),
    ("Notification Microsoft Teams",          "teams-message",     _tpl_teams),
    ("Partage de document SharePoint",        "sharepoint-share",  _tpl_sharepoint),
    ("Ticket Helpdesk DSI — Haute priorité",  "it-ticket",         _tpl_it_ticket),
]


class _MockTarget:
    id = 42
    first_name = "Marie"
    last_name = "Martin"
    department = "Direction"


_PIXEL = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
_URL = "javascript:void(0)"


def _extract_body(html: str) -> str:
    m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL)
    return m.group(1) if m else html


def main() -> None:
    mock = _MockTarget()
    pages: list[str] = []

    total = len(TEMPLATES)
    for i, (label, key, fn) in enumerate(TEMPLATES, 1):
        ctx = _dynamic_ctx(mock, key)
        html = fn("Marie Martin", _URL, _PIXEL, ctx)
        body = _extract_body(html)
        pages.append(f"""
<div class="page">
  <div class="page-header">
    <span class="badge">{i}/{total}</span>
    <span class="title">{label}</span>
    <span class="key">{key}</span>
  </div>
  <div class="email-wrapper">{body}</div>
</div>""")

    document = """\
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<title>CyberScan — Templates phishing</title>
<style>
  @page { size: A4; margin: 12mm; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #e8eaed; font-family: Arial, sans-serif; }
  .page {
    page-break-after: always;
    background: #f1f3f4;
    padding: 14px;
    min-height: calc(297mm - 24mm);
  }
  .page:last-child { page-break-after: avoid; }
  .page-header {
    display: flex; align-items: center; gap: 10px;
    padding-bottom: 10px; margin-bottom: 14px;
    border-bottom: 2px solid #dadce0;
  }
  .badge {
    background: #1a73e8; color: #fff; border-radius: 50%;
    width: 28px; height: 28px; display: flex; align-items: center;
    justify-content: center; font-size: 11px; font-weight: 700;
    flex-shrink: 0;
  }
  .title { font-size: 15px; font-weight: 700; color: #202124; flex: 1; }
  .key {
    font-size: 11px; color: #5f6368; background: #fff;
    padding: 2px 8px; border-radius: 12px; border: 1px solid #dadce0;
  }
  .email-wrapper { max-width: 600px; margin: 0 auto; }
  .email-wrapper table { max-width: 100% !important; width: 100% !important; }
  a { pointer-events: none; }
</style>
</head>
<body>
""" + "\n".join(pages) + "\n</body>\n</html>"

    out = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "phishing_templates_preview.html",
    )
    out = os.path.normpath(out)
    with open(out, "w", encoding="utf-8") as f:
        f.write(document)
    print(f"HTML généré : {out}")


if __name__ == "__main__":
    main()
