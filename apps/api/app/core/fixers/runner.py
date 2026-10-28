from __future__ import annotations

import shutil
from pathlib import Path

from docx import Document

from app.core.docx_model import DocumentIR
from app.core.fixers.bibliography import BibliographyFixer
from app.core.fixers.caption import CaptionFixer
from app.core.fixers.figure import FigureFixer
from app.core.fixers.font import FontFixer
from app.core.fixers.heading import HeadingFixer
from app.core.fixers.numbering import NumberingFixer
from app.core.fixers.page import PageFixer
from app.core.fixers.para import ParaFixer
from app.core.fixers.structure import StructureFixer
from app.core.fixers.table import TableFixer
from app.core.fixers.toc import TocFixer
from app.core.integrity import verify_text_integrity
from app.core.messages import ErrorCode
from app.core.rules.evaluator import rule_evaluator
from app.core.rules.models import Change, Finding, FixMode, RuleProfile


class FixRunner:
    """Orchestrates deterministic document fixing, integrity verification, and re-open validation."""

    def run(
        self,
        input_path: str | Path,
        output_path: str | Path,
        profile: RuleProfile,
        mode: str = "all",
        categories: list[str] | None = None,
        finding_ids: list[str] | None = None,
        approved_suggest_ids: list[str] | None = None,
        user_role_overrides: dict[int, str] | None = None,
    ) -> tuple[list[Change], list[Finding]]:
        in_p = Path(input_path)
        out_p = Path(output_path)

        # Work on a copy so input_path is never mutated if in_p != out_p
        if in_p.resolve() != out_p.resolve():
            shutil.copy2(in_p, out_p)

        ir = DocumentIR.from_docx(str(out_p))
        all_findings = rule_evaluator.evaluate(ir, profile, user_role_overrides=user_role_overrides)

        selected_findings = self._select_findings(
            all_findings=all_findings,
            mode=mode,
            categories=categories,
            finding_ids=finding_ids,
            approved_suggest_ids=approved_suggest_ids,
        )

        if not selected_findings:
            return [], all_findings

        head_fixer = HeadingFixer()
        toc_fixer = TocFixer()
        cap_fixer = CaptionFixer()
        fixers = [
            PageFixer(),
            FontFixer(),
            ParaFixer(),
            head_fixer,
            cap_fixer,
            FigureFixer(),
            TableFixer(),
            BibliographyFixer(),
            StructureFixer(),
            toc_fixer,
            NumberingFixer(),
        ]

        changes: list[Change] = []
        for fixer in fixers:
            fixer_changes = fixer.apply(ir, selected_findings, profile)
            changes.extend(fixer_changes)

        ir.doc.save(str(out_p))

        # 1. Re-open validation in python-docx and DocumentIR
        try:
            _ = Document(str(out_p))
            _ = DocumentIR.from_docx(str(out_p))
        except Exception as exc:
            raise RuntimeError(f"{ErrorCode.FIX_REOPEN_FAILED}: {exc}") from exc

        # 2. Text integrity verification
        approved_rules = {f.rule_id for f in selected_findings if f.fix_mode == FixMode.SUGGEST}
        ok, diff_msg = verify_text_integrity(
            before_doc_or_path=in_p,
            after_doc_or_path=out_p,
            approved_rule_ids=approved_rules,
            excluded_prefixes=head_fixer.excluded_prefixes,
            excluded_lines=toc_fixer.excluded_lines,
            replaced_pairs=cap_fixer.replaced_pairs,
        )
        if not ok:
            raise RuntimeError(f"{ErrorCode.FIX_INTEGRITY_FAILED}: {diff_msg}")

        # Re-evaluate remaining findings after fix
        updated_ir = DocumentIR.from_docx(str(out_p))
        remaining_findings = rule_evaluator.evaluate(
            updated_ir, profile, user_role_overrides=user_role_overrides
        )

        return changes, remaining_findings

    @staticmethod
    def _select_findings(
        all_findings: list[Finding],
        mode: str,
        categories: list[str] | None,
        finding_ids: list[str] | None,
        approved_suggest_ids: list[str] | None,
    ) -> list[Finding]:
        cat_set = {c.upper() for c in (categories or [])}
        fid_set = set(finding_ids or [])
        suggest_set = set(approved_suggest_ids or []) | fid_set

        selected: list[Finding] = []
        for f in all_findings:
            if f.fix_mode == FixMode.MANUAL:
                continue

            if f.fix_mode == FixMode.SUGGEST:
                # Suggest rules require explicit approval by finding ID or rule ID
                if f.id in suggest_set or f.rule_id in suggest_set:
                    selected.append(f)
                continue

            # f.fix_mode == FixMode.AUTO
            if mode == "findings":
                if f.id in fid_set or f.rule_id in fid_set:
                    selected.append(f)
            elif mode == "categories":
                if f.category.upper() in cat_set:
                    selected.append(f)
            else:
                selected.append(f)

        return selected


fix_runner = FixRunner()
