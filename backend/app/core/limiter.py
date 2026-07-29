import ipaddress
import secrets as _secrets

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

    Anti-spoof gate (defense-in-depth, S2 / audit finding #4): a request that
    reaches the ALB directly (bypassing CloudFront) can forge X-Forwarded-For and
    is INDISTINGUISHABLE at the app layer from a legitimate CloudFront chain by
    length alone. The robust fix is the infra lock (ALB behind CloudFront via a
    secret X-Origin-Verify header). When ORIGIN_VERIFY_SECRET is configured, we
    enforce that header here: a request lacking it did not transit CloudFront, so
    its X-Forwarded-For is untrusted and we use the TCP peer IP instead. No-op
    (behaviour unchanged) until the secret is provisioned on both ends.
    """
    secret = settings.ORIGIN_VERIFY_SECRET
    if (
        isinstance(secret, str)
        and secret
        and not _secrets.compare_digest(request.headers.get("X-Origin-Verify", ""), secret)
    ):
        return request.client.host if request.client else "unknown"

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


_LOOPBACK = {"127.0.0.1", "::1", "localhost"}


def _rate_limit_key(request: Request) -> str:
    """
    In production, use the real client IP so rate limits apply normally.
    In dev/test, loopback requests each get a unique key so limits never fire —
    this lets the E2E test suite register/login freely without hitting auth limits.
    """
    ip = _get_real_ip(request)
    if settings.APP_ENV != "production" and ip in _LOOPBACK:
        return f"dev_loopback_{id(request)}"
    return ip


# storage_uri partagé si REDIS_URL est configuré (compteurs globaux à toutes les
# tâches ECS) ; sinon "memory://" in-process — défaut slowapi, comportement
# inchangé tant qu'ElastiCache n'est pas provisionné (cf. audit finding #5).
limiter = Limiter(key_func=_rate_limit_key, storage_uri=settings.REDIS_URL or "memory://")
