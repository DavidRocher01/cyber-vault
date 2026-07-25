"""
Integration tests — user profile endpoints.
Covers: update email, update password, export RGPD, delete account.
Parcours #43–#49.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


async def _auth(client: AsyncClient, email: str, password: str = "StrongPass123!") -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": password})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── Update email ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_email_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "email1@test.com")
        r = await c.put(
            f"{BASE}/users/me/email",
            headers=h,
            json={
                "email": "newemail1@test.com",
                "current_password": "StrongPass123!",
            },
        )
    assert r.status_code == 200
    assert r.json()["email"] == "newemail1@test.com"


@pytest.mark.asyncio
async def test_update_email_wrong_password_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "email2@test.com")
        r = await c.put(
            f"{BASE}/users/me/email",
            headers=h,
            json={
                "email": "newemail2@test.com",
                "current_password": "WrongPassword!",
            },
        )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_update_email_duplicate_returns_409():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "taken@test.com", "password": "StrongPass123!"},
        )
        h = await _auth(c, "email3@test.com")
        r = await c.put(
            f"{BASE}/users/me/email",
            headers=h,
            json={
                "email": "taken@test.com",
                "current_password": "StrongPass123!",
            },
        )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_update_email_invalid_format_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "email4@test.com")
        r = await c.put(
            f"{BASE}/users/me/email",
            headers=h,
            json={
                "email": "not-an-email",
                "current_password": "StrongPass123!",
            },
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_email_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.put(
            f"{BASE}/users/me/email",
            json={
                "email": "x@test.com",
                "current_password": "any",
            },
        )
    assert r.status_code == 401


# ── Update password ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_password_success_returns_204():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "pw1@test.com")
        r = await c.put(
            f"{BASE}/users/me/password",
            headers=h,
            json={
                "current_password": "StrongPass123!",
                "new_password": "NewStrongPass456!",
            },
        )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_update_password_allows_login_with_new_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "pw2@test.com")
        await c.put(
            f"{BASE}/users/me/password",
            headers=h,
            json={
                "current_password": "StrongPass123!",
                "new_password": "NewStrongPass456!",
            },
        )
        login = await c.post(
            f"{BASE}/auth/login",
            json={"email": "pw2@test.com", "password": "NewStrongPass456!"},
        )
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_update_password_old_password_no_longer_works():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "pw3@test.com")
        await c.put(
            f"{BASE}/users/me/password",
            headers=h,
            json={
                "current_password": "StrongPass123!",
                "new_password": "NewStrongPass456!",
            },
        )
        old = await c.post(
            f"{BASE}/auth/login",
            json={"email": "pw3@test.com", "password": "StrongPass123!"},
        )
    assert old.status_code == 401


@pytest.mark.asyncio
async def test_update_password_wrong_current_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "pw4@test.com")
        r = await c.put(
            f"{BASE}/users/me/password",
            headers=h,
            json={
                "current_password": "WrongPassword!",
                "new_password": "NewStrongPass456!",
            },
        )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_update_password_too_short_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "pw5@test.com")
        r = await c.put(
            f"{BASE}/users/me/password",
            headers=h,
            json={
                "current_password": "StrongPass123!",
                "new_password": "short",
            },
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_password_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.put(
            f"{BASE}/users/me/password",
            json={
                "current_password": "any",
                "new_password": "NewStrongPass456!",
            },
        )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_update_password_revokes_existing_sessions():
    """G0-0 : un refresh token émis avant le changement de mot de passe doit être
    rejeté après (invalidation de session, comme le reset)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "pw-sess@test.com")
        # Le refresh (cookie httpOnly) fonctionne avant le changement.
        assert (await c.post(f"{BASE}/auth/refresh")).status_code == 200

        r = await c.put(
            f"{BASE}/users/me/password",
            headers=h,
            json={
                "current_password": "StrongPass123!",
                "new_password": "NewStrongPass456!",
            },
        )
        assert r.status_code == 204

        # Après changement : tous les refresh tokens sont révoqués -> 401.
        assert (await c.post(f"{BASE}/auth/refresh")).status_code == 401


