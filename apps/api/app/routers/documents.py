from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from app.core.messages import ErrorCode, format_message
from app.core.render import PAGINATION_WARNING_ID
from app.core.rules.models import Change, Finding
from app.services.ingest import validator
from app.services.storage import storage
from app.services.workflow import metrics_registry, workflow_service

router = APIRouter(prefix="/v1/documents", tags=["Documents"])


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    message: str


class AnalyzeRequest(BaseModel):
    profile_id: str = "contoh-s1-skripsi"


class AnalyzeResponse(BaseModel):
    job_id: str
    doc_id: str
    profile_id: str
    total_findings: int
    findings: list[Finding]
    roles: list[dict[str, Any]] = Field(default_factory=list)
    metrics_ms: dict[str, float] = Field(default_factory=dict)


class RoleOverrideItem(BaseModel):
    block_index: int
    role: str


class RoleUpdateRequest(BaseModel):
    roles: list[RoleOverrideItem] = Field(default_factory=list)
    overrides: dict[str, str] = Field(default_factory=dict)


class FixRequest(BaseModel):
    profile_id: Optional[str] = None
    mode: str = "all"  # "all" | "categories" | "findings"
    categories: list[str] = Field(default_factory=list)
    finding_ids: list[str] = Field(default_factory=list)
    approved_suggest_ids: list[str] = Field(default_factory=list)


class FixResponse(BaseModel):
    job_id: str
    doc_id: str
    profile_id: str
    total_changes: int
    changes: list[Change]
    remaining_findings: list[Finding] = Field(default_factory=list)
    metrics_ms: dict[str, float] = Field(default_factory=dict)


def _require_session(doc_id: str) -> None:
    if not storage.session_exists(doc_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sesi dokumen tidak ditemukan atau telah kedaluwarsa.",
            headers={"X-Error-Code": ErrorCode.DOC_NOT_FOUND},
        )


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)) -> UploadResponse:
    """Uploads and validates a Word (.docx) document."""
    content = await file.read()
    filename = file.filename or "dokumen.docx"

    validator.validate_file(filename, content)

    doc_id = storage.create_document_session(filename=filename)
    storage.save_upload(doc_id, content)
    metrics_registry.total_uploads += 1

    return UploadResponse(
        doc_id=doc_id,
        filename=filename,
        message=format_message("ingest.success"),
    )


@router.post("/{doc_id}/analyze", response_model=AnalyzeResponse)
def analyze_document(doc_id: str, request: AnalyzeRequest) -> AnalyzeResponse:
    """Analyzes a document against a chosen campus rule profile."""
    _require_session(doc_id)
    try:
        res = workflow_service.analyze(doc_id, request.profile_id)
        return AnalyzeResponse(**res)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profil aturan '{request.profile_id}' tidak ditemukan.",
            headers={"X-Error-Code": ErrorCode.PROFILE_NOT_FOUND},
        )


@router.get("/{doc_id}/findings")
def get_document_findings(
    doc_id: str,
    category: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    fix_mode: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    """Returns filtered findings for a document."""
    _require_session(doc_id)
    items = workflow_service.get_findings(
        doc_id, category=category, severity=severity, fix_mode=fix_mode
    )
    return {
        "doc_id": doc_id,
        "total_findings": len(items),
        "findings": items,
    }


@router.get("/{doc_id}/roles")
def get_document_roles(doc_id: str) -> dict[str, Any]:
    """Returns paragraph structural role assignments, confidence scores, and evidence."""
    _require_session(doc_id)
    roles = workflow_service.get_roles(doc_id)
    low_conf_count = sum(1 for r in roles if r.get("needs_confirmation"))
    return {
        "doc_id": doc_id,
        "total_blocks": len(roles),
        "needs_confirmation_count": low_conf_count,
        "roles": roles,
    }


@router.put("/{doc_id}/roles", response_model=AnalyzeResponse)
def update_document_roles(doc_id: str, request: RoleUpdateRequest) -> AnalyzeResponse:
    """Confirms or updates paragraph roles and re-evaluates findings."""
    _require_session(doc_id)
    updates: dict[int, str] = {}
    for item in request.roles:
        updates[item.block_index] = item.role
    for k, v in request.overrides.items():
        if str(k).isdigit():
            updates[int(k)] = v

    res = workflow_service.update_roles(doc_id, updates)
    return AnalyzeResponse(**res)


@router.post("/{doc_id}/fix", response_model=FixResponse)
def fix_document(doc_id: str, request: FixRequest) -> FixResponse:
    """Applies selected formatting fixes to a copy of the document."""
    _require_session(doc_id)
    try:
        res = workflow_service.fix(
            doc_id=doc_id,
            profile_id=request.profile_id,
            mode=request.mode,
            categories=request.categories,
            finding_ids=request.finding_ids,
            approved_suggest_ids=request.approved_suggest_ids,
        )
        return FixResponse(**res)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profil aturan '{request.profile_id}' tidak ditemukan.",
            headers={"X-Error-Code": ErrorCode.PROFILE_NOT_FOUND},
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proses perbaikan dibatalkan demi keamanan dokumen: {exc}",
            headers={"X-Error-Code": ErrorCode.FIX_INTEGRITY_FAILED},
        )


