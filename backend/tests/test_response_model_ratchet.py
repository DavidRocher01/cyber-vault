"""Garde-fou de contrat : un endpoint doit declarer ce qu'il renvoie.

POURQUOI CE TEST EXISTE. Un endpoint sans `response_model` est INVISIBLE au
schema OpenAPI. Consequences mesurees le 2026-08-10 :

  - aucune verification de contrat ne peut le voir. En voulant confronter les
    interfaces TypeScript aux schemas Pydantic, l'interface `Badge` du profil a
    ete rapprochee de `BadgeOut` du domaine sensibilisation — deux concepts sans
    rapport — parce que le VRAI endpoint, `/users/me/badges`, ne declare rien.
    J'allais signaler un bug inexistant ;
  - la reponse n'est ni validee ni filtree : un champ ajoute a un dict de retour
    part chez le client sans que personne ne l'ait decide. Sur un produit qui
    manipule des donnees de securite, c'est une fuite en puissance ;
  - la documentation d'API ment par omission.

118 endpoints sur 257 etaient dans ce cas — 46 %. On ne les corrige pas d'un
coup, alors ce test agit en RATCHET, comme celui des acces DB : la baseline gele
l'existant, et ne doit que RETRECIR.

Il echoue si un NOUVEL endpoint nait sans `response_model` (derive), ou si un
endpoint de la baseline a ete type sans etre retire de la liste (la baseline ne
doit jamais mentir).

CE QUI EST LEGITIMEMENT EXCLU : les reponses qui ne sont pas du JSON — fichiers,
flux, redirections — et les webhooks, dont le corps est dicte par l'appelant.
"""

import re
from pathlib import Path

_ENDPOINTS = Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "endpoints"

_ROUTE = re.compile(
    r"@router\.(?:get|post|put|patch|delete)\((.*?)\)\s*\n(?:@[^\n]*\n)*\s*(?:async )?def (\w+)",
    re.S,
)

# Endpoints qui ne renvoient PAS de JSON : un `response_model` n'aurait aucun
# sens. Documenter chaque ajout.
_HORS_SUJET: set[str] = set()

