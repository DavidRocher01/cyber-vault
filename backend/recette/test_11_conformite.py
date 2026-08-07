"""Conformite NIS2 / ISO 27001 — l'angle mort de la recette, comble le 2026-08-07.

POURQUOI CE FICHIER EXISTE. Le lot du 2026-08-07 a touche en profondeur les deux
ecrans de conformite — nouvelle table, nouvelle colonne, nouvelles routes — et la
recette post-mise-en-production n'en verifiait AUCUN. Son feu vert ne disait donc
rien de ce qui venait d'etre livre.

CE QUE CETTE SUITE ATTRAPE, ET C'EST LE POINT IMPORTANT. `GET /nis2/me` ne lit la
table `preuves_criteres` QUE si une evaluation existe deja. Un test qui se
contenterait de lire un compte vierge passerait au vert avec une migration
oubliee. On ecrit donc une evaluation AVANT de relire — c'est ce qui fait
reellement travailler la requete des pieces.

EFFET DE BORD ASSUME : la suite ecrit l'auto-evaluation du compte canari. C'est
un upsert, sur un compte dedie dont la recette fait deja table rase du coffre et
des scans a chaque passage.
"""

from __future__ import annotations

from conftest import API, requires_canary

# ── Les deux ecrans repondent ────────────────────────────────────────────────


@requires_canary
def test_nis2_repond_et_sert_le_catalogue(canary):
    c = canary["client"]
    r = c.get(f"{API}/nis2/me")
    assert r.status_code == 200, f"/nis2/me KO: {r.status_code} {r.text[:300]}"

    corps = r.json()
    assert isinstance(corps.get("categories"), list), "catalogue absent"
    total = sum(len(cat.get("items", [])) for cat in corps["categories"])
    assert total == 34, f"34 criteres attendus, {total} servis"


@requires_canary
def test_iso27001_repond_et_sert_le_catalogue(canary):
    c = canary["client"]
    r = c.get(f"{API}/iso27001/me")
    assert r.status_code == 200, f"/iso27001/me KO: {r.status_code} {r.text[:300]}"
    assert isinstance(r.json().get("categories"), list), "catalogue absent"


# ── LE test qui exerce la table des preuves ──────────────────────────────────


@requires_canary
def test_une_evaluation_enregistree_se_relit_avec_ses_pieces(canary):
    """CELUI QUI ATTRAPERAIT UNE MIGRATION OUBLIEE.

    Sur un compte sans evaluation, la requete des pieces n'est jamais emise :
    le test passerait au vert alors que `preuves_criteres` n'existe pas. On
    ecrit donc d'abord, puis on relit.
    """
    c = canary["client"]

    ecriture = c.put(f"{API}/nis2/me", json={"items": {"rssi": "compliant"}})
    assert ecriture.status_code == 200, (
        f"PUT /nis2/me KO: {ecriture.status_code} {ecriture.text[:300]}"
    )

    relecture = c.get(f"{API}/nis2/me")
    assert relecture.status_code == 200, (
        f"GET apres ecriture KO: {relecture.status_code} {relecture.text[:300]} "
        "— la table des pieces manque-t-elle en base ?"
    )

    corps = relecture.json()
    assert corps["items"].get("rssi") == "compliant", "la reponse enregistree n'est pas relue"
    # `pieces` doit etre present et exploitable, meme vide : c'est la preuve que
    # la requete sur `preuves_criteres` a bien abouti.
    assert isinstance(corps.get("pieces"), dict), "champ `pieces` absent — migration jouee ?"


# ── Les routes du depot de pieces existent ───────────────────────────────────


@requires_canary
def test_les_routes_de_pieces_sont_montees(canary):
    """404 signifierait que le lot n'est pas deploye ; on accepte tout le reste.

    Le code exact depend du plan du compte canari (403 si Gratuit) et de
    l'existence de la piece (404 sur l'identifiant, mais apres authentification).
    On ne teste donc que la presence de la route, pas son verdict.
    """
    c = canary["client"]

    depot = c.post(f"{API}/nis2/me/criteres/rssi/pieces")
    assert depot.status_code != 404, "route de depot absente — lot non deploye ?"
    # 422 (fichier manquant) ou 403 (plan Gratuit) sont deux reponses saines.
    assert depot.status_code in (403, 413, 422), f"reponse inattendue: {depot.status_code}"


@requires_canary
def test_l_export_auditeur_repond(canary):
    """Il porte les pieces depuis le 2026-08-07 : une regression le ferait lever."""
    c = canary["client"]
    r = c.get(f"{API}/nis2/me/pdf/auditor")

    assert r.status_code != 404, "route d'export absente"
    # 403 si le plan canari n'inclut pas l'export — c'est une reponse saine.
    assert r.status_code in (200, 403), f"export KO: {r.status_code} {r.text[:300]}"
    if r.status_code == 200:
        assert r.content.startswith(b"%PDF-"), "le corps n'est pas un PDF"
