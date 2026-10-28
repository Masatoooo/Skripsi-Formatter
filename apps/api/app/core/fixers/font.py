from __future__ import annotations

from docx.oxml.ns import qn

from app.core.docx_model import DocumentIR
from app.core.fixers.base import BaseFixer
from app.core.rules.models import Change, Finding, FixMethod, RuleProfile
from app.core.style_manager import (
    assign_style_to_paragraph,
    ensure_doc_defaults,
    ensure_style_for_role,
)
from app.core.units import pt_to_half_points
from app.core.xml_helpers import (
    get_or_add_pPr,
    set_color_on_rPr,
    set_font_family_on_rPr,
    set_font_size_on_rPr,
)


class FontFixer(BaseFixer):
    """Fixes font family, font size, font color, and stray fonts via Styles and run cleanup."""

    category = "FONT"

    def apply(
        self,
        ir: DocumentIR,
        findings: list[Finding],
        profile: RuleProfile,
    ) -> list[Change]:
        font_findings = [f for f in findings if f.category == "FONT"]
        if not font_findings:
            return []

        ensure_doc_defaults(ir.doc, profile)
        ensured_roles: dict[str, str] = {}
        changes: list[Change] = []

        for f in font_findings:
            blk_idx = f.location.block_index
            if blk_idx < 0 or blk_idx >= len(ir.blocks):
                continue
            block = ir.blocks[blk_idx]
            if block.block_type != "paragraph" or block.has_tracked_changes:
                continue

            role = block.assigned_role or "body"
            role_spec = profile.roles.get(role, {})
            if role == "front_title" and not role_spec:
                role_spec = profile.roles.get("chapter_title", {})

            exp_font = str(role_spec.get("font_family", profile.text.font_family))
            exp_size = float(role_spec.get("font_size_pt", profile.text.font_size_pt))
            exp_color = str(role_spec.get("color_hex", profile.text.color_hex)).upper().lstrip("#")

            if role not in ensured_roles:
                ensured_roles[role] = ensure_style_for_role(ir.doc, role, profile)
            style_id = ensured_roles[role]

            p_el = block.raw_element
            if not block.style_id or block.style_id == "Normal":
                assign_style_to_paragraph(p_el, style_id)
                block.style_id = style_id

            pPr = get_or_add_pPr(p_el)
            p_rPr = pPr.find(qn("w:rPr"))

            if f.rule_id in ("FONT-001", "FONT-004"):
                if p_rPr is not None:
                    set_font_family_on_rPr(p_rPr, exp_font)
                for r in p_el.findall(qn("w:r")):
                    rPr = r.find(qn("w:rPr"))
                    if rPr is not None:
                        set_font_family_on_rPr(rPr, exp_font)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=exp_font,
                        method=FixMethod.STYLE,
                    )
                )

            elif f.rule_id == "FONT-002":
                hp = pt_to_half_points(exp_size)
                if p_rPr is not None:
                    set_font_size_on_rPr(p_rPr, hp)
                for r in p_el.findall(qn("w:r")):
                    rPr = r.find(qn("w:rPr"))
                    if rPr is not None:
                        set_font_size_on_rPr(rPr, hp)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f"{exp_size:g} pt",
                        method=FixMethod.STYLE,
                    )
                )

            elif f.rule_id == "FONT-003":
                if p_rPr is not None:
                    set_color_on_rPr(p_rPr, exp_color)
                for r in p_el.findall(qn("w:r")):
                    rPr = r.find(qn("w:rPr"))
                    if rPr is not None:
                        set_color_on_rPr(rPr, exp_color)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=exp_color,
                        method=FixMethod.STYLE,
                    )
                )

        return changes
