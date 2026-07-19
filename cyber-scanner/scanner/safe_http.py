"""
SSRF-safe drop-in wrapper around `requests` for the scanner probes.

Le scanner reçoit une URL cible (validée côté backend par assert_no_ssrf AVANT
le lancement), mais chaque sonde refaisait ensuite des requêtes `requests` brutes
qui (a) suivaient les redirections sans revalidation et (b) re-résolvaient le nom
(fenêtre de DNS-rebinding / TOCTOU). Ce module rejoue le rôle du garde httpx du
backend (_redirect_ssrf_guard) côté scanner :

  - valide que l'hôte cible résout UNIQUEMENT vers des IP publiques ;
  - désactive l'auto-redirect de requests et suit les hops MANUELLEMENT en
    revalidant l'hôte de CHAQUE redirection avant de la suivre ;
  - respecte `allow_redirects` (les sondes qui le mettent à False ne suivent rien).

Usage : `from scanner import safe_http as requests` dans les sondes qui frappent
l'URL cible. Les appels `requests.get/head/post/options/request` et
`requests.exceptions.*` restent identiques (drop-in), donc les mocks de tests
qui patchent `<sonde>.requests.get` continuent de fonctionner.
"""

import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import requests as _requests

# Ré-export pour que `requests.exceptions.X` fonctionne à l'identique dans les sondes.
exceptions = _requests.exceptions

_MAX_REDIRECTS = 5

_PRIVATE_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # AWS IMDS + link-local
    ipaddress.ip_network("100.64.0.0/10"),  # Carrier-grade NAT
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_private(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # illisible -> on bloque (fail-closed)
    # IPv4-mapped IPv6 (::ffff:127.0.0.1) : déballer pour ne pas contourner le filtre.
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    if (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    ):
        return True
    return any(addr in net for net in _PRIVATE_NETWORKS)


def _assert_public(url: str) -> None:
    """Lève requests.exceptions.InvalidURL si l'hôte résout vers une IP interne."""
    host = urlparse(url).hostname
    if not host:
        raise exceptions.InvalidURL(f"URL sans hôte : {url}")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise exceptions.ConnectionError(f"Résolution impossible : {host}") from exc
    for info in infos:
        if _is_private(info[4][0]):
            raise exceptions.InvalidURL(f"SSRF bloqué : {host} résout vers une IP interne/privée")


def request(method: str, url: str, **kwargs):
    """requests.request SSRF-safe : valide l'hôte, suit les redirections en
    revalidant chaque hop (si allow_redirects, défaut True)."""
    follow = kwargs.pop("allow_redirects", True)
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        _assert_public(current)
        resp = _requests.request(method, current, allow_redirects=False, **kwargs)
        if follow and resp.is_redirect:
            location = resp.headers.get("location")
            if not location:
                return resp
            current = urljoin(current, location)
            continue
        return resp
    raise exceptions.TooManyRedirects(f"Trop de redirections : {url}")


def get(url: str, **kwargs):
    return request("GET", url, **kwargs)


def head(url: str, **kwargs):
    return request("HEAD", url, **kwargs)


def post(url: str, **kwargs):
    return request("POST", url, **kwargs)


def options(url: str, **kwargs):
    return request("OPTIONS", url, **kwargs)
