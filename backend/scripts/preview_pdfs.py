#!/usr/bin/env python3
"""Genere un echantillon de CHAQUE type de PDF, avec des donnees realistes.

POURQUOI CE SCRIPT EXISTE
Le 2026-07-31, trois defauts visuels vivaient depuis longtemps dans les
rapports — bandeau d'en-tete dont la marque recouvrait le titre sur TOUTES les
pages, accents manquants dans les chaines en dur, libelles tronques au nombre
de caracteres. Aucun n'etait detectable en lisant le code ni en lancant les
tests : ils ne se voient qu'en REGARDANT le PDF. Il n'existait aucun moyen
simple d'en produire un.

Usage
-----
    python scripts/preview_pdfs.py                 # tous, en PDF
    python scripts/preview_pdfs.py nis2 devis      # seulement ceux-la
    python scripts/preview_pdfs.py --png           # + rendu PNG page par page
    python scripts/preview_pdfs.py --liste         # noms disponibles

Le rendu PNG demande `pypdfium2` (pip install pypdfium2). Il est volontairement
optionnel : ce n'est pas une dependance du projet, seulement un confort local.

Les echantillons n'ont AUCUNE valeur de test automatique — ils ne verifient
rien. Ils servent a poser l'oeil sur le resultat, ce qu'aucun test ne fait.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

_DATE = datetime(2026, 7, 31, 9, 0, tzinfo=UTC)
_CLIENT = "Menuiserie Delorme SAS"
_DOMAINE = "delorme-menuiserie.fr"
_EMAIL = "dirigeant@delorme-menuiserie.fr"


def _statuts(categories: list[dict]) -> dict[str, str]:
    """Repartit les quatre statuts sur le referentiel, pour exercer tous les rendus."""
    ordre = ["compliant", "partial", "non_compliant", "na"]
    return {
        it["id"]: ordre[(i + j) % 4]
        for i, cat in enumerate(categories)
        for j, it in enumerate(cat["items"])
    }


# ── Echantillons ─────────────────────────────────────────────────────────────


def ech_nis2() -> bytes:
    from app.api.v1.endpoints.nis2 import NIS2_CATEGORIES
    from app.services.nis2_pdf import generate_nis2_pdf

    return generate_nis2_pdf(NIS2_CATEGORIES, _statuts(NIS2_CATEGORIES), 62, _DATE, _EMAIL)


def ech_nis2_auditeur() -> bytes:
    from app.api.v1.endpoints.nis2 import NIS2_CATEGORIES
    from app.services.nis2_auditor_pdf import generate_nis2_auditor_pdf

    return generate_nis2_auditor_pdf(
        categories=NIS2_CATEGORIES,
        items=_statuts(NIS2_CATEGORIES),
        score=62,
        user_email=_EMAIL,
        updated_at=_DATE,
        company_name=_CLIENT,
    )


def ech_iso27001() -> bytes:
    from app.api.v1.endpoints.iso27001 import ISO27001_CATEGORIES as CATS
    from app.services.iso27001_pdf import generate_iso27001_pdf

    return generate_iso27001_pdf(CATS, _statuts(CATS), 71, _DATE, _EMAIL)


def ech_devis() -> bytes:
    from app.services.quote_pdf import generate_quote_pdf

    return generate_quote_pdf(
        quote_number="DEV-2026-0042",
        issue_date=date(2026, 7, 31),
        validity_days=30,
        client_name=_CLIENT,
        client_email="contact@delorme-menuiserie.fr",
        client_address="12 rue des Artisans\n35000 Rennes",
        subject="Audit de sécurité et mise en conformité NIS2",
        items=[
            {
                "description": "Audit de sécurité initial (10 sites)",
                "quantity": 1,
                "unit_price_cents": 149000,
            },
            {
                "description": "Accompagnement conformité NIS2",
                "quantity": 3,
                "unit_price_cents": 49000,
            },
            {
                "description": "Sensibilisation — 30 apprenants",
                "quantity": 1,
                "unit_price_cents": 19900,
            },
        ],
        total_cents=149000 + 3 * 49000 + 19900,
    )


def ech_facture() -> bytes:
    from app.services.invoice_pdf import generate_invoice_pdf

    return generate_invoice_pdf(
        invoice_number="FAC-2026-0117",
        issue_date=date(2026, 7, 31),
        client_name=_CLIENT,
        client_email="contact@delorme-menuiserie.fr",
        client_address="12 rue des Artisans\n35000 Rennes",
        description="Accompagnement conformité NIS2 — juillet 2026",
        amount_cents=49000,
    )


def ech_scan_url() -> bytes:
    from app.services.url_scan_pdf import generate_url_scan_pdf

    return generate_url_scan_pdf(
        {
            "url": f"https://{_DOMAINE}/contact",
            "verdict": "suspicious",
            "threat_score": 46,
            "created_at": _DATE,
            "redirects": [f"https://{_DOMAINE}/contact", "https://tracking.example.net/r/8f2"],
            "ssl_valid": True,
            "findings": [
                {
                    "severity": "high",
                    "title": "Redirection vers un domaine tiers",
                    "detail": "La page redirige vers un domaine non contrôlé par l'organisation.",
                },
                {
                    "severity": "medium",
                    "title": "En-tête Content-Security-Policy absent",
                    "detail": "Aucune politique de sécurité du contenu n'est déclarée.",
                },
                {
                    "severity": "low",
                    "title": "Cookie sans attribut SameSite",
                    "detail": "Un cookie de session ne précise pas SameSite.",
                },
            ],
        }
    )


def ech_scan_marque() -> bytes:
    from app.services.branded_scan_pdf import generate_branded_pdf

    return generate_branded_pdf(
        company_name="Cabinet Vasseur — RSSI externalisé",
        accent_color="#0ea5e9",
        logo_b64=None,
        domain=_DOMAINE,
        overall_status="WARNING",  # vocabulaire attendu : OK / WARNING / CRITICAL
        score_pct=68,
        scan_date="31/07/2026",
        findings=[
            {
                "severity": "critical",
                "title": "TLS 1.0 encore accepté",
                "description": "Le serveur négocie une version obsolète du protocole.",
            },
            {
                "severity": "warning",
                "title": "En-tête HSTS absent",
                "description": "Aucune directive Strict-Transport-Security n'est envoyée.",
            },
            {
                "severity": "info",
                "title": "Bannière de version exposée",
                "description": "Le serveur annonce sa version dans l'en-tête Server.",
            },
        ],
    )


def ech_rssi() -> bytes:
    from app.services.rssi_report_pdf import generate_rssi_report

    return generate_rssi_report(
        client={"name": _CLIENT, "domain": _DOMAINE, "sector": "Menuiserie industrielle"},
        actions=[
            {
                "title": "Déploiement du MFA sur la messagerie",
                "status": "done",
                "due_date": "2026-06-15",
            },
            {
                "title": "Rédaction de la politique de sécurité SI",
                "status": "in_progress",
                "due_date": "2026-09-01",
            },
            {
                "title": "Plan de continuité d'activité",
                "status": "todo",
                "due_date": "2026-11-30",
            },
        ],
        visits=[
            {"date": "2026-05-12", "summary": "Cadrage et inventaire des actifs."},
            {"date": "2026-07-08", "summary": "Revue des accès et des sauvegardes."},
        ],
        deliverables=[{"name": "Politique de sécurité SI v1.pdf", "date": "2026-07-08"}],
        consultant={"display_name": "Claire Vasseur", "company_name": "Cabinet Vasseur"},
    )


def ech_dossier_darkweb() -> bytes:
    from app.services.darkweb_dossier.reporting import generate_dossier_pdf

    dossier = SimpleNamespace(
        company_name=_CLIENT,
        domain=_DOMAINE,
        status="completed",
        total_emails=42,
        exposed_emails=7,
        total_breach_instances=19,
        checked_count=42,
        unverified_count=0,
        risk_score=58,
        severity_score=64,
        top_sources_json='[{"name": "LinkedIn 2012", "count": 9}, {"name": "Collection #1", "count": 6}]',
        created_at=_DATE,
        finished_at=_DATE,
        last_monitored_at=_DATE,
        monitor_active=True,
    )
    cibles = [
        SimpleNamespace(
            email=f"{p}@{_DOMAINE}",
            status="exposed" if i < 3 else "clean",
            check_status="checked",
            total_breaches=(3 - i) if i < 3 else 0,
            breach_sources_json=(
                '[{"name": "LinkedIn 2012", "data_classes": ["Adresses e-mail", "Mots de passe"]}]'
                if i < 3
                else "[]"
            ),
            checked_at=_DATE,
        )
        for i, p in enumerate(["contact", "compta", "rh", "atelier", "direction"])
    ]
    return generate_dossier_pdf(dossier, cibles)


ECHANTILLONS = {
    "nis2": ech_nis2,
    "nis2-auditeur": ech_nis2_auditeur,
    "iso27001": ech_iso27001,
    "devis": ech_devis,
    "facture": ech_facture,
    "scan-url": ech_scan_url,
    "scan-marque": ech_scan_marque,
    "rssi": ech_rssi,
    "darkweb": ech_dossier_darkweb,
}


# ── Rendu ────────────────────────────────────────────────────────────────────


def rendre_png(chemin_pdf: Path, dossier: Path, echelle: int = 2) -> int:
    try:
        import pypdfium2 as pdfium
    except ImportError:
        print(
            "  (rendu PNG ignoré — `pip install pypdfium2` pour l'activer)",
            file=sys.stderr,
        )
        return 0
    doc = pdfium.PdfDocument(str(chemin_pdf))
    for i in range(len(doc)):
        cible = dossier / f"{chemin_pdf.stem}_p{i + 1}.png"
        doc[i].render(scale=echelle).to_pil().save(cible)
    n = len(doc)
    doc.close()
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("noms", nargs="*", help="échantillons à générer (défaut : tous)")
    ap.add_argument("--png", action="store_true", help="rendre aussi chaque page en PNG")
    ap.add_argument("--out", default="", help="dossier de sortie")
    ap.add_argument("--liste", action="store_true", help="lister les noms disponibles")
    a = ap.parse_args()

    if a.liste:
        for nom in ECHANTILLONS:
            print(f"  {nom}")
        return 0

    inconnus = [n for n in a.noms if n not in ECHANTILLONS]
    if inconnus:
        print(f"Inconnu(s) : {', '.join(inconnus)}", file=sys.stderr)
        print(f"Disponibles : {', '.join(ECHANTILLONS)}", file=sys.stderr)
        return 2

    sortie = Path(a.out) if a.out else RACINE / "previsualisation_pdf"
    sortie.mkdir(parents=True, exist_ok=True)

    choisis = a.noms or list(ECHANTILLONS)
    echecs = 0
    for nom in choisis:
        try:
            octets = ECHANTILLONS[nom]()
        except Exception as exc:  # noqa: BLE001 — un echantillon casse ne doit pas bloquer les autres
            print(f"  {nom:<16} ECHEC : {type(exc).__name__}: {exc}", file=sys.stderr)
            echecs += 1
            continue
        chemin = sortie / f"{nom}.pdf"
        chemin.write_bytes(octets)
        detail = f"{len(octets) // 1024} Ko"
        if a.png:
            pages = rendre_png(chemin, sortie)
            if pages:
                detail += f", {pages} page(s) en PNG"
        print(f"  {nom:<16} {detail}")

    print(f"\n  → {sortie}")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
