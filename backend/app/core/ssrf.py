import ipaddress
import socket
from urllib.parse import urlparse

from fastapi import HTTPException

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
        return True  # unparseable → block (fail-closed)

    # IPv4-mapped IPv6 (ex. ::ffff:127.0.0.1) : déballer vers l'IPv4 sous-jacente
    # pour empêcher de contourner les contrôles en enveloppant une IP interne.
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped

    # Classification native (défense en profondeur) : couvre 0.0.0.0/8 et :: (unspecified),
    # loopback, link-local (169.254 / fe80), multicast et plages réservées — en plus
    # des plages privées explicites ci-dessous.
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


def assert_no_ssrf(url: str) -> None:
    """Raise HTTP 422 if the URL resolves to a private/internal IP address."""
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=422, detail="URL invalide : hôte manquant")

    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise HTTPException(status_code=422, detail=f"Impossible de résoudre l'hôte : {hostname}")

    for info in infos:
        ip = info[4][0]
        if _is_private(ip):
            raise HTTPException(
                status_code=422,
                detail="URL refusée : l'hôte résout vers une adresse IP privée ou réservée",
            )
