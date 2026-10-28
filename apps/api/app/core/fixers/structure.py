from __future__ import annotations

from app.core.docx_model import DocumentIR
from app.core.fixers.base import BaseFixer
from app.core.rules.models import Change, Finding, FixMethod, RuleProfile
from app.core.xml_helpers import PPR_ORDER, get_or_add_pPr, set_boolean_prop


class StructureFixer(BaseFixer):
    """Fixes STR-004 (ensuring required thesis sections start on a new page)."""

    category = "STR"

    def apply(
        self,
        ir: DocumentIR,
        findings: list[Finding],
        profile: RuleProfile,
    ) -> list[Change]:
        str_findings = [f for f in findings if f.category == "STR" and f.rule_id == "STR-004"]
        if not str_findings:
            return []

        changes: list[Change] = []
        for f in str_findings:
            blk_idx = f.location.block_index
            if blk_idx < 0 or blk_idx >= len(ir.blocks):
                continue
            block = ir.blocks[blk_idx]
            if block.block_type != "paragraph" or block.has_tracked_changes:
                continue

            pPr = get_or_add_pPr(block.raw_element)
            set_boolean_prop(pPr, "pageBreakBefore", True, PPR_ORDER)
            changes.append(
                Change(
                    finding_id=f.id,
                    rule_id=f.rule_id,
                    location=f.location,
                    old_value=f.actual,
                    new_value="pageBreakBefore=true",
                    method=FixMethod.DIRECT,
                )
            )

        return changes
