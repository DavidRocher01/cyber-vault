"""
Scan service — runs the cyber-scanner against a site URL,
saves the PDF, and updates the Scan record in DB.
"""

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ssrf import assert_no_ssrf
from app.models.scan import Scan
from app.models.site import Site

# Resolve cyber-scanner path (sibling of backend/)
SCANNER_DIR = Path(__file__).resolve().parents[3] / "cyber-scanner"
sys.path.insert(0, str(SCANNER_DIR))


async def _get_plan_tier(db: AsyncSession, user_id: int) -> int:
    """Return the tier level of the user's active subscription (default 1 = Gratuit).

    Source de vérité unique : subscription_service.get_active_tier.
    """
    from app.services.subscription_service import get_active_tier

    return await get_active_tier(db, user_id)


def _run_all_modules(
    url: str, hostname: str, tier: int, hibp_key: str, allow_active: bool
) -> dict[str, dict]:
    """Execute tous les scanners applicables et renvoie leurs resultats par module.

    Les modules joues dependent du tier (Pro >= 3, Entreprise >= 4) et de
    ``allow_active`` (scan de ports nmap intrusif). Un module non joue vaut un dict
    vide, neutre pour le PDF comme pour le verdict global. Les imports restent
    locaux : le paquet scanner est charge a la demande et reste mockable via
    ``sys.modules`` dans les tests.
    """
    from scanner.cms_detector import detect_cms
    from scanner.cookie_checker import check_cookies
    from scanner.cors_checker import check_cors
    from scanner.dns_scanner import scan_subdomains
    from scanner.email_checker import check_email_security
    from scanner.headers_checker import check_headers
    from scanner.ip_reputation import check_ip_reputation
    from scanner.port_scanner import scan_ports
    from scanner.ssl_checker import check_ssl
    from scanner.waf_detector import detect_waf

    ssl_result = check_ssl(hostname)
    headers_result = check_headers(url)
    email_result = check_email_security(hostname)
    cookie_result = check_cookies(url)
    cors_result = check_cors(url)
    ip_result = check_ip_reputation(hostname)
    dns_result = scan_subdomains(hostname)
    cms_result = detect_cms(url)
    waf_result = detect_waf(url)
    # Scan de ports nmap = INTRUSIF : uniquement si le domaine est vérifié.
    port_result = scan_ports(hostname) if allow_active else {}

    breach_result: dict = {}
    if hibp_key:
        from scanner.breach_checker import check_breach

        breach_result = check_breach(hostname, api_key=hibp_key, mode="domain")

    tech_result = tls_result = takeover_result = ti_result = methods_result = {}
    if tier >= 3:
        from scanner.http_methods import check_http_methods
        from scanner.subdomain_takeover import check_subdomain_takeover
        from scanner.tech_fingerprint import fingerprint_tech
        from scanner.threat_intel import get_threat_intel
        from scanner.tls_auditor import audit_tls

        tech_result = fingerprint_tech(url)
        tls_result = audit_tls(hostname)
        found_subs = [s["subdomain"] for s in dns_result.get("found", [])]
        takeover_result = check_subdomain_takeover(found_subs)
        ti_result = get_threat_intel(hostname)
        methods_result = check_http_methods(url)

    redirect_result = clickjacking_result = dirlist_result = robots_result = jwt_result = {}
    if tier >= 4:
        from scanner.clickjacking import check_clickjacking
        from scanner.directory_listing import check_directory_listing
        from scanner.jwt_checker import check_jwt
        from scanner.open_redirect import check_open_redirect
        from scanner.robots_sitemap import analyse_robots_sitemap

        redirect_result = check_open_redirect(url)
        clickjacking_result = check_clickjacking(url)
        dirlist_result = check_directory_listing(url)
        robots_result = analyse_robots_sitemap(url)
        jwt_result = check_jwt(url)

    # Source unique des résultats par module : le PDF, le verdict global ET la
    # remédiation en dérivent, évitant toute divergence (un module présent ici
    # mais oublié dans l'agrégation faussait silencieusement le verdict).
    return {
        "ssl": ssl_result,
        "headers": headers_result,
        "email": email_result,
        "cookies": cookie_result,
        "cors": cors_result,
        "ip": ip_result,
        "dns": dns_result,
        "cms": cms_result,
        "waf": waf_result,
        "ports": port_result,
        "breach": breach_result,
        "tech": tech_result,
        "tls": tls_result,
        "takeover": takeover_result,
        "threat_intel": ti_result,
        "http_methods": methods_result,
        "open_redirect": redirect_result,
        "clickjacking": clickjacking_result,
        "directory_listing": dirlist_result,
        "robots": robots_result,
        "jwt": jwt_result,
    }


