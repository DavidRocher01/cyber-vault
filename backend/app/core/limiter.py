import ipaddress

from slowapi import Limiter
from starlette.requests import Request

from app.core.config import settings


def _is_public_ip(ip_str: str) -> bool:
    """Return True only if ip_str is a routable, non-private, non-loopback address."""
    try:
        addr = ipaddress.ip_address(ip_str)
        return not (addr.is_private or addr.is_loopback or addr.is_reserved or addr.is_link_local)
    except ValueError:
        return False


def _get_real_ip(request: Request) -> str:
    """
    Extract the real client IP when running behind N trusted reverse proxies.

    X-Forwarded-For is built left-to-right: each proxy appends the IP of the
    host that connected to it.  With TRUSTED_PROXY_COUNT=N we trust the last N
    entries and use the one just before them as the real client IP.

    Example (CloudFront + ALB, N=2):
        X-Forwarded-For: <client>  <CF-edge>
                          ^idx=0    ^idx=1   (ALB appended CF-edge)
        → real client = ips[len - 2] = ips[0]

    Spoofing defence: if there are fewer than N+1 IPs in the chain (the request
    bypassed some proxies), we fall back to request.client.host which is the IP
    that actually connected to the server — at least that cannot be spoofed at
    the TCP layer.
    """
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    ips = [ip.strip() for ip in forwarded_for.split(",") if ip.strip()]

    n = settings.TRUSTED_PROXY_COUNT
    if n > 0 and ips and len(ips) >= n:
        # Strip the N rightmost IPs (added by trusted proxies) and use the
        # leftmost remaining IP — the outermost non-trusted address.
        candidate = ips[-n]
        if _is_public_ip(candidate):
            return candidate

    # Fewer IPs than expected (bypassed proxies) or n=0 — fall back to the
    # rightmost public IP which is the least-spoofable entry.
    for ip in reversed(ips):
        if _is_public_ip(ip):
            return ip

    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_get_real_ip)
