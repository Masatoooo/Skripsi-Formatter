from __future__ import annotations

import re

from docx.oxml.ns import qn
from docx.shared import Twips

from app.core.docx_model import DocumentIR
from app.core.fields import (
    insert_section_break_before_paragraph,
    set_header_footer_page_field,
    set_section_pg_num_type,
)
from app.core.fixers.base import BaseFixer
from app.core.rules.models import Change, Finding, FixMethod, RuleProfile
from app.core.units import cm_to_twips, get_paper_dimensions_cm


class NumberingFixer(BaseFixer):
    """Fixes section breaks and page numbering (Roman front-matter, Arabic body, positions, chapter first page)."""

    category = "NUM"

    def apply(
        self,
        ir: DocumentIR,
        findings: list[Finding],
        profile: RuleProfile,
    ) -> list[Change]:
        num_findings = [f for f in findings if f.category == "NUM"]
        if not num_findings:
            return []

        pg_cfg = profile.page_numbering
        if not pg_cfg:
            return []

        font_family = profile.text.font_family
        font_size_pt = profile.text.font_size_pt
        color_hex = profile.text.color_hex

        # 1. Ensure section breaks exist between cover, front_matter, and body chapters when needed
        need_section_splits = any(
            f.rule_id in ("NUM-001", "NUM-002", "NUM-003", "NUM-004", "NUM-005")
            for f in num_findings
        )
        if need_section_splits:
            self._ensure_thesis_section_breaks(ir, profile)

        # 2. Classify each current section in `ir.doc.sections` by inspecting the paragraphs belonging to it
        doc = ir.doc
        sect_groups, sect_has_chapter = self._classify_doc_sections(doc, ir)

        fm_cfg = pg_cfg.get("front_matter", {})
        body_cfg = pg_cfg.get("body", {})
        cover_cfg = pg_cfg.get("cover", {})
        first_pg_cfg = body_cfg.get("chapter_first_page", {})

        exp_margins = profile.page.margins_cm
        exp_hf = profile.page.header_footer_distance_cm or {}
        w_cm, h_cm = get_paper_dimensions_cm(profile.page.size, profile.page.orientation)

        first_body_seen = False
        for idx, sect in enumerate(doc.sections):
            # Ensure newly created sections also have profile margins & paper size
            sect.page_width = Twips(cm_to_twips(w_cm))
            sect.page_height = Twips(cm_to_twips(h_cm))
            sect.top_margin = Twips(cm_to_twips(exp_margins.top))
            sect.bottom_margin = Twips(cm_to_twips(exp_margins.bottom))
            sect.left_margin = Twips(cm_to_twips(exp_margins.left))
            sect.right_margin = Twips(cm_to_twips(exp_margins.right))
            if "header" in exp_hf:
                sect.header_distance = Twips(cm_to_twips(exp_hf["header"]))
            if "footer" in exp_hf:
                sect.footer_distance = Twips(cm_to_twips(exp_hf["footer"]))

            group = sect_groups.get(idx, "body")
            has_chap = sect_has_chapter.get(idx, False)
            sectPr = sect._sectPr

            if group == "cover":
                if cover_cfg.get("numbered") is False:
                    sect.different_first_page_header_footer = False
                    set_header_footer_page_field(
                        sect,
                        "none",
                        is_first_page=False,
                        font_family=font_family,
                        font_size_pt=font_size_pt,
                        color_hex=color_hex,
                    )
            elif group == "front_matter":
                fmt = fm_cfg.get("format", "lowerRoman")
                start = int(fm_cfg.get("start", 1))
                pos = fm_cfg.get("position", "bottom_center")
                sect.different_first_page_header_footer = False
                set_section_pg_num_type(sectPr, fmt=fmt, start=start if idx <= 1 else None)
                set_header_footer_page_field(
                    sect,
                    pos,
                    is_first_page=False,
                    font_family=font_family,
                    font_size_pt=font_size_pt,
                    color_hex=color_hex,
                )
            else:
                fmt = body_cfg.get("format", "decimal")
                body_start: int | None = (
                    int(body_cfg.get("start", 1)) if not first_body_seen else None
                )
                first_body_seen = True
                pos = body_cfg.get("position", "top_right")
                first_pos = first_pg_cfg.get("position")

                set_section_pg_num_type(sectPr, fmt=fmt, start=body_start)
                set_header_footer_page_field(
                    sect,
                    pos,
                    is_first_page=False,
                    font_family=font_family,
                    font_size_pt=font_size_pt,
                    color_hex=color_hex,
                )
                if has_chap and first_pos:
                    set_header_footer_page_field(
                        sect,
                        first_pos,
                        is_first_page=True,
                        font_family=font_family,
                        font_size_pt=font_size_pt,
                        color_hex=color_hex,
                    )

        changes: list[Change] = []
        for f in num_findings:
            changes.append(
                Change(
                    finding_id=f.id,
                    rule_id=f.rule_id,
                    location=f.location,
                    old_value=f.actual,
                    new_value=f.expected,
                    method=FixMethod.DIRECT,
                )
            )
        return changes

    def _ensure_thesis_section_breaks(self, ir: DocumentIR, profile: RuleProfile) -> None:
        """Inserts section breaks before first front_matter title and before each chapter_label if needed."""
        doc = ir.doc
        first_front_seen = False
        has_cover = any(b.assigned_role == "cover" for b in ir.blocks)

        for b in ir.blocks:
            if b.block_type != "paragraph":
                continue
            role = b.assigned_role
            txt = (b.text or "").strip()

            if (
                role == "front_title"
                and not first_front_seen
                and not re.match(r"^(DAFTAR\s+PUSTAKA|LAMPIRAN)", txt, re.I)
            ):
                first_front_seen = True
                if has_cover and b.index > 0:
                    insert_section_break_before_paragraph(doc, b.raw_element)

            elif role == "chapter_label" and b.index > 0:
                insert_section_break_before_paragraph(doc, b.raw_element)

    def _classify_doc_sections(
        self, doc: object, ir: DocumentIR
    ) -> tuple[dict[int, str], dict[int, bool]]:
        """Maps each section index in `doc.sections` to `('cover' | 'front_matter' | 'body')` and `has_chapter`."""
        # Map raw paragraph elements to their assigned role in `ir.blocks`
        el_to_role: dict[object, str] = {}
        el_to_text: dict[object, str] = {}
        for b in ir.blocks:
            if b.assigned_role:
                el_to_role[b.raw_element] = b.assigned_role
                el_to_text[b.raw_element] = (b.text or "").strip()

        sect_roles: dict[int, list[tuple[str, str]]] = {}
        curr_sec = 0
        for child in doc.element.body:  # type: ignore[attr-defined]
            if child.tag.endswith("}p"):
                r = el_to_role.get(child)
                t = el_to_text.get(child, "")
                if r and r != "other":
                    sect_roles.setdefault(curr_sec, []).append((r, t))
                pPr = child.find(qn("w:pPr"))
                if pPr is not None and pPr.find(qn("w:sectPr")) is not None:
                    curr_sec += 1

        groups: dict[int, str] = {}
        has_chapter: dict[int, bool] = {}
        total_secs = len(doc.sections)  # type: ignore[attr-defined]

        for s_idx in range(total_secs):
            items = sect_roles.get(s_idx, [])
            roles_only = {r for r, _ in items}
            has_chap = "chapter_label" in roles_only
            has_chapter[s_idx] = has_chap

            is_cover = "cover" in roles_only and not (
                roles_only & {"front_title", "toc_entry", "chapter_label", "chapter_title"}
            )
            has_early_front = "toc_entry" in roles_only or any(
                r == "front_title" and not re.match(r"^(DAFTAR\s+PUSTAKA|LAMPIRAN)", t, re.I)
                for r, t in items
            )

            if is_cover:
                groups[s_idx] = "cover"
            elif has_early_front and not has_chap:
                groups[s_idx] = "front_matter"
            else:
                groups[s_idx] = "body"

        return groups, has_chapter
