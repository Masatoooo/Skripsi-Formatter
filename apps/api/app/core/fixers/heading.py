from __future__ import annotations

import re

from docx.oxml.ns import qn

from app.core.docx_model import DocumentIR
from app.core.fields import ensure_multilevel_heading_num_id
from app.core.fixers.base import BaseFixer
from app.core.rules.models import Change, Finding, FixMethod, RuleProfile
from app.core.style_manager import assign_style_to_paragraph, ensure_style_for_role
from app.core.units import (
    cm_to_twips,
    line_spacing_multiplier_to_wline,
    pt_to_twips,
)
from app.core.xml_helpers import (
    PPR_ORDER,
    RPR_ORDER,
    get_or_add_ordered,
    get_or_add_pPr,
    get_or_add_rPr,
    set_boolean_prop,
    set_w_val,
)


class HeadingFixer(BaseFixer):
    """Fixes chapter headings, sub-headings, keepWithNext, pageBreakBefore, and typed heading numbers."""

    category = "HEAD"

    def __init__(self) -> None:
        self.excluded_prefixes: list[str] = []

    def apply(
        self,
        ir: DocumentIR,
        findings: list[Finding],
        profile: RuleProfile,
    ) -> list[Change]:
        head_findings = [f for f in findings if f.category == "HEAD"]
        if not head_findings:
            return []

        ensured_roles: dict[str, str] = {}
        changes: list[Change] = []

        for f in head_findings:
            blk_idx = f.location.block_index
            if blk_idx < 0 or blk_idx >= len(ir.blocks):
                continue
            block = ir.blocks[blk_idx]
            if block.block_type != "paragraph" or block.has_tracked_changes:
                continue

            role = block.assigned_role or "heading_2"
            role_spec = dict(profile.roles.get(role, {}))
            if role == "front_title" and not role_spec:
                role_spec = dict(profile.roles.get("chapter_title", {}))

            if role not in ensured_roles:
                ensured_roles[role] = ensure_style_for_role(ir.doc, role, profile)
            style_id = ensured_roles[role]

            p_el = block.raw_element
            pPr = get_or_add_pPr(p_el)
            assign_style_to_paragraph(p_el, style_id)
            block.style_id = style_id

            if f.rule_id in ("HEAD-001", "HEAD-002"):
                # Align paragraph and run properties with role specification
                exp_al = str(
                    role_spec.get("alignment", "center" if f.rule_id == "HEAD-001" else "left")
                )
                jc_val = "both" if exp_al == "justify" else exp_al
                set_w_val(pPr, "jc", jc_val, PPR_ORDER)

                spacing = get_or_add_ordered(pPr, "spacing", PPR_ORDER)
                spacing.set(
                    qn("w:before"), str(pt_to_twips(float(role_spec.get("space_before_pt", 0.0))))
                )
                spacing.set(
                    qn("w:after"), str(pt_to_twips(float(role_spec.get("space_after_pt", 0.0))))
                )
                spacing.set(
                    qn("w:line"),
                    str(
                        line_spacing_multiplier_to_wline(float(role_spec.get("line_spacing", 1.5)))
                    ),
                )
                spacing.set(qn("w:lineRule"), "auto")

                ind = get_or_add_ordered(pPr, "ind", PPR_ORDER)
                ind.set(qn("w:left"), str(cm_to_twips(float(role_spec.get("left_indent_cm", 0.0)))))
                ind.set(
                    qn("w:right"), str(cm_to_twips(float(role_spec.get("right_indent_cm", 0.0))))
                )
                hanging_cm = float(role_spec.get("hanging_indent_cm", 0.0))
                if hanging_cm > 0:
                    if qn("w:firstLine") in ind.attrib:
                        del ind.attrib[qn("w:firstLine")]
                    ind.set(qn("w:hanging"), str(cm_to_twips(hanging_cm)))
                else:
                    if qn("w:hanging") in ind.attrib:
                        del ind.attrib[qn("w:hanging")]
                    ind.set(qn("w:firstLine"), "0")

                exp_bold = bool(role_spec.get("bold", True))
                exp_caps = bool(role_spec.get("all_caps", False))
                p_rPr = get_or_add_ordered(pPr, "rPr", PPR_ORDER)
                set_boolean_prop(p_rPr, "b", exp_bold, RPR_ORDER)
                set_boolean_prop(p_rPr, "bCs", exp_bold, RPR_ORDER)
                if exp_caps:
                    set_boolean_prop(p_rPr, "caps", True, RPR_ORDER)

                for r in p_el.findall(qn("w:r")):
                    rPr = get_or_add_rPr(r)
                    set_boolean_prop(rPr, "b", exp_bold, RPR_ORDER)
                    set_boolean_prop(rPr, "bCs", exp_bold, RPR_ORDER)
                    if exp_caps:
                        set_boolean_prop(rPr, "caps", True, RPR_ORDER)

                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f.expected,
                        method=FixMethod.STYLE,
                    )
                )

            elif f.rule_id == "HEAD-003":
                # Suggest rule: strip typed heading number prefix and attach w:numPr
                stripped_prefix = self._strip_typed_number_from_paragraph(p_el)
                if stripped_prefix:
                    self.excluded_prefixes.append(stripped_prefix)
                ilvl = 1
                if role == "heading_3":
                    ilvl = 2
                elif role == "heading_4":
                    ilvl = 3
                num_id = ensure_multilevel_heading_num_id(ir.doc)
                numPr = get_or_add_ordered(pPr, "numPr", PPR_ORDER)
                set_w_val(numPr, "ilvl", str(ilvl), ["ilvl", "numId"])
                set_w_val(numPr, "numId", str(num_id), ["ilvl", "numId"])
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f"Numbering otomatis (numId={num_id}, ilvl={ilvl})",
                        method=FixMethod.STYLE,
                    )
                )

            elif f.rule_id == "HEAD-004":
                set_boolean_prop(pPr, "keepNext", True, PPR_ORDER)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value="keep_with_next=true",
                        method=FixMethod.STYLE,
                    )
                )

            elif f.rule_id == "HEAD-005":
                set_boolean_prop(pPr, "pageBreakBefore", True, PPR_ORDER)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value="pageBreakBefore=true",
                        method=FixMethod.STYLE,
                    )
                )

        return changes

    @staticmethod
    def _strip_typed_number_from_paragraph(p_el: object) -> str | None:
        """Strips leading `1.1 ` or `1.1.1 ` from the text runs of `p_el` and returns the stripped prefix."""
        # Collect text across initial runs
        runs = p_el.findall(qn("w:r"))  # type: ignore[attr-defined]
        full_text = ""
        t_elements = []
        for r in runs:
            for t in r.findall(qn("w:t")):
                if t.text:
                    full_text += t.text
                    t_elements.append(t)

        m = re.match(r"^(\s*\d+(?:\.\d+)+\s+)", full_text)
        if not m:
            return None

        prefix_to_remove = m.group(1)
        remaining = len(prefix_to_remove)
        for t in t_elements:
            txt = t.text or ""
            if len(txt) <= remaining:
                remaining -= len(txt)
                t.text = ""
            else:
                t.text = txt[remaining:]
                remaining = 0
            if remaining == 0:
                break

        return prefix_to_remove.strip()
