from __future__ import annotations

from docx.oxml.ns import qn

from app.core.docx_model import DocumentIR
from app.core.fixers.base import BaseFixer
from app.core.rules.models import Change, Finding, FixMethod, RuleProfile
from app.core.style_manager import assign_style_to_paragraph, ensure_style_for_role
from app.core.units import (
    cm_to_twips,
    line_spacing_multiplier_to_wline,
    pt_to_half_points,
    pt_to_twips,
)
from app.core.xml_helpers import (
    PPR_ORDER,
    TBLPR_ORDER,
    TRPR_ORDER,
    get_or_add_ordered,
    get_or_add_pPr,
    get_or_add_rPr,
    get_or_add_tblPr,
    get_or_add_trPr,
    set_boolean_prop,
    set_font_family_on_rPr,
    set_font_size_on_rPr,
    set_w_val,
)


class TableFixer(BaseFixer):
    """Fixes table width, repeating header rows, cantSplit rows, cell typography, and table alignment."""

    category = "TBL"

    def apply(
        self,
        ir: DocumentIR,
        findings: list[Finding],
        profile: RuleProfile,
    ) -> list[Change]:
        tbl_findings = [f for f in findings if f.category == "TBL"]
        if not tbl_findings:
            return []

        changes: list[Change] = []
        tbl_style_id: str | None = None

        for f in tbl_findings:
            blk_idx = f.location.block_index
            if blk_idx < 0 or blk_idx >= len(ir.blocks):
                continue
            block = ir.blocks[blk_idx]
            if block.block_type != "table" or block.table_info is None:
                continue

            tbl_el = block.raw_element
            tblPr = get_or_add_tblPr(tbl_el)
            tinfo = block.table_info

            if f.rule_id == "TBL-001":
                sect = ir.sections[min(block.section_index, len(ir.sections) - 1)]
                max_w_cm = sect.page_width_cm - sect.left_margin_cm - sect.right_margin_cm
                max_twips = cm_to_twips(max_w_cm)
                old_twips = cm_to_twips(tinfo.width_cm) if tinfo.width_cm > 0 else max_twips
                scale = float(max_twips) / float(max(old_twips, 1))

                tblW = get_or_add_ordered(tblPr, "tblW", TBLPR_ORDER)
                tblW.set(qn("w:w"), str(max_twips))
                tblW.set(qn("w:type"), "dxa")

                tblGrid = tbl_el.find(qn("w:tblGrid"))
                if tblGrid is not None:
                    for gc in tblGrid.findall(qn("w:gridCol")):
                        w_v = gc.get(qn("w:w"))
                        if w_v and str(w_v).isdigit():
                            gc.set(qn("w:w"), str(int(round(int(w_v) * scale))))

                for tcW in tbl_el.iter(qn("w:tcW")):
                    w_v = tcW.get(qn("w:w"))
                    if w_v and str(w_v).isdigit() and tcW.get(qn("w:type")) in ("dxa", None):
                        tcW.set(qn("w:w"), str(int(round(int(w_v) * scale))))

                tinfo.width_cm = max_w_cm
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f"{max_w_cm:.2f} cm",
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "TBL-002":
                rows = tbl_el.findall(qn("w:tr"))
                if rows:
                    first_trPr = get_or_add_trPr(rows[0])
                    set_boolean_prop(first_trPr, "tblHeader", True, TRPR_ORDER)
                    tinfo.has_tbl_header = True
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value="tblHeader=true",
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "TBL-003":
                for row_el in tbl_el.findall(qn("w:tr")):
                    trPr = get_or_add_trPr(row_el)
                    set_boolean_prop(trPr, "cantSplit", True, TRPR_ORDER)
                tinfo.all_rows_cant_split = True
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value="cantSplit=true",
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "TBL-004":
                if tbl_style_id is None:
                    tbl_style_id = ensure_style_for_role(ir.doc, "table_text", profile)
                tbl_spec = profile.roles.get("table_text", {})
                exp_font = str(tbl_spec.get("font_family", profile.text.font_family))
                exp_sz = float(tbl_spec.get("font_size_pt", 11.0))
                exp_ls = float(tbl_spec.get("line_spacing", 1.0))
                exp_sb = float(tbl_spec.get("space_before_pt", 0.0))
                exp_sa = float(tbl_spec.get("space_after_pt", 0.0))
                hp = pt_to_half_points(exp_sz)

                for p_el in tbl_el.iter(qn("w:p")):
                    assign_style_to_paragraph(p_el, tbl_style_id)
                    pPr = get_or_add_pPr(p_el)
                    spacing = get_or_add_ordered(pPr, "spacing", PPR_ORDER)
                    spacing.set(qn("w:before"), str(pt_to_twips(exp_sb)))
                    spacing.set(qn("w:after"), str(pt_to_twips(exp_sa)))
                    spacing.set(qn("w:line"), str(line_spacing_multiplier_to_wline(exp_ls)))
                    spacing.set(qn("w:lineRule"), "auto")

                    for r in p_el.findall(qn("w:r")):
                        rPr = get_or_add_rPr(r)
                        set_font_family_on_rPr(rPr, exp_font)
                        set_font_size_on_rPr(rPr, hp)

                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f"{exp_font} {exp_sz:g}pt, spasi {exp_ls:.2f}",
                        method=FixMethod.STYLE,
                    )
                )

            elif f.rule_id == "TBL-005":
                tbl_spec = profile.roles.get("table_text", {})
                exp_align = str(tbl_spec.get("table_alignment", "center"))
                set_w_val(tblPr, "jc", exp_align, TBLPR_ORDER)
                tinfo.alignment = exp_align
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=exp_align,
                        method=FixMethod.DIRECT,
                    )
                )

        return changes
