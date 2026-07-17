"""Parcours d'authentification : login, /me, refresh (cookie), logout, et le
chemin d'erreur critique (bad creds -> 401, jamais 500 = regression PyJWT)."""

from conftest import API, CANARY_EMAIL, CANARY_PASSWORD, requires_canary


def test_login_bad_credentials_returns_401(client):
    """Chemin auth le plus important a surveiller : de mauvais identifiants
    doivent renvoyer 401. Un 500 ici = casse runtime du hashing/JWT."""
    r = client.post(
        f"{API}/auth/login",
        json={"email": "nobody-recette@example.com", "password": "definitely-wrong"},
    )
    assert r.status_code == 401, f"attendu 401, recu {r.status_code}: {r.text[:200]}"


@requires_canary
def test_login_returns_bearer_token(canary):
    assert canary["token"], "pas de bearer token apres login canari"


@requires_canary
def test_me_returns_canary_identity(canary):
    c = canary["client"]
    r = c.get(f"{API}/users/me")
    assert r.status_code == 200, f"/users/me KO: {r.status_code} {r.text[:200]}"
    body = r.json()
    assert body["email"].lower() == CANARY_EMAIL.lower(), f"identite inattendue: {body}"
    assert body["is_active"] is True


@requires_canary
def test_refresh_rotates_access_token(client):
    """Le refresh lit le cookie httpOnly pose au login et rend un nouveau token."""
    login = client.post(
        f"{API}/auth/login",
        json={"email": CANARY_EMAIL, "password": CANARY_PASSWORD},
    )
    assert login.status_code == 200
    # Le cookie refresh_token est desormais dans le jar du client.
    r = client.post(f"{API}/auth/refresh")
    assert r.status_code == 200, f"refresh KO: {r.status_code} {r.text[:200]}"
    assert r.json().get("access_token"), "refresh sans access_token"


@requires_canary
def test_logout_revokes_session(client):
    login = client.post(
        f"{API}/auth/login",
        json={"email": CANARY_EMAIL, "password": CANARY_PASSWORD},
    )
    assert login.status_code == 200
    out = client.post(f"{API}/auth/logout")
    assert out.status_code == 204, f"logout KO: {out.status_code}"
    # Apres logout, le refresh doit etre refuse (session revoquee).
    again = client.post(f"{API}/auth/refresh")
    assert again.status_code == 401, f"refresh doit etre 401 apres logout, recu {again.status_code}"
