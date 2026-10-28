from __future__ import annotations

from docx.oxml.ns import qn

from app.core.docx_model import DocumentIR
from app.core.fixers.base import BaseFixer
from app.core.rules.models import Change, Finding, FixMethod, RuleProfile
from app.core.style_manager import assign_style_to_paragraph, ensure_style_for_role
from app.core.units import (
    cm_to_twips,
    line_spacing_multiplier_to_wline,
    pt_to_twips,
)
from app.core.xml_helpers import PPR_ORDER, get_or_add_ordered, get_or_add_pPr


class BibliographyFixer(BaseFixer):
    """Fixes bibliography hanging indent, spacing, and approved alphabetical sorting."""

    category = "BIB"

    def apply(
        self,
        ir: DocumentIR,
        findings: list[Finding],
        profile: RuleProfile,
    ) -> list[Change]:
        bib_findings = [f for f in findings if f.category == "BIB"]
        if not bib_findings:
            return []

        bib_spec = profile.roles.get("bibliography_entry", {})
        style_id = ensure_style_for_role(ir.doc, "bibliography_entry", profile)
        changes: list[Change] = []
        sort_requested = False

        for f in bib_findings:
            if f.rule_id == "BIB-001":
                sort_requested = True
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value="Urutan alfabetis A-Z",
                        method=FixMethod.DIRECT,
                    )
                )
                continue

            blk_idx = f.location.block_index
            if blk_idx < 0 or blk_idx >= len(ir.blocks):
                continue
            block = ir.blocks[blk_idx]
            if block.block_type != "paragraph" or block.has_tracked_changes:
                continue

            p_el = block.raw_element
            pPr = get_or_add_pPr(p_el)
            assign_style_to_paragraph(p_el, style_id)
            block.style_id = style_id

            if f.rule_id == "BIB-002":
                exp_hi = float(bib_spec.get("hanging_indent_cm", 1.25))
                ind = get_or_add_ordered(pPr, "ind", PPR_ORDER)
                if qn("w:firstLine") in ind.attrib:
                    del ind.attrib[qn("w:firstLine")]
                ind.set(qn("w:hanging"), str(cm_to_twips(exp_hi)))
                ind.set(qn("w:left"), str(cm_to_twips(float(bib_spec.get("left_indent_cm", 0.0)))))
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f"{exp_hi:.2f} cm",
                        method=FixMethod.STYLE,
                    )
                )

            elif f.rule_id == "BIB-003":
                exp_ls = float(bib_spec.get("line_spacing", 1.0))
                exp_sa = float(bib_spec.get("space_after_pt", 12.0))
                spacing = get_or_add_ordered(pPr, "spacing", PPR_ORDER)
                spacing.set(qn("w:before"), "0")
                spacing.set(qn("w:after"), str(pt_to_twips(exp_sa)))
                spacing.set(qn("w:line"), str(line_spacing_multiplier_to_wline(exp_ls)))
                spacing.set(qn("w:lineRule"), "auto")
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f"line={exp_ls:.2f}, after={exp_sa:g}pt",
                        method=FixMethod.STYLE,
                    )
                )

        if sort_requested:
            bib_blocks = [
                b
                for b in ir.blocks
                if b.assigned_role == "bibliography_entry" and not b.has_tracked_changes
            ]
            if len(bib_blocks) >= 2:
                anchor_prev = bib_blocks[0].raw_element.getprevious()
                parent = bib_blocks[0].raw_element.getparent()
                sorted_blocks = sorted(bib_blocks, key=lambda b: (b.text or "").strip().lower())
                for b in bib_blocks:
                    if b.raw_element.getparent() is not None:
                        b.raw_element.getparent().remove(b.raw_element)
                if anchor_prev is not None:
                    curr = anchor_prev
                    for sb in sorted_blocks:
                        curr.addnext(sb.raw_element)
                        curr = sb.raw_element
                elif parent is not None:
                    for idx, sb in enumerate(sorted_blocks):
                        parent.insert(idx, sb.raw_element)

        return changes
