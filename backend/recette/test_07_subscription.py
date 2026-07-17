"""Abonnement & entitlements : le canari doit avoir un abonnement actif
(business tier). Valide le chemin de lecture facturation/droits."""

from conftest import API, requires_canary


@requires_canary
def test_canary_has_active_subscription(canary):
    c = canary["client"]
    r = c.get(f"{API}/subscriptions/me")
    assert r.status_code == 200, f"/subscriptions/me KO: {r.status_code} {r.text[:200]}"
    sub = r.json()
    assert sub is not None, "canari sans abonnement actif (attendu business)"
    assert sub["status"] == "active", f"abonnement non actif: {sub.get('status')}"

    plan = sub.get("plan") or {}
    assert plan.get("tier_level", 0) >= 1, f"tier plan invalide: {plan}"
    assert plan.get("name"), f"plan sans nom: {plan}"