@pytest.mark.asyncio
async def test_update_email_revokes_existing_sessions():
    """G0-1 : un refresh token émis avant le changement d'email doit être rejeté
    après (invalidation de session)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "email-sess@test.com")
        # Le refresh (cookie httpOnly) fonctionne avant le changement.
        assert (await c.post(f"{BASE}/auth/refresh")).status_code == 200

        r = await c.put(
            f"{BASE}/users/me/email",
            headers=h,
            json={
                "email": "email-sess-new@test.com",
                "current_password": "StrongPass123!",
            },
        )
        assert r.status_code == 200

        # Après changement : tous les refresh tokens sont révoqués -> 401.
        assert (await c.post(f"{BASE}/auth/refresh")).status_code == 401


# ── Export RGPD ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_my_data_returns_json():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "export1@test.com")
        r = await c.get(f"{BASE}/users/me/export", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
async def test_export_my_data_contains_account_info():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "export2@test.com")
        r = await c.get(f"{BASE}/users/me/export", headers=h)
    data = r.json()
    assert "account" in data
    assert data["account"]["email"] == "export2@test.com"


@pytest.mark.asyncio
async def test_export_my_data_contains_sites_and_scans_keys():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "export3@test.com")
        r = await c.get(f"{BASE}/users/me/export", headers=h)
    data = r.json()
    assert "sites" in data
    assert "scans" in data
    assert isinstance(data["sites"], list)
    assert isinstance(data["scans"], list)


@pytest.mark.asyncio
async def test_export_my_data_contains_exported_at():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "export4@test.com")
        r = await c.get(f"{BASE}/users/me/export", headers=h)
    assert "exported_at" in r.json()


@pytest.mark.asyncio
async def test_export_my_data_has_content_disposition_header():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "export5@test.com")
        r = await c.get(f"{BASE}/users/me/export", headers=h)
    assert "content-disposition" in r.headers
    assert "attachment" in r.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_my_data_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/users/me/export")
    assert r.status_code == 401


# ── Delete account ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_account_success_returns_204():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "del1@test.com")
        r = await c.request(
            "DELETE", f"{BASE}/users/me", headers=h, json={"password": "StrongPass123!"}
        )
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_account_prevents_further_login():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "del2@test.com")
        await c.request(
            "DELETE", f"{BASE}/users/me", headers=h, json={"password": "StrongPass123!"}
        )
        login = await c.post(
            f"{BASE}/auth/login",
            json={"email": "del2@test.com", "password": "StrongPass123!"},
        )
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_wrong_password_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "del3@test.com")
        r = await c.request(
            "DELETE", f"{BASE}/users/me", headers=h, json={"password": "WrongPassword!"}
        )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.request("DELETE", f"{BASE}/users/me", json={"password": "any"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_token_no_longer_valid_after_deletion():
    """Après suppression, l'access token existant ne doit plus fonctionner."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "del4@test.com")
        await c.request(
            "DELETE", f"{BASE}/users/me", headers=h, json={"password": "StrongPass123!"}
        )
        r = await c.get(f"{BASE}/users/me", headers=h)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejected_when_account_deactivated():
    """G0-3 : un compte désactivé ne doit plus pouvoir renouveler son access token,
    même si son refresh token cookie n'est pas encore expiré (le token reste valide,
    c'est le compte inactif qui bloque)."""
    from sqlalchemy import update

    import app.core.database as _db
    from app.models.user import User

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await _auth(c, "deact@test.com")
        # Le refresh fonctionne tant que le compte est actif (et tourne le cookie).
        assert (await c.post(f"{BASE}/auth/refresh")).status_code == 200

        async with _db.AsyncSessionLocal() as db:
            await db.execute(
                update(User).where(User.email == "deact@test.com").values(is_active=False)
            )
            await db.commit()

        # Compte désactivé : le refresh est refusé bien que le cookie soit encore valide.
        assert (await c.post(f"{BASE}/auth/refresh")).status_code == 401


# ── Suppression de compte : cascade FK & retention legale (G0-2) ────────────────


def _uid(headers: dict) -> int:
    from app.core.security import decode_access_token

    return int(decode_access_token(headers["Authorization"].removeprefix("Bearer ").strip()))


