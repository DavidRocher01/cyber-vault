"""
Tests unitaires pour domain_lookalike.py.
Aucune dépendance BD / réseau — pur Python.
"""

import pytest
from app.services.domain_lookalike import (
    _parse_domain,
    _is_valid_domain,
    generate_lookalikes,
)


# ---------------------------------------------------------------------------
# _parse_domain
# ---------------------------------------------------------------------------

class TestParseDomain:
    def test_simple_com(self):
        assert _parse_domain("example.com") == ("example", ".com")

    def test_strips_whitespace(self):
        assert _parse_domain("  example.com  ") == ("example", ".com")

    def test_lowercases(self):
        assert _parse_domain("Example.COM") == ("example", ".com")

    def test_simple_fr(self):
        assert _parse_domain("monsite.fr") == ("monsite", ".fr")

    def test_co_uk_treated_as_two_part_tld(self):
        name, tld = _parse_domain("example.co.uk")
        assert tld == ".co.uk"
        assert name == "example"

    def test_com_br_treated_as_two_part_tld(self):
        name, tld = _parse_domain("site.com.br")
        assert tld == ".com.br"
        assert name == "site"

    def test_no_dot_falls_back(self):
        name, tld = _parse_domain("nodot")
        assert name == "nodot"
        assert tld == ".com"

    def test_subdomain_ignored_in_name(self):
        # standard parse: first segment is name for a simple domain
        name, tld = _parse_domain("monentreprise.com")
        assert name == "monentreprise"
        assert tld == ".com"


# ---------------------------------------------------------------------------
# _is_valid_domain
# ---------------------------------------------------------------------------

class TestIsValidDomain:
    def test_valid_alphanum(self):
        assert _is_valid_domain("example") is True

    def test_valid_with_hyphen(self):
        assert _is_valid_domain("my-site") is True

    def test_empty_string(self):
        assert _is_valid_domain("") is False

    def test_starts_with_hyphen(self):
        assert _is_valid_domain("-bad") is False

    def test_ends_with_hyphen(self):
        assert _is_valid_domain("bad-") is False

    def test_too_short_single_char(self):
        # Single char passes regex (it matches [a-z0-9] only, not the full pattern needing start+end)
        # The regex requires at least 2 chars due to [a-z0-9] ... [a-z0-9] anchors
        assert _is_valid_domain("a") is False  # regex requires start & end char so 1 char fails

    def test_uppercase_rejected(self):
        assert _is_valid_domain("MyDomain") is False


# ---------------------------------------------------------------------------
# generate_lookalikes
# ---------------------------------------------------------------------------

class TestGenerateLookalikes:
    def test_returns_list(self):
        result = generate_lookalikes("acme.com")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_respects_max_results(self):
        result = generate_lookalikes("acme.com", max_results=5)
        assert len(result) <= 5

    def test_always_includes_sim_subdomain(self):
        result = generate_lookalikes("acme.com")
        techniques = [r["technique"] for r in result]
        assert "sim_subdomain" in techniques

    def test_sim_subdomain_does_not_require_purchase(self):
        result = generate_lookalikes("acme.com")
        sim = next(r for r in result if r["technique"] == "sim_subdomain")
        assert sim["requires_purchase"] is False

    def test_sorted_by_realism_desc(self):
        result = generate_lookalikes("acme.com", max_results=30)
        # sim_subdomain is always pinned at index 0 (free, no purchase) — exclude from sort check
        paid = [r for r in result if r["technique"] != "sim_subdomain"]
        scores = [r["realism_score"] for r in paid]
        assert scores == sorted(scores, reverse=True)

    def test_no_duplicates(self):
        result = generate_lookalikes("acme.com", max_results=30)
        domains = [r["domain"] for r in result]
        assert len(domains) == len(set(domains))

    def test_each_item_has_required_keys(self):
        result = generate_lookalikes("acme.com", max_results=5)
        required = {"domain", "technique", "realism_score", "requires_purchase",
                    "purchase_url", "setup_instructions", "note"}
        for item in result:
            assert required.issubset(item.keys())

    def test_combosquatting_domains_contain_name(self):
        result = generate_lookalikes("acme.com", max_results=30)
        combo = [r for r in result if "combosquatting" in r["technique"]]
        assert len(combo) > 0
        for item in combo:
            assert "acme" in item["domain"]

    def test_tld_swap_keeps_name(self):
        result = generate_lookalikes("acme.com", max_results=30)
        tld = [r for r in result if r["technique"] == "tld_swap"]
        assert len(tld) > 0
        for item in tld:
            assert item["domain"].startswith("acme.")

    def test_empty_name_returns_empty(self):
        assert generate_lookalikes("") == []

    def test_single_char_domain_returns_empty(self):
        assert generate_lookalikes("a.com") == []

    def test_realism_score_in_range(self):
        result = generate_lookalikes("acme.com", max_results=30)
        for item in result:
            assert 1 <= item["realism_score"] <= 10

    def test_purchased_domains_have_purchase_url(self):
        result = generate_lookalikes("acme.com", max_results=30)
        for item in result:
            if item["requires_purchase"]:
                assert item["purchase_url"].startswith("https://")

    def test_french_domain(self):
        result = generate_lookalikes("monentreprise.fr", max_results=30)
        assert len(result) > 0
        # TLD swap should not include .fr again
        tld_domains = [r["domain"] for r in result if r["technique"] == "tld_swap"]
        assert all(not d.endswith(".fr") for d in tld_domains)
