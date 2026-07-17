"""Coeur produit : cycle scan de site complet. On enregistre notre propre
domaine comme site, on lance un scan, on verifie que le pipeline asynchrone vit
(le scan quitte 'pending') et, s'il aboutit dans la fenetre, que le rapport PDF
est disponible. Puis on nettoie (soft delete du site).

Le canari est sur un plan a max_sites < 0 : la limite de frequence de scan est
desactivee, donc register->scan->delete passe a CHAQUE deploy sans 429."""

from conftest import API, BASE_URL, MARKER, poll_until, requires_canary

TERMINAL = {"done", "failed"}


@requires_canary
def test_site_register_scan_report_cycle(canary):
    c = canary["client"]
    import time

    site = c.post(
        f"{API}/sites",
        json={"url": BASE_URL, "name": f"{MARKER}-{int(time.time())}"},
    )
    assert site.status_code == 201, f"register site KO: {site.status_code} {site.text[:200]}"
    site_id = site.json()["id"]

    try:
        trig = c.post(f"{API}/scans/trigger/{site_id}")
        assert trig.status_code == 202, f"trigger KO: {trig.status_code} {trig.text[:200]}"
        scan_id = trig.json()["scan_id"]

        def fetch():
            return c.get(f"{API}/scans/{scan_id}").json()

        # Le worker doit consommer le scan (sortir de 'pending').
        result = poll_until(
            fetch,
            predicate=lambda s: s.get("status") != "pending",
            timeout_s=120.0,
            interval_s=5.0,
        )
        assert result.get("status") != "pending", (
            "scan de site reste 'pending' >120s : pipeline de scan mort ou bloque"
        )

        # S'il aboutit, le rapport PDF doit etre servi (status done + pdf_path).
        if result.get("status") == "done":
            pdf = c.get(f"{API}/scans/{scan_id}/pdf")
            assert pdf.status_code == 200, f"PDF indisponible sur scan done: {pdf.status_code}"
            assert pdf.headers.get("content-type", "").startswith("application/pdf")
    finally:
        deleted = c.delete(f"{API}/sites/{site_id}")
        assert deleted.status_code in (204, 404), f"delete site KO: {deleted.status_code}"