def _compute_overall(modules: dict[str, dict]) -> str:
    """Deduit le verdict global (OK/WARNING/CRITICAL) des statuts par module.

    `takeover` et `robots` en sont volontairement exclus ; `breach` n'entre en
    compte que s'il n'a pas d'erreur. Un module non joue (dict vide ->
    ``.get("status")`` = None) est sans effet sur le verdict.
    """
    status_keys = {
        "ssl",
        "headers",
        "email",
        "cookies",
        "cors",
        "ip",
        "dns",
        "cms",
        "waf",
        "ports",
        "tech",
        "tls",
        "threat_intel",
        "http_methods",
        "open_redirect",
        "clickjacking",
        "directory_listing",
        "jwt",
    }
    all_statuses = [r.get("status") for k, r in modules.items() if k in status_keys]
    breach_result = modules.get("breach") or {}
    if breach_result and not breach_result.get("error"):
        all_statuses.append(breach_result.get("status"))

    if "CRITICAL" in all_statuses:
        return "CRITICAL"
    if "WARNING" in all_statuses:
        return "WARNING"
    return "OK"


def _write_report(
    url: str, modules: dict[str, dict], tier: int, allow_active: bool, output_path: str
) -> None:
    """Genere le PDF d'audit a partir des resultats de modules (drapeaux skipped
    derives du tier et de ``allow_active``)."""
    from scanner.report_generator import generate_report

    generate_report(
        target_url=url,
        ssl_result=modules["ssl"],
        headers_result=modules["headers"],
        port_result=modules["ports"],
        ports_skipped=not allow_active,
        sca_result={},
        sca_skipped=True,
        email_result=modules["email"],
        email_skipped=False,
        cookie_result=modules["cookies"],
        cookie_skipped=False,
        cors_result=modules["cors"],
        cors_skipped=False,
        ip_result=modules["ip"],
        ip_skipped=False,
        dns_result=modules["dns"],
        dns_skipped=False,
        cms_result=modules["cms"],
        cms_skipped=False,
        waf_result=modules["waf"],
        waf_skipped=False,
        tech_result=modules["tech"],
        tech_skipped=(tier < 3),
        tls_result=modules["tls"],
        tls_skipped=(tier < 3),
        takeover_result=modules["takeover"],
        takeover_skipped=(tier < 3),
        ti_result=modules["threat_intel"],
        ti_skipped=(tier < 3),
        methods_result=modules["http_methods"],
        methods_skipped=(tier < 3),
        redirect_result=modules["open_redirect"],
        redirect_skipped=(tier < 4),
        clickjacking_result=modules["clickjacking"],
        clickjacking_skipped=(tier < 4),
        dirlist_result=modules["directory_listing"],
        dirlist_skipped=(tier < 4),
        robots_result=modules["robots"],
        robots_skipped=(tier < 4),
        jwt_result=modules["jwt"],
        jwt_skipped=(tier < 4),
        output_path=output_path,
    )


def _write_remediation(url: str, modules: dict[str, dict], output_dir: str) -> dict:
    """Genere les scripts de remediation ; renvoie {} si la generation echoue
    (l'echec ne doit jamais faire planter le scan)."""
    try:
        from scanner.remediation import generate_remediation

        return generate_remediation(
            target_url=url,
            port_result=modules["ports"],
            headers_result=modules["headers"],
            sca_result=None,
            ssl_result=modules["ssl"],
            cors_result=modules["cors"],
            cookie_result=modules["cookies"],
            http_methods_result=modules["http_methods"],
            clickjacking_result=modules["clickjacking"],
            directory_listing_result=modules["directory_listing"],
            open_redirect_result=modules["open_redirect"],
            robots_result=modules["robots"],
            email_result=modules["email"],
            waf_result=modules["waf"],
            output_dir=output_dir,
        )
    except Exception as exc:
        logger.warning(f"Remediation generation failed: {exc}")
        return {}


