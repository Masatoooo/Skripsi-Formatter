from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.core.rules.loader import profile_loader

router = APIRouter(prefix="/v1/profiles", tags=["Profiles"])


@router.get("")
def list_profiles() -> list[dict[str, Any]]:
    """List all registered campus formatting rule profiles."""
    return profile_loader.list_available_profiles()


@router.get("/{profile_id}")
def get_profile(profile_id: str) -> dict[str, Any]:
    """Retrieve full detail of a specific rule profile."""
    try:
        profile = profile_loader.load(profile_id)
        return profile.model_dump()
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profil aturan '{profile_id}' tidak ditemukan.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal memuat profil: {str(e)}",
        )
