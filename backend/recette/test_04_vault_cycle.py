"""Cycle d'ecriture complet sur le coffre : create -> list -> get -> delete ->
absent. Le backend stocke des blobs opaques (chiffres cote client), donc on
envoie des chaines marqueur ; peu importe leur "dechiffrabilite"."""

import time

from conftest import API, MARKER, requires_canary


@requires_canary
def test_vault_create_read_delete_cycle(canary):
    c = canary["client"]
    tag = f"{MARKER}-{int(time.time())}"

    # CREATE
    created = c.post(
        f"{API}/vault/",
        json={
            "password_encrypted": f"{tag}-pwd-blob",
            "title_encrypted": f"{tag}-title-blob",
            "category": "login",
        },
    )
    assert created.status_code == 201, f"create KO: {created.status_code} {created.text[:200]}"
    item_id = created.json()["id"]

    try:
        # LIST -> l'item doit apparaitre
        listed = c.get(f"{API}/vault/", params={"limit": 200})
        assert listed.status_code == 200
        ids = [it["id"] for it in listed.json()]
        assert item_id in ids, "l'item cree n'apparait pas dans la liste"

        # GET one -> blob rendu tel quel
        got = c.get(f"{API}/vault/{item_id}")
        assert got.status_code == 200, f"get KO: {got.status_code}"
        assert got.json()["password_encrypted"] == f"{tag}-pwd-blob"
    finally:
        # DELETE (toujours, meme si une assertion casse)
        deleted = c.delete(f"{API}/vault/{item_id}")
        assert deleted.status_code == 204, f"delete KO: {deleted.status_code}"

    # ABSENT apres suppression
    gone = c.get(f"{API}/vault/{item_id}")
    assert gone.status_code == 404, f"l'item devrait etre 404 apres delete, recu {gone.status_code}"
