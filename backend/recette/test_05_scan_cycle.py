"""Cycle scan asynchrone : lancer un url-scan sur notre propre domaine (cible
sure), verifier que le worker le prend en charge (sort de 'pending'), puis
nettoyer. On scanne rochercybersecurite.com : aucune cible tierce impactee.

On n'exige PAS le 'done' complet (le rendu screenshot peut etre lent) pour ne
pas declencher un rollback sur une simple lenteur ; on exige que le pipeline
asynchrone VIVE (le scan quitte l'etat 'pending'). Si le scan atteint un etat
terminal dans la fenetre, on verifie la coherence du resultat."""

from conftest import API, BASE_URL, poll_until, requires_canary

TERMINAL = {"done", "failed"}


@requires_canary
def test_url_scan_pipeline_is_alive(canary):
    c = canary["client"]

    launched = c.post(f"{API}/url-scans", json={"url": BASE_URL})
    assert launched.status_code == 202, f"launch KO: {launched.status_code} {launched.text[:200]}"
    scan_id = launched.json()["id"]

    try:

        def fetch():
            return c.get(f"{API}/url-scans/{scan_id}").json()

        # Le worker doit consommer le scan (sortir de 'pending') dans la fenetre.
        result = poll_until(
            fetch,
            predicate=lambda s: s.get("status") != "pending",
            timeout_s=90.0,
            interval_s=4.0,
        )
        status = result.get("status")
        assert status != "pending", (
            "le scan est reste 'pending' >90s : worker de scan mort ou file bloquee"
        )

        # Si terminal, coherence minimale du resultat.
        if status == "done":
            assert result.get("results_json") is not None, "scan 'done' sans results_json"
    finally:
        deleted = c.delete(f"{API}/url-scans/{scan_id}")
        assert deleted.status_code in (204, 404), f"delete scan KO: {deleted.status_code}"
