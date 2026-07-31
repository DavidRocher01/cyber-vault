#!/usr/bin/env python3
"""Vérifie la LISIBILITÉ des PDF générés : texte invisible et chevauchements.

POURQUOI CE SCRIPT EXISTE
Aucun test ne regardait un PDF. Ils vérifiaient qu'il est *produit*, jamais
qu'il est *lisible*. Le 2026-07-31, la bascule en thème clair a rendu le
rapport de phishing à moitié illisible — en-têtes de colonnes, domaine ciblé,
plan et dates écrits en blanc sur blanc. Les 1454 tests passaient.

Deux contrôles, tous deux dérivés du rendu réel :

1. TEXTE INVISIBLE — chaque glyphe est rendu, puis on mesure l'écart de
   luminance dans sa boîte. Un glyphe qui ne se détache pas de son fond
   (écart < `_SEUIL_CONTRASTE`) est signalé. C'est exactement le défaut du
   rapport de phishing, et il est indétectable par extraction de texte :
   du blanc sur blanc s'extrait parfaitement.

2. CHEVAUCHEMENT — les caractères sont regroupés en segments, puis on cherche
   les paires de segments dont les boîtes se recouvrent au-delà de
   `_SEUIL_RECOUVREMENT`. C'est la famille de défauts la plus fréquente sur ces
   générateurs : marque par-dessus le titre, titre par-dessus le sous-titre,
   contenu par-dessus la page de garde.

Usage
-----
    python scripts/check_pdf_lisibilite.py                  # tous les PDF du dossier
    python scripts/check_pdf_lisibilite.py fichier.pdf ...  # ceux-la seulement

Le script suppose que les échantillons ont été générés au préalable :

    python scripts/preview_pdfs.py

Il demande `pypdfium2` et `Pillow`, volontairement PAS des dépendances du
projet : c'est un outil de contrôle local, il s'abstient proprement s'ils
manquent.

LIMITES ASSUMÉES
- Un texte volontairement discret (filigrane, mention légale très pâle) sera
  signalé. Mieux vaut un faux positif à écarter qu'un titre invisible livré.
- Le recouvrement est calculé sur des boîtes rectangulaires : deux textes qui
  s'imbriquent sans se toucher réellement peuvent être signalés.
- Rien ici ne juge l'esthétique ni la présence des informations attendues.
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

_ECHELLE = 3  # facteur de rendu ; plus haut = plus precis, plus lent
_SEUIL_CONTRASTE = 30.0  # ecart de luminance minimal (0-255) dans la boite du glyphe
_SEUIL_RECOUVREMENT = 0.25  # part du plus petit segment couverte par l'autre
_MIN_GLYPHES_INVISIBLES = 3  # en dessous, c'est du bruit (glyphes decoratifs)
# Un glyphe tres fin (« l », « I », « . ») ne couvre que un a deux pixels au
# rendu : l'anticrenelage lisse son contraste et le fait passer sous le seuil
# alors qu'il est parfaitement visible. Constate sur le pied de page du
# dossier dark web — un « l » de 0,62 pt. On ne mesure donc que les glyphes
# assez larges ; un vrai texte invisible en comporte forcement.
_LARGEUR_MIN_MESURABLE = 1.5  # points


def _luminance(px) -> float:
    r, g, b = px[:3]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def glyphes_invisibles(page, textpage) -> list[str]:
    """Glyphes dont la boîte ne présente aucun contraste avec son fond."""
    img = page.render(scale=_ECHELLE).to_pil().convert("RGB")
    _, hauteur_pt = page.get_size()
    trouves: list[str] = []
    for i in range(textpage.count_chars()):
        car = textpage.get_text_range(i, 1)
        if not car.strip():
            continue
        gauche, bas, droite, haut = textpage.get_charbox(i)
        if droite - gauche < _LARGEUR_MIN_MESURABLE or haut - bas < 0.5:
            continue
        x0, x1 = int(gauche * _ECHELLE), int(droite * _ECHELLE) + 1
        y0, y1 = int((hauteur_pt - haut) * _ECHELLE), int((hauteur_pt - bas) * _ECHELLE) + 1
        zone = img.crop((max(x0, 0), max(y0, 0), min(x1, img.width), min(y1, img.height)))
        if zone.width == 0 or zone.height == 0:
            continue
        valeurs = [_luminance(p) for p in zone.getdata()]
        if max(valeurs) - min(valeurs) < _SEUIL_CONTRASTE:
            trouves.append(car)
    return trouves


def _segments(textpage) -> list[dict]:
    """Regroupe les caractères en segments contigus (même ligne, sans grand saut)."""
    segs: list[dict] = []
    courant: dict | None = None
    for i in range(textpage.count_chars()):
        car = textpage.get_text_range(i, 1)
        gauche, bas, droite, haut = textpage.get_charbox(i)
        if not car.strip() or droite - gauche < 0.1:
            courant = None
            continue
        if courant and abs(bas - courant["b"]) < 1.5 and gauche - courant["r"] < 3.0:
            courant["r"] = max(courant["r"], droite)
            courant["t"] = max(courant["t"], haut)
            courant["b"] = min(courant["b"], bas)
            courant["txt"] += car
        else:
            courant = {"l": gauche, "b": bas, "r": droite, "t": haut, "txt": car}
            segs.append(courant)
    return segs


def _recouvrement(a: dict, b: dict) -> float:
    dx = min(a["r"], b["r"]) - max(a["l"], b["l"])
    dy = min(a["t"], b["t"]) - max(a["b"], b["b"])
    if dx <= 0 or dy <= 0:
        return 0.0
    aire_a = (a["r"] - a["l"]) * (a["t"] - a["b"])
    aire_b = (b["r"] - b["l"]) * (b["t"] - b["b"])
    return (dx * dy) / min(aire_a, aire_b)


def chevauchements(textpage) -> list[tuple[str, str, float]]:
    segs = _segments(textpage)
    trouves = []
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            part = _recouvrement(segs[i], segs[j])
            if part > _SEUIL_RECOUVREMENT:
                trouves.append((segs[i]["txt"][:34], segs[j]["txt"][:34], part))
    return trouves


def analyser(chemin: Path) -> list[str]:
    import pypdfium2 as pdfium

    anomalies: list[str] = []
    doc = pdfium.PdfDocument(str(chemin))
    try:
        for numero in range(len(doc)):
            page = doc[numero]
            textpage = page.get_textpage()
            invisibles = glyphes_invisibles(page, textpage)
            if len(invisibles) >= _MIN_GLYPHES_INVISIBLES:
                extrait = "".join(invisibles)[:60]
                anomalies.append(
                    f"p{numero + 1} · {len(invisibles)} glyphe(s) sans contraste : {extrait!r}"
                )
            for a, b, part in chevauchements(textpage):
                anomalies.append(
                    f"p{numero + 1} · chevauchement {int(part * 100)}% : {a!r} ↔ {b!r}"
                )
    finally:
        doc.close()
    return anomalies


def main() -> int:
    try:
        import pypdfium2  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError:
        print(
            "pypdfium2 et Pillow requis (pip install pypdfium2 pillow) — contrôle ignoré.",
            file=sys.stderr,
        )
        return 0

    if len(sys.argv) > 1:
        fichiers = [Path(a) for a in sys.argv[1:]]
    else:
        dossier = RACINE / "previsualisation_pdf"
        if not dossier.is_dir():
            print(
                f"{dossier} introuvable — lancer d'abord scripts/preview_pdfs.py",
                file=sys.stderr,
            )
            return 2
        fichiers = sorted(dossier.glob("*.pdf"))

    if not fichiers:
        print("Aucun PDF à analyser.", file=sys.stderr)
        return 2

    total = 0
    for f in fichiers:
        anomalies = analyser(f)
        total += len(anomalies)
        if anomalies:
            print(f"\n{f.name}")
            for a in anomalies:
                print(f"  {a}")

    print(f"\n{len(fichiers)} PDF analysés — {total} anomalie(s).")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
