"""
Coverage tests for app/api/v1/endpoints/phishing.py — targets error paths,
authorization/isolation, empty/limit states, validations, status transitions
and short-circuits that the main test_phishing.py suite does not exercise.

All email sending and PDF generation are mocked; no external service is hit.
asyncio_mode=auto → plain `async def test_*` (no decorator needed).
"""

import io
import unittest.mock as mock

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phishing import (
    PhishingCampaign,
    PhishingDomainVerification,
)
from app.services import phishing_service
from tests.conftest import create_plan_and_subscription, register_and_login


async def _grant_pro(client: AsyncClient) -> None:
    """Abonnement Pro (tier 3) pour le user courant — requis pour LANCER une
    campagne en mode entreprise directe (le gating par plan est au lancement)."""
    await create_plan_and_subscription(
        client, {"Authorization": client.headers["Authorization"]}, tier=3
    )


BASE = "/api/v1/phishing"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_campaign(client: AsyncClient, name="Campagne", tier="express") -> int:
    r = await client.post(f"{BASE}/campaigns", json={"name": name, "plan_tier": tier})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _csv_file(rows: list[str], header: str = "email,first_name") -> dict:
    content = header + "\n" + "\n".join(rows) + "\n"
    return {"file": ("targets.csv", io.BytesIO(content.encode("utf-8")), "text/csv")}


async def _fetch_campaign(db: AsyncSession, campaign_id: int) -> PhishingCampaign:
    result = await db.execute(select(PhishingCampaign).where(PhishingCampaign.id == campaign_id))
    return result.scalar_one()


# ---------------------------------------------------------------------------
# create_campaign — validation failures
# ---------------------------------------------------------------------------


class TestCreateCampaignValidation:
    async def test_invalid_tier_rejected_422(self, auth_client: AsyncClient):
        r = await auth_client.post(f"{BASE}/campaigns", json={"name": "Bad", "plan_tier": "gold"})
        assert r.status_code == 422

    async def test_too_short_name_rejected_422(self, auth_client: AsyncClient):
        r = await auth_client.post(f"{BASE}/campaigns", json={"name": "A", "plan_tier": "standard"})
        assert r.status_code == 422

    async def test_created_campaign_defaults(self, auth_client: AsyncClient):
        r = await auth_client.post(
            f"{BASE}/campaigns", json={"name": "Fresh", "plan_tier": "premium"}
        )
        data = r.json()
        assert data["status"] == "draft"
        assert data["targets_count"] == 0
        assert data["click_rate"] == 0


# ---------------------------------------------------------------------------
# Authorization / isolation — other user's campaign is invisible (404)
# ---------------------------------------------------------------------------


class TestCampaignIsolation:
    async def test_other_user_cannot_get_campaign(self, http_client: AsyncClient):
        h1 = await register_and_login(http_client, "owner@test.com")
        r = await http_client.post(
            f"{BASE}/campaigns",
            json={"name": "Owner camp", "plan_tier": "standard"},
            headers=h1,
        )
        cid = r.json()["id"]

        h2 = await register_and_login(http_client, "intruder@test.com")
        r2 = await http_client.get(f"{BASE}/campaigns/{cid}", headers=h2)
        assert r2.status_code == 404

    async def test_other_user_cannot_patch_campaign(self, http_client: AsyncClient):
        h1 = await register_and_login(http_client, "owner2@test.com")
        r = await http_client.post(
            f"{BASE}/campaigns",
            json={"name": "Owner camp", "plan_tier": "standard"},
            headers=h1,
        )
        cid = r.json()["id"]

        h2 = await register_and_login(http_client, "intruder2@test.com")
        r2 = await http_client.patch(f"{BASE}/campaigns/{cid}", json={"name": "Hacked"}, headers=h2)
        assert r2.status_code == 404

    async def test_other_user_cannot_launch_campaign(self, http_client: AsyncClient):
        h1 = await register_and_login(http_client, "owner3@test.com")
        cid = None
        r = await http_client.post(
            f"{BASE}/campaigns",
            json={"name": "Owner camp", "plan_tier": "standard"},
            headers=h1,
        )
        cid = r.json()["id"]

        h2 = await register_and_login(http_client, "intruder3@test.com")
        r2 = await http_client.post(f"{BASE}/campaigns/{cid}/launch", headers=h2)
        assert r2.status_code == 404

    async def test_other_user_cannot_list_targets(self, http_client: AsyncClient):
        h1 = await register_and_login(http_client, "owner4@test.com")
        r = await http_client.post(
            f"{BASE}/campaigns",
            json={"name": "Owner camp", "plan_tier": "standard"},
            headers=h1,
        )
        cid = r.json()["id"]

        h2 = await register_and_login(http_client, "intruder4@test.com")
        r2 = await http_client.get(f"{BASE}/campaigns/{cid}/targets", headers=h2)
        assert r2.status_code == 404

    async def test_list_only_returns_own_campaigns(self, http_client: AsyncClient):
        h1 = await register_and_login(http_client, "alice_list@test.com")
        await http_client.post(
            f"{BASE}/campaigns",
            json={"name": "Alice camp", "plan_tier": "standard"},
            headers=h1,
        )
        h2 = await register_and_login(http_client, "bob_list@test.com")
        r = await http_client.get(f"{BASE}/campaigns", headers=h2)
        assert r.status_code == 200
        assert r.json() == []


