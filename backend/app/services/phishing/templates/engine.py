"""Moteur : wrappers HTML + contexte dynamique des scenarios."""

import random
from datetime import UTC, datetime
from typing import Any


def _email_wrap(
    preheader: str,
    brand_bg: str,
    brand_html: str,
    body_html: str,
    footer_html: str = "",
) -> str:
    if not footer_html:
        footer_html = '<p style="color:#aaa;font-size:11px;margin:0">Message automatique — ne pas répondre.</p>'
    filler = "&nbsp;&#8203;" * 40
    return (
        '<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title></title></head>'
        f'<body style="margin:0;padding:0;background:#f1f3f4;font-family:Arial,Helvetica,sans-serif">'
        f'<span style="display:none;max-height:0;overflow:hidden;font-size:1px;line-height:1px;color:#f1f3f4">{preheader}{filler}</span>'
        '<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f3f4;padding:24px 0">'
        '<tr><td align="center">'
        '<table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border-radius:4px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.12)">'
        f'<tr><td style="background:{brand_bg};padding:18px 30px">{brand_html}</td></tr>'
        f'<tr><td style="padding:30px 30px 24px">{body_html}</td></tr>'
        f'<tr><td style="background:#f8f9fa;padding:18px 30px;border-top:1px solid #e8eaed">{footer_html}</td></tr>'
        "</table></td></tr></table></body></html>"
    )


def _attachment_badge(filename: str, filetype: str = "PDF") -> str:
    icons = {"PDF": "📄", "XLSX": "📊", "DOCX": "📝", "EXE": "📦"}
    icon = icons.get(filetype, "📎")
    # Returns inline HTML — safe to embed in an f-string via {_attachment_badge(...)}
    return (
        f'<table width="100%" cellpadding="12" cellspacing="0" '
        f'style="border:1px solid #e0e0e0;border-radius:4px;background:#fafafa;margin:0 0 20px">'
        f'<tr><td style="width:32px;vertical-align:middle;padding-right:12px;font-size:22px">{icon}</td>'
        f'<td style="vertical-align:middle">'
        f'<span style="font-size:13px;font-weight:600;color:#333">{filename}</span>'
        f' <span style="font-size:12px;color:#888">· {filetype}</span></td>'
        f"</tr></table>"
    )


def _dynamic_ctx(target: Any, scenario_key: str) -> dict[str, Any]:
    rng = random.Random(f"{getattr(target, 'id', 0) or 0}-{scenario_key}")
    now = datetime.now(UTC)
    y = now.year
    months = [
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]
    day = rng.randint(5, 25)
    month = months[(now.month) % 12]
    dept = (getattr(target, "department", None) or "").strip()
    ab_variant = (getattr(target, "id", 0) or 0) % 2
    teams_sender = rng.choice(
        [
            "Alexandre Martin",
            "Sophie Durand",
            "Pierre Moreau",
            "Claire Bernard",
            "Thomas Laurent",
        ]
    )
    teams_channel = rng.choice(
        ["Général", "Projet Q3", "Infrastructure IT", dept or "Équipe", "Direction"]
    )
    teams_preview = rng.choice(
        [
            "Peux-tu regarder ce document rapidement ?",
            "J'ai besoin de ton avis sur ce point urgent.",
            "Merci de valider avant la réunion.",
            "Important — action requise de ta part.",
        ]
    )
    sp_sender = rng.choice(["Service IT", "Direction Générale", "RH", "Comptabilité"])
    sp_file, sp_size = rng.choice(
        [
            ("Budget_2025_prévisionnel.xlsx", "Excel · 2,1 Mo"),
            ("Procédure_accès_distant.pdf", "PDF · 856 Ko"),
            ("Rapport_audit_interne.docx", "Word · 1,4 Mo"),
            ("Plan_continuité_activité.pptx", "PowerPoint · 3,8 Mo"),
            ("Organigramme_2025.pdf", "PDF · 412 Ko"),
        ]
    )
    ticket_num = f"TK-{rng.randint(10000, 99999)}"
    ticket_subject = rng.choice(
        [
            "Renouvellement certificat SSL",
            "Migration Active Directory",
            "Mise à jour politique de sécurité",
            "Audit accès privilégiés",
            "Configuration MFA obligatoire",
        ]
    )
    return {
        "invoice_ref": f"INV-{y}-{rng.randint(1000, 9999)}",
        "invoice_amount": f"{rng.randint(500, 9_999):,}".replace(",", " ") + " €",
        "ceo_amount": rng.choice(["15 000 €", "22 000 €", "35 000 €", "48 500 €"]),
        "ceo_deadline": rng.choice(["avant 14h00", "avant 16h00", "avant 17h30", "avant 18h00"]),
        "bank_last4": str(rng.randint(1000, 9999)),
        "bank_name": rng.choice(
            [
                "Société Générale",
                "BNP Paribas",
                "La Banque Postale",
                "Crédit Mutuel",
                "CIC",
            ]
        ),
        "bank_amount": f"{rng.randint(450, 3_500):,}".replace(",", " ") + " €",
        "parcel_ref": f"FR{rng.randint(1_000_000_000, 9_999_999_999)}",
        "parcel_fee": f"{rng.choice([1.80, 2.50, 2.90, 3.20]):.2f} €",
        "parcel_carrier": rng.choice(["Chronopost", "Colissimo", "DPD France"]),
        "cve_id": f"CVE-{y}-{rng.randint(10_000, 99_999)}",
        "cvss": f"{rng.uniform(9.0, 9.9):.1f}",
        "prize_amount": rng.choice([100, 150, 200, 250]),
        "doc_ref": f"DOC-{y}-{rng.randint(100, 999)}",
        "doc_deadline": rng.choice(
            [f"ce vendredi {day} {month}", "lundi prochain", f"le {day} {month}"]
        ),
        "salary_pct": rng.choice(["2.8 %", "3.1 %", "3.4 %", "4.0 %"]),
        "pw_days": rng.choice(["2 jours", "3 jours", "5 jours", "ce soir à minuit"]),
        "o365_device": rng.choice(
            [
                "iPhone 15",
                "Windows 11 PC",
                "MacBook Pro",
                "Samsung Galaxy S24",
                "iPad Pro",
            ]
        ),
        "o365_location": rng.choice(
            [
                "Amsterdam, Pays-Bas",
                "Francfort, Allemagne",
                "Londres, Royaume-Uni",
                "Dublin, Irlande",
                "Zurich, Suisse",
            ]
        ),
        "dept": dept,
        "ab_variant": ab_variant,
        "teams_sender": teams_sender,
        "teams_initial": teams_sender[0].upper(),
        "teams_channel": teams_channel,
        "teams_preview": teams_preview,
        "sp_sender": sp_sender,
        "sp_initial": sp_sender[0].upper(),
        "sp_file": sp_file,
        "sp_size": sp_size,
        "ticket_num": ticket_num,
        "ticket_subject": ticket_subject,
    }
