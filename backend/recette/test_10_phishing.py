"""Recette phishing : cycle complet de gestion d'une campagne SANS ENVOI.

⚠️ Mode simulation STRICT : on ne lance JAMAIS la campagne (`/launch`) — aucun
email réel n'est envoyé. On exerce create → cible (ajout/suppression) → config →
annulation, puis on supprime la campagne (cleanup). Le launch (envoi Resend) est
délibérément hors recette.
"""

import time

from conftest import API, MARKER, requires_canary


@requires_canary
def test_phishing_campaign_lifecycle_without_send(canary):
    c = canary["client"]
    name = f"{MARKER}-phish-{int(time.time())}"

    created = c.post(f"{API}/phishing/campaigns", json={"name": name, "plan_tier": "standard"})
    assert created.status_code == 201, f"create KO: {created.status_code} {created.text[:200]}"
    camp = created.json()
    cid = camp["id"]
    assert camp["rssi_client_id"] is None, "campagne entreprise directe attendue"
    assert camp["sending_domain"], "domaine d'envoi non exposé"

    try:
        # Ajout d'une cible unitaire (Lot 2)
        tgt = c.post(
            f"{API}/phishing/campaigns/{cid}/targets/single",
            json={"email": "recette-cible@example.com"},
        )
        assert tgt.status_code == 201, f"add target KO: {tgt.status_code} {tgt.text[:200]}"

        # Configuration (scénario + CGU), sans lancer
        patched = c.patch(
            f"{API}/phishing/campaigns/{cid}",
            json={"scenario_keys": ["ceo-fraud"], "cgu_accepted": True},
        )
        assert patched.status_code == 200, patched.text

        targets = c.get(f"{API}/phishing/campaigns/{cid}/targets").json()
        assert len(targets) == 1
        # Suppression unitaire (Lot 2)
        deleted = c.delete(f"{API}/phishing/campaigns/{cid}/targets/{targets[0]['id']}")
        assert deleted.status_code == 204

        # Annulation (Lot 3) — surtout PAS de /launch (zéro mail réel)
        cancelled = c.post(f"{API}/phishing/campaigns/{cid}/cancel")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"
    finally:
        c.delete(f"{API}/phishing/campaigns/{cid}")  # cleanup

    assert c.get(f"{API}/phishing/campaigns/{cid}").status_code == 404
