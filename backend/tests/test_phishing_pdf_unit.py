"""Unit tests — phishing_report_pdf.py."""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.models.phishing import PhishingCampaign, PhishingTarget
from app.services.phishing_report_pdf import (
    _get_recommendations,
    _risk_color,
    _risk_label,
    generate_phishing_report,
)

# ── helpers ────────────────────────────────────────────────────────────────────


def _campaign(
    name="Test Campaign",
    targets_count=50,
    emails_sent=50,
    opened_count=20,
    clicked_count=10,
    submitted_count=3,
    status="completed",
    plan_tier="standard",
    scenario_keys='["ceo-fraud"]',
    finished_at=None,
) -> MagicMock:
    c = MagicMock(spec=PhishingCampaign)
    c.name = name
    c.targets_count = targets_count
    c.emails_sent = emails_sent
    c.opened_count = opened_count
    c.clicked_count = clicked_count
    c.submitted_count = submitted_count
    c.status = status
    c.plan_tier = plan_tier
    c.scenario_keys = scenario_keys
    c.finished_at = finished_at or datetime(2026, 5, 1, 12, 0, tzinfo=UTC)
    c.started_at = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)
    return c


def _target(
    email="user@example.com",
    first_name="Alice",
    department="IT",
    status="clicked",
    scenario_key=None,
    clicked_at=None,
    email_sent_at=None,
) -> MagicMock:
    t = MagicMock(spec=PhishingTarget)
    t.email = email
    t.first_name = first_name
    t.last_name = "Test"
    t.department = department
    t.status = status
    t.scenario_key = scenario_key
    t.clicked_at = clicked_at
    t.email_sent_at = email_sent_at
    return t


# ── _risk_color ────────────────────────────────────────────────────────────────


def test_risk_color_high():
    from reportlab.lib import colors

    color = _risk_color(0.35)
    assert color == colors.HexColor("#ef4444")


def test_risk_color_medium():
    from reportlab.lib import colors

    color = _risk_color(0.20)
    assert color == colors.HexColor("#eab308")


def test_risk_color_low():
    from reportlab.lib import colors

    color = _risk_color(0.05)
    assert color == colors.HexColor("#22c55e")


def test_risk_color_boundary_30():
    from reportlab.lib import colors

    assert _risk_color(0.30) == colors.HexColor("#ef4444")


def test_risk_color_boundary_15():
    from reportlab.lib import colors

    assert _risk_color(0.15) == colors.HexColor("#eab308")


# ── _risk_label ────────────────────────────────────────────────────────────────


def test_risk_label_high():
    assert _risk_label(0.30) == "ÉLEVÉ"
    assert _risk_label(0.50) == "ÉLEVÉ"


def test_risk_label_medium():
    assert _risk_label(0.15) == "MOYEN"
    assert _risk_label(0.25) == "MOYEN"


def test_risk_label_low():
    assert _risk_label(0.00) == "FAIBLE"
    assert _risk_label(0.14) == "FAIBLE"


# ── _get_recommendations ───────────────────────────────────────────────────────


def test_recommendations_high_click_rate():
    recs = _get_recommendations(0.35, 0.05)
    assert any("30 %" in r or "élevé" in r.lower() for r in recs)


def test_recommendations_high_submit_rate():
    recs = _get_recommendations(0.10, 0.15)
    assert any("soumission" in r.lower() or "rotation" in r.lower() for r in recs)


def test_recommendations_normal():
    recs = _get_recommendations(0.10, 0.05)
    assert len(recs) >= 3
    assert all(isinstance(r, str) for r in recs)


def test_recommendations_both_high():
    recs = _get_recommendations(0.40, 0.20)
    assert len(recs) >= 5


# ── generate_phishing_report — smoke tests ────────────────────────────────────


def test_generate_report_returns_pdf():
    camp = _campaign()
    targets = [
        _target("alice@corp.fr", "Alice", "Finance", "submitted"),
        _target("bob@corp.fr", "Bob", "IT", "clicked"),
        _target("carol@corp.fr", "Carol", "RH", "opened"),
        _target("dave@corp.fr", "Dave", "Direction", "pending"),
    ]
    pdf = generate_phishing_report(camp, targets)
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"


def test_generate_report_empty_targets():
    camp = _campaign(
        targets_count=0,
        emails_sent=0,
        opened_count=0,
        clicked_count=0,
        submitted_count=0,
    )
    pdf = generate_phishing_report(camp, [])
    assert pdf[:4] == b"%PDF"


def test_generate_report_high_click_rate():
    camp = _campaign(emails_sent=100, clicked_count=40, submitted_count=15)
    targets = [_target(f"user{i}@corp.fr", f"User{i}", "IT", "clicked") for i in range(10)]
    pdf = generate_phishing_report(camp, targets)
    assert pdf[:4] == b"%PDF"


def test_generate_report_all_submitted():
    camp = _campaign(emails_sent=10, clicked_count=10, submitted_count=10)
    targets = [_target(f"t{i}@corp.fr", f"T{i}", "Compta", "submitted") for i in range(10)]
    pdf = generate_phishing_report(camp, targets)
    assert pdf[:4] == b"%PDF"


def test_generate_report_many_targets():
    camp = _campaign(emails_sent=200, opened_count=80, clicked_count=30, submitted_count=5)
    targets = [
        _target(
            f"user{i}@corp.fr",
            f"User{i}",
            ["IT", "Finance", "RH", "Direction"][i % 4],
            ["pending", "opened", "clicked", "submitted"][i % 4],
        )
        for i in range(50)
    ]
    pdf = generate_phishing_report(camp, targets)
    assert pdf[:4] == b"%PDF"


def test_generate_report_no_sent_emails():
    camp = _campaign(emails_sent=0, opened_count=0, clicked_count=0, submitted_count=0)
    pdf = generate_phishing_report(camp, [])
    assert pdf[:4] == b"%PDF"


def test_generate_report_no_scenario():
    camp = _campaign(scenario_keys=None)
    pdf = generate_phishing_report(camp, [])
    assert pdf[:4] == b"%PDF"


def test_generate_report_multiple_scenarios():
    camp = _campaign(scenario_keys='["ceo-fraud","o365-credentials","it-support"]')
    pdf = generate_phishing_report(camp, [])
    assert pdf[:4] == b"%PDF"


def test_generate_report_target_no_department():
    camp = _campaign(emails_sent=5, clicked_count=2)
    t = _target("anon@corp.fr", "Anon", None, "clicked")
    pdf = generate_phishing_report(camp, [t])
    assert pdf[:4] == b"%PDF"


def test_scenario_labels_match_registry():
    """Les libelles PDF DOIVENT couvrir exactement le registre de scenarios.

    Garde-fou anti-derive : toute cle ajoutee/retiree dans _SCENARIO_TEMPLATES
    sans mise a jour de SCENARIO_LABELS (ou l'inverse) casse ce test.
    """
    from app.services.phishing_templates import (
        _SCENARIO_TEMPLATES,
        SCENARIO_LABELS,
    )

    assert set(SCENARIO_LABELS) == set(_SCENARIO_TEMPLATES), (
        "SCENARIO_LABELS desynchronise du registre : "
        f"en trop={set(SCENARIO_LABELS) - set(_SCENARIO_TEMPLATES)}, "
        f"manquants={set(_SCENARIO_TEMPLATES) - set(SCENARIO_LABELS)}"
    )
