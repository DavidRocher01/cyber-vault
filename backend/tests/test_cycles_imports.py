"""Garde-fou : aucun cycle d'import entre les services.

POURQUOI CE FICHIER EXISTE.

`pdf_brand` et `pdf_covers` se sont importés mutuellement pendant des mois.
`pdf_covers` avait été extrait de `pdf_brand`, mais les appelants n'avaient pas
suivi : `pdf_brand` ré-exportait les fonctions déplacées, avec ses imports
rejetés en bas de fichier sous un commentaire avertissant qu'ils *devaient*
venir après les constantes.

Ça tenait — tant qu'on entrait par `pdf_brand`. Le geste naturel, importer la
fonction depuis le module où elle vit, levait une erreur :

    >>> import app.services.pdf.covers
    ImportError: cannot import name 'draw_compliance_cover' from partially
    initialized module (most likely due to a circular import)

Personne ne l'avait vu parce que personne n'avait essayé cet ordre-là. Un cycle
ne se manifeste qu'au premier import qui prend la boucle par l'autre bout, et
il n'y a aucune raison que ce soit celui qu'on teste.

Ce test lit le graphe d'imports plutôt que d'exécuter les modules : il voit donc
aussi les cycles qui « fonctionnent » par chance d'ordonnancement.
"""

import ast
import pathlib

SERVICES = pathlib.Path(__file__).resolve().parents[1] / "app" / "services"
PREFIXE = "app.services"


def _nom_module(chemin: pathlib.Path) -> str:
    relatif = chemin.relative_to(SERVICES).with_suffix("")
    parties = [p for p in relatif.parts if p != "__init__"]
    return ".".join(parties) or relatif.parts[0]


def _graphe() -> dict[str, set[str]]:
    """Les arêtes `module -> module` internes a `app/services/`."""
    fichiers = [f for f in SERVICES.rglob("*.py") if "__pycache__" not in f.parts]
    connus = {_nom_module(f) for f in fichiers}
    aretes: dict[str, set[str]] = {n: set() for n in connus}

    for fichier in fichiers:
        source = _nom_module(fichier)
        arbre = ast.parse(fichier.read_text(encoding="utf-8"))
        for noeud in ast.walk(arbre):
            cibles: list[str] = []
            if isinstance(noeud, ast.ImportFrom) and noeud.module:
                cibles.append(noeud.module)
            elif isinstance(noeud, ast.Import):
                cibles += [alias.name for alias in noeud.names]

            for cible in cibles:
                if not cible.startswith(PREFIXE):
                    continue
                reste = cible[len(PREFIXE) :].lstrip(".")
                if not reste:
                    continue
                # On rattache au module le plus precis qui existe reellement :
                # `pdf.covers` si ce module existe, sinon le paquet `pdf`.
                for candidat in (reste, reste.split(".")[0]):
                    if candidat in connus and candidat != source:
                        aretes[source].add(candidat)
                        break
    return aretes


def _cycles(aretes: dict[str, set[str]]) -> list[list[str]]:
    """Parcours en profondeur ; un arc vers un noeud de la pile ferme un cycle."""
    EN_COURS, TERMINE = 1, 2
    etat: dict[str, int] = {}
    trouves: list[list[str]] = []

    def visiter(noeud: str, pile: list[str]) -> None:
        etat[noeud] = EN_COURS
        pile.append(noeud)
        for voisin in sorted(aretes.get(noeud, ())):
            if etat.get(voisin) is None:
                visiter(voisin, pile)
            elif etat[voisin] == EN_COURS:
                trouves.append(pile[pile.index(voisin) :] + [voisin])
        pile.pop()
        etat[noeud] = TERMINE

    for noeud in sorted(aretes):
        if etat.get(noeud) is None:
            visiter(noeud, [])
    return trouves


def test_le_graphe_est_bien_construit():
    """Garde-fou du garde-fou : un extracteur casse ne verrait aucune arête, et
    le test de cycles passerait sur un graphe vide."""
    aretes = _graphe()
    assert len(aretes) > 50, "trop peu de modules — l'extraction a echoue"
    assert sum(len(v) for v in aretes.values()) > 20, "aucune dependance detectee"


def test_aucun_cycle_d_import_entre_services():
    cycles = _cycles(_graphe())

    # Deux parcours peuvent decrire la meme boucle : on dedoublonne par ensemble.
    uniques = {frozenset(c): c for c in cycles}
    assert not uniques, "Cycles d'import detectes :\n  " + "\n  ".join(
        " -> ".join(c) for c in uniques.values()
    )
