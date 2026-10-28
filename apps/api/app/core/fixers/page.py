from __future__ import annotations

from docx.oxml.ns import qn
from docx.shared import Twips

from app.core.docx_model import DocumentIR
from app.core.fixers.base import BaseFixer
from app.core.rules.models import Change, Finding, FixMethod, RuleProfile
from app.core.units import cm_to_twips, get_paper_dimensions_cm
from app.core.xml_helpers import SECTPR_ORDER, get_or_add_ordered


class PageFixer(BaseFixer):
    """Fixes page size, orientation, margins, and header/footer distances per section."""

    category = "PAGE"

    def apply(
        self,
        ir: DocumentIR,
        findings: list[Finding],
        profile: RuleProfile,
    ) -> list[Change]:
        page_findings = [f for f in findings if f.category == "PAGE"]
        if not page_findings:
            return []

        changes: list[Change] = []
        exp_margins = profile.page.margins_cm
        exp_hf = profile.page.header_footer_distance_cm or {}

        for f in page_findings:
            sec_idx = f.location.section_index
            if sec_idx < 0 or sec_idx >= len(ir.sections):
                continue
            sect_ir = ir.sections[sec_idx]
            sect_obj = sect_ir.section_obj
            sectPr = sect_ir.raw_sectPr

            if f.rule_id == "PAGE-004":
                exp_orient = profile.page.orientation
                w_cm, h_cm = get_paper_dimensions_cm(profile.page.size, exp_orient)
                pgSz = get_or_add_ordered(sectPr, "pgSz", SECTPR_ORDER)
                pgSz.set(qn("w:w"), str(cm_to_twips(w_cm)))
                pgSz.set(qn("w:h"), str(cm_to_twips(h_cm)))
                if exp_orient == "landscape":
                    pgSz.set(qn("w:orient"), "landscape")
                elif qn("w:orient") in pgSz.attrib:
                    del pgSz.attrib[qn("w:orient")]
                sect_ir.orientation = exp_orient
                sect_ir.page_width_cm = w_cm
                sect_ir.page_height_cm = h_cm
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=exp_orient,
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "PAGE-001":
                w_cm, h_cm = get_paper_dimensions_cm(profile.page.size, sect_ir.orientation)
                pgSz = get_or_add_ordered(sectPr, "pgSz", SECTPR_ORDER)
                pgSz.set(qn("w:w"), str(cm_to_twips(w_cm)))
                pgSz.set(qn("w:h"), str(cm_to_twips(h_cm)))
                sect_ir.page_width_cm = w_cm
                sect_ir.page_height_cm = h_cm
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f"{profile.page.size} ({w_cm:.1f} x {h_cm:.1f} cm)",
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "PAGE-002":
                if f.message_id == "finding.page.margin_top":
                    sect_obj.top_margin = Twips(cm_to_twips(exp_margins.top))
                    sect_ir.top_margin_cm = exp_margins.top
                    new_v = f"{exp_margins.top:.2f} cm"
                elif f.message_id == "finding.page.margin_bottom":
                    sect_obj.bottom_margin = Twips(cm_to_twips(exp_margins.bottom))
                    sect_ir.bottom_margin_cm = exp_margins.bottom
                    new_v = f"{exp_margins.bottom:.2f} cm"
                elif f.message_id == "finding.page.margin_left":
                    sect_obj.left_margin = Twips(cm_to_twips(exp_margins.left))
                    sect_ir.left_margin_cm = exp_margins.left
                    new_v = f"{exp_margins.left:.2f} cm"
                elif f.message_id == "finding.page.margin_right":
                    sect_obj.right_margin = Twips(cm_to_twips(exp_margins.right))
                    sect_ir.right_margin_cm = exp_margins.right
                    new_v = f"{exp_margins.right:.2f} cm"
                else:
                    sect_obj.top_margin = Twips(cm_to_twips(exp_margins.top))
                    sect_obj.bottom_margin = Twips(cm_to_twips(exp_margins.bottom))
                    sect_obj.left_margin = Twips(cm_to_twips(exp_margins.left))
                    sect_obj.right_margin = Twips(cm_to_twips(exp_margins.right))
                    new_v = (
                        f"top={exp_margins.top}, left={exp_margins.left}, "
                        f"bottom={exp_margins.bottom}, right={exp_margins.right} cm"
                    )
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=new_v,
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "PAGE-003":
                if f.message_id == "finding.page.header_dist" and "header" in exp_hf:
                    sect_obj.header_distance = Twips(cm_to_twips(exp_hf["header"]))
                    sect_ir.header_distance_cm = exp_hf["header"]
                    new_v = f"{exp_hf['header']:.2f} cm"
                elif f.message_id == "finding.page.footer_dist" and "footer" in exp_hf:
                    sect_obj.footer_distance = Twips(cm_to_twips(exp_hf["footer"]))
                    sect_ir.footer_distance_cm = exp_hf["footer"]
                    new_v = f"{exp_hf['footer']:.2f} cm"
                else:
                    continue
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=new_v,
                        method=FixMethod.DIRECT,
                    )
                )

        return changes
