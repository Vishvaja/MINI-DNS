from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi import Request

# 100 requests/minute per IP
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])

@limiter.limit
def exempt_health_check(request: Request):
    return request.url.path == "/health"
