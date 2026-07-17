"""Sensibilisation (e-learning) : parcours d'un module de formation par le
canari. On liste les modules, on complete le module 'phishing' (bonne reponse),
on relit la progression.

NB: l'awareness "multi-tenant" (org + learner + magic-link) est volontairement
hors recette car il envoie un email. Le module training est per-user, sans email
ni organisation. La progression n'est pas nettoyable (pas d'endpoint DELETE) mais
l'operation est idempotente (re-completer reste 'correct')."""

from conftest import API, requires_canary


@requires_canary
def test_training_module_flow(canary):
    c = canary["client"]

    mods = c.get(f"{API}/training/modules")
    assert mods.status_code == 200, f"/training/modules KO: {mods.status_code}"
    ids = [m["id"] for m in mods.json()]
    assert "phishing" in ids, f"module 'phishing' absent: {ids}"

    done = c.post(f"{API}/training/modules/phishing/complete", json={"answer": "b"})
    assert done.status_code == 200, f"complete KO: {done.status_code} {done.text[:200]}"
    assert done.json().get("correct") is True, f"reponse 'b' devrait etre correcte: {done.json()}"

    prog = c.get(f"{API}/training/progress")
    assert prog.status_code == 200
    assert "phishing" in prog.json().get("completed_ids", []), (
        "progression 'phishing' non enregistree"
    )
