"""Tests du garde SSRF safe_http (validation IP + revalidation des redirections)."""

from unittest.mock import MagicMock, patch

import pytest

from scanner import safe_http


def _addrinfo(ip: str):
    # getaddrinfo -> [(family, type, proto, canonname, sockaddr)]
    return [(2, 1, 6, "", (ip, 0))]


def test_is_private_blocks_internal_and_allows_public():
    for ip in ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "::1", "172.16.0.1"]:
        assert safe_http._is_private(ip), ip
    for ip in ["8.8.8.8", "1.1.1.1", "93.184.216.34"]:
        assert not safe_http._is_private(ip), ip


def test_assert_public_blocks_private_resolution():
    with patch("scanner.safe_http.socket.getaddrinfo", return_value=_addrinfo("169.254.169.254")):
        with pytest.raises(safe_http.exceptions.InvalidURL):
            safe_http._assert_public("http://metadata.internal/latest/meta-data/")


def test_assert_public_allows_public():
    with patch("scanner.safe_http.socket.getaddrinfo", return_value=_addrinfo("8.8.8.8")):
        safe_http._assert_public("http://example.com/")  # ne lève pas


def test_get_blocks_redirect_to_internal():
    """Une redirection d'un hôte public vers une IP interne est bloquée AVANT de la suivre."""
    redirect = MagicMock()
    redirect.is_redirect = True
    redirect.headers = {"location": "http://169.254.169.254/latest/meta-data/"}

    def fake_getaddrinfo(host, *a, **k):
        return _addrinfo("8.8.8.8" if host == "public.example" else "169.254.169.254")

    with (
        patch("scanner.safe_http.socket.getaddrinfo", side_effect=fake_getaddrinfo),
        patch("scanner.safe_http._requests.request", return_value=redirect),
    ):
        with pytest.raises(safe_http.exceptions.InvalidURL):
            safe_http.get("http://public.example/")


def test_get_follows_public_redirect_and_returns_final():
    redirect = MagicMock()
    redirect.is_redirect = True
    redirect.headers = {"location": "http://public.example/next"}
    final = MagicMock()
    final.is_redirect = False
    final.status_code = 200

    with (
        patch("scanner.safe_http.socket.getaddrinfo", return_value=_addrinfo("8.8.8.8")),
        patch("scanner.safe_http._requests.request", side_effect=[redirect, final]),
    ):
        resp = safe_http.get("http://public.example/")
    assert resp is final


def test_allow_redirects_false_does_not_follow():
    redirect = MagicMock()
    redirect.is_redirect = True
    redirect.headers = {"location": "http://169.254.169.254/"}
    with (
        patch("scanner.safe_http.socket.getaddrinfo", return_value=_addrinfo("8.8.8.8")),
        patch("scanner.safe_http._requests.request", return_value=redirect),
    ):
        # allow_redirects=False : on renvoie la 3xx sans la suivre (donc sans bloquer).
        resp = safe_http.get("http://public.example/", allow_redirects=False)
    assert resp is redirect
