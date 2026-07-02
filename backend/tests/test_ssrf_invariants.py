"""
Invariants ANTI-SSRF — app/core/ssrf.py.

Le scanner et la vérification de phishing acceptent des URL fournies par
l'utilisateur : assert_no_ssrf() est la seule barrière qui empêche un attaquant
de faire pointer une URL "publique" vers un service interne (metadata cloud,
Redis, base de données, réseau privé…).

Ces tests encodent les INVARIANTS de sécurité, pas seulement le comportement
courant : chaque cible interne/réservée DOIT lever HTTPException(422), et seule
une URL publique normale doit passer. Aucun appel réseau réel n'est fait
(socket.getaddrinfo est systématiquement patché) → tests déterministes.
"""

import socket
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.ssrf import assert_no_ssrf


def _resolve_to(ip: str):
    """Fabrique un faux retour getaddrinfo qui résout n'importe quel hôte vers `ip`.

    C'est aussi le vecteur de DNS-rebinding : un hostname parfaitement public
    (ex. evil.example.com) qui résout vers une IP privée.
    """
    return [(socket.AF_INET, socket.SOCK_STREAM, 0, "", (ip, 0))]


def _assert_blocked(url: str, resolved_ip: str) -> None:
    """assert_no_ssrf DOIT lever 422 quand `url` résout vers `resolved_ip`."""
    with patch("app.core.ssrf.socket.getaddrinfo", return_value=_resolve_to(resolved_ip)):
        with pytest.raises(HTTPException) as exc:
            assert_no_ssrf(url)
    assert exc.value.status_code == 422, f"attendu 422 pour {url} -> {resolved_ip}"


# ── Cibles internes qui DOIVENT être bloquées ────────────────────────────────


class TestBlockedTargets:
    def test_localhost_hostname_blocked(self):
        # Un hostname "localhost" qui résout vers la loopback.
        _assert_blocked("https://localhost/admin", "127.0.0.1")

    def test_loopback_literal_blocked(self):
        _assert_blocked("http://127.0.0.1:8000/internal", "127.0.0.1")

    def test_loopback_whole_8_block_blocked(self):
        # Toute 127.0.0.0/8 est loopback, pas seulement 127.0.0.1.
        _assert_blocked("http://127.255.255.254/", "127.255.255.254")

    def test_ipv6_loopback_blocked(self):
        _assert_blocked("http://[::1]/", "::1")

    def test_rfc1918_10_blocked(self):
        _assert_blocked("https://public-name.example.com/", "10.0.0.1")

    def test_rfc1918_172_low_boundary_blocked(self):
        _assert_blocked("https://public-name.example.com/", "172.16.0.0")

    def test_rfc1918_172_high_boundary_blocked(self):
        # Borne haute de 172.16.0.0/12.
        _assert_blocked("https://public-name.example.com/", "172.31.255.255")

    def test_rfc1918_192_168_blocked(self):
        _assert_blocked("https://public-name.example.com/", "192.168.1.1")

    def test_aws_imds_metadata_blocked(self):
        # 169.254.169.254 = endpoint metadata AWS/GCP/Azure — vol de creds IAM.
        _assert_blocked("http://attacker-controlled.com/", "169.254.169.254")

    def test_link_local_range_blocked(self):
        # Toute la plage link-local 169.254.0.0/16, pas juste .169.254.
        _assert_blocked("http://attacker-controlled.com/", "169.254.0.1")

    def test_ipv6_unique_local_blocked(self):
        _assert_blocked("http://internal-v6.example.com/", "fc00::1")

    def test_ipv6_link_local_blocked(self):
        _assert_blocked("http://internal-v6.example.com/", "fe80::1")

    def test_cgnat_blocked(self):
        _assert_blocked("http://public.example.com/", "100.64.0.1")


# ── DNS rebinding : hostname public → IP privée ──────────────────────────────