def _run_scan_sync(
    url: str, tier: int, scan_id: int, hibp_key: str, allow_active: bool = True
) -> dict:
    """
    All blocking scanner calls, executed in a thread pool executor so the
    asyncio event loop stays free to serve API requests during the scan.
    Returns a dict with keys: results, overall, pdf_path.

    Orchestre quatre etapes pures (chacune extraite dans son helper) :
    collecte des modules -> PDF -> verdict global -> scripts de remediation.

    allow_active : si False, on saute le scan de ports nmap (module INTRUSIF).
    Réservé aux domaines dont l'utilisateur a prouvé la propriété (anti-scan de
    tiers non consentants). Les autres modules (GET/DNS/TLS) restent passifs.
    """
    from urllib.parse import urlparse

    hostname = urlparse(url).hostname or url

    module_results = _run_all_modules(url, hostname, tier, hibp_key, allow_active)

    pdf_dir = SCANNER_DIR / "reports" / "clients"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_local = pdf_dir / f"scan_{scan_id}.pdf"
    _write_report(url, module_results, tier, allow_active, str(pdf_local))

    # LE RAPPORT EST RANGE AILLEURS QUE SUR LE DISQUE DU CONTENEUR, et c'est ce
    # qui lui permet de survivre. L'outil de scan ecrit sur disque — on ne le
    # change pas — mais ce qu'on retient en base est une REFERENCE, pas un
    # chemin : un chemin ne survit pas a la tache Fargate qui l'a ecrit.
    #
    # Le 2026-08-09, sept minutes apres un deploiement, `GET /scans/163/pdf`
    # repondait 500 : la base affirmait un fichier que le disque n'avait plus.
    #
    # SI LE RAPPORT N'A PAS ETE PRODUIT, ON NE RETIENT RIEN. Auparavant le chemin
    # etait stocke quoi qu'il arrive : la base promettait un fichier qui n'avait
    # jamais existe, et l'endpoint repondait 500 en allant le chercher.
    from app.services.storage import ranger_rapport

    reference = (
        ranger_rapport(pdf_local.read_bytes(), pdf_local.name) if pdf_local.is_file() else None
    )

    overall = _compute_overall(module_results)

    remediation_paths = _write_remediation(
        url, module_results, str(pdf_dir / f"remediation_{scan_id}")
    )

    results = {
        **module_results,
        "_meta": {
            "tier": tier,
            "url": url,
            "remediation_scripts": remediation_paths,
        },
    }

    return {"results": results, "overall": overall, "pdf_path": reference}


async def _active_scan_allowed(user_id: int, url: str, db: AsyncSession) -> bool:
    """True si l'utilisateur a prouvé la propriété du domaine (scan nmap autorisé).
    Couvre l'hôte exact et l'apex sans préfixe 'www.' (vérifier l'apex vaut pour www)."""
    from urllib.parse import urlparse

    from app.services import phishing_service

    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    candidates = {host}
    if host.startswith("www."):
        candidates.add(host[4:])
    for domain in candidates:
        if await phishing_service.is_domain_verified(user_id, domain, db):
            return True
    return False