# ---------------------------------------------------------------------------
# update_campaign — status guard & domain verification branch
# ---------------------------------------------------------------------------


class TestUpdateCampaign:
    async def test_cannot_update_active_campaign(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        cid = await _create_campaign(auth_client)
        campaign = await _fetch_campaign(db_session, cid)
        campaign.status = "active"
        await db_session.commit()

        r = await auth_client.patch(f"{BASE}/campaigns/{cid}", json={"name": "Nope"})
        assert r.status_code == 400
        assert "active" in r.json()["detail"].lower()

    async def test_cannot_update_completed_campaign(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        cid = await _create_campaign(auth_client)
        campaign = await _fetch_campaign(db_session, cid)
        campaign.status = "completed"
        await db_session.commit()

        r = await auth_client.patch(f"{BASE}/campaigns/{cid}", json={"name": "Nope"})
        assert r.status_code == 400

    async def test_domain_change_unverified_sets_false(self, auth_client: AsyncClient):
        cid = await _create_campaign(auth_client)
        # No verification record exists for this domain → domain_verified stays False
        r = await auth_client.patch(f"{BASE}/campaigns/{cid}", json={"domain": "newdomain.com"})
        assert r.status_code == 200
        body = r.json()
        assert body["domain"] == "newdomain.com"
        assert body["domain_verified"] is False

    async def test_domain_change_verified_sets_true(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        cid = await _create_campaign(auth_client)
        campaign = await _fetch_campaign(db_session, cid)
        user_id = campaign.user_id
        # Seed a verified domain-verification row for this user
        db_session.add(
            PhishingDomainVerification(
                user_id=user_id,
                domain="verified.com",
                verification_token="tok",
                verified=True,
            )
        )
        await db_session.commit()

        r = await auth_client.patch(f"{BASE}/campaigns/{cid}", json={"domain": "verified.com"})
        assert r.status_code == 200
        assert r.json()["domain_verified"] is True

    async def test_update_scenarios_and_cgu(self, auth_client: AsyncClient):
        cid = await _create_campaign(auth_client)
        r = await auth_client.patch(
            f"{BASE}/campaigns/{cid}",
            json={"scenario_keys": ["ceo-fraud", "o365-credentials"], "cgu_accepted": True},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["scenario_keys"] == ["ceo-fraud", "o365-credentials"]
        assert body["cgu_accepted"] is True

    async def test_update_nonexistent_returns_404(self, auth_client: AsyncClient):
        r = await auth_client.patch(f"{BASE}/campaigns/999999", json={"name": "Valid Name"})
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# upload_targets — validations, limits, decode, empty
# ---------------------------------------------------------------------------


class TestUploadTargets:
    async def test_rejects_non_csv_extension(self, auth_client: AsyncClient):
        cid = await _create_campaign(auth_client)
        files = {"file": ("targets.txt", io.BytesIO(b"email\na@b.com\n"), "text/plain")}
        r = await auth_client.post(f"{BASE}/campaigns/{cid}/targets", files=files)
        assert r.status_code == 400
        assert "csv" in r.json()["detail"].lower()

    async def test_empty_csv_returns_400(self, auth_client: AsyncClient):
        cid = await _create_campaign(auth_client)
        # Header only, no valid emails
        files = {"file": ("targets.csv", io.BytesIO(b"email,first_name\n"), "text/csv")}
        r = await auth_client.post(f"{BASE}/campaigns/{cid}/targets", files=files)
        assert r.status_code == 400
        assert "email valide" in r.json()["detail"].lower()

    async def test_rows_without_at_sign_skipped(self, auth_client: AsyncClient):
        cid = await _create_campaign(auth_client)
        files = _csv_file(["notanemail,Bob", "real@corp.com,Alice"])
        r = await auth_client.post(f"{BASE}/campaigns/{cid}/targets", files=files)
        assert r.status_code == 200
        assert r.json()["targets_added"] == 1

    async def test_rough_count_over_limit_rejected(self, auth_client: AsyncClient):
        # express tier limit = 50; produce a file with > 55 newlines to trip the
        # rough-count short-circuit before full parse.
        cid = await _create_campaign(auth_client, tier="express")
        rows = [f"user{i}@corp.com,Name{i}" for i in range(60)]
        files = _csv_file(rows)
        r = await auth_client.post(f"{BASE}/campaigns/{cid}/targets", files=files)
        assert r.status_code == 400
        assert "50" in r.json()["detail"]

    async def test_latin1_fallback_decoding(self, auth_client: AsyncClient):
        cid = await _create_campaign(auth_client)
        # Bytes that are invalid utf-8 (0xE9 = é in latin-1) → forces latin-1 fallback
        raw = "email,first_name\njos\xe9@corp.com,Jos\xe9\n".encode("latin-1")
        files = {"file": ("targets.csv", io.BytesIO(raw), "text/csv")}
        r = await auth_client.post(f"{BASE}/campaigns/{cid}/targets", files=files)
        assert r.status_code == 200
        assert r.json()["targets_added"] == 1

    async def test_cannot_upload_when_active(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        cid = await _create_campaign(auth_client)
        campaign = await _fetch_campaign(db_session, cid)
        campaign.status = "active"
        await db_session.commit()

        files = _csv_file(["a@corp.com,A"])
        r = await auth_client.post(f"{BASE}/campaigns/{cid}/targets", files=files)
        assert r.status_code == 400
        assert "active" in r.json()["detail"].lower()

    async def test_upload_to_nonexistent_campaign_404(self, auth_client: AsyncClient):
        files = _csv_file(["a@corp.com,A"])
        r = await auth_client.post(f"{BASE}/campaigns/999999/targets", files=files)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# launch_campaign — pre-flight validations & background task
# ---------------------------------------------------------------------------


class TestLaunchValidations:
    async def test_launch_no_targets_400(self, auth_client: AsyncClient):
        cid = await _create_campaign(auth_client)
        r = await auth_client.post(f"{BASE}/campaigns/{cid}/launch")
        assert r.status_code == 400
        assert "cible" in r.json()["detail"].lower()

    async def test_launch_no_scenario_400(self, auth_client: AsyncClient, db_session: AsyncSession):
        cid = await _create_campaign(auth_client)
        # Upload targets so targets_count > 0, but leave scenario_keys empty
        files = _csv_file(["a@corp.com,A"])
        await auth_client.post(f"{BASE}/campaigns/{cid}/targets", files=files)

        r = await auth_client.post(f"{BASE}/campaigns/{cid}/launch")
        assert r.status_code == 400
        assert "scénario" in r.json()["detail"].lower()

    async def test_launch_cgu_not_accepted_400(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        cid = await _create_campaign(auth_client)
        await _grant_pro(auth_client)
        files = _csv_file(["a@corp.com,A"])
        await auth_client.post(f"{BASE}/campaigns/{cid}/targets", files=files)
        await auth_client.patch(f"{BASE}/campaigns/{cid}", json={"scenario_keys": ["ceo-fraud"]})

        r = await auth_client.post(f"{BASE}/campaigns/{cid}/launch")
        assert r.status_code == 400
        assert "conditions" in r.json()["detail"].lower()

    async def test_launch_active_campaign_rejected_400(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        cid = await _create_campaign(auth_client)
        campaign = await _fetch_campaign(db_session, cid)
        campaign.status = "active"
        await db_session.commit()

        r = await auth_client.post(f"{BASE}/campaigns/{cid}/launch")
        assert r.status_code == 400
        assert "active" in r.json()["detail"].lower()

    async def test_launch_success_transitions_to_sending(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        cid = await _create_campaign(auth_client)
        await _grant_pro(auth_client)
        files = _csv_file(["a@corp.com,A"])
        await auth_client.post(f"{BASE}/campaigns/{cid}/targets", files=files)
        await auth_client.patch(
            f"{BASE}/campaigns/{cid}",
            json={"scenario_keys": ["ceo-fraud"], "cgu_accepted": True},
        )

        # Mock the background batch so no real Resend send happens.
        async def _noop_batch():
            return None

        with mock.patch.object(phishing_service, "send_pending_batch", side_effect=_noop_batch):
            r = await auth_client.post(f"{BASE}/campaigns/{cid}/launch")

        assert r.status_code == 202
        body = r.json()
        assert body["status"] == "sending"
        assert body["campaign_id"] == cid

        campaign = await _fetch_campaign(db_session, cid)
        assert campaign.status == "sending"
        assert campaign.started_at is not None

    async def test_launch_value_error_returns_400(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        cid = await _create_campaign(auth_client)
        await _grant_pro(auth_client)
        files = _csv_file(["a@corp.com,A"])
        await auth_client.post(f"{BASE}/campaigns/{cid}/targets", files=files)
        await auth_client.patch(
            f"{BASE}/campaigns/{cid}",
            json={"scenario_keys": ["ceo-fraud"], "cgu_accepted": True},
        )

        async def _raise_value_error(campaign, db):
            raise ValueError("boom-validation")

        with mock.patch.object(phishing_service, "launch_campaign", side_effect=_raise_value_error):
            r = await auth_client.post(f"{BASE}/campaigns/{cid}/launch")
        assert r.status_code == 400
        assert "boom-validation" in r.json()["detail"]

    async def test_launch_unexpected_error_returns_502(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        cid = await _create_campaign(auth_client)
        await _grant_pro(auth_client)
        files = _csv_file(["a@corp.com,A"])
        await auth_client.post(f"{BASE}/campaigns/{cid}/targets", files=files)
        await auth_client.patch(
            f"{BASE}/campaigns/{cid}",
            json={"scenario_keys": ["ceo-fraud"], "cgu_accepted": True},
        )

        async def _raise_unexpected(campaign, db):
            raise KeyError("unexpected internal")

        with mock.patch.object(phishing_service, "launch_campaign", side_effect=_raise_unexpected):
            r = await auth_client.post(f"{BASE}/campaigns/{cid}/launch")
        assert r.status_code == 502
        # Raw exception detail must not leak
        assert "unexpected internal" not in r.json()["detail"]

    async def test_launch_without_plan_is_403(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        # Campagne entreprise ENTIEREMENT configurée mais SANS abonnement Pro :
        # le lancement (l'envoi réel) est gaté par le plan.
        cid = await _create_campaign(auth_client)
        files = _csv_file(["a@corp.com,A"])
        await auth_client.post(f"{BASE}/campaigns/{cid}/targets", files=files)
        await auth_client.patch(
            f"{BASE}/campaigns/{cid}",
            json={"scenario_keys": ["ceo-fraud"], "cgu_accepted": True},
        )
        r = await auth_client.post(f"{BASE}/campaigns/{cid}/launch")
        assert r.status_code == 403
        assert "abonnement" in r.json()["detail"].lower()


# ---------------------------------------------------------------------------
# download_report_pdf — status guard, empty campaign, success
# ---------------------------------------------------------------------------


class TestDownloadPdf:
    async def test_pdf_unavailable_for_draft(self, auth_client: AsyncClient):
        cid = await _create_campaign(auth_client)
        r = await auth_client.get(f"{BASE}/campaigns/{cid}/pdf")
        assert r.status_code == 400
        assert "rapport" in r.json()["detail"].lower()

    async def test_pdf_generated_for_completed_empty_campaign(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        cid = await _create_campaign(auth_client)
        campaign = await _fetch_campaign(db_session, cid)
        campaign.status = "completed"
        await db_session.commit()

        # Mock PDF generation so the report library isn't exercised here.
        with mock.patch(
            "app.api.v1.endpoints.phishing.generate_phishing_report",
            return_value=b"%PDF-fake",
        ) as m:
            r = await auth_client.get(f"{BASE}/campaigns/{cid}/pdf")
        assert r.status_code == 200
        assert r.headers["content-type"] == "application/pdf"
        assert "attachment" in r.headers["content-disposition"]
        # Called with the (empty) target list
        assert m.call_args.args[1] == []

    async def test_pdf_for_active_campaign_ok(
        self, auth_client: AsyncClient, db_session: AsyncSession
    ):
        cid = await _create_campaign(auth_client)
        campaign = await _fetch_campaign(db_session, cid)
        campaign.status = "active"
        await db_session.commit()

        with mock.patch(
            "app.api.v1.endpoints.phishing.generate_phishing_report",
            return_value=b"%PDF-fake",
        ):
            r = await auth_client.get(f"{BASE}/campaigns/{cid}/pdf")
        assert r.status_code == 200

    async def test_pdf_nonexistent_campaign_404(self, auth_client: AsyncClient):
        r = await auth_client.get(f"{BASE}/campaigns/999999/pdf")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# get_campaign / list_targets — include targets, empty states
# ---------------------------------------------------------------------------


class TestCampaignReads:
    async def test_get_campaign_includes_targets(self, auth_client: AsyncClient):
        cid = await _create_campaign(auth_client)
        files = _csv_file(["x@corp.com,X", "y@corp.com,Y"])
        await auth_client.post(f"{BASE}/campaigns/{cid}/targets", files=files)

        r = await auth_client.get(f"{BASE}/campaigns/{cid}")
        assert r.status_code == 200
        body = r.json()
        assert len(body["targets"]) == 2
        assert {t["email"] for t in body["targets"]} == {"x@corp.com", "y@corp.com"}

    async def test_list_targets_empty(self, auth_client: AsyncClient):
        cid = await _create_campaign(auth_client)
        r = await auth_client.get(f"{BASE}/campaigns/{cid}/targets")
        assert r.status_code == 200
        assert r.json() == []


# ---------------------------------------------------------------------------
# domain-verify endpoints
# ---------------------------------------------------------------------------


class TestDomainVerify:
    async def test_request_domain_verification_returns_token(self, auth_client: AsyncClient):
        r = await auth_client.post(f"{BASE}/domain-verify", json={"domain": "Example.COM"})
        assert r.status_code == 201
        body = r.json()
        assert body["domain"] == "example.com"  # lowercased
        assert body["verified"] is False
        assert body["verification_token"]
        assert body["dns_record_name"] == "_rocher-verify.example.com"
        assert body["dns_record_type"] == "TXT"

    async def test_check_without_request_returns_404(self, auth_client: AsyncClient):
        r = await auth_client.post(
            f"{BASE}/domain-verify/check", json={"domain": "never-requested.com"}
        )
        assert r.status_code == 404
        assert "aucune demande" in r.json()["detail"].lower()

    async def test_check_after_request_verifies_in_dev(self, auth_client: AsyncClient):
        # In development APP_ENV, check_domain_verification auto-verifies.
        await auth_client.post(f"{BASE}/domain-verify", json={"domain": "devcheck.com"})
        r = await auth_client.post(f"{BASE}/domain-verify/check", json={"domain": "devcheck.com"})
        assert r.status_code == 200
        body = r.json()
        assert body["domain"] == "devcheck.com"
        assert body["verified"] is True
        assert body["verified_at"] is not None

    async def test_domain_verify_isolation(self, http_client: AsyncClient):
        h1 = await register_and_login(http_client, "dv_owner@test.com")
        await http_client.post(f"{BASE}/domain-verify", json={"domain": "shared.com"}, headers=h1)
        # Another user checking the same domain string has no record of their own → 404
        h2 = await register_and_login(http_client, "dv_other@test.com")
        r = await http_client.post(
            f"{BASE}/domain-verify/check", json={"domain": "shared.com"}, headers=h2
        )
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Unauthenticated access is rejected on protected routes
# ---------------------------------------------------------------------------


class TestAuthRequired:
    async def test_create_requires_auth(self, http_client: AsyncClient):
        r = await http_client.post(f"{BASE}/campaigns", json={"name": "X", "plan_tier": "standard"})
        assert r.status_code in (401, 403)

    async def test_domain_verify_requires_auth(self, http_client: AsyncClient):
        r = await http_client.post(f"{BASE}/domain-verify", json={"domain": "x.com"})
        assert r.status_code in (401, 403)
