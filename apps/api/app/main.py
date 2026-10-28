from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.messages import ErrorCode, format_message
from app.routers import documents, health, jobs, profiles

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API untuk Skripsi Formatter: alat pemeriksa dan perapi format dokumen skripsi (.docx)",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory sliding-window rate limiter per IP
_rate_buckets: dict[str, list[float]] = defaultdict(list)


def reset_rate_limiter() -> None:
    """Clears rate limiter state (useful for tests)."""
    _rate_buckets.clear()


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next: Callable[[Request], Any]) -> Response:
    limit = settings.rate_limit_per_minute
    if limit > 0:
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        window = _rate_buckets[client_ip]
        # Prune timestamps older than 60s
        while window and now - window[0] > 60.0:
            window.pop(0)
        if len(window) >= limit:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": format_message("rate_limit.exceeded")},
                headers={"X-Error-Code": ErrorCode.RATE_LIMIT_EXCEEDED},
            )
        window.append(now)

    response: Response = await call_next(request)
    return response


# Routers
app.include_router(health.router)
app.include_router(profiles.router)
app.include_router(documents.router)
app.include_router(jobs.router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Selamat datang di Skripsi Formatter API.",
        "docs": "/docs",
        "health": "/health",
    }
