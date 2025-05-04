from fastapi import FastAPI
from app.auth.rate_limiter import limiter
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from app.services.ttl_cleanup import start_cleanup_task
from app.api import dns_routes

import os

app = FastAPI()

# Middleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

if not os.getenv("TESTING", "0") == "1":
    start_cleanup_task(app)
    
# Error handler for rate limit
@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."}
    )

# Routes
app.include_router(dns_routes.router, prefix="/api/dns")
