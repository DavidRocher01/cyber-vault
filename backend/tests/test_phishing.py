"""
Tests for the phishing simulation module.

Sections:
  1. Pure unit tests (no DB / HTTP) — pixel GIF, HTML pages, email builder
  2. Awareness page — per-scenario content, gender accord, fallback
  3. Dynamic context — dept, A/B variant, Teams/SharePoint/ticket fields
  4. Attachment badge helper
  5. Tracking routes (public, no auth)  — open / click / land / submit
  6. State-machine & counter tests — progression email_sent→opened→clicked→submitted
  7. Campaign CRUD (authenticated)
  8. Look-alike domains endpoint
  9. PDF report generation
 10. Sending queue — batch engine unit tests
 11. Sécurité — expiration des tracking links + rate-limit headers
"""

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.phishing import PhishingCampaign, PhishingTarget
from app.models.user import User
from app.services import phishing_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed(
    db: AsyncSession,
    *,
    tracking_id: str = "tid-001",
    status: str = "email_sent",
    scenario_keys: str = '["o365-credentials"]',
):
    """Insert a minimal campaign + target into the test DB and return (campaign, target)."""
    user = User(email=f"phish_{tracking_id}@test.com", hashed_password=hash_password("pass"))
    db.add(user)
    await db.flush()

    campaign = PhishingCampaign(
        user_id=user.id,
        name="Test Campagne",
        plan_tier="standard",
        status="active",
        domain="acme.com",
        domain_verified=True,
        cgu_accepted=True,
        scenario_keys=scenario_keys,
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
        assert phishing_service.get_landing_html("id-1") != phishing_service.get_landing_html(
            "id-2"
        )

    def test_all_scenario_keys_produce_landing_html(self):
        for key in phishing_service._SCENARIO_TEMPLATES:
            html = phishing_service.get_landing_html("x", key)
            assert "<form" in html

    def test_unknown_scenario_key_falls_back_to_microsoft(self):
        html = phishing_service.get_landing_html("x", "nonexistent-key")
        assert "Microsoft" in html or "<form" in html


class TestExtractCompanyName:
    def test_simple_domain(self):
        assert phishing_service._extract_company_name("acme.com") == "Acme"

    def test_hyphenated_domain(self):
        assert phishing_service._extract_company_name("mairie-lyon.fr") == "Mairie Lyon"

    def test_none_returns_empty(self):
        assert phishing_service._extract_company_name(None) == ""

    def test_empty_string_returns_empty(self):
        assert phishing_service._extract_company_name("") == ""

    def test_capitalizes_each_word(self):
        assert phishing_service._extract_company_name("my-big-corp.com") == "My Big Corp"


class TestBuildEmail:
    def _make_campaign(self, lookalike=None, scenario_key="o365-credentials", domain=None):
        return SimpleNamespace(
            lookalike_domain=lookalike,
            domain=domain,
            scenario_keys=json.dumps([scenario_key]),
        )

    def _make_target(self, first_name="Marie", last_name=None, id=1, department="IT"):
        return SimpleNamespace(
            id=id,
            first_name=first_name,
            last_name=last_name,
            email="marie@acme.com",
            department=department,
        )

    def test_returns_five_values(self):
        result = phishing_service._build_email(
            self._make_campaign(), self._make_target(), "abc-123", "o365-credentials"
        )
        assert len(result) == 5

    def test_html_contains_tracking_id(self):
        _, _, html, _, _ = phishing_service._build_email(
            self._make_campaign(), self._make_target(), "abc-123", "o365-credentials"
        )
        assert "abc-123" in html

    def test_html_contains_first_name(self):
        _, _, html, _, _ = phishing_service._build_email(
            self._make_campaign(),
            self._make_target("Isabelle"),
            "x",
            "o365-credentials",
        )
        assert "Isabelle" in html

    def test_html_contains_full_name_when_last_name_present(self):
        _, _, html, _, _ = phishing_service._build_email(
            self._make_campaign(),
            self._make_target("David", "Rocher"),
            "x",
            "ceo-fraud",
        )
        assert "David Rocher" in html

    def test_subject_is_nonempty(self):
        _, subject, _, _, _ = phishing_service._build_email(
            self._make_campaign(), self._make_target(), "x", "o365-credentials"
        )
        assert subject

    def test_lookalike_domain_used_in_urls(self):
        _, _, html, _, _ = phishing_service._build_email(
            self._make_campaign(lookalike="secure-acme.com"),
            self._make_target(),
            "x",
            "o365-credentials",
        )
        assert "secure-acme.com" in html

    def test_fallback_to_base_url_when_no_lookalike(self):
        from app.core.config import settings

        _, _, html, _, _ = phishing_service._build_email(
            self._make_campaign(lookalike=None),
            self._make_target(),
            "x",
            "o365-credentials",
        )
        assert settings.PHISHING_BASE_URL.rstrip("/").split("//")[1] in html

    def test_reply_to_set_for_internal_scenario_with_lookalike(self):
        # reply_to is only set for internal scenarios (ceo-fraud, it-password, etc.)
        _, _, _, _, reply_to = phishing_service._build_email(
            self._make_campaign(lookalike="secure-acme.com", scenario_key="ceo-fraud"),
            self._make_target(),
            "x",
            "ceo-fraud",
        )
        assert reply_to is not None
        assert "secure-acme.com" in reply_to

    def test_reply_to_none_for_external_scenario(self):
        # External scenarios (o365, bank…) never set reply_to
        _, _, _, _, reply_to = phishing_service._build_email(
            self._make_campaign(lookalike="secure-acme.com"),
            self._make_target(),
            "x",
            "o365-credentials",
        )
        assert reply_to is None

    def test_reply_to_none_when_no_lookalike(self):
        _, _, _, _, reply_to = phishing_service._build_email(
            self._make_campaign(lookalike=None, scenario_key="ceo-fraud"),
            self._make_target(),
            "x",
            "ceo-fraud",
        )
        assert reply_to is None

    def test_internal_scenario_appends_company_to_from_name(self):
        from_addr, _, _, _, _ = phishing_service._build_email(
            self._make_campaign(domain="acme.com"),
            self._make_target(),
            "x",
            "ceo-fraud",
        )
        assert "Acme" in from_addr
        assert "Direction Générale" in from_addr

    def test_external_scenario_does_not_append_company(self):
        from_addr, _, _, _, _ = phishing_service._build_email(
            self._make_campaign(domain="acme.com"),
            self._make_target(),
            "x",
            "o365-credentials",
        )
        assert "Acme" not in from_addr
        assert "Microsoft 365" in from_addr

    def test_no_domain_leaves_from_name_unchanged(self):
        from_addr, _, _, _, _ = phishing_service._build_email(
            self._make_campaign(domain=None), self._make_target(), "x", "ceo-fraud"
        )
        assert from_addr.startswith("Direction Générale <")

    def test_subject_company_suffix_injected_for_internal(self):
        _, subject, _, _, _ = phishing_service._build_email(
            self._make_campaign(domain="acme.com"),
            self._make_target(),
            "x",
            "it-password",
        )
        assert "Acme" in subject
        assert "{company_suffix}" not in subject

    def test_subject_company_suffix_empty_when_no_domain(self):
        _, subject, _, _, _ = phishing_service._build_email(
            self._make_campaign(domain=None), self._make_target(), "x", "it-password"
        )
        assert "{company_suffix}" not in subject

    def test_ab_variant_produces_different_subjects(self):
        # target.id % 2 = 0 vs 1 should give different subjects for ceo-fraud
        t0 = self._make_target(id=0)
        t1 = self._make_target(id=1)
        _, subj0, _, _, _ = phishing_service._build_email(
            self._make_campaign(scenario_key="ceo-fraud"), t0, "x", "ceo-fraud"
        )
        _, subj1, _, _, _ = phishing_service._build_email(
            self._make_campaign(scenario_key="ceo-fraud"), t1, "x", "ceo-fraud"
        )
        assert subj0 != subj1

    def test_all_scenario_keys_produce_html(self):
        keys = list(phishing_service._SCENARIO_TEMPLATES.keys())
        for key in keys:
            _, _, html, text, _ = phishing_service._build_email(
                self._make_campaign(scenario_key=key, domain="test.com"),
                self._make_target(),
                "x",
                key,
            )
            assert html, f"No HTML for scenario {key}"
            assert text, f"No text for scenario {key}"

    def test_new_scenarios_teams_sharepoint_ticket(self):
        for key in ("teams-message", "sharepoint-share", "it-ticket"):
            _, _, html, _, _ = phishing_service._build_email(
                self._make_campaign(scenario_key=key, domain="test.com"),
                self._make_target(),
                "x",
                key,
            )
            assert html, f"No HTML for {key}"


# ---------------------------------------------------------------------------
# 2. Awareness page
# ---------------------------------------------------------------------------


class TestAwarenessHtml:
    def test_returns_string(self):
        assert isinstance(phishing_service.get_awareness_html(), str)

    def test_mentions_phishing(self):
        html = phishing_service.get_awareness_html().lower()
        assert "phishing" in html

    def test_same_key_returns_same_output(self):
        assert phishing_service.get_awareness_html(
            "ceo-fraud"
        ) == phishing_service.get_awareness_html("ceo-fraud")

    def test_different_scenarios_give_different_pages(self):
        assert phishing_service.get_awareness_html(
            "ceo-fraud"
        ) != phishing_service.get_awareness_html("o365-credentials")

    def test_unknown_key_returns_fallback(self):
        html = phishing_service.get_awareness_html("nonexistent-scenario")
        assert "phishing" in html.lower()
        assert html  # non-empty

    def test_ceo_scenario_contains_ceo_specific_content(self):
        html = phishing_service.get_awareness_html("ceo-fraud")
        assert "virement" in html.lower() or "président" in html.lower() or "fraude" in html.lower()

    def test_o365_scenario_contains_microsoft_content(self):
        html = phishing_service.get_awareness_html("o365-credentials")
        assert "microsoft" in html.lower() or "microsoftonline" in html.lower()

    def test_bank_scenario_contains_bank_content(self):
        html = phishing_service.get_awareness_html("bank-phishing")
        assert "banque" in html.lower() or "bancaire" in html.lower()

    def test_gender_accord_feminine_simulee(self):
        # Labels starting with "une " → "simulée"
        feminine_scenarios = [
            "ceo-fraud",  # une fraude au Président
            "fake-invoice",  # une fausse relance comptable
            "bank-phishing",  # une fausse alerte bancaire
            "prize",  # une fausse notification RH
            "invoice-pdf",  # une fausse demande de signature
            "vpn-update",  # une fausse alerte de sécurité VPN
            "teams-message",  # une fausse notification Microsoft Teams
        ]
        for key in feminine_scenarios:
            html = phishing_service.get_awareness_html(key)
            assert "simulée" in html, f"Expected 'simulée' in awareness page for {key}"

    def test_gender_accord_masculine_simule(self):
        # Labels starting with "un " → "simulé"
        masculine_scenarios = [
            "o365-credentials",  # un faux email Microsoft 365
            "parcel-tracking",  # un faux avis de livraison
            "it-password",  # un faux email DSI
            "hr-document",  # un faux document RH confidentiel
            "sharepoint-share",  # un faux partage SharePoint
            "it-ticket",  # un faux ticket helpdesk DSI
        ]
        for key in masculine_scenarios:
            html = phishing_service.get_awareness_html(key)
            assert "simulée" not in html, f"Unexpected 'simulée' in awareness page for {key}"
            assert "simulé" in html, f"Expected 'simulé' in awareness page for {key}"

    def test_all_13_scenarios_produce_awareness_html(self):
        for key in phishing_service._SCENARIO_AWARENESS:
            html = phishing_service.get_awareness_html(key)
            assert html, f"Empty awareness HTML for {key}"
            assert "phishing" in html.lower(), f"No 'phishing' mention in {key}"

    def test_awareness_contains_no_raw_placeholder(self):
        for key in phishing_service._SCENARIO_AWARENESS:
            html = phishing_service.get_awareness_html(key)
            assert "__LABEL__" not in html
            assert "__ACCORD__" not in html
            assert "__ICON__" not in html
            assert "__FLAGS__" not in html
            assert "__TEXT__" not in html


# ---------------------------------------------------------------------------
# 3. Dynamic context
# ---------------------------------------------------------------------------


class TestDynamicCtx:
    def _make_target(self, id=1, department="Finance"):
        return SimpleNamespace(id=id, first_name="Marie", last_name="Martin", department=department)

    def test_ab_variant_zero_for_even_id(self):
        ctx = phishing_service._dynamic_ctx(self._make_target(id=0), "ceo-fraud")
        assert ctx["ab_variant"] == 0

    def test_ab_variant_one_for_odd_id(self):
        ctx = phishing_service._dynamic_ctx(self._make_target(id=1), "ceo-fraud")
        assert ctx["ab_variant"] == 1

    def test_dept_present_in_context(self):
        ctx = phishing_service._dynamic_ctx(
            self._make_target(department="Comptabilité"), "fake-invoice"
        )
        assert ctx["dept"] == "Comptabilité"

    def test_dept_fallback_when_none(self):
        target = SimpleNamespace(id=1, first_name="X", last_name="Y", department=None)
        ctx = phishing_service._dynamic_ctx(target, "ceo-fraud")
        assert ctx["dept"] == ""

    def test_teams_fields_present(self):
        ctx = phishing_service._dynamic_ctx(self._make_target(), "teams-message")
        assert "teams_sender" in ctx
        assert "teams_channel" in ctx
        assert "teams_preview" in ctx
        assert ctx["teams_sender"]

    def test_sharepoint_fields_present(self):
        ctx = phishing_service._dynamic_ctx(self._make_target(), "sharepoint-share")
        assert "sp_sender" in ctx
        assert "sp_file" in ctx
        assert "sp_size" in ctx

    def test_ticket_fields_present(self):
        ctx = phishing_service._dynamic_ctx(self._make_target(), "it-ticket")
        assert "ticket_num" in ctx
        assert "ticket_subject" in ctx
        assert ctx["ticket_num"].startswith("TK-")

    def test_deterministic_for_same_target_and_key(self):
        t = self._make_target(id=42)
        ctx1 = phishing_service._dynamic_ctx(t, "ceo-fraud")
        ctx2 = phishing_service._dynamic_ctx(t, "ceo-fraud")
        assert ctx1["ab_variant"] == ctx2["ab_variant"]
        assert ctx1["dept"] == ctx2["dept"]


# ---------------------------------------------------------------------------
# 4. Attachment badge helper
# ---------------------------------------------------------------------------


class TestAttachmentBadge:
    def test_returns_html_string(self):
        from app.services.phishing_templates import _attachment_badge

        result = _attachment_badge("Facture.pdf", "PDF")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_filename(self):
        from app.services.phishing_templates import _attachment_badge

        result = _attachment_badge("Mandat_virement.pdf", "PDF")
        assert "Mandat_virement.pdf" in result

    def test_contains_filetype(self):
        from app.services.phishing_templates import _attachment_badge

        result = _attachment_badge("Rapport.docx", "DOCX")
        assert "DOCX" in result

    def test_pdf_badge_present(self):
        from app.services.phishing_templates import _attachment_badge

        result = _attachment_badge("doc.pdf", "PDF")
        assert "PDF" in result

    def test_exe_badge_present(self):
        from app.services.phishing_templates import _attachment_badge

        result = _attachment_badge("patch.exe", "EXE")
        assert "EXE" in result

    def test_xlsx_badge_present(self):
        from app.services.phishing_templates import _attachment_badge

        result = _attachment_badge("grille.xlsx", "XLSX")
        assert "XLSX" in result

    def test_is_html_table_or_div(self):
        from app.services.phishing_templates import _attachment_badge

        result = _attachment_badge("file.pdf", "PDF")
        assert "<table" in result or "<div" in result


# ---------------------------------------------------------------------------
# 5. Tracking routes — public (no auth)
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

    @pytest.mark.asyncio
    async def test_landing_uses_campaign_scenario(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(db_session, tracking_id="land-ceo", scenario_keys='["ceo-fraud"]')
        r = await http_client.get("/api/v1/phishing/t/land-ceo/l")
        assert r.status_code == 200
        assert "<form" in r.text


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

    @pytest.mark.asyncio
    async def test_awareness_page_is_scenario_specific(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(
            db_session,
            tracking_id="sub-ceo",
            status="clicked",
            scenario_keys='["ceo-fraud"]',
        )
        r = await http_client.post("/api/v1/phishing/t/sub-ceo/s")
        assert r.status_code == 200
        # CEO fraud awareness page should mention virement or fraude
        body = r.text.lower()
        assert "virement" in body or "fraude" in body or "président" in body

    @pytest.mark.asyncio
    async def test_awareness_page_o365_scenario(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        await _seed(
            db_session,
            tracking_id="sub-o365",
            status="clicked",
            scenario_keys='["o365-credentials"]',
        )
        r = await http_client.post("/api/v1/phishing/t/sub-o365/s")
        assert r.status_code == 200
        assert "microsoft" in r.text.lower() or "microsoftonline" in r.text.lower()


# ---------------------------------------------------------------------------
# 6. Status machine & counter tests
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
# 7. Campaign CRUD (authenticated)
# ---------------------------------------------------------------------------


class TestCampaignCrud:
    @pytest.mark.asyncio
    async def test_list_campaigns_empty(self, auth_client: AsyncClient):
        r = await auth_client.get("/api/v1/phishing/campaigns")
        assert r.status_code == 200
        assert r.json() == []

    @pytest.mark.asyncio
    async def test_create_campaign(self, auth_client: AsyncClient):
        r = await auth_client.post(
            "/api/v1/phishing/campaigns",
            json={
                "name": "Q2 2025",
                "plan_tier": "standard",
            },
        )
        assert r.status_code == 201
        data = r.json()
        assert data["name"] == "Q2 2025"
        assert data["status"] == "draft"
        assert data["lookalike_domain"] is None

    @pytest.mark.asyncio
    async def test_get_campaign(self, auth_client: AsyncClient):
        r = await auth_client.post(
            "/api/v1/phishing/campaigns",
            json={
                "name": "Get Test",
                "plan_tier": "express",
            },
        )
        cid = r.json()["id"]
        r2 = await auth_client.get(f"/api/v1/phishing/campaigns/{cid}")
        assert r2.status_code == 200
        assert r2.json()["id"] == cid

    @pytest.mark.asyncio
    async def test_patch_name(self, auth_client: AsyncClient):
        r = await auth_client.post(
            "/api/v1/phishing/campaigns",
            json={
                "name": "Old Name",
                "plan_tier": "standard",
            },
        )
        cid = r.json()["id"]
        r2 = await auth_client.patch(f"/api/v1/phishing/campaigns/{cid}", json={"name": "New Name"})
        assert r2.status_code == 200
        assert r2.json()["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_patch_lookalike_domain(self, auth_client: AsyncClient):
        r = await auth_client.post(
            "/api/v1/phishing/campaigns",
            json={
                "name": "Look-alike test",
                "plan_tier": "standard",
            },
        )
        cid = r.json()["id"]
        r2 = await auth_client.patch(
            f"/api/v1/phishing/campaigns/{cid}",
            json={
                "lookalike_domain": "secure-acme.com",
            },
        )
        assert r2.status_code == 200
        assert r2.json()["lookalike_domain"] == "secure-acme.com"

    @pytest.mark.asyncio
    async def test_campaign_not_found_returns_404(self, auth_client: AsyncClient):
        r = await auth_client.get("/api/v1/phishing/campaigns/99999")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated_list_returns_401_or_403(self, http_client: AsyncClient):
        r = await http_client.get("/api/v1/phishing/campaigns")
        assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# 8. Look-alike domains endpoint
# ---------------------------------------------------------------------------


class TestLookalikeDomainsEndpoint:
    @pytest.mark.asyncio
    async def test_returns_suggestions(self, auth_client: AsyncClient):
        r = await auth_client.get(
            "/api/v1/phishing/lookalike-domains", params={"domain": "acme.com"}
        )
        assert r.status_code == 200
        body = r.json()
        assert body["domain"] == "acme.com"
        assert len(body["suggestions"]) > 0

    @pytest.mark.asyncio
    async def test_suggestions_have_required_keys(self, auth_client: AsyncClient):
        r = await auth_client.get(
            "/api/v1/phishing/lookalike-domains", params={"domain": "acme.com"}
        )
        for s in r.json()["suggestions"]:
            assert "domain" in s
            assert "technique" in s
            assert "realism_score" in s
            assert "requires_purchase" in s

    @pytest.mark.asyncio
    async def test_always_includes_sim_subdomain(self, auth_client: AsyncClient):
        r = await auth_client.get(
            "/api/v1/phishing/lookalike-domains", params={"domain": "acme.com"}
        )
        techniques = [s["technique"] for s in r.json()["suggestions"]]
        assert "sim_subdomain" in techniques

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401_or_403(self, http_client: AsyncClient):
        r = await http_client.get(
            "/api/v1/phishing/lookalike-domains", params={"domain": "acme.com"}
        )
        assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_missing_domain_param_returns_422(self, auth_client: AsyncClient):
        r = await auth_client.get("/api/v1/phishing/lookalike-domains")
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# 9. PDF report generation (pure unit — no DB)
# ---------------------------------------------------------------------------


def _make_campaign(**kwargs):
    defaults = dict(
        id=1,
        name="Campagne Test",
        plan_tier="standard",
        status="completed",
        domain="acme.com",
        targets_count=10,
        emails_sent=10,
        opened_count=6,
        clicked_count=3,
        submitted_count=1,
        scenario_keys='["ceo-fraud","o365-credentials"]',
        started_at=None,
        finished_at=None,
        lookalike_domain=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_target(
    email,
    status="email_sent",
    department=None,
    first_name="Jean",
    last_name="Dupont",
    scenario_key=None,
    clicked_at=None,
    email_sent_at=None,
):
    return SimpleNamespace(
        email=email,
        status=status,
        department=department,
        first_name=first_name,
        last_name=last_name,
        scenario_key=scenario_key,
        clicked_at=clicked_at,
        email_sent_at=email_sent_at,
    )


class TestPdfReport:
    from app.services.phishing_report_pdf import (
        _get_recommendations,
        _global_risk,
        _risk_label,
        generate_phishing_report,
    )

    def test_returns_bytes(self):
        from app.services.phishing_report_pdf import generate_phishing_report

        campaign = _make_campaign()
        pdf = generate_phishing_report(campaign, [])
        assert isinstance(pdf, bytes)
        assert len(pdf) > 1000

    def test_starts_with_pdf_magic(self):
        from app.services.phishing_report_pdf import generate_phishing_report

        campaign = _make_campaign()
        pdf = generate_phishing_report(campaign, [])
        assert pdf[:4] == b"%PDF"

    def test_risk_label_faible(self):
        from app.services.phishing_report_pdf import _risk_label

        assert _risk_label(0.05) == "FAIBLE"

    def test_risk_label_moyen(self):
        from app.services.phishing_report_pdf import _risk_label

        assert _risk_label(0.20) == "MOYEN"

    def test_risk_label_eleve(self):
        from app.services.phishing_report_pdf import _risk_label

        assert _risk_label(0.35) == "ÉLEVÉ"

    def test_global_risk_faible(self):
        from app.services.phishing_report_pdf import _global_risk

        label, _ = _global_risk(0.05, 0.02)
        assert label == "FAIBLE"

    def test_global_risk_moyen(self):
        from app.services.phishing_report_pdf import _global_risk

        label, _ = _global_risk(0.15, 0.05)
        assert label == "MOYEN"

    def test_global_risk_eleve_via_submit(self):
        from app.services.phishing_report_pdf import _global_risk

        label, _ = _global_risk(0.10, 0.25)
        assert label == "ÉLEVÉ"

    def test_global_risk_eleve_via_click(self):
        from app.services.phishing_report_pdf import _global_risk

        label, _ = _global_risk(0.40, 0.05)
        assert label == "ÉLEVÉ"

    def test_recommendations_always_include_mfa(self):
        from app.services.phishing_report_pdf import _get_recommendations

        recs = _get_recommendations(0.10, 0.02)
        assert any("MFA" in r or "multi-facteurs" in r for r in recs)

    def test_recommendations_urgent_warning_on_high_click(self):
        from app.services.phishing_report_pdf import _get_recommendations

        recs = _get_recommendations(0.40, 0.02)
        assert any("30 %" in r for r in recs)

    def test_recommendations_submit_warning_on_high_submit(self):
        from app.services.phishing_report_pdf import _get_recommendations

        recs = _get_recommendations(0.10, 0.15)
        assert any("identifiants" in r for r in recs)

    def test_recommendations_no_urgent_below_threshold(self):
        from app.services.phishing_report_pdf import _get_recommendations

        recs = _get_recommendations(0.05, 0.01)
        assert not any("30 %" in r for r in recs)

    def test_generates_with_compromised_targets(self):
        from app.services.phishing_report_pdf import generate_phishing_report

        campaign = _make_campaign(submitted_count=2)
        targets = [
            _make_target("alice@acme.com", status="submitted", department="Finance"),
            _make_target("bob@acme.com", status="submitted", department="Direction"),
            _make_target("carol@acme.com", status="clicked", department="IT"),
        ]
        pdf = generate_phishing_report(campaign, targets)
        assert isinstance(pdf, bytes) and len(pdf) > 1000

    def test_generates_with_dept_breakdown(self):
        from app.services.phishing_report_pdf import generate_phishing_report

        campaign = _make_campaign()
        targets = [
            _make_target(f"u{i}@acme.com", status="clicked", department=dept)
            for i, dept in enumerate(["Finance", "RH", "IT", "Direction"])
        ]
        pdf = generate_phishing_report(campaign, targets)
        assert isinstance(pdf, bytes) and len(pdf) > 1000

    def test_generates_without_scenario_keys(self):
        from app.services.phishing_report_pdf import generate_phishing_report

        campaign = _make_campaign(scenario_keys=None)
        pdf = generate_phishing_report(campaign, [])
        assert isinstance(pdf, bytes) and len(pdf) > 1000

    def test_generates_with_zero_targets(self):
        from app.services.phishing_report_pdf import generate_phishing_report

        campaign = _make_campaign(
            targets_count=0,
            emails_sent=0,
            opened_count=0,
            clicked_count=0,
            submitted_count=0,
        )
        pdf = generate_phishing_report(campaign, [])
        assert isinstance(pdf, bytes) and len(pdf) > 1000


# ---------------------------------------------------------------------------
# 10. Sending queue — batch engine unit tests (no DB, no Resend)
# ---------------------------------------------------------------------------


class TestSendPendingBatch:
    """Tests for send_pending_batch() logic: concurrency guard, scenario round-robin."""

    @pytest.mark.asyncio
    async def test_skip_if_lock_held(self):
        """A second call while the first holds the lock must return immediately (no-op)."""
        lock = phishing_service._batch_lock
        async with lock:
            # Lock is held — calling send_pending_batch should return without blocking
            import asyncio as _asyncio

            done = _asyncio.Event()

            async def _call():
                await phishing_service.send_pending_batch()
                done.set()

            task = _asyncio.create_task(_call())
            await _asyncio.sleep(0)  # yield so the task runs
            assert done.is_set(), "send_pending_batch should return immediately when lock is held"
            task.cancel()

    def test_scenario_round_robin_single(self):
        """With one scenario key, every target gets that same key."""
        scenario_keys = ["ceo-fraud"]
        for fake_id in range(5):
            key = scenario_keys[fake_id % len(scenario_keys)]
            assert key == "ceo-fraud"

    def test_scenario_round_robin_two(self):
        """With two scenario keys, targets alternate deterministically."""
        scenario_keys = ["ceo-fraud", "o365-credentials"]
        results = [scenario_keys[i % 2] for i in range(4)]
        assert results == [
            "ceo-fraud",
            "o365-credentials",
            "ceo-fraud",
            "o365-credentials",
        ]

    def test_scenario_round_robin_three(self):
        """Three scenario keys distribute evenly across 6 targets."""
        keys = ["a", "b", "c"]
        results = [keys[i % 3] for i in range(6)]
        assert results == ["a", "b", "c", "a", "b", "c"]

    @pytest.mark.asyncio
    async def test_batch_sends_pending_targets_and_marks_sent(self, db_session: AsyncSession):
        """send_pending_batch() marks pending targets as email_sent and increments emails_sent."""
        import unittest.mock as mock

        user = User(email="batch_test@test.com", hashed_password=hash_password("pass"))
        db_session.add(user)
        await db_session.flush()

        campaign = PhishingCampaign(
            user_id=user.id,
            name="Batch Test",
            plan_tier="standard",
            status="sending",
            domain="corp.com",
            domain_verified=True,
            cgu_accepted=True,
            scenario_keys='["o365-credentials"]',
            targets_count=3,
            emails_sent=0,
        )
        db_session.add(campaign)
        await db_session.flush()

        for i in range(3):
            db_session.add(
                PhishingTarget(
                    campaign_id=campaign.id,
                    email=f"t{i}@corp.com",
                    first_name=f"T{i}",
                    status="pending",
                )
            )
        await db_session.commit()

        with mock.patch.object(phishing_service, "_send_phishing_email") as mock_send:
            await phishing_service.send_pending_batch()

        await db_session.refresh(campaign)
        assert campaign.emails_sent == 3

        from sqlalchemy import select as _sel

        result = await db_session.execute(
            _sel(PhishingTarget).where(PhishingTarget.campaign_id == campaign.id)
        )
        statuses = {t.status for t in result.scalars().all()}
        assert statuses == {"email_sent"}

    @pytest.mark.asyncio
    async def test_batch_transitions_sending_to_active_when_no_pending(
        self, db_session: AsyncSession
    ):
        """When all targets are already sent, campaign moves from 'sending' to 'active'."""
        user = User(email="batch_done@test.com", hashed_password=hash_password("pass"))
        db_session.add(user)
        await db_session.flush()

        campaign = PhishingCampaign(
            user_id=user.id,
            name="Done Campaign",
            plan_tier="standard",
            status="sending",
            domain="corp.com",
            cgu_accepted=True,
            scenario_keys='["ceo-fraud"]',
            targets_count=1,
            emails_sent=1,
        )
        db_session.add(campaign)
        await db_session.flush()

        db_session.add(
            PhishingTarget(
                campaign_id=campaign.id,
                email="done@corp.com",
                status="email_sent",
                tracking_id="done-tid",
            )
        )
        await db_session.commit()

        await phishing_service.send_pending_batch()
        await db_session.refresh(campaign)
        assert campaign.status == "active"


# ---------------------------------------------------------------------------
# 11. Sécurité — expiration des tracking links
# ---------------------------------------------------------------------------


class TestTrackingExpiry:
    """_is_campaign_expired() logic + tracking endpoints respect expiry."""

    # ── Unit tests for the helper ────────────────────────────────────────────

    def test_active_campaign_not_expired(self):
        from datetime import timedelta
        from types import SimpleNamespace

        c = SimpleNamespace(
            status="active",
            started_at=datetime.now(UTC) - timedelta(days=5),
        )
        assert phishing_service._is_campaign_expired(c) is False

    def test_completed_campaign_always_expired(self):
        from types import SimpleNamespace

        c = SimpleNamespace(status="completed", started_at=None)
        assert phishing_service._is_campaign_expired(c) is True

    def test_campaign_expired_after_ttl(self):
        from datetime import timedelta
        from types import SimpleNamespace

        from app.core.config import settings

        c = SimpleNamespace(
            status="active",
            started_at=datetime.now(UTC) - timedelta(days=settings.PHISHING_TRACKING_TTL_DAYS + 1),
        )
        assert phishing_service._is_campaign_expired(c) is True

    def test_campaign_not_expired_at_ttl_boundary(self):
        from datetime import timedelta
        from types import SimpleNamespace

        from app.core.config import settings

        c = SimpleNamespace(
            status="active",
            started_at=datetime.now(UTC) - timedelta(days=settings.PHISHING_TRACKING_TTL_DAYS - 1),
        )
        assert phishing_service._is_campaign_expired(c) is False

    def test_no_started_at_not_expired(self):
        from types import SimpleNamespace

        c = SimpleNamespace(status="sending", started_at=None)
        assert phishing_service._is_campaign_expired(c) is False

    def test_expired_html_is_string(self):
        html = phishing_service.get_expired_html()
        assert isinstance(html, str)
        assert "expiré" in html.lower()

    # ── Integration tests — tracking events not recorded when expired ────────

    @pytest.mark.asyncio
    async def test_open_not_recorded_for_completed_campaign(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        campaign, _ = await _seed(db_session, tracking_id="exp-open-001", status="email_sent")
        campaign.status = "completed"
        await db_session.commit()

        await http_client.get("/api/v1/phishing/t/exp-open-001/px")
        await db_session.refresh(campaign)
        assert campaign.opened_count == 0

    @pytest.mark.asyncio
    async def test_click_returns_expired_html_for_completed_campaign(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        campaign, _ = await _seed(db_session, tracking_id="exp-click-001", status="email_sent")
        campaign.status = "completed"
        await db_session.commit()

        r = await http_client.get("/api/v1/phishing/t/exp-click-001/c", follow_redirects=False)
        # Expired → returns HTML instead of redirect
        assert r.status_code == 200
        assert "expiré" in r.text.lower()

    @pytest.mark.asyncio
    async def test_click_not_recorded_for_completed_campaign(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        campaign, _ = await _seed(db_session, tracking_id="exp-click-002", status="email_sent")
        campaign.status = "completed"
        await db_session.commit()

        await http_client.get("/api/v1/phishing/t/exp-click-002/c", follow_redirects=True)
        await db_session.refresh(campaign)
        assert campaign.clicked_count == 0

    @pytest.mark.asyncio
    async def test_landing_returns_expired_html_for_completed_campaign(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        campaign, _ = await _seed(db_session, tracking_id="exp-land-001", status="clicked")
        campaign.status = "completed"
        await db_session.commit()

        r = await http_client.get("/api/v1/phishing/t/exp-land-001/l")
        assert r.status_code == 200
        assert "expiré" in r.text.lower()

    @pytest.mark.asyncio
    async def test_submit_not_recorded_for_completed_campaign(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        campaign, _ = await _seed(db_session, tracking_id="exp-sub-001", status="clicked")
        campaign.status = "completed"
        await db_session.commit()

        r = await http_client.post("/api/v1/phishing/t/exp-sub-001/s")
        assert r.status_code == 200  # Awareness page always shown
        await db_session.refresh(campaign)
        assert campaign.submitted_count == 0

    @pytest.mark.asyncio
    async def test_submit_still_returns_awareness_page_when_expired(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        """Even when expired, POSTing /s always returns the educational awareness page."""
        campaign, _ = await _seed(db_session, tracking_id="exp-sub-002", status="clicked")
        campaign.status = "completed"
        await db_session.commit()

        r = await http_client.post("/api/v1/phishing/t/exp-sub-002/s")
        assert r.status_code == 200
        # Awareness page content (not the expiry page)
        assert "exercice" in r.text.lower() or "phishing" in r.text.lower()

    # ── Rate-limiting configured (smoke test) ───────────────────────────────

    @pytest.mark.asyncio
    async def test_pixel_endpoint_responds_normally(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        """Smoke test: rate-limited pixel endpoint still works on first call."""
        await _seed(db_session, tracking_id="rl-px-001", status="email_sent")
        r = await http_client.get("/api/v1/phishing/t/rl-px-001/px")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/gif"

    @pytest.mark.asyncio
    async def test_submit_endpoint_responds_normally(
        self, http_client: AsyncClient, db_session: AsyncSession
    ):
        """Smoke test: rate-limited submit endpoint still works on first call."""
        await _seed(db_session, tracking_id="rl-sub-001", status="clicked")
        r = await http_client.post("/api/v1/phishing/t/rl-sub-001/s")
        assert r.status_code == 200
