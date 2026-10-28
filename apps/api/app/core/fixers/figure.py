from __future__ import annotations

from app.core.docx_model import A_NS, WP_NS, DocumentIR
from app.core.fixers.base import BaseFixer
from app.core.rules.models import Change, Finding, FixMethod, RuleProfile
from app.core.units import cm_to_emu
from app.core.xml_helpers import PPR_ORDER, get_or_add_pPr, set_w_val


class FigureFixer(BaseFixer):
    """Fixes inline image alignment and proportional scaling within page margins."""

    category = "FIG"

    def apply(
        self,
        ir: DocumentIR,
        findings: list[Finding],
        profile: RuleProfile,
    ) -> list[Change]:
        fig_findings = [f for f in findings if f.category == "FIG"]
        if not fig_findings:
            return []

        changes: list[Change] = []

        for f in fig_findings:
            blk_idx = f.location.block_index
            if blk_idx < 0 or blk_idx >= len(ir.blocks):
                continue
            block = ir.blocks[blk_idx]
            if block.block_type != "paragraph" or block.has_tracked_changes:
                continue

            p_el = block.raw_element
            pPr = get_or_add_pPr(p_el)

            if f.rule_id == "FIG-001":
                set_w_val(pPr, "jc", "center", PPR_ORDER)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value="center",
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "FIG-002":
                sect = ir.sections[min(block.section_index, len(ir.sections) - 1)]
                max_w_cm = sect.page_width_cm - sect.left_margin_cm - sect.right_margin_cm
                max_cx_emu = cm_to_emu(max_w_cm)

                for img in block.images:
                    if img.cx_emu > max_cx_emu and img.raw_drawing is not None:
                        ratio = float(max_cx_emu) / float(img.cx_emu)
                        new_cy_emu = int(round(img.cy_emu * ratio))
                        drawing = img.raw_drawing
                        # Update both wp:extent and a:xfrm/a:ext per DOCX_NOTES.md section 7
                        for extent in drawing.iter(f"{WP_NS}extent"):
                            extent.set("cx", str(max_cx_emu))
                            extent.set("cy", str(new_cy_emu))
                        for xfrm in drawing.iter(f"{A_NS}xfrm"):
                            a_ext = xfrm.find(f"{A_NS}ext")
                            if a_ext is not None:
                                a_ext.set("cx", str(max_cx_emu))
                                a_ext.set("cy", str(new_cy_emu))
                        img.cx_emu = max_cx_emu
                        img.cy_emu = new_cy_emu
                        img.width_cm = max_w_cm

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

        return changes
