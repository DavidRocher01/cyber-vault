from slowapi import Limiter
from starlette.requests import Request


def _get_real_ip(request: Request) -> str:
    # Trust X-Forwarded-For set by ALB/CloudFront (first IP = real client)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=_get_real_ip)
