from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.logger import log_audit_event


class StorageService:
    """Manages secure temporary document storage, jobs, and session artifacts with TTL."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir or settings.storage_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._jobs: dict[str, dict[str, Any]] = {}

    def create_document_session(self, filename: str = "dokumen.docx") -> str:
        """Generates a unique document session ID and folder."""
        self.cleanup_expired()
        doc_id = str(uuid.uuid4())
        session_path = self.root_dir / doc_id
        session_path.mkdir(parents=True, exist_ok=True)
        self.save_json(
            doc_id,
            "meta.json",
            {
                "doc_id": doc_id,
                "filename": filename,
                "created_at": time.time(),
                "profile_id": None,
            },
        )
        log_audit_event("SESSION_CREATED", doc_id)
        return doc_id

    def session_exists(self, doc_id: str) -> bool:
        try:
            uuid.UUID(doc_id)
        except ValueError:
            return False
        return (self.get_session_dir(doc_id) / "original.docx").exists()

    def get_session_dir(self, doc_id: str) -> Path:
        return self.root_dir / doc_id

    def get_original_file_path(self, doc_id: str) -> Path:
        return self.get_session_dir(doc_id) / "original.docx"

    def get_fixed_file_path(self, doc_id: str) -> Path:
        return self.get_session_dir(doc_id) / "fixed.docx"

    def get_preview_pdf_path(self, doc_id: str, which: str = "after") -> Path:
        safe_which = "before" if which == "before" else "after"
        return self.get_session_dir(doc_id) / f"preview_{safe_which}.pdf"

    def save_upload(self, doc_id: str, content: bytes) -> Path:
        """Saves uploaded raw bytes into original.docx."""
        path = self.get_original_file_path(doc_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(content)
        log_audit_event("FILE_SAVED", doc_id, details={"size_bytes": len(content)})
        return path

    def prepare_working_copy(self, doc_id: str) -> Path:
        """Copies original.docx to fixed.docx so original.docx is never touched."""
        orig = self.get_original_file_path(doc_id)
        fixed = self.get_fixed_file_path(doc_id)
        shutil.copy2(orig, fixed)
        return fixed

    def save_json(self, doc_id: str, name: str, data: Any) -> Path:
        path = self.get_session_dir(doc_id) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    def load_json(self, doc_id: str, name: str, default: Any = None) -> Any:
        path = self.get_session_dir(doc_id) / name
        if not path.exists():
            return default
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def create_job(self, doc_id: str, job_type: str) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        job = {
            "job_id": job_id,
            "doc_id": doc_id,
            "job_type": job_type,
            "status": "queued",
            "created_at": time.time(),
            "updated_at": time.time(),
            "metrics_ms": {},
            "error_code": None,
            "error_message": None,
            "result_summary": {},
        }
        self._jobs[job_id] = job
        self.save_json(doc_id, f"job_{job_id}.json", job)
        return job

    def update_job(
        self,
        job_id: str,
        status: str,
        metrics_ms: dict[str, float] | None = None,
        result_summary: dict[str, Any] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        if not job:
            return None
        job["status"] = status
        job["updated_at"] = time.time()
        if metrics_ms is not None:
            job["metrics_ms"].update(metrics_ms)
        if result_summary is not None:
            job["result_summary"].update(result_summary)
        if error_code is not None:
            job["error_code"] = error_code
        if error_message is not None:
            job["error_message"] = error_message
        doc_id = job["doc_id"]
        if self.get_session_dir(doc_id).exists():
            self.save_json(doc_id, f"job_{job_id}.json", job)
        return job

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        if job_id in self._jobs:
            return self._jobs[job_id]
        # Fallback search on disk
        for session_dir in self.root_dir.iterdir():
            if session_dir.is_dir():
                job_file = session_dir / f"job_{job_id}.json"
                if job_file.exists():
                    with open(job_file, encoding="utf-8") as f:
                        job: dict[str, Any] = json.load(f)
                        self._jobs[job_id] = job
                        return job
        return None

    def delete_document(self, doc_id: str) -> bool:
        """Explicitly deletes a document session and all derived artifacts."""
        session_path = self.get_session_dir(doc_id)
        if session_path.exists():
            shutil.rmtree(session_path)
            # Clean associated jobs from memory
            to_delete = [jid for jid, j in self._jobs.items() if j.get("doc_id") == doc_id]
            for jid in to_delete:
                del self._jobs[jid]
            log_audit_event("SESSION_DELETED", doc_id)
            return True
        return False

    def cleanup_expired(self, max_age_seconds: int | None = None) -> int:
        """Removes sessions older than TTL."""
        ttl = max_age_seconds if max_age_seconds is not None else settings.temp_file_ttl_seconds
        now = time.time()
        deleted_count = 0

        if not self.root_dir.exists():
            return 0

        for session_dir in list(self.root_dir.iterdir()):
            if session_dir.is_dir():
                meta_file = session_dir / "meta.json"
                mtime = session_dir.stat().st_mtime
                if meta_file.exists():
                    try:
                        with open(meta_file, encoding="utf-8") as f:
                            meta = json.load(f)
                            mtime = float(meta.get("created_at", mtime))
                    except Exception:
                        pass
                if now - mtime > ttl:
                    doc_id = session_dir.name
                    shutil.rmtree(session_dir, ignore_errors=True)
                    to_delete = [jid for jid, j in self._jobs.items() if j.get("doc_id") == doc_id]
                    for jid in to_delete:
                        del self._jobs[jid]
                    log_audit_event("SESSION_EXPIRED_CLEANUP", doc_id)
                    deleted_count += 1

        return deleted_count


storage = StorageService()
