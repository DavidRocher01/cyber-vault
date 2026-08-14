"""Construction du sitemap — une seule source, toujours a jour.

POURQUOI CE MODULE EXISTE. Le sitemap etait ecrit DEUX FOIS. Un fichier statique
`frontend/src/sitemap.xml`, ecrit a la main, et un endpoint dynamique dans
`main.py` qui interrogeait la base. Seul le premier etait servi : CloudFront
envoie tout ce qui n'est pas `/api/*` vers S3, si bien que la version dynamique
n'a jamais ete atteinte par personne. Mesure le 2026-08-14 : 23 URL servies,
zero `lastmod`, et les deux articles de blog annonces uniquement parce que
quelqu'un les avait recopies a la main.

CE QUE CA COUTAIT. Publier un article depuis l'administration ne suffisait pas :
il fallait en plus editer le fichier statique et redeployer, sinon Google n'en
etait jamais informe. Deux gestes dans deux mondes, dont un que rien ne
rappelait — et aucun test ne pouvait le rattraper, les articles vivant en base,
invisibles depuis le depot.

CE QUI RESTE ECRIT A LA MAIN, ET POURQUOI. Les pages publiques ci-dessous : ce
sont des routes Angular, elles ne vivent pas en base. Mais elles sont
confrontees a `cyberscan.routes.ts` par `frontend/src/seo-statique.spec.ts`, qui
lit CETTE liste. Une page publique nouvelle non annoncee fait echouer le test.
C'est la meme parade que partout ailleurs dans ce projet : une liste ecrite a la
main se perime en silence, et la seule defense est de la confronter a sa source.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

BASE = "https://rochercybersecurite.com"

# (chemin, changefreq, priority) — reprises telles quelles de l'ancien fichier
# statique, pour ne rien changer aux signaux deja envoyes aux moteurs.
PAGES_PUBLIQUES: tuple[tuple[str, str, str], ...] = (
    ("/", "weekly", "1.0"),
    ("/scan-gratuit", "monthly", "0.9"),
    ("/nis2", "monthly", "0.9"),
    ("/iso27001", "monthly", "0.9"),
    ("/contact", "monthly", "0.8"),
    ("/blog", "weekly", "0.8"),
    ("/rssi-externalise", "monthly", "0.8"),
    ("/cout-cyberattaque", "monthly", "0.8"),
    ("/darkweb-offre", "monthly", "0.8"),
    ("/simulation-phishing", "monthly", "0.8"),
    ("/quiz-maturite", "monthly", "0.7"),
    ("/awareness-pricing", "monthly", "0.7"),
    ("/ressources", "monthly", "0.6"),
    ("/bonnes-pratiques", "monthly", "0.6"),
    ("/api", "monthly", "0.6"),
    ("/reserver", "monthly", "0.6"),
    ("/cgu", "yearly", "0.3"),
    ("/cgv", "yearly", "0.3"),
    ("/dpa", "yearly", "0.3"),
    ("/politique-confidentialite", "yearly", "0.3"),
    ("/mentions-legales", "yearly", "0.3"),
)


def construire(articles: list) -> str:
    """Rend le sitemap complet : pages publiques puis articles publies.

    `articles` porte des objets a `slug` et `updated_at` — les `BlogPost` du
    service de blog. Le `lastmod` vient d'`updated_at` et non de `date` : c'est
    la derniere modification reelle, donc le signal de fraicheur qu'attend un
    moteur quand un article est corrige apres publication.
    """
    lignes = [
        f"  <url><loc>{BASE}{chemin}</loc>"
        f"<changefreq>{freq}</changefreq><priority>{prio}</priority></url>"
        for chemin, freq, prio in PAGES_PUBLIQUES
    ]

    for article in articles:
        lastmod = ""
        if article.updated_at:
            lastmod = f"<lastmod>{article.updated_at.date().isoformat()}</lastmod>"
        lignes.append(
            f"  <url><loc>{BASE}/blog/{escape(article.slug)}</loc>{lastmod}"
            "<changefreq>monthly</changefreq><priority>0.7</priority></url>"
        )

    corps = "\n".join(lignes)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{corps}\n"
        "</urlset>"
    )
