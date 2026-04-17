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
    ipaddress.ip_network("100.64.0.0/10"),   # Carrier-grade NAT
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_private(ip_str: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip_str)
        return any(addr in net for net in _PRIVATE_NETWORKS)
    except ValueError:
        return True  # unparseable → block


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
