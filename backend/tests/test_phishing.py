"""
Tests for the phishing simulation module.

Sections:
  1. Pure unit tests (no DB / HTTP) — pixel GIF, HTML pages, email builder
  2. Tracking routes (public, no auth)  — open / click / land / submit
  3. State-machine & counter tests — progression email_sent→opened→clicked→submitted
  4. Campaign CRUD (authenticated)
  5. Look-alike domains endpoint
"""
import json
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.phishing import PhishingCampaign, PhishingTarget
from app.services import phishing_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed(db: AsyncSession, *, tracking_id: str = "tid-001", status: str = "email_sent"):
    """Insert a minimal campaign + target into the test DB and return (campaign, target)."""
    campaign = PhishingCampaign(
        user_id=1,
        name="Test Campagne",
        plan_tier="standard",
        status="active",
        domain="acme.com",
        domain_verified=True,
        cgu_accepted=True,
        scenario_keys='["o365-credentials"]',
        targets_count=1,
        emails_sent=1,
        opened_count=0,
        clicked_count=0,
        submitted_count=0,
    )
    db.add(campaign)
    await db.flush()

    target = PhishingTarget(
        campaign_id=campaign.id,
        email="cible@acme.com",
        first_name="Jean",
        tracking_id=tracking_id,
        status=status,
    )
    db.add(target)
    await db.commit()
    await db.refresh(campaign)
    await db.refresh(target)
    return campaign, target


# ---------------------------------------------------------------------------
# 1. Pure unit tests
# ---------------------------------------------------------------------------

class TestPixelGif:
    def test_returns_bytes(self):
        assert isinstance(phishing_service.get_pixel_gif(), bytes)

    def test_starts_with_gif_header(self):
        assert phishing_service.get_pixel_gif()[:6] == b"GIF89a"

    def test_length_is_nonzero(self):
        assert len(phishing_service.get_pixel_gif()) > 0


class TestLandingHtml:
    def test_returns_string(self):
        assert isinstance(phishing_service.get_landing_html("abc"), str)

    def test_contains_form(self):
        html = phishing_service.get_landing_html("abc")
        assert "<form" in html

    def test_form_action_points_to_submit_route(self):
        html = phishing_service.get_landing_html("my-id")
        assert "/phishing/t/my-id/s" in html

    def test_different_tracking_ids_give_different_actions(self):
        assert phishing_service.get_landing_html("id-1") != phishing_service.get_landing_html("id-2")


class TestAwarenessHtml:
    def test_returns_string(self):
        assert isinstance(phishing_service.get_awareness_html(), str)

    def test_mentions_phishing(self):
        html = phishing_service.get_awareness_html().lower()
        assert "phishing" in html

    def test_is_same_every_call(self):
        assert phishing_service.get_awareness_html() == phishing_service.get_awareness_html()


class TestBuildEmail:
    def _make_campaign(self, lookalike=None, scenario_key="o365-credentials"):
        return SimpleNamespace(
            lookalike_domain=lookalike,
            scenario_keys=json.dumps([scenario_key]),
        )

    def _make_target(self, first_name="Marie"):
        return SimpleNamespace(
            first_name=first_name,
            email="marie@acme.com",
        )

    def test_returns_four_values(self):
        result = phishing_service._build_email(
            self._make_campaign(), self._make_target(), "abc-123", "o365-credentials"
        )
        assert len(result) == 4

    def test_html_contains_tracking_id(self):
        _, _, html, _ = phishing_service._build_email(
            self._make_campaign(), self._make_target(), "abc-123", "o365-credentials"
        )
        assert "abc-123" in html

    def test_html_contains_first_name(self):
        _, _, html, _ = phishing_service._build_email(
            self._make_campaign(), self._make_target("Isabelle"), "x", "o365-credentials"
        )
        assert "Isabelle" in html

    def test_subject_is_nonempty(self):
        _, subject, _, _ = phishing_service._build_email(
            self._make_campaign(), self._make_target(), "x", "o365-credentials"
        )
        assert subject

    def test_lookalike_domain_used_in_urls(self):
        _, _, html, _ = phishing_service._build_email(
            self._make_campaign(lookalike="secure-acme.com"),
            self._make_target(), "x", "o365-credentials",
        )
        assert "secure-acme.com" in html

    def test_fallback_to_base_url_when_no_lookalike(self):
        from app.core.config import settings
        _, _, html, _ = phishing_service._build_email(
            self._make_campaign(lookalike=None), self._make_target(), "x", "o365-credentials"
        )
        assert settings.PHISHING_BASE_URL.rstrip("/").split("//")[1] in html

    def test_all_scenario_keys_produce_html(self):
        keys = list(phishing_service._SCENARIO_TEMPLATES.keys())
        for key in keys:
            _, _, html, text = phishing_service._build_email(
                self._make_campaign(scenario_key=key), self._make_target(), "x", key
            )
            assert html
            assert text


