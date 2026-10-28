from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.config import settings
from app.services.workflow import metrics_registry

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check() -> dict[str, Any]:
    """Health check endpoint to verify API readiness."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/v1/metrics")
def get_metrics() -> dict[str, Any]:
    """Observability endpoint exposing privacy-safe stage durations and rule counters."""
    return metrics_registry.snapshot()
