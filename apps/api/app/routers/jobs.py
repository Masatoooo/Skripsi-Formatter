from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.core.messages import ErrorCode
from app.services.storage import storage

router = APIRouter(prefix="/v1/jobs", tags=["Jobs"])


@router.get("/{job_id}")
def get_job_status(job_id: str) -> dict[str, Any]:
    """Retrieves the status, stage metrics, and summary of an asynchronous/workflow job."""
    job = storage.get_job(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' tidak ditemukan.",
            headers={"X-Error-Code": ErrorCode.JOB_NOT_FOUND},
        )
    return job
