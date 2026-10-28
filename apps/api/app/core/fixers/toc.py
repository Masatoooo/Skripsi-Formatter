from __future__ import annotations

import re
from typing import Any

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.core.docx_model import DocumentIR
from app.core.fields import add_field, mark_document_update_fields_on_open
from app.core.fixers.base import BaseFixer
from app.core.rules.models import Change, Finding, FixMethod, RuleProfile
from app.core.units import cm_to_twips, get_paper_dimensions_cm
from app.core.xml_helpers import PPR_ORDER, get_or_add_ordered, get_or_add_pPr


class TocFixer(BaseFixer):
    """Fixes Table of Contents (TOC), List of Figures (LOF), and List of Tables (LOT)."""

    category = "TOC"

    def __init__(self) -> None:
        self.excluded_lines: list[str] = []

    def apply(
        self,
        ir: DocumentIR,
        findings: list[Finding],
        profile: RuleProfile,
    ) -> list[Change]:
        toc_findings = [f for f in findings if f.category in ("TOC", "LOF", "LOT")]
        if not toc_findings:
            return []

        toc_cfg = profile.toc or {}
        levels = int(toc_cfg.get("levels", 3))
        toc_instr = f'TOC \\o "1-{levels}" \\h \\z \\u'
        changes: list[Change] = []

        # Always ensure TOC1..3 styles have right-aligned dot-leader tabs and updateFields is set
        self._ensure_toc_styles_with_leaders(ir.doc, profile)
        mark_document_update_fields_on_open(ir.doc)
        ir.has_update_fields = True

        for f in toc_findings:
            if f.rule_id == "TOC-002":
                # Suggest rule: replace typed TOC lines with a dynamic TOC field
                typed_blocks = [
                    b
                    for b in ir.blocks
                    if b.assigned_role == "toc_entry"
                    and not any(fld.field_type == "TOC" for fld in b.fields)
                ]
                if typed_blocks:
                    first_b = typed_blocks[0]
                    anchor_p = first_b.raw_element
                    for tb in typed_blocks:
                        norm_txt = re.sub(r"[ \t\u00a0]+", " ", (tb.text or "")).strip()
                        if norm_txt:
                            self.excluded_lines.append(norm_txt)
                    for tb in typed_blocks[1:]:
                        parent = tb.raw_element.getparent()
                        if parent is not None:
                            parent.remove(tb.raw_element)

                    # Replace first typed TOC paragraph's runs with a TOC field
                    for ch in list(anchor_p):
                        if not ch.tag.endswith("}pPr"):
                            anchor_p.remove(ch)
                    cached_toc = self._build_initial_toc_cache(ir)
                    add_field(
                        anchor_p,
                        toc_instr,
                        cached_text=cached_toc,
                        font_family=profile.text.font_family,
                        font_size_pt=profile.text.font_size_pt,
                        color_hex=profile.text.color_hex,
                    )
                    changes.append(
                        Change(
                            finding_id=f.id,
                            rule_id=f.rule_id,
                            location=f.location,
                            old_value=f.actual,
                            new_value=f"Field {toc_instr}",
                            method=FixMethod.DIRECT,
                        )
                    )

            elif f.rule_id == "TOC-001":
                anchor_p = self._find_heading_paragraph(
                    ir, "DAFTAR ISI"
                ) or self._find_front_matter_tail(ir)
                new_p = OxmlElement("w:p")
                cached_toc = self._build_initial_toc_cache(ir)
                add_field(
                    new_p,
                    toc_instr,
                    cached_text=cached_toc,
                    font_family=profile.text.font_family,
                    font_size_pt=profile.text.font_size_pt,
                    color_hex=profile.text.color_hex,
                )
                if anchor_p is not None:
                    self._insert_after_preserving_sectPr(anchor_p, new_p)
                elif ir.blocks:
                    self._insert_after_preserving_sectPr(ir.blocks[-1].raw_element, new_p)
                else:
                    ir.doc.element.body.insert(0, new_p)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f"Field {toc_instr}",
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "TOC-003":
                blk_idx = f.location.block_index
                if 0 <= blk_idx < len(ir.blocks):
                    p_el = ir.blocks[blk_idx].raw_element
                    for it in p_el.iter(qn("w:instrText")):
                        if it.text and "TOC" in it.text.upper():
                            it.text = f" {toc_instr} "
                    for fs in p_el.iter(qn("w:fldSimple")):
                        if "TOC" in (fs.get(qn("w:instr")) or "").upper():
                            fs.set(qn("w:instr"), toc_instr)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f"1-{levels}",
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "TOC-004":
                mark_document_update_fields_on_open(ir.doc)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value="updateFields=true",
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "TOC-005":
                self._ensure_toc_styles_with_leaders(ir.doc, profile)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value="w:tab val=right leader=dot",
                        method=FixMethod.STYLE,
                    )
                )

            elif f.rule_id == "LOF-001":
                lof_label = profile.captions.get("figure", {}).get("label", "Gambar")
                lof_instr = f'TOC \\h \\z \\c "{lof_label}"'
                anchor_p = self._find_heading_paragraph(
                    ir, "DAFTAR GAMBAR"
                ) or self._find_heading_paragraph(ir, "DAFTAR ISI")
                new_p = OxmlElement("w:p")
                add_field(
                    new_p,
                    lof_instr,
                    cached_text="",
                    font_family=profile.text.font_family,
                    font_size_pt=profile.text.font_size_pt,
                    color_hex=profile.text.color_hex,
                )
                if anchor_p is not None:
                    self._insert_after_preserving_sectPr(anchor_p, new_p)
                else:
                    ir.doc.element.body.insert(0, new_p)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f"Field {lof_instr}",
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "LOT-001":
                lot_label = profile.captions.get("table", {}).get("label", "Tabel")
                lot_instr = f'TOC \\h \\z \\c "{lot_label}"'
                anchor_p = self._find_heading_paragraph(
                    ir, "DAFTAR TABEL"
                ) or self._find_heading_paragraph(ir, "DAFTAR ISI")
                new_p = OxmlElement("w:p")
                add_field(
                    new_p,
                    lot_instr,
                    cached_text="",
                    font_family=profile.text.font_family,
                    font_size_pt=profile.text.font_size_pt,
                    color_hex=profile.text.color_hex,
                )
                if anchor_p is not None:
                    self._insert_after_preserving_sectPr(anchor_p, new_p)
                else:
                    ir.doc.element.body.insert(0, new_p)
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f"Field {lot_instr}",
                        method=FixMethod.DIRECT,
                    )
                )

        return changes

    @staticmethod
    def _insert_after_preserving_sectPr(anchor_p: Any, new_p: Any) -> None:
        """Inserts `new_p` after `anchor_p`. If `anchor_p` holds a `w:sectPr`, moves it to `new_p` so `new_p` stays in the same section."""
        anchor_p.addnext(new_p)
        a_pPr = anchor_p.find(qn("w:pPr"))
        if a_pPr is not None:
            sectPr = a_pPr.find(qn("w:sectPr"))
            if sectPr is not None:
                a_pPr.remove(sectPr)
                new_pPr = get_or_add_pPr(new_p)
                new_pPr.append(sectPr)

    @staticmethod
    def _find_heading_paragraph(ir: DocumentIR, title_substr: str) -> Any:
        target = title_substr.upper()
        for b in ir.blocks:
            if b.block_type == "paragraph" and target in (b.text or "").upper():
                return b.raw_element
        return None

    @staticmethod
    def _find_front_matter_tail(ir: DocumentIR) -> Any:
        last_fm: Any = None
        for b in ir.blocks:
            if b.assigned_role == "chapter_label":
                break
            if b.block_type == "paragraph" and b.assigned_role != "cover":
                last_fm = b.raw_element
        return last_fm

    @staticmethod
    def _build_initial_toc_cache(ir: DocumentIR) -> str:
        """Builds initial cached TOC entries from document headings and estimated page numbers."""
        entries: list[str] = []
        for b in ir.blocks:
            if b.assigned_role in (
                "front_title",
                "chapter_label",
                "chapter_title",
                "heading_2",
                "heading_3",
            ):
                title = (b.text or "").strip().replace("\n", " ")
                if title:
                    entries.append(f"{title}\t{b.approx_page}")
        return "\n".join(entries)

    @staticmethod
    def _ensure_toc_styles_with_leaders(doc: object, profile: RuleProfile) -> None:
        w_cm, _ = get_paper_dimensions_cm(profile.page.size, profile.page.orientation)
        text_width_cm = w_cm - profile.page.margins_cm.left - profile.page.margins_cm.right
        tab_pos_twips = cm_to_twips(max(10.0, text_width_cm))
        leader_cfg = profile.toc.get("leader", "dots")
        leader_val = "dot" if leader_cfg in ("dots", "dot") else "none"

        styles_el = doc.styles.element  # type: ignore[attr-defined]
        for lvl in (1, 2, 3):
            sid = f"TOC{lvl}"
            st_el = None
            for s in styles_el.findall(qn("w:style")):
                if s.get(qn("w:styleId")) == sid:
                    st_el = s
                    break
            if st_el is None:
                st_el = OxmlElement("w:style")
                st_el.set(qn("w:type"), "paragraph")
                st_el.set(qn("w:styleId"), sid)
                name_el = OxmlElement("w:name")
                name_el.set(qn("w:val"), f"toc {lvl}")
                st_el.append(name_el)
                styles_el.append(st_el)

            pPr = get_or_add_pPr(st_el)
            tabs = get_or_add_ordered(pPr, "tabs", PPR_ORDER)
            for existing_tab in list(tabs.findall(qn("w:tab"))):
                tabs.remove(existing_tab)
            tab = OxmlElement("w:tab")
            tab.set(qn("w:val"), "right")
            tab.set(qn("w:leader"), leader_val)
            tab.set(qn("w:pos"), str(tab_pos_twips))
            tabs.append(tab)
