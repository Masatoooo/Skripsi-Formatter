from __future__ import annotations

import html
import time
from pathlib import Path
from typing import Any

from app.core.docx_model import DocumentIR
from app.core.fixers.runner import fix_runner
from app.core.render import render_docx_to_pdf
from app.core.roles import DEFAULT_CONFIDENCE_THRESHOLD, role_classifier
from app.core.rules.evaluator import rule_evaluator
from app.core.rules.loader import profile_loader
from app.core.rules.models import Finding
from app.services.logger import log_audit_event
from app.services.storage import storage


class MetricsRegistry:
    """In-memory observability metrics counter (privacy-safe, no document text)."""

    def __init__(self) -> None:
        self.total_uploads: int = 0
        self.total_analyses: int = 0
        self.total_fixes: int = 0
        self.total_renders: int = 0
        self.findings_by_rule: dict[str, int] = {}
        self.stage_durations_ms: dict[str, list[float]] = {
            "parse": [],
            "classify": [],
            "evaluate": [],
            "fix": [],
            "render": [],
        }

    def record_stage(self, stage: str, ms: float) -> None:
        bucket = self.stage_durations_ms.setdefault(stage, [])
        bucket.append(round(ms, 2))
        if len(bucket) > 200:
            bucket.pop(0)

    def record_findings(self, findings: list[Finding]) -> None:
        for f in findings:
            self.findings_by_rule[f.rule_id] = self.findings_by_rule.get(f.rule_id, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        avg_ms = {
            k: (round(sum(v) / len(v), 2) if v else 0.0) for k, v in self.stage_durations_ms.items()
        }
        return {
            "total_uploads": self.total_uploads,
            "total_analyses": self.total_analyses,
            "total_fixes": self.total_fixes,
            "total_renders": self.total_renders,
            "avg_stage_ms": avg_ms,
            "findings_by_rule": dict(self.findings_by_rule),
        }


metrics_registry = MetricsRegistry()


class DocumentWorkflowService:
    """Orchestrates document analysis, role confirmation, fixing, reporting, and rendering."""

    def analyze(self, doc_id: str, profile_id: str) -> dict[str, Any]:
        orig_path = storage.get_original_file_path(doc_id)
        profile = profile_loader.load(profile_id)

        job = storage.create_job(doc_id, "analyze")
        storage.update_job(job["job_id"], "running")

        try:
            t0 = time.perf_counter()
            ir = DocumentIR.from_docx(str(orig_path))
            parse_ms = (time.perf_counter() - t0) * 1000.0
            metrics_registry.record_stage("parse", parse_ms)

            # Load any user-confirmed role overrides for this session
            saved_overrides_raw = storage.load_json(doc_id, "role_overrides.json", default={})
            user_overrides = {int(k): str(v) for k, v in saved_overrides_raw.items()}

            t1 = time.perf_counter()
            role_assignments = role_classifier.classify(ir, user_overrides=user_overrides)
            classify_ms = (time.perf_counter() - t1) * 1000.0
            metrics_registry.record_stage("classify", classify_ms)

            t2 = time.perf_counter()
            findings = rule_evaluator.evaluate(ir, profile, user_role_overrides=user_overrides)
            evaluate_ms = (time.perf_counter() - t2) * 1000.0
            metrics_registry.record_stage("evaluate", evaluate_ms)

            metrics_registry.total_analyses += 1
            metrics_registry.record_findings(findings)

            # Save session state
            meta = storage.load_json(doc_id, "meta.json", default={})
            meta["profile_id"] = profile_id
            storage.save_json(doc_id, "meta.json", meta)
            storage.save_json(doc_id, "findings.json", [f.model_dump() for f in findings])

            roles_payload = []
            for ra in role_assignments:
                blk = ir.blocks[ra.block_index]
                excerpt = (blk.text or "").strip().replace("\n", " ")[:100]
                roles_payload.append(
                    {
                        **ra.model_dump(),
                        "needs_confirmation": (
                            ra.confidence < DEFAULT_CONFIDENCE_THRESHOLD and not ra.user_confirmed
                        ),
                        "excerpt": excerpt,
                    }
                )
            storage.save_json(doc_id, "roles.json", roles_payload)

            stage_metrics = {
                "parse_ms": round(parse_ms, 2),
                "classify_ms": round(classify_ms, 2),
                "evaluate_ms": round(evaluate_ms, 2),
            }
            storage.update_job(
                job["job_id"],
                "done",
                metrics_ms=stage_metrics,
                result_summary={"total_findings": len(findings)},
            )
            log_audit_event(
                "ANALYZE_COMPLETED",
                doc_id,
                details={"profile_id": profile_id, "total_findings": len(findings)},
            )

            return {
                "job_id": job["job_id"],
                "doc_id": doc_id,
                "profile_id": profile_id,
                "total_findings": len(findings),
                "findings": findings,
                "roles": roles_payload,
                "metrics_ms": stage_metrics,
            }
        except Exception as exc:
            storage.update_job(
                job["job_id"],
                "failed",
                error_code="ANALYZE_FAILED",
                error_message=str(exc),
            )
            raise

    def get_findings(
        self,
        doc_id: str,
        category: str | None = None,
        severity: str | None = None,
        fix_mode: str | None = None,
    ) -> list[dict[str, Any]]:
        raw_findings: list[dict[str, Any]] = storage.load_json(doc_id, "findings.json", default=[])
        results = raw_findings
        if category:
            cat_up = category.upper()
            results = [f for f in results if f.get("category", "").upper() == cat_up]
        if severity:
            sev_low = severity.lower()
            results = [f for f in results if f.get("severity", "").lower() == sev_low]
        if fix_mode:
            fm_low = fix_mode.lower()
            results = [f for f in results if f.get("fix_mode", "").lower() == fm_low]
        return results

    def get_roles(self, doc_id: str) -> list[dict[str, Any]]:
        roles = storage.load_json(doc_id, "roles.json", default=None)
        if roles is not None:
            return list(roles)
        # If analyze hasn't been called yet, classify on the fly
        orig_path = storage.get_original_file_path(doc_id)
        ir = DocumentIR.from_docx(str(orig_path))
        assignments = role_classifier.classify(ir)
        payload = []
        for ra in assignments:
            blk = ir.blocks[ra.block_index]
            excerpt = (blk.text or "").strip().replace("\n", " ")[:100]
            payload.append(
                {
                    **ra.model_dump(),
                    "needs_confirmation": ra.confidence < DEFAULT_CONFIDENCE_THRESHOLD,
                    "excerpt": excerpt,
                }
            )
        storage.save_json(doc_id, "roles.json", payload)
        return payload

    def update_roles(self, doc_id: str, role_updates: dict[int, str]) -> dict[str, Any]:
        saved_overrides_raw = storage.load_json(doc_id, "role_overrides.json", default={})
        for blk_idx, role_name in role_updates.items():
            saved_overrides_raw[str(blk_idx)] = role_name
        storage.save_json(doc_id, "role_overrides.json", saved_overrides_raw)

        meta = storage.load_json(doc_id, "meta.json", default={})
        profile_id = meta.get("profile_id") or "contoh-s1-skripsi"
        res = self.analyze(doc_id, profile_id)
        log_audit_event(
            "ROLES_CONFIRMED",
            doc_id,
            details={"updated_count": len(role_updates)},
        )
        return res

    def fix(
        self,
        doc_id: str,
        profile_id: str | None = None,
        mode: str = "all",
        categories: list[str] | None = None,
        finding_ids: list[str] | None = None,
        approved_suggest_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        meta = storage.load_json(doc_id, "meta.json", default={})
        active_profile_id = profile_id or meta.get("profile_id") or "contoh-s1-skripsi"
        profile = profile_loader.load(active_profile_id)

        saved_overrides_raw = storage.load_json(doc_id, "role_overrides.json", default={})
        user_overrides = {int(k): str(v) for k, v in saved_overrides_raw.items()}

        job = storage.create_job(doc_id, "fix")
        storage.update_job(job["job_id"], "running")

        try:
            orig_path = storage.get_original_file_path(doc_id)
            fixed_path = storage.prepare_working_copy(doc_id)

            t0 = time.perf_counter()
            changes, remaining = fix_runner.run(
                input_path=orig_path,
                output_path=fixed_path,
                profile=profile,
                mode=mode,
                categories=categories,
                finding_ids=finding_ids,
                approved_suggest_ids=approved_suggest_ids,
                user_role_overrides=user_overrides,
            )
            fix_ms = (time.perf_counter() - t0) * 1000.0
            metrics_registry.record_stage("fix", fix_ms)
            metrics_registry.total_fixes += 1

            storage.save_json(doc_id, "changelog.json", [c.model_dump() for c in changes])
            storage.save_json(doc_id, "findings_after.json", [f.model_dump() for f in remaining])

            stage_metrics = {"fix_ms": round(fix_ms, 2)}
            storage.update_job(
                job["job_id"],
                "done",
                metrics_ms=stage_metrics,
                result_summary={
                    "total_changes": len(changes),
                    "remaining_findings": len(remaining),
                },
            )
            log_audit_event(
                "FIX_COMPLETED",
                doc_id,
                details={
                    "profile_id": active_profile_id,
                    "changes_count": len(changes),
                    "remaining_count": len(remaining),
                },
            )

            return {
                "job_id": job["job_id"],
                "doc_id": doc_id,
                "profile_id": active_profile_id,
                "total_changes": len(changes),
                "changes": changes,
                "remaining_findings": remaining,
                "metrics_ms": stage_metrics,
            }
        except Exception as exc:
            storage.update_job(
                job["job_id"],
                "failed",
                error_code="FIX_FAILED",
                error_message=str(exc),
            )
            raise

    def render_preview(self, doc_id: str, which: str = "after") -> tuple[Path, str]:
        safe_which = "before" if which == "before" else "after"
        if safe_which == "after":
            src_docx = storage.get_fixed_file_path(doc_id)
            if not src_docx.exists():
                src_docx = storage.get_original_file_path(doc_id)
        else:
            src_docx = storage.get_original_file_path(doc_id)

        out_pdf = storage.get_preview_pdf_path(doc_id, safe_which)
        t0 = time.perf_counter()
        _, status_note = render_docx_to_pdf(src_docx, out_pdf)
        render_ms = (time.perf_counter() - t0) * 1000.0
        metrics_registry.record_stage("render", render_ms)
        metrics_registry.total_renders += 1
        return out_pdf, status_note

    def build_html_report(self, doc_id: str) -> str:
        meta = storage.load_json(doc_id, "meta.json", default={})
        findings = storage.load_json(doc_id, "findings.json", default=[])
        changes = storage.load_json(doc_id, "changelog.json", default=[])
        profile_id = meta.get("profile_id") or "contoh-s1-skripsi"
        filename = html.escape(str(meta.get("filename", "dokumen.docx")))

        rows_html = []
        for f in findings:
            rule_id = html.escape(str(f.get("rule_id", "")))
            cat = html.escape(str(f.get("category", "")))
            sev = html.escape(str(f.get("severity", "")))
            fm = html.escape(str(f.get("fix_mode", "")))
            msg = html.escape(str(f.get("message", "")))
            act = html.escape(str(f.get("actual", "")))
            exp = html.escape(str(f.get("expected", "")))
            loc = f.get("location", {})
            loc_str = f"Section {int(loc.get('section_index', 0)) + 1}, Blok #{int(loc.get('block_index', 0)) + 1}"
            rows_html.append(
                f"<tr><td><code>{rule_id}</code></td><td>{cat}</td><td>{sev}</td>"
                f"<td>{fm}</td><td>{loc_str}</td><td>{msg}</td><td>{act}</td><td>{exp}</td></tr>"
            )

        table_body = (
            "\n".join(rows_html)
            if rows_html
            else ("<tr><td colspan='8'>Tidak ada temuan pelanggaran format (0 temuan).</td></tr>")
        )

        return f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="utf-8" />
  <title>Laporan Kepatuhan Format Skripsi — {filename}</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; margin: 32px; color: #0f172a; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color: #475569; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border: 1px solid #cbd5e1; padding: 8px 10px; text-align: left; vertical-align: top; }}
    th {{ background: #f1f5f9; }}
  </style>
</head>
<body>
  <h1>Laporan Kepatuhan Format Skripsi</h1>
  <div class="meta">
    Dokumen: <strong>{filename}</strong> &middot;
    Profil Aturan: <code>{html.escape(str(profile_id))}</code> &middot;
    Total Temuan: <strong>{len(findings)}</strong> &middot;
    Perubahan Diterapkan: <strong>{len(changes)}</strong>
  </div>
  <table>
    <thead>
      <tr>
        <th>Kode</th><th>Kategori</th><th>Severity</th><th>Mode</th>
        <th>Lokasi</th><th>Deskripsi Temuan</th><th>Aktual</th><th>Diharapkan</th>
      </tr>
    </thead>
    <tbody>
      {table_body}
    </tbody>
  </table>
</body>
</html>"""


workflow_service = DocumentWorkflowService()