@router.get("/{doc_id}/preview")
def preview_document(doc_id: str, which: str = Query(default="after")) -> FileResponse:
    """Renders and returns a PDF preview ('before' or 'after') with pagination warning."""
    _require_session(doc_id)
    pdf_path, status_note = workflow_service.render_preview(doc_id, which=which)
    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"pratinjau-{which}.pdf",
        headers={
            "X-Pagination-Warning": PAGINATION_WARNING_ID,
            "X-Render-Status": status_note,
            "Access-Control-Expose-Headers": "X-Pagination-Warning, X-Render-Status",
        },
    )


@router.get("/{doc_id}/download")
def download_document(doc_id: str, which: str = Query(default="fixed")) -> FileResponse:
    """Downloads either the fixed or the original document."""
    _require_session(doc_id)
    if which == "fixed":
        path = storage.get_fixed_file_path(doc_id)
        if not path.exists():
            path = storage.get_original_file_path(doc_id)
    else:
        path = storage.get_original_file_path(doc_id)

    return FileResponse(
        path=path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"skripsi-{which}.docx",
    )


@router.get("/{doc_id}/changelog")
def get_document_changelog(doc_id: str) -> dict[str, Any]:
    """Returns the change log of all formatting modifications made to the document."""
    _require_session(doc_id)
    changes = storage.load_json(doc_id, "changelog.json", default=[])
    return {
        "doc_id": doc_id,
        "total_changes": len(changes),
        "changes": changes,
    }


@router.get("/{doc_id}/report")
def get_document_report(doc_id: str, format: str = Query(default="json")) -> Response:
    """Exports the compliance findings report in JSON or HTML format."""
    _require_session(doc_id)
    if format.lower() == "html":
        html_content = workflow_service.build_html_report(doc_id)
        return HTMLResponse(content=html_content)

    meta = storage.load_json(doc_id, "meta.json", default={})
    findings = storage.load_json(doc_id, "findings.json", default=[])
    changes = storage.load_json(doc_id, "changelog.json", default=[])
    return Response(
        content=__import__("json").dumps(
            {
                "doc_id": doc_id,
                "filename": meta.get("filename", "dokumen.docx"),
                "profile_id": meta.get("profile_id"),
                "total_findings": len(findings),
                "findings": findings,
                "total_changes": len(changes),
                "changes": changes,
            },
            ensure_ascii=False,
            indent=2,
        ),
        media_type="application/json",
    )


@router.delete("/{doc_id}")
def delete_document(doc_id: str) -> dict[str, Any]:
    """Deletes the document session and all derived files immediately."""
    deleted = storage.delete_document(doc_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokumen tidak ditemukan.",
            headers={"X-Error-Code": ErrorCode.DOC_NOT_FOUND},
        )
    return {
        "doc_id": doc_id,
        "deleted": True,
        "message": "Data dokumen dan seluruh berkas turunan telah dihapus sepenuhnya.",
    }
