"""Le sitemap construit doit rester lisible par un moteur.

POURQUOI CE FICHIER EXISTE. Le sitemap servi jusqu'au 2026-08-14 etait un
fichier statique : un article publie depuis l'administration n'y apparaissait
jamais, sauf a rouvrir le depot et redeployer. Il est desormais construit depuis
la base. Ce qu'on gagne en fraicheur, on le perd en verifiabilite a l'oeil : plus
personne ne relit le fichier avant de le publier, donc ces tests sont la seule
relecture qui reste.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from xml.etree import ElementTree

from app.services import sitemap_service

_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"


def _article(slug: str, updated_at: datetime | None = None) -> SimpleNamespace:
    return SimpleNamespace(slug=slug, updated_at=updated_at)


def _locs(xml: str) -> list[str]:
    racine = ElementTree.fromstring(xml)
    return [u.findtext(f"{_NS}loc") for u in racine.findall(f"{_NS}url")]


def test_le_document_est_un_xml_valide():
    """Un sitemap malforme est rejete en bloc, pas partiellement lu."""
    xml = sitemap_service.construire([_article("un-article", datetime(2026, 8, 14, tzinfo=UTC))])
    racine = ElementTree.fromstring(xml)
    assert racine.tag == f"{_NS}urlset"


def test_toutes_les_pages_publiques_sont_annoncees():
    locs = _locs(sitemap_service.construire([]))
    attendues = {sitemap_service.BASE + c for c, _, _ in sitemap_service.PAGES_PUBLIQUES}
    assert attendues <= set(locs)
    assert len(locs) == len(sitemap_service.PAGES_PUBLIQUES)


def test_aucune_url_en_double():
    """L'ancienne version declarait `("", ...)` ET `("/", ...)`, soit deux fois
    la page d'accueil. Un doublon dilue le signal envoye au moteur."""
    locs = _locs(sitemap_service.construire([_article("un-article")]))
    assert len(locs) == len(set(locs)), "URL en double dans le sitemap"


def test_les_articles_publies_sont_ajoutes_avec_leur_date():
    xml = sitemap_service.construire(
        [
            _article("audit-cybersecurite-pme-prix-2026", datetime(2026, 8, 14, 9, 30, tzinfo=UTC)),
            _article("vulnerabilites-courantes-sites-ecommerce", datetime(2026, 7, 1, tzinfo=UTC)),
        ]
    )
    assert f"{sitemap_service.BASE}/blog/audit-cybersecurite-pme-prix-2026" in _locs(xml)
    # `lastmod` vient d'`updated_at` : c'est le signal de fraicheur qui manquait
    # totalement au fichier statique (mesure : zero `lastmod` sur 23 URL).
    assert "<lastmod>2026-08-14</lastmod>" in xml
    assert "<lastmod>2026-07-01</lastmod>" in xml


def test_un_article_sans_date_ne_produit_pas_de_lastmod_vide():
    """Un `<lastmod></lastmod>` vide rend le document invalide."""
    xml = sitemap_service.construire([_article("sans-date", None)])
    assert "<lastmod>" not in xml
    ElementTree.fromstring(xml)


def test_un_slug_hostile_ne_casse_pas_le_document():
    """Les slugs viennent de l'administration, donc d'un humain qui peut se
    tromper. Un `&` non echappe suffit a rendre tout le sitemap illisible."""
    xml = sitemap_service.construire([_article("titre-avec-&-et-<balise>")])
    racine = ElementTree.fromstring(xml)
    assert any("&" in (u.findtext(f"{_NS}loc") or "") for u in racine.findall(f"{_NS}url"))