@pytest.mark.asyncio
async def test_delete_account_cascades_children_and_keeps_legal_records():
    """G0-2 : supprimer un compte porteur de donnees liees ne doit pas lever de 500.
    Les donnees possedees cascadent ; factures/devis sont CONSERVES (retention legale
    ~10 ans) avec le lien personnel detache (user_id -> NULL)."""
    from datetime import date

    from sqlalchemy import select

    import app.core.database as _db
    from app.models.invoice import Invoice
    from app.models.nis2_assessment import Nis2Assessment
    from app.models.quote import Quote
    from app.models.scan import Scan
    from app.models.site import Site

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "casc1@test.com")
        uid = _uid(h)

        async with _db.AsyncSessionLocal() as db:
            site = Site(user_id=uid, url="https://ex.com", name="ex")
            db.add(site)
            await db.flush()
            db.add(Scan(site_id=site.id, status="done"))  # chaine 2e niveau via sites.id
            db.add(Nis2Assessment(user_id=uid))
            db.add(
                Invoice(
                    invoice_number="F-2026-0001",
                    invoice_seq=1,
                    invoice_year=2026,
                    user_id=uid,
                    type="subscription",
                    client_name="Client SARL",
                    client_email="c@ex.com",
                    description="Abonnement Pro",
                    amount_cents=4900,
                    issue_date=date(2026, 1, 1),
                )
            )
            db.add(
                Quote(
                    quote_number="D-2026-0001",
                    quote_seq=1,
                    quote_year=2026,
                    user_id=uid,
                    client_name="Client SARL",
                    client_email="c@ex.com",
                    subject="Audit",
                    total_cents=100000,
                    issue_date=date(2026, 1, 1),
                )
            )
            await db.commit()

        r = await c.request(
            "DELETE", f"{BASE}/users/me", headers=h, json={"password": "StrongPass123!"}
        )
    assert r.status_code == 204

    async with _db.AsyncSessionLocal() as db:
        # CASCADE : donnees possedees supprimees avec le compte
        assert (await db.execute(select(Site).where(Site.user_id == uid))).first() is None
        assert (await db.execute(select(Scan))).first() is None
        assert (
            await db.execute(select(Nis2Assessment).where(Nis2Assessment.user_id == uid))
        ).first() is None
        # SET NULL : facture/devis conserves, lien personnel detache, montants intacts
        inv = (await db.execute(select(Invoice))).scalar_one()
        assert inv.user_id is None
        assert inv.amount_cents == 4900
        quo = (await db.execute(select(Quote))).scalar_one()
        assert quo.user_id is None
        assert quo.total_cents == 100000


@pytest.mark.asyncio
async def test_delete_portal_client_keeps_consultant_client_record():
    """PIEGE double role : supprimer le compte d'un CLIENT de portail ne doit pas
    detruire la fiche rssi_clients (elle appartient au CONSULTANT) — seulement couper
    le lien de portail (client_user_id -> NULL)."""
    from sqlalchemy import select

    import app.core.database as _db
    from app.models.rssi_client import RssiClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        hc = await _auth(c, "consultant-del@test.com")
        hb = await _auth(c, "portal-client-del@test.com")
        consultant_id = _uid(hc)
        client_id = _uid(hb)

        async with _db.AsyncSessionLocal() as db:
            db.add(
                RssiClient(
                    consultant_user_id=consultant_id, client_user_id=client_id, name="Acme SARL"
                )
            )
            await db.commit()

        # Le CLIENT de portail supprime SON compte
        r = await c.request(
            "DELETE", f"{BASE}/users/me", headers=hb, json={"password": "StrongPass123!"}
        )
    assert r.status_code == 204

    async with _db.AsyncSessionLocal() as db:
        rc = (await db.execute(select(RssiClient))).scalar_one()  # la fiche EXISTE toujours
        assert rc.consultant_user_id == consultant_id
        assert rc.client_user_id is None  # lien de portail coupe


# ── Notification preferences ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_notification_preferences_defaults_all_true():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "notif1@test.com")
        r = await c.get(f"{BASE}/users/me/notification-preferences", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["notif_scan_done"] is True
    assert data["notif_scan_critical"] is True
    assert data["notif_url_scan_done"] is True
    assert data["notif_code_scan_done"] is True


@pytest.mark.asyncio
async def test_update_notification_preferences_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "notif2@test.com")
        r = await c.put(
            f"{BASE}/users/me/notification-preferences",
            headers=h,
            json={
                "notif_scan_done": False,
                "notif_scan_critical": True,
                "notif_url_scan_done": False,
                "notif_code_scan_done": True,
                "notif_ssl_expiry": True,
            },
        )
    assert r.status_code == 200
    data = r.json()
    assert data["notif_scan_done"] is False
    assert data["notif_scan_critical"] is True
    assert data["notif_url_scan_done"] is False
    assert data["notif_code_scan_done"] is True


@pytest.mark.asyncio
async def test_update_notification_preferences_persisted():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "notif3@test.com")
        await c.put(
            f"{BASE}/users/me/notification-preferences",
            headers=h,
            json={
                "notif_scan_done": False,
                "notif_scan_critical": False,
                "notif_url_scan_done": True,
                "notif_code_scan_done": True,
                "notif_ssl_expiry": True,
            },
        )
        r = await c.get(f"{BASE}/users/me/notification-preferences", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["notif_scan_done"] is False
    assert data["notif_scan_critical"] is False


@pytest.mark.asyncio
async def test_get_notification_preferences_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/users/me/notification-preferences")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_update_notification_preferences_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.put(
            f"{BASE}/users/me/notification-preferences",
            json={
                "notif_scan_done": False,
                "notif_scan_critical": False,
                "notif_url_scan_done": False,
                "notif_code_scan_done": False,
            },
        )
    assert r.status_code == 401
