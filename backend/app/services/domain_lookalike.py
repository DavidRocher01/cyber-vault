"""
Look-alike domain generator for phishing simulations.

Given a target domain (e.g. "monentreprise.com"), generates realistic
typosquatted / combosquatted variants grouped by technique and scored by
realism (1–10).

Also always includes a "sim subdomain" option that works immediately without
any domain purchase (uses our existing PHISHING_BASE_URL).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse

from app.core.config import settings

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

Technique = Literal[
    "sim_subdomain",
    "combosquatting_prepend",
    "combosquatting_append",
    "tld_swap",
    "typo_missing_char",
    "typo_double_char",
    "typo_char_swap",
    "typo_homoglyph",
    "subdomain_trick",
]


@dataclass
class LookalikeDomain:
    domain: str
    technique: Technique
    realism_score: int  # 1-10 (10 = most realistic)
    requires_purchase: bool
    purchase_url: str = ""
    setup_instructions: str = ""
    note: str = ""

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "technique": self.technique,
            "realism_score": self.realism_score,
            "requires_purchase": self.requires_purchase,
            "purchase_url": self.purchase_url,
            "setup_instructions": self.setup_instructions,
            "note": self.note,
        }


# ---------------------------------------------------------------------------
# Keyword lists (French market, common phishing lures)
# ---------------------------------------------------------------------------

_PREPEND_KEYWORDS = [
    "login",
    "secure",
    "connexion",
    "portail",
    "espace",
    "mon",
    "auth",
    "sign-in",
    "acces",
    "acceder",
]

_APPEND_KEYWORDS = [
    "rh",
    "paie",
    "support",
    "portail",
    "login",
    "secure",
    "connexion",
    "espace",
    "acces",
    "service",
    "client",
    "pro",
]

_ALT_TLDS = [".net", ".co", ".org", ".fr", ".eu", ".io", ".online", ".site"]

# ASCII homoglyphs — visually close substitutions that survive in domain names
_HOMOGLYPHS: dict[str, list[str]] = {
    "a": ["à", "á", "â"],
    "e": ["é", "è", "ê"],
    "i": ["í", "ì"],
    "o": ["ô", "ö"],
    # ASCII look-alikes (no Unicode needed, more practical)
    "rn": ["m"],  # "rn" looks like "m"
    "vv": ["w"],  # "vv" looks like "w"
    "cl": ["d"],  # "cl" looks like "d"
}

# Keyboard adjacency (AZERTY — common mistype substitutions)
_KEYBOARD_ADJACENT: dict[str, str] = {
    "a": "z",
    "z": "a",
    "e": "r",
    "r": "e",
    "t": "r",
    "y": "u",
    "u": "y",
    "i": "o",
    "o": "i",
    "p": "o",
    "s": "d",
    "d": "s",
    "f": "g",
    "g": "f",
    "h": "j",
    "j": "h",
    "k": "l",
    "l": "k",
    "m": "n",
    "n": "m",
    "b": "v",
    "v": "b",
    "c": "x",
    "x": "c",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_domain(domain: str) -> tuple[str, str]:
    """Return (name, tld) for 'example.com' → ('example', '.com')."""
    domain = domain.lower().strip()
    # Handle multi-part TLDs like .co.uk — take last two parts as TLD if second-to-last is ≤ 2 chars
    parts = domain.split(".")
    if len(parts) >= 3 and len(parts[-2]) <= 3:
        name = ".".join(parts[:-2])
        tld = "." + ".".join(parts[-2:])
    elif len(parts) >= 2:
        name = parts[0]
        tld = "." + ".".join(parts[1:])
    else:
        name = domain
        tld = ".com"
    return name, tld


def _purchase_url(domain: str) -> str:
    return f"https://www.namecheap.com/domains/registration/results/?domain={domain}"


def _setup_instructions(domain: str) -> str:
    # Une cible CNAME est un HOSTNAME : ni schema, ni port, ni chemin. Or
    # PHISHING_BASE_URL contient un chemin (ex. https://rochercybersecurite.com/api/v1),
    # et un simple replace("https://", "") laissait "rochercybersecurite.com/api/v1" —
    # une instruction DNS inapplicable. urlparse().hostname isole proprement l'hote.
    api_host = urlparse(settings.PHISHING_BASE_URL).hostname or settings.PHISHING_BASE_URL
    return (
        f"1. Achetez le domaine '{domain}' (~10 €/an).\n"
        f"2. Dans votre registrar DNS, créez :\n"
        f"   CNAME {domain} → {api_host}\n"
        f"   (ou A {domain} → l'IP de votre API)\n"
        f"3. Optionnel : ajoutez le domaine à Cloudflare (SSL gratuit).\n"
        f"4. Renseignez '{domain}' dans le champ 'Domaine look-alike' de votre campagne."
    )


def _dedup(candidates: list[LookalikeDomain]) -> list[LookalikeDomain]:
    seen: set[str] = set()
    result: list[LookalikeDomain] = []
    for c in candidates:
        if c.domain not in seen:
            seen.add(c.domain)
            result.append(c)
    return result


def _is_valid_domain(name: str) -> bool:
    return bool(name) and bool(re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", name))


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


def _sim_subdomain(name: str, tld: str) -> LookalikeDomain:
    base = settings.PHISHING_BASE_URL.rstrip("/")
    return LookalikeDomain(
        domain=base,
        technique="sim_subdomain",
        realism_score=5,
        requires_purchase=False,
        note=(
            "Disponible immédiatement — utilise notre infrastructure existante. "
            "L'URL visible est celle de Rocher Cybersécurité (moins réaliste, mais 0 € et 0 configuration)."
        ),
    )


def _combosquatting(name: str, tld: str) -> list[LookalikeDomain]:
    results = []
    for kw in _PREPEND_KEYWORDS[:5]:
        d = f"{kw}-{name}{tld}"
        results.append(
            LookalikeDomain(
                domain=d,
                technique="combosquatting_prepend",
                realism_score=9,
                requires_purchase=True,
                purchase_url=_purchase_url(d),
                setup_instructions=_setup_instructions(d),
            )
        )
    for kw in _APPEND_KEYWORDS[:5]:
        d = f"{name}-{kw}{tld}"
        results.append(
            LookalikeDomain(
                domain=d,
                technique="combosquatting_append",
                realism_score=8,
                requires_purchase=True,
                purchase_url=_purchase_url(d),
                setup_instructions=_setup_instructions(d),
            )
        )
    return results


def _tld_swap(name: str, tld: str) -> list[LookalikeDomain]:
    results = []
    for alt in _ALT_TLDS:
        if alt == tld:
            continue
        d = f"{name}{alt}"
        results.append(
            LookalikeDomain(
                domain=d,
                technique="tld_swap",
                realism_score=7,
                requires_purchase=True,
                purchase_url=_purchase_url(d),
                setup_instructions=_setup_instructions(d),
            )
        )
    return results


def _typo_missing(name: str, tld: str) -> list[LookalikeDomain]:
    results = []
    for i in range(len(name)):
        variant = name[:i] + name[i + 1 :]
        if len(variant) < 3 or not _is_valid_domain(variant):
            continue
        d = f"{variant}{tld}"
        results.append(
            LookalikeDomain(
                domain=d,
                technique="typo_missing_char",
                realism_score=6,
                requires_purchase=True,
                purchase_url=_purchase_url(d),
                setup_instructions=_setup_instructions(d),
            )
        )
    return results[:4]


def _typo_double(name: str, tld: str) -> list[LookalikeDomain]:
    results = []
    for i, ch in enumerate(name):
        variant = name[:i] + ch + name[i:]
        if not _is_valid_domain(variant):
            continue
        d = f"{variant}{tld}"
        results.append(
            LookalikeDomain(
                domain=d,
                technique="typo_double_char",
                realism_score=5,
                requires_purchase=True,
                purchase_url=_purchase_url(d),
                setup_instructions=_setup_instructions(d),
            )
        )
    return results[:4]


def _typo_swap(name: str, tld: str) -> list[LookalikeDomain]:
    results = []
    for i in range(len(name) - 1):
        variant = name[:i] + name[i + 1] + name[i] + name[i + 2 :]
        if variant == name or not _is_valid_domain(variant):
            continue
        d = f"{variant}{tld}"
        results.append(
            LookalikeDomain(
                domain=d,
                technique="typo_char_swap",
                realism_score=6,
                requires_purchase=True,
                purchase_url=_purchase_url(d),
                setup_instructions=_setup_instructions(d),
            )
        )
    return results[:4]


def _typo_keyboard(name: str, tld: str) -> list[LookalikeDomain]:
    results = []
    for i, ch in enumerate(name):
        if ch in _KEYBOARD_ADJACENT:
            variant = name[:i] + _KEYBOARD_ADJACENT[ch] + name[i + 1 :]
            if variant == name or not _is_valid_domain(variant):
                continue
            d = f"{variant}{tld}"
            results.append(
                LookalikeDomain(
                    domain=d,
                    technique="typo_char_swap",
                    realism_score=5,
                    requires_purchase=True,
                    purchase_url=_purchase_url(d),
                    setup_instructions=_setup_instructions(d),
                )
            )
    return results[:3]


def _subdomain_trick(name: str, tld: str) -> list[LookalikeDomain]:
    """e.g. 'example.com.login-secure.fr' — looks like a subdomain of the real site."""
    results = []
    lures = [
        "login-secure.fr",
        "espace-client.fr",
        "portail-rh.com",
        "connexion-secure.net",
    ]
    for lure in lures:
        d = f"{name}{tld}.{lure}"
        results.append(
            LookalikeDomain(
                domain=d,
                technique="subdomain_trick",
                realism_score=9,
                requires_purchase=True,
                purchase_url=_purchase_url(lure),
                setup_instructions=(
                    f"Achetez '{lure}', puis créez un CNAME:\n  {name}{tld}.{lure} → votre API"
                ),
                note="Très réaliste : l'URL commence par le vrai domaine de l'entreprise.",
            )
        )
    return results


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_lookalikes(target_domain: str, max_results: int = 30) -> list[dict]:
    """
    Generate look-alike domain suggestions for target_domain.
    Returns a sorted list of dicts (highest realism first), capped at max_results.
    Always includes the sim_subdomain option (no purchase required).
    """
    name, tld = _parse_domain(target_domain)
    if not name or len(name) < 2:
        return []

    sim = _sim_subdomain(name, tld)

    candidates: list[LookalikeDomain] = []
    candidates += _subdomain_trick(name, tld)
    candidates += _combosquatting(name, tld)
    candidates += _tld_swap(name, tld)
    candidates += _typo_missing(name, tld)
    candidates += _typo_swap(name, tld)
    candidates += _typo_keyboard(name, tld)
    candidates += _typo_double(name, tld)

    candidates = _dedup(candidates)
    candidates.sort(key=lambda c: (-c.realism_score, c.domain))

    # sim_subdomain is always included first (free, no purchase needed)
    # and does not consume a slot from the paid-domain results
    return [sim.to_dict()] + [c.to_dict() for c in candidates[: max_results - 1]]