class TestDnsRebinding:
    def test_public_hostname_resolving_private_is_blocked(self):
        # Invariant central : le contrôle porte sur l'IP RÉSOLUE, pas sur le nom.
        _assert_blocked("https://totally-legit-cdn.example.com/", "192.168.50.10")

    def test_any_private_ip_among_several_blocks(self):
        # Multi-A record : une seule IP privée doit suffire à bloquer.
        infos = [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("1.1.1.1", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("10.1.2.3", 0)),
        ]
        with patch("app.core.ssrf.socket.getaddrinfo", return_value=infos):
            with pytest.raises(HTTPException) as exc:
                assert_no_ssrf("https://round-robin.example.com/")
        assert exc.value.status_code == 422


# ── Schémes non-http / hôtes invalides ───────────────────────────────────────


class TestSchemesAndInvalidHosts:
    def test_file_scheme_no_host_blocked(self):
        # file:///etc/passwd n'a pas d'hôte → 422 (hôte manquant).
        with pytest.raises(HTTPException) as exc:
            assert_no_ssrf("file:///etc/passwd")
        assert exc.value.status_code == 422
        assert "hôte" in exc.value.detail

    def test_gopher_scheme_to_internal_blocked(self):
        # gopher://127.0.0.1:6379 (attaque Redis) : l'hôte résout en loopback.
        _assert_blocked("gopher://127.0.0.1:6379/_INFO", "127.0.0.1")

    def test_ftp_scheme_to_private_blocked(self):
        _assert_blocked("ftp://fileserver.example.com/secret", "10.10.10.10")

    def test_empty_host_blocked(self):
        with pytest.raises(HTTPException) as exc:
            assert_no_ssrf("https://")
        assert exc.value.status_code == 422
        assert "hôte" in exc.value.detail

    def test_unresolvable_host_blocked(self):
        # Une résolution DNS qui échoue ne doit jamais "passer" par défaut.
        with patch(
            "app.core.ssrf.socket.getaddrinfo",
            side_effect=socket.gaierror("Name or service not known"),
        ):
            with pytest.raises(HTTPException) as exc:
                assert_no_ssrf("https://does-not-exist.invalid/")
        assert exc.value.status_code == 422
        assert "résoudre" in exc.value.detail

    def test_garbage_ip_from_resolver_blocked(self):
        # Défense en profondeur : si le resolver renvoie une IP non parsable,
        # _is_private renvoie True (fail-closed) → doit bloquer.
        _assert_blocked("https://weird.example.com/", "not-an-ip-at-all")


# ── URL publique légitime : DOIT passer ──────────────────────────────────────


class TestAllowedTargets:
    def test_public_https_url_passes(self):
        with patch("app.core.ssrf.socket.getaddrinfo", return_value=_resolve_to("93.184.216.34")):
            assert_no_ssrf("https://example.com")  # ne doit PAS lever

    def test_public_dns_resolver_passes(self):
        with patch("app.core.ssrf.socket.getaddrinfo", return_value=_resolve_to("8.8.8.8")):
            assert_no_ssrf("https://dns.google/resolve")

    def test_172_15_is_public_and_passes(self):
        # Juste en-dessous de la plage 172.16.0.0/12 → doit rester autorisé
        # (garantit qu'on ne bloque pas trop large).
        with patch("app.core.ssrf.socket.getaddrinfo", return_value=_resolve_to("172.15.0.1")):
            assert_no_ssrf("https://public.example.com/")


# ── Adresses "unspecified" / IPv4-mapped (durci le 2026-07-02) ────────────────


class TestUnspecifiedAddress:
    def test_all_zeros_should_be_blocked(self):
        # 0.0.0.0 route vers localhost sur de nombreuses stacks → doit être refusé.
        _assert_blocked("http://0.0.0.0/", "0.0.0.0")

    def test_ipv6_unspecified_blocked(self):
        # :: (IPv6 unspecified) → même risque que 0.0.0.0.
        _assert_blocked("http://[::]/", "::")

    def test_ipv4_mapped_loopback_blocked(self):
        # ::ffff:127.0.0.1 : loopback IPv4 enveloppée en IPv6 — ne doit pas contourner.
        _assert_blocked("https://sneaky.example.com/", "::ffff:127.0.0.1")
