"""Module RSSI (B2B) : le canari (consultant) cree un client, le retrouve dans
la liste, puis le supprime. On N'APPELLE PAS /invite (qui enverrait un email)."""

import time

from conftest import API, MARKER, requires_canary


@requires_canary
def test_rssi_client_create_list_delete(canary):
    c = canary["client"]
    name = f"{MARKER}-client-{int(time.time())}"

    created = c.post(
        f"{API}/rssi/clients",
        json={"name": name, "email": "recette-client@example.com", "formula": "essentiel"},
    )
    assert created.status_code == 201, (
        f"create client KO: {created.status_code} {created.text[:200]}"
    )
    client_id = created.json()["id"]

    try:
        listed = c.get(f"{API}/rssi/clients")
        assert listed.status_code == 200
        ids = [cl["id"] for cl in listed.json()]
        assert client_id in ids, "le client cree n'apparait pas dans la liste"
    finally:
        deleted = c.delete(f"{API}/rssi/clients/{client_id}")
        assert deleted.status_code == 204, f"delete client KO: {deleted.status_code}"