# ---------------------------------------------------------------------------
# 2. Tracking routes — public (no auth)
# ---------------------------------------------------------------------------

class TestTrackingPixel:
    @pytest.mark.asyncio
    async def test_returns_gif(self, http_client: AsyncClient, db_session: AsyncSession):
        await _seed(db_session, tracking_id="px-001")
        r = await http_client.get("/api/v1/phishing/t/px-001/px")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/gif"

    @pytest.mark.asyncio
    async def test_gif_bytes_match(self, http_client: AsyncClient, db_session: AsyncSession):
        await _seed(db_session, tracking_id="px-002")
        r = await http_client.get("/api/v1/phishing/t/px-002/px")
        assert r.content[:6] == b"GIF89a"

    @pytest.mark.asyncio
    async def test_unknown_tracking_id_still_returns_200(self, http_client: AsyncClient):
        r = await http_client.get("/api/v1/phishing/t/unknown-id/px")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_no_cache_headers(self, http_client: AsyncClient, db_session: AsyncSession):
        await _seed(db_session, tracking_id="px-003")
        r = await http_client.get("/api/v1/phishing/t/px-003/px")
        assert "no-store" in r.headers.get("cache-control", "").lower()


class TestTrackingClick:
    @pytest.mark.asyncio
    async def test_redirects(self, http_client: AsyncClient, db_session: AsyncSession):
        await _seed(db_session, tracking_id="click-001")
        r = await http_client.get("/api/v1/phishing/t/click-001/c", follow_redirects=False)
        assert r.status_code == 302

    @pytest.mark.asyncio
    async def test_redirect_location_points_to_landing(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, tracking_id="click-002")
        r = await http_client.get("/api/v1/phishing/t/click-002/c", follow_redirects=False)
        assert "/l" in r.headers["location"]

    @pytest.mark.asyncio
    async def test_unknown_id_redirects_gracefully(self, http_client: AsyncClient):
        r = await http_client.get("/api/v1/phishing/t/ghost/c", follow_redirects=False)
        assert r.status_code == 302


class TestTrackingLanding:
    @pytest.mark.asyncio
    async def test_returns_html(self, http_client: AsyncClient):
        r = await http_client.get("/api/v1/phishing/t/any-id/l")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]

    @pytest.mark.asyncio
    async def test_form_action_contains_submit_route(self, http_client: AsyncClient):
        r = await http_client.get("/api/v1/phishing/t/my-tid/l")
        assert "/phishing/t/my-tid/s" in r.text


class TestTrackingSubmit:
    @pytest.mark.asyncio
    async def test_returns_awareness_html(self, http_client: AsyncClient, db_session: AsyncSession):
        await _seed(db_session, tracking_id="sub-001", status="clicked")
        r = await http_client.post("/api/v1/phishing/t/sub-001/s")
        assert r.status_code == 200
        assert "phishing" in r.text.lower()

    @pytest.mark.asyncio
    async def test_unknown_id_returns_200(self, http_client: AsyncClient):
        r = await http_client.post("/api/v1/phishing/t/ghost-id/s")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# 3. Status machine & counter tests
# ---------------------------------------------------------------------------