async def run_scan(scan_id: int, db: AsyncSession) -> None:
    """
    Execute a full scan for the given scan_id.
    Updates scan.status, scan.pdf_path, scan.results_json, scan.overall_status.
    """
    # Fetch scan + site
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan: Scan | None = result.scalar_one_or_none()
    if not scan:
        return

    site_result = await db.execute(select(Site).where(Site.id == scan.site_id))
    site: Site | None = site_result.scalar_one_or_none()
    if not site:
        scan.status = "failed"
        scan.error_message = "Site not found"
        await db.commit()
        return

    scan.status = "running"
    scan.started_at = datetime.now(UTC)
    await db.commit()

    tier = await _get_plan_tier(db, site.user_id)

    url = site.url
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    # Re-validation SSRF a l'EXECUTION (anti DNS-rebinding / TOCTOU) : le domaine a
    # pu etre rebascule vers une IP interne entre le trigger (ou la verification de
    # propriete) et l'execution differee. Critique ici car scan_ports (nmap) et
    # check_ssl (socket TLS) re-resolvent le DNS SANS passer par scanner.safe_http.
    try:
        assert_no_ssrf(url)
    except HTTPException:
        scan.status = "failed"
        scan.error_message = (
            "URL refusee : l'hote resout vers une adresse interne au moment du scan"
        )
        scan.finished_at = datetime.now(UTC)
        await db.commit()
        return

    from app.core.config import settings

    hibp_key = settings.HIBP_API_KEY

    # Scan de ports nmap (intrusif) uniquement si l'utilisateur a prouvé la
    # propriété du domaine (niveau 2 : passif libre / intrusif vérifié).
    allow_active = await _active_scan_allowed(site.user_id, url, db)

    try:
        # Run all blocking scanner calls in a thread pool so the asyncio event
        # loop stays free to serve other API requests during the scan.
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None, _run_scan_sync, url, tier, scan_id, hibp_key, allow_active
        )

        scan.status = "done"
        scan.overall_status = result["overall"]
        scan.pdf_path = result["pdf_path"]
        scan.results_json = json.dumps(result["results"], default=str)
        scan.finished_at = datetime.now(UTC)
        await db.commit()

        # Email alert on CRITICAL (manual scans)
        if result["overall"] == "CRITICAL" and result["pdf_path"]:
            try:
                from app.models.user import User
                from app.services.email_service import send_scan_report

                user_result = await db.execute(select(User).where(User.id == site.user_id))
                user = user_result.scalar_one_or_none()
                if user:
                    send_scan_report(
                        to_email=user.email,
                        site_url=site.url,
                        overall_status="CRITICAL",
                        pdf_path=result["pdf_path"],
                    )
            except Exception as exc:
                logger.warning(f"Scan report email failed: {exc}")

    except Exception as exc:
        # Ne pas avaler l'echec en silence : trace complete -> CloudWatch + Sentry.
        logger.exception(f"Scan {scan.id} failed: {exc}")
        scan.status = "failed"
        scan.error_message = str(exc)[:500]
        scan.finished_at = datetime.now(UTC)
        await db.commit()


def _refabriquer_rapport(scan_id: int, results_json: str) -> bytes | None:
    """Reconstruit le PDF depuis les resultats conserves en base, ou `None`.

    UN ECHEC N'EST PAS UNE ERREUR SERVEUR. Le module `scanner` n'est pas
    toujours la — il est absent du poste de developpement, par exemple — et un
    vieux `results_json` peut ne plus porter tous les modules attendus. Dans les
    deux cas l'appelant repondra 404, ce qui est la verite : pas de rapport.
    """
    import tempfile

    from app.core.utils import safe_json_load

    resultats = safe_json_load(results_json, {})
    meta = resultats.get("_meta", {})
    try:
        with tempfile.TemporaryDirectory() as dossier:
            chemin = str(Path(dossier) / f"scan_{scan_id}.pdf")
            _write_report(
                meta.get("url", "unknown"),
                resultats,
                int(meta.get("tier", 1)),
                bool(resultats.get("ports")),
                chemin,
            )
            return Path(chemin).read_bytes()
    except Exception:
        return None


async def obtenir_rapport(db: AsyncSession, scan: Scan) -> bytes | None:
    """Contenu du rapport d'un scan, refabrique et range s'il a disparu.

    POURQUOI CETTE FONCTION VIT DANS LE SERVICE ET NON DANS L'ENDPOINT. Elle
    ECRIT en base — elle remplace la reference morte par la nouvelle. Un
    endpoint ne fait jamais d'acces DB direct ; c'est la regle du projet, et le
    ratchet `test_endpoints_db_access_ratchet` l'a rattrapee quand je l'ai
    enfreinte.

    ON REFABRIQUE PLUTOT QUE DE RENVOYER L'UTILISATEUR CHEZ LUI : le plan
    Gratuit n'autorise qu'un scan par 30 jours, donc lui repondre « relancez un
    scan » serait lui demander l'impossible pour recuperer un rapport qu'il a
    deja paye de son quota.
    """
    if not scan.pdf_path:
        return None

    from app.services.storage import lire_rapport, ranger_rapport

    contenu = lire_rapport(scan.pdf_path)
    if contenu is not None:
        return contenu
    if not scan.results_json:
        return None

    # HORS DE LA BOUCLE D'EVENEMENTS : la generation est synchrone et prend
    # plusieurs centaines de millisecondes ; la laisser dans la boucle
    # bloquerait toutes les autres requetes pendant ce temps.
    contenu = await asyncio.to_thread(_refabriquer_rapport, scan.id, scan.results_json)
    if contenu is None:
        return None

    # Range au passage : la demande suivante n'aura plus rien a refaire.
    scan.pdf_path = ranger_rapport(contenu, f"scan_{scan.id}.pdf")
    await db.commit()
    return contenu
