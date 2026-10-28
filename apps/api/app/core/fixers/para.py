from __future__ import annotations

from docx.oxml import OxmlElement
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
from app.core.xml_helpers import (
    PPR_ORDER,
    get_or_add_ordered,
    get_or_add_pPr,
    local_tag,
    set_boolean_prop,
    set_w_val,
)


class ParaFixer(BaseFixer):
    """Fixes paragraph spacing, indentation, alignment, widow control, and approved whitespace suggestions."""

    category = "PARA"

    def apply(
        self,
        ir: DocumentIR,
        findings: list[Finding],
        profile: RuleProfile,
    ) -> list[Change]:
        para_findings = [
            f for f in findings if f.category == "PARA" and f.rule_id.startswith("PARA-")
        ]
        if not para_findings:
            return []

        ensured_roles: dict[str, str] = {}
        changes: list[Change] = []
        elements_to_remove: list[tuple[Finding, object]] = []

        for f in para_findings:
            blk_idx = f.location.block_index
            if blk_idx < 0 or blk_idx >= len(ir.blocks):
                continue
            block = ir.blocks[blk_idx]
            if block.block_type != "paragraph" or block.has_tracked_changes:
                continue

            role = block.assigned_role or "body"
            role_spec = profile.roles.get(role, {})
            if role not in ensured_roles:
                ensured_roles[role] = ensure_style_for_role(ir.doc, role, profile)
            style_id = ensured_roles[role]

            p_el = block.raw_element
            pPr = get_or_add_pPr(p_el)

            if not block.style_id or block.style_id == "Normal":
                assign_style_to_paragraph(p_el, style_id)
                block.style_id = style_id

            if f.rule_id == "PARA-001":
                exp_ls = float(role_spec.get("line_spacing", 1.5))
                spacing = get_or_add_ordered(pPr, "spacing", PPR_ORDER)
                spacing.set(qn("w:line"), str(line_spacing_multiplier_to_wline(exp_ls)))
                spacing.set(qn("w:lineRule"), "auto")
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f"{exp_ls:.2f}",
                        method=FixMethod.STYLE,
                    )
                )

            elif f.rule_id == "PARA-002":
                spacing = get_or_add_ordered(pPr, "spacing", PPR_ORDER)
                if f.message_id == "finding.para.space_before":
                    exp_sb = float(role_spec.get("space_before_pt", 0.0))
                    spacing.set(qn("w:before"), str(pt_to_twips(exp_sb)))
                    new_v = f"{exp_sb:g} pt"
                else:
                    exp_sa = float(role_spec.get("space_after_pt", 0.0))
                    spacing.set(qn("w:after"), str(pt_to_twips(exp_sa)))
                    new_v = f"{exp_sa:g} pt"
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=new_v,
                        method=FixMethod.STYLE,
                    )
                )

            elif f.rule_id == "PARA-003":
                ind = get_or_add_ordered(pPr, "ind", PPR_ORDER)
                if f.message_id == "finding.para.indent_first":
                    exp_fl = float(role_spec.get("first_line_indent_cm", 0.0))
                    if qn("w:hanging") in ind.attrib:
                        del ind.attrib[qn("w:hanging")]
                    ind.set(qn("w:firstLine"), str(cm_to_twips(exp_fl)))
                    new_v = f"{exp_fl:.2f} cm"
                elif f.message_id == "finding.para.indent_left":
                    exp_li = float(role_spec.get("left_indent_cm", 0.0))
                    ind.set(qn("w:left"), str(cm_to_twips(exp_li)))
                    new_v = f"{exp_li:.2f} cm"
                elif f.message_id == "finding.para.indent_right":
                    exp_ri = float(role_spec.get("right_indent_cm", 0.0))
                    ind.set(qn("w:right"), str(cm_to_twips(exp_ri)))
                    new_v = f"{exp_ri:.2f} cm"
                else:
                    exp_hi = float(role_spec.get("hanging_indent_cm", 0.0))
                    if qn("w:firstLine") in ind.attrib:
                        del ind.attrib[qn("w:firstLine")]
                    ind.set(qn("w:hanging"), str(cm_to_twips(exp_hi)))
                    new_v = f"{exp_hi:.2f} cm"
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=new_v,
                        method=FixMethod.STYLE,
                    )
                )

            elif f.rule_id == "PARA-004":
                exp_al = str(role_spec.get("alignment", "justify"))
                jc_val = "both" if exp_al == "justify" else exp_al
                set_w_val(pPr, "jc", jc_val, PPR_ORDER)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=exp_al,
                        method=FixMethod.STYLE,
                    )
                )

            elif f.rule_id == "PARA-005":
                # Suggest rule: remove empty spacing paragraph if parent exists and not holding a sectPr
                if pPr.find(qn("w:sectPr")) is None and p_el.getparent() is not None:
                    elements_to_remove.append((f, p_el))

            elif f.rule_id == "PARA-006":
                # Suggest rule: strip leading spaces/tabs from the start of paragraph runs
                self._strip_leading_whitespace_from_p(p_el)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value="First-line indent tanpa spasi/tab manual",
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "PARA-007":
                # Suggest rule: replace manual line breaks (w:br) with space
                self._replace_manual_linebreaks_with_space(p_el)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value="Spasi normal tanpa line break manual",
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "PARA-008":
                set_boolean_prop(pPr, "widowControl", True, PPR_ORDER)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value="Aktif (true)",
                        method=FixMethod.STYLE,
                    )
                )

        # Execute deferred empty paragraph removals (keep at least 1 paragraph in body)
        for f, p_el in elements_to_remove:
            parent = p_el.getparent()  # type: ignore[attr-defined]
            if parent is not None and len(parent.findall(qn("w:p"))) > 1:
                parent.remove(p_el)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value="Paragraf kosong berulang dihapus",
                        method=FixMethod.DIRECT,
                    )
                )

        return changes

    @staticmethod
    def _strip_leading_whitespace_from_p(p_el: object) -> None:
        for r in p_el.findall(qn("w:r")):  # type: ignore[attr-defined]
            for child in list(r):
                tag = local_tag(child)
                if tag == "tab":
                    r.remove(child)
                elif tag == "t" and child.text:
                    stripped = child.text.lstrip(" \t")
                    child.text = stripped
                    if stripped:
                        return
                elif tag in ("drawing", "fldChar"):
                    return

    @staticmethod
    def _replace_manual_linebreaks_with_space(p_el: object) -> None:
        for r in p_el.findall(qn("w:r")):  # type: ignore[attr-defined]
            for idx, child in enumerate(list(r)):
                if local_tag(child) == "br" and child.get(qn("w:type")) not in ("page", "column"):
                    t_space = OxmlElement("w:t")
                    t_space.set(qn("xml:space"), "preserve")
                    t_space.text = " "
                    r.replace(child, t_space)