class TestStatusProgression:
    @pytest.mark.asyncio
    async def test_pixel_updates_status_to_opened(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        campaign, target = await _seed(db_session, tracking_id="prog-001", status="email_sent")
        await http_client.get("/api/v1/phishing/t/prog-001/px")
        await db_session.refresh(target)
        assert target.status == "opened"

    @pytest.mark.asyncio
    async def test_click_updates_status_to_clicked(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        campaign, target = await _seed(db_session, tracking_id="prog-002", status="opened")
        await http_client.get("/api/v1/phishing/t/prog-002/c", follow_redirects=False)
        await db_session.refresh(target)
        assert target.status == "clicked"

    @pytest.mark.asyncio
    async def test_submit_updates_status_to_submitted(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        campaign, target = await _seed(db_session, tracking_id="prog-003", status="clicked")
        await http_client.post("/api/v1/phishing/t/prog-003/s")
        await db_session.refresh(target)
        assert target.status == "submitted"

    @pytest.mark.asyncio
    async def test_open_increments_campaign_counter(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        campaign, _ = await _seed(db_session, tracking_id="cnt-001", status="email_sent")
        await http_client.get("/api/v1/phishing/t/cnt-001/px")
        await db_session.refresh(campaign)
        assert campaign.opened_count == 1

    @pytest.mark.asyncio
    async def test_click_increments_campaign_counter(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        campaign, _ = await _seed(db_session, tracking_id="cnt-002", status="opened")
        await http_client.get("/api/v1/phishing/t/cnt-002/c", follow_redirects=False)
        await db_session.refresh(campaign)
        assert campaign.clicked_count == 1

    @pytest.mark.asyncio
    async def test_submit_increments_campaign_counter(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        campaign, _ = await _seed(db_session, tracking_id="cnt-003", status="clicked")
        await http_client.post("/api/v1/phishing/t/cnt-003/s")
        await db_session.refresh(campaign)
        assert campaign.submitted_count == 1

    @pytest.mark.asyncio
    async def test_double_open_does_not_double_count(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        campaign, _ = await _seed(db_session, tracking_id="cnt-004", status="email_sent")
        await http_client.get("/api/v1/phishing/t/cnt-004/px")
        await http_client.get("/api/v1/phishing/t/cnt-004/px")
        await db_session.refresh(campaign)
        assert campaign.opened_count == 1

    @pytest.mark.asyncio
    async def test_double_submit_does_not_double_count(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        campaign, _ = await _seed(db_session, tracking_id="cnt-005", status="clicked")
        await http_client.post("/api/v1/phishing/t/cnt-005/s")
        await http_client.post("/api/v1/phishing/t/cnt-005/s")
        await db_session.refresh(campaign)
        assert campaign.submitted_count == 1


# ---------------------------------------------------------------------------
# 4. Campaign CRUD (authenticated)
# ---------------------------------------------------------------------------

class TestCampaignCrud:
    @pytest.mark.asyncio
    async def test_list_campaigns_empty(self, auth_client: AsyncClient):
        r = await auth_client.get("/api/v1/phishing/campaigns")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_create_campaign(self, auth_client: AsyncClient):
        r = await auth_client.post("/api/v1/phishing/campaigns", json={
            "name": "Q2 2025",
            "plan_tier": "standard",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Q2 2025"
        assert data["status"] == "draft"
        assert data["lookalike_domain"] is None

    @pytest.mark.asyncio
    async def test_get_campaign(self, auth_client: AsyncClient):
        r = await auth_client.post("/api/v1/phishing/campaigns", json={
            "name": "Get Test",
            "plan_tier": "express",
        })
        cid = r.json()["id"]
        r2 = await auth_client.get(f"/api/v1/phishing/campaigns/{cid}")
        assert r2.status_code == 200
        assert r2.json()["id"] == cid

    @pytest.mark.asyncio
    async def test_patch_name(self, auth_client: AsyncClient):
        r = await auth_client.post("/api/v1/phishing/campaigns", json={
            "name": "Old Name",
            "plan_tier": "standard",
        })
        cid = r.json()["id"]
        r2 = await auth_client.patch(f"/api/v1/phishing/campaigns/{cid}", json={"name": "New Name"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_patch_lookalike_domain(self, auth_client: AsyncClient):
        r = await auth_client.post("/api/v1/phishing/campaigns", json={
            "name": "Look-alike test",
            "plan_tier": "standard",
        })
        cid = r.json()["id"]
        r2 = await auth_client.patch(f"/api/v1/phishing/campaigns/{cid}", json={
            "lookalike_domain": "secure-acme.com",
        })
        assert r2.status_code == 200
        assert r2.json()["lookalike_domain"] == "secure-acme.com"

    @pytest.mark.asyncio
    async def test_campaign_not_found_returns_404(self, auth_client: AsyncClient):
        r = await auth_client.get("/api/v1/phishing/campaigns/99999")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated_list_returns_403(self, http_client: AsyncClient):
        # HTTPBearer returns 403 (not 401) when Authorization header is absent
        r = await http_client.get("/api/v1/phishing/campaigns")
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# 5. Look-alike domains endpoint
# ---------------------------------------------------------------------------

class TestLookalikeDomainsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_suggestions(self, auth_client: AsyncClient):
        r = await auth_client.get("/api/v1/phishing/lookalike-domains", params={"domain": "acme.com"})
        assert r.status_code == 200
        body = r.json()
        assert body["domain"] == "acme.com"
        assert len(body["suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_suggestions_have_required_keys(self, auth_client: AsyncClient):
        r = await auth_client.get("/api/v1/phishing/lookalike-domains", params={"domain": "acme.com"})
        for s in r.json()["suggestions"]:
            assert "domain" in s
            assert "technique" in s
            assert "realism_score" in s
            assert "requires_purchase" in s

    @pytest.mark.asyncio
    async def test_always_includes_sim_subdomain(self, auth_client: AsyncClient):
        r = await auth_client.get("/api/v1/phishing/lookalike-domains", params={"domain": "acme.com"})
        techniques = [s["technique"] for s in r.json()["suggestions"]]
        assert "sim_subdomain" in techniques

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_403(self, http_client: AsyncClient):
        r = await http_client.get("/api/v1/phishing/lookalike-domains", params={"domain": "acme.com"})
        assert r.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_domain_param_returns_422(self, auth_client: AsyncClient):
        r = await auth_client.get("/api/v1/phishing/lookalike-domains")
        assert r.status_code == 422