# Dette heritee. CETTE LISTE NE DOIT QUE RETRECIR : typer un endpoint -> le
# retirer d'ici. Elle est deliberement explicite plutot que comptee : un simple
# seuil laisserait remplacer un endpoint type par un autre qui ne l'est pas.
_BASELINE: set[str] = {
    "admin_acquisition.py::vue_acquisition",
    "admin_invoices.py::admin_create_invoice",
    "admin_invoices.py::admin_download_pdf",
    "admin_invoices.py::admin_get_invoice",
    "admin_invoices.py::admin_list_invoices",
    "admin_quotes.py::admin_create_quote",
    "admin_quotes.py::admin_download_quote_pdf",
    "admin_quotes.py::admin_list_quotes",
    "admin_scans.py::list_public_scans",
    "admin_stats.py::get_stats",
    "admin_stats.py::sync_awareness_content",
    "admin_users.py::list_users",
    "admin_users.py::set_user_plan",
    "admin_users.py::toggle_rssi_consultant",
    "auth.py::forgot_password",
    "auth.py::login",
    "auth.py::logout",
    "auth.py::reset_password",
    "awareness/certificates.py::download_certificate_pdf",
    "awareness/certificates.py::download_nis2_report_pdf",
    "awareness/certificates.py::get_nis2_report",
    "awareness/learners.py::request_magic_link",
    "awareness/organizations.py::enroll_all_learners",
    "blog.py::delete_article",
    "bookings.py::admin_cancel_booking",
    "bookings.py::cancel_booking",
    "bookings.py::delete_slot",
    "code_scans.py::delete_code_scan",
    "collab.py::remove_collaborator",
    "contact.py::admin_update_status",
    "contact.py::submit_contact",
    "cost_calc.py::get_questions",
    "darkweb_dossier.py::delete_dossier",
    "darkweb_dossier.py::download_dossier_pdf",
    "darkweb_dossier.py::export_csv",
    "darkweb_dossier.py::sync_catalog",
    "darkweb_dossier.py::toggle_monitor",
    "dev_testing.py::become_consultant",
    "health.py::health",
    "invoices.py::download_invoice_pdf",
    "invoices.py::get_invoice",
    "invoices.py::list_invoices",
    "iso27001.py::export_assessment_pdf",
    "newsletter.py::confirm",
    "newsletter.py::fetch_og_image",
    "newsletter.py::unsubscribe",
    "nis2.py::export_assessment_pdf",
    "nis2.py::export_auditor_pdf",
    "nis2.py::retirer_une_piece",
    "nis2.py::telecharger_une_piece",
    "notifications.py::delete_notification",
    "notifications.py::mark_all_read",
    "pca.py::generate_pca",
    "phishing.py::add_single_target",
    "phishing.py::cancel_campaign",
    "phishing.py::check_domain_verification",
    "phishing.py::create_campaign",
    "phishing.py::delete_campaign",
    "phishing.py::delete_single_target",
    "phishing.py::download_report_pdf",
    "phishing.py::get_campaign",
    "phishing.py::get_lookalike_domains",
    "phishing.py::launch_campaign",
    "phishing.py::list_campaigns",
    "phishing.py::list_targets",
    "phishing.py::request_domain_verification",
    "phishing.py::tracking_click",
    "phishing.py::tracking_landing",
    "phishing.py::tracking_pixel",
    "phishing.py::tracking_submit",
    "phishing.py::update_campaign",
    "phishing.py::upload_targets",
    "portal.py::download_my_deliverable",
    "portal.py::download_my_report",
    "quiz.py::get_questions",
    "quotes.py::accept_quote",
    "quotes.py::reject_quote",
    "rssi/actions.py::delete_action",
    "rssi/actions.py::export_actions_csv",
    "rssi/clients.py::delete_client",
    "rssi/clients.py::enable_client_awareness",
    "rssi/clients.py::invite_client_to_portal",
    "rssi/clients.py::unlink_site_from_client",
    "rssi/dashboard.py::get_clients_summary",
    "rssi/dashboard.py::get_dashboard_overview",
    "rssi/dashboard.py::get_pending_alerts",
    "rssi/dashboard.py::get_suggestions",
    "rssi/dashboard.py::get_upcoming_events",
    "rssi/deliverables.py::delete_deliverable",
    "rssi/deliverables.py::download_deliverable_file",
    "rssi/deliverables.py::upload_deliverable_file",
    "rssi/nis2.py::exporter_le_dossier",
    "rssi/nis2.py::retirer_une_piece",
    "rssi/nis2.py::telecharger_une_piece",
    "rssi/report.py::get_client_report",
    "rssi/visits.py::delete_visit",
    "scans.py::download_branded_pdf",
    "scans.py::download_pdf",
    "scans.py::download_remediation_script",
    "scans.py::export_scans_csv",
    "scans.py::list_finding_statuses",
    "scans.py::upsert_finding_status",
    "sites.py::check_site_domain_verify",
    "sites.py::delete_site",
    "sites.py::get_site_domain_status",
    "sites.py::get_site_subdomains",
    "sites.py::request_site_domain_verify",
    "subscriptions.py::get_extra_sites_info",
    "training.py::complete_module",
    "url_scans.py::delete_url_scan",
    "url_scans.py::download_url_scan_pdf",
    "url_scans.py::get_quota",
    "users.py::delete_my_account",
    "users.py::export_my_data",
    "users.py::update_password",
    "vault.py::delete_item",
    "webhooks.py::stripe_webhook",
}


def _sans_response_model() -> set[str]:
    trouves: set[str] = set()
    for fichier in _ENDPOINTS.rglob("*.py"):
        if fichier.name == "__init__.py":
            continue
        relatif = fichier.relative_to(_ENDPOINTS).as_posix()
        for decorateur, nom in _ROUTE.findall(fichier.read_text(encoding="utf-8")):
            cle = f"{relatif}::{nom}"
            if "response_model" not in decorateur and cle not in _HORS_SUJET:
                trouves.add(cle)
    return trouves


def test_le_parseur_lit_vraiment_les_endpoints():
    """Un parseur muet ferait passer les deux tests suivants sans rien verifier."""
    assert len(_sans_response_model()) > 0 or not _BASELINE


def test_aucun_nouvel_endpoint_sans_response_model():
    nouveaux = sorted(_sans_response_model() - _BASELINE)

    assert not nouveaux, (
        f"{len(nouveaux)} endpoint(s) sans `response_model` — invisible(s) au schema "
        f"OpenAPI, donc a toute verification de contrat, et renvoyant une reponse "
        f"ni validee ni filtree :\n  " + "\n  ".join(nouveaux)
    )


def test_la_baseline_ne_ment_pas():
    """Un endpoint type doit sortir de la liste, sinon elle cesse de decrire le reel."""
    corriges = sorted(_BASELINE - _sans_response_model())

    assert not corriges, (
        f"{len(corriges)} endpoint(s) desormais type(s) mais encore listes comme dette — "
        f"les retirer de `_BASELINE` :\n  " + "\n  ".join(corriges)
    )
