from __future__ import annotations

import hashlib
import re
from typing import Any

from docx.oxml.ns import qn

from app.core.docx_model import (
    DocumentBlock,
    DocumentIR,
    extract_visible_paragraph_text,
)
from app.core.formatting import EffectiveFormat, StyleHierarchyResolver
from app.core.messages import format_message
from app.core.roles import role_classifier
from app.core.rules.catalog import resolve_rule_config
from app.core.rules.models import Finding, FixMode, Location, RuleProfile, Severity
from app.core.units import get_paper_dimensions_cm, is_approx_equal


def make_finding_id(rule_id: str, section_index: int, block_index: int, actual: Any) -> str:
    """Generates a deterministic, stable finding ID from rule_id + location + actual value."""
    raw = f"{rule_id}:{section_index}:{block_index}:{actual}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]
    return f"f-{rule_id.lower()}-{digest}"


class RuleEvaluator:
    """Evaluates a DocumentIR against a RuleProfile to produce Findings."""

    def evaluate(
        self,
        ir: DocumentIR,
        profile: RuleProfile,
        user_role_overrides: dict[int, str] | None = None,
    ) -> list[Finding]:
        resolver = StyleHierarchyResolver(ir.doc)

        # Ensure roles are classified on all blocks
        if not any(b.assigned_role for b in ir.blocks) or user_role_overrides:
            role_classifier.classify(ir, resolver=resolver, user_overrides=user_role_overrides)

        formats: dict[int, EffectiveFormat] = {}
        for block in ir.blocks:
            if block.block_type == "paragraph":
                formats[block.index] = resolver.resolve_paragraph(block.raw_element)

        findings: list[Finding] = []

        def add_finding(
            rule_id: str,
            message_id: str,
            actual: Any,
            expected: Any,
            section_index: int = 0,
            block_index: int = 0,
            approx_page: int = 1,
            excerpt: str | None = None,
            **msg_kwargs: Any,
        ) -> None:
            enabled, severity, fix_mode, category = resolve_rule_config(rule_id, profile)
            if not enabled:
                return
            fid = make_finding_id(rule_id, section_index, block_index, actual)
            clean_excerpt = (excerpt or "")[:80].strip() if excerpt else None
            msg = format_message(
                message_id,
                section=section_index + 1,
                block=block_index + 1,
                actual=actual,
                expected=expected,
                **msg_kwargs,
            )
            findings.append(
                Finding(
                    id=fid,
                    rule_id=rule_id,
                    category=category,
                    severity=severity,
                    location=Location(
                        block_index=block_index,
                        section_index=section_index,
                        approx_page=approx_page,
                        excerpt=clean_excerpt,
                    ),
                    actual=str(actual),
                    expected=str(expected),
                    fix_mode=fix_mode,
                    message_id=message_id,
                    message=msg,
                )
            )

        # Tolerances from profile
        tol_margin = profile.tolerances.get("margin_cm", 0.05)
        tol_indent = profile.tolerances.get("indent_cm", 0.05)
        tol_font_sz = profile.tolerances.get("font_size_pt", 0.0)
        tol_spacing = profile.tolerances.get("spacing_pt", 0.5)
        tol_line = profile.tolerances.get("line_spacing", 0.02)

        # --- 1. PAGE Rules (PAGE-001..004) ---
        exp_w_cm, exp_h_cm = get_paper_dimensions_cm(profile.page.size, profile.page.orientation)
        exp_margins = profile.page.margins_cm
        exp_hf = profile.page.header_footer_distance_cm or {}

        for sect in ir.sections:
            # PAGE-004: Orientation
            if sect.orientation != profile.page.orientation:
                add_finding(
                    "PAGE-004",
                    "finding.page.orientation",
                    actual=sect.orientation,
                    expected=profile.page.orientation,
                    section_index=sect.index,
                )

            # PAGE-001: Paper size (compare accounting for current orientation)
            curr_exp_w, curr_exp_h = get_paper_dimensions_cm(profile.page.size, sect.orientation)
            if not (
                is_approx_equal(sect.page_width_cm, curr_exp_w, 0.15)
                and is_approx_equal(sect.page_height_cm, curr_exp_h, 0.15)
            ):
                add_finding(
                    "PAGE-001",
                    "finding.page.size",
                    actual=f"{sect.page_width_cm:.1f} x {sect.page_height_cm:.1f} cm",
                    expected=f"{profile.page.size} ({exp_w_cm:.1f} x {exp_h_cm:.1f} cm)",
                    section_index=sect.index,
                )

            # PAGE-002: Margins
            if not is_approx_equal(sect.top_margin_cm, exp_margins.top, tol_margin):
                add_finding(
                    "PAGE-002",
                    "finding.page.margin_top",
                    actual=f"{sect.top_margin_cm:.2f} cm",
                    expected=f"{exp_margins.top:.2f} cm",
                    section_index=sect.index,
                )
            if not is_approx_equal(sect.bottom_margin_cm, exp_margins.bottom, tol_margin):
                add_finding(
                    "PAGE-002",
                    "finding.page.margin_bottom",
                    actual=f"{sect.bottom_margin_cm:.2f} cm",
                    expected=f"{exp_margins.bottom:.2f} cm",
                    section_index=sect.index,
                )
            if not is_approx_equal(sect.left_margin_cm, exp_margins.left, tol_margin):
                add_finding(
                    "PAGE-002",
                    "finding.page.margin_left",
                    actual=f"{sect.left_margin_cm:.2f} cm",
                    expected=f"{exp_margins.left:.2f} cm",
                    section_index=sect.index,
                )
            if not is_approx_equal(sect.right_margin_cm, exp_margins.right, tol_margin):
                add_finding(
                    "PAGE-002",
                    "finding.page.margin_right",
                    actual=f"{sect.right_margin_cm:.2f} cm",
                    expected=f"{exp_margins.right:.2f} cm",
                    section_index=sect.index,
                )

            # PAGE-003: Header & Footer distance
            if "header" in exp_hf and not is_approx_equal(
                sect.header_distance_cm, exp_hf["header"], tol_margin
            ):
                add_finding(
                    "PAGE-003",
                    "finding.page.header_dist",
                    actual=f"{sect.header_distance_cm:.2f} cm",
                    expected=f"{exp_hf['header']:.2f} cm",
                    section_index=sect.index,
                )
            if "footer" in exp_hf and not is_approx_equal(
                sect.footer_distance_cm, exp_hf["footer"], tol_margin
            ):
                add_finding(
                    "PAGE-003",
                    "finding.page.footer_dist",
                    actual=f"{sect.footer_distance_cm:.2f} cm",
                    expected=f"{exp_hf['footer']:.2f} cm",
                    section_index=sect.index,
                )

        # --- 2. Block-level Rules (FONT, PARA, HEAD, CAP, FIG, TBL, BIB) ---
        consecutive_empty = 0
        last_heading_level = 1
        fig_caption_numbers: list[tuple[int, int]] = []
        tbl_caption_numbers: list[tuple[int, int]] = []
        bib_blocks: list[DocumentBlock] = []

        for idx, block in enumerate(ir.blocks):
            role = block.assigned_role or "other"
            text_clean = (block.text or "").strip()

            # Tracked changes / comments / SDT / Textbox advisories
            if block.has_tracked_changes:
                findings.append(
                    Finding(
                        id=make_finding_id(
                            "DOC-001", block.section_index, block.index, "tracked_changes"
                        ),
                        rule_id="DOC-001",
                        category="PARA",
                        severity=Severity.WARNING,
                        location=Location(
                            block_index=block.index,
                            section_index=block.section_index,
                            approx_page=block.approx_page,
                            excerpt=text_clean[:60] if text_clean else None,
                        ),
                        actual="Revisi aktif (w:ins/w:del)",
                        expected="Revisi diterima/ditolak (Accept/Reject Changes)",
                        fix_mode=FixMode.MANUAL,
                        message_id="finding.doc.tracked_changes",
                        message=format_message(
                            "finding.doc.tracked_changes", block=block.index + 1
                        ),
                    )
                )

            if block.block_type == "table":
                self._evaluate_table_block(
                    block=block,
                    ir=ir,
                    profile=profile,
                    resolver=resolver,
                    prev_block=ir.blocks[idx - 1] if idx > 0 else None,
                    next_block=ir.blocks[idx + 1] if idx + 1 < len(ir.blocks) else None,
                    add_finding=add_finding,
                )
                continue

            # Empty paragraph check (PARA-005)
            if not text_clean and not block.images and not block.fields:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    add_finding(
                        "PARA-005",
                        "finding.para.empty_spacing",
                        actual=f"{consecutive_empty} paragraf kosong berurutan",
                        expected="Gunakan pengaturan Space Before/After pada Style",
                        section_index=block.section_index,
                        block_index=block.index,
                        approx_page=block.approx_page,
                    )
                continue
            else:
                consecutive_empty = 0

            fmt = formats.get(block.index)
            if fmt is None:
                continue

            # Check images inside paragraph (FIG-001..003, CAP-001)
            if block.images:
                self._evaluate_figure_block(
                    block=block,
                    fmt=fmt,
                    ir=ir,
                    profile=profile,
                    prev_block=ir.blocks[idx - 1] if idx > 0 else None,
                    next_block=ir.blocks[idx + 1] if idx + 1 < len(ir.blocks) else None,
                    add_finding=add_finding,
                )
                if not text_clean:
                    continue

            # Paragraphs with role == "other" or "cover" or "toc_entry" skip standard FONT/PARA checks
            if role in ("other", "cover", "toc_entry"):
                continue

            role_spec = profile.roles.get(role, {})
            if role == "front_title" and not role_spec:
                role_spec = profile.roles.get("chapter_title", {})

            # --- FONT Rules (FONT-001..004) ---
            exp_font = str(role_spec.get("font_family", profile.text.font_family))
            exp_size = float(role_spec.get("font_size_pt", profile.text.font_size_pt))
            exp_color = str(role_spec.get("color_hex", profile.text.color_hex)).upper().lstrip("#")

            # FONT-001: Font family
            font_slots = [
                f for f in (fmt.font_family, fmt.font_ascii, fmt.font_hAnsi, fmt.font_cs) if f
            ]
            if fmt.font_family.lower() != exp_font.lower() or any(
                s.lower() != exp_font.lower() for s in font_slots
            ):
                actual_font_desc = fmt.font_family
                if fmt.font_family.lower() == exp_font.lower():
                    bad_slot = next(s for s in font_slots if s.lower() != exp_font.lower())
                    actual_font_desc = f"{fmt.font_family} (slot campuran: {bad_slot})"
                add_finding(
                    "FONT-001",
                    "finding.font.family",
                    actual=actual_font_desc,
                    expected=exp_font,
                    section_index=block.section_index,
                    block_index=block.index,
                    approx_page=block.approx_page,
                    excerpt=text_clean,
                    role=role,
                )

            # FONT-002: Font size
            if not is_approx_equal(fmt.font_size_pt, exp_size, tol_font_sz):
                add_finding(
                    "FONT-002",
                    "finding.font.size",
                    actual=f"{fmt.font_size_pt:g} pt",
                    expected=f"{exp_size:g} pt",
                    section_index=block.section_index,
                    block_index=block.index,
                    approx_page=block.approx_page,
                    excerpt=text_clean,
                    role=role,
                )

            # FONT-003: Font color
            if fmt.color_hex.upper().lstrip("#") != exp_color:
                add_finding(
                    "FONT-003",
                    "finding.font.color",
                    actual=fmt.color_hex.upper(),
                    expected=exp_color,
                    section_index=block.section_index,
                    block_index=block.index,
                    approx_page=block.approx_page,
                    excerpt=text_clean,
                    role=role,
                )

            # FONT-004: Stray fonts in middle of paragraph
            if len({f.lower() for f in fmt.run_fonts}) > 1:
                add_finding(
                    "FONT-004",
                    "finding.font.stray",
                    actual=", ".join(fmt.run_fonts),
                    expected=exp_font,
                    section_index=block.section_index,
                    block_index=block.index,
                    approx_page=block.approx_page,
                    excerpt=text_clean,
                )

            # --- PARA-006 & PARA-007 (Manual indent spaces/tabs, manual line break) ---
            if len(block.leading_whitespace) >= 2 or "\t" in block.leading_whitespace:
                add_finding(
                    "PARA-006",
                    "finding.para.manual_indent",
                    actual=repr(block.leading_whitespace),
                    expected="First-line indent pada Style paragraf",
                    section_index=block.section_index,
                    block_index=block.index,
                    approx_page=block.approx_page,
                    excerpt=text_clean,
                )

            if block.has_manual_line_break and role not in ("chapter_label",):
                add_finding(
                    "PARA-007",
                    "finding.para.manual_linebreak",
                    actual="Line break manual (w:br)",
                    expected="Paragraf terpisah dengan Style yang sesuai",
                    section_index=block.section_index,
                    block_index=block.index,
                    approx_page=block.approx_page,
                    excerpt=text_clean,
                )

            # --- Role-specific checks ---
            if role in ("body", "block_quote", "list_item"):
                # PARA-001: Line spacing
                if "line_spacing" in role_spec:
                    exp_ls = float(role_spec["line_spacing"])
                    if not is_approx_equal(fmt.line_spacing, exp_ls, tol_line):
                        add_finding(
                            "PARA-001",
                            "finding.para.line_spacing",
                            actual=f"{fmt.line_spacing:.2f}",
                            expected=f"{exp_ls:.2f}",
                            section_index=block.section_index,
                            block_index=block.index,
                            approx_page=block.approx_page,
                            excerpt=text_clean,
                            role=role,
                        )

                # PARA-002: Space before & after
                if "space_before_pt" in role_spec:
                    exp_sb = float(role_spec["space_before_pt"])
                    if not is_approx_equal(fmt.space_before_pt, exp_sb, tol_spacing):
                        add_finding(
                            "PARA-002",
                            "finding.para.space_before",
                            actual=f"{fmt.space_before_pt:g} pt",
                            expected=f"{exp_sb:g} pt",
                            section_index=block.section_index,
                            block_index=block.index,
                            approx_page=block.approx_page,
                            excerpt=text_clean,
                            role=role,
                        )
                if "space_after_pt" in role_spec:
                    exp_sa = float(role_spec["space_after_pt"])
                    if not is_approx_equal(fmt.space_after_pt, exp_sa, tol_spacing):
                        add_finding(
                            "PARA-002",
                            "finding.para.space_after",
                            actual=f"{fmt.space_after_pt:g} pt",
                            expected=f"{exp_sa:g} pt",
                            section_index=block.section_index,
                            block_index=block.index,
                            approx_page=block.approx_page,
                            excerpt=text_clean,
                            role=role,
                        )

                # PARA-003: Indentation
                if "first_line_indent_cm" in role_spec:
                    exp_fl = float(role_spec["first_line_indent_cm"])
                    if not is_approx_equal(fmt.first_line_indent_cm, exp_fl, tol_indent):
                        add_finding(
                            "PARA-003",
                            "finding.para.indent_first",
                            actual=f"{fmt.first_line_indent_cm:.2f} cm",
                            expected=f"{exp_fl:.2f} cm",
                            section_index=block.section_index,
                            block_index=block.index,
                            approx_page=block.approx_page,
                            excerpt=text_clean,
                            role=role,
                        )
                if "left_indent_cm" in role_spec:
                    exp_li = float(role_spec["left_indent_cm"])
                    if not is_approx_equal(fmt.left_indent_cm, exp_li, tol_indent):
                        add_finding(
                            "PARA-003",
                            "finding.para.indent_left",
                            actual=f"{fmt.left_indent_cm:.2f} cm",
                            expected=f"{exp_li:.2f} cm",
                            section_index=block.section_index,
                            block_index=block.index,
                            approx_page=block.approx_page,
                            excerpt=text_clean,
                            role=role,
                        )
                if "right_indent_cm" in role_spec:
                    exp_ri = float(role_spec["right_indent_cm"])
                    if not is_approx_equal(fmt.right_indent_cm, exp_ri, tol_indent):
                        add_finding(
                            "PARA-003",
                            "finding.para.indent_right",
                            actual=f"{fmt.right_indent_cm:.2f} cm",
                            expected=f"{exp_ri:.2f} cm",
                            section_index=block.section_index,
                            block_index=block.index,
                            approx_page=block.approx_page,
                            excerpt=text_clean,
                            role=role,
                        )

                # PARA-004: Alignment
                if "alignment" in role_spec:
                    exp_al = str(role_spec["alignment"])
                    if fmt.alignment != exp_al:
                        add_finding(
                            "PARA-004",
                            "finding.para.alignment",
                            actual=fmt.alignment,
                            expected=exp_al,
                            section_index=block.section_index,
                            block_index=block.index,
                            approx_page=block.approx_page,
                            excerpt=text_clean,
                            role=role,
                        )

                # PARA-008: Widow/Orphan control
                if not fmt.widow_control:
                    add_finding(
                        "PARA-008",
                        "finding.para.widow_control",
                        actual="Nonaktif (false)",
                        expected="Aktif (true)",
                        section_index=block.section_index,
                        block_index=block.index,
                        approx_page=block.approx_page,
                        excerpt=text_clean,
                    )

            # --- HEAD Rules (HEAD-001..006) ---
            elif role in ("chapter_label", "chapter_title", "front_title"):
                last_heading_level = 1
                self._evaluate_chapter_heading(
                    block=block,
                    fmt=fmt,
                    role_spec=role_spec,
                    ir=ir,
                    tol_line=tol_line,
                    tol_spacing=tol_spacing,
                    add_finding=add_finding,
                )

            elif role in ("heading_2", "heading_3", "heading_4"):
                curr_lvl = int(role.split("_")[1])
                if curr_lvl > last_heading_level + 1:
                    add_finding(
                        "HEAD-006",
                        "finding.head.skipped_level",
                        actual=str(last_heading_level),
                        expected=str(curr_lvl),
                        section_index=block.section_index,
                        block_index=block.index,
                        approx_page=block.approx_page,
                        excerpt=text_clean,
                    )
                last_heading_level = curr_lvl
                self._evaluate_subheading(
                    block=block,
                    fmt=fmt,
                    role_spec=role_spec,
                    tol_line=tol_line,
                    tol_spacing=tol_spacing,
                    tol_indent=tol_indent,
                    add_finding=add_finding,
                )

            # --- CAP Rules (CAP-002..005) ---
            elif role in ("caption_figure", "caption_table"):
                self._evaluate_caption_block(
                    block=block,
                    idx=idx,
                    fmt=fmt,
                    role_spec=role_spec,
                    ir=ir,
                    profile=profile,
                    tol_line=tol_line,
                    tol_spacing=tol_spacing,
                    fig_caption_numbers=fig_caption_numbers,
                    tbl_caption_numbers=tbl_caption_numbers,
                    add_finding=add_finding,
                )

            # --- BIB Rules (BIB-002..003) ---
            elif role == "bibliography_entry":
                bib_blocks.append(block)
                if "hanging_indent_cm" in role_spec:
                    exp_hi = float(role_spec["hanging_indent_cm"])
                    if not is_approx_equal(fmt.hanging_indent_cm, exp_hi, tol_indent):
                        add_finding(
                            "BIB-002",
                            "finding.bib.hanging_indent",
                            actual=f"{fmt.hanging_indent_cm:.2f} cm",
                            expected=f"{exp_hi:.2f} cm",
                            section_index=block.section_index,
                            block_index=block.index,
                            approx_page=block.approx_page,
                            excerpt=text_clean,
                        )
                exp_ls = float(role_spec.get("line_spacing", 1.0))
                exp_sa = float(role_spec.get("space_after_pt", 12.0))
                if not (
                    is_approx_equal(fmt.line_spacing, exp_ls, tol_line)
                    and is_approx_equal(fmt.space_after_pt, exp_sa, tol_spacing)
                ):
                    add_finding(
                        "BIB-003",
                        "finding.bib.spacing",
                        actual=f"line={fmt.line_spacing:.2f}, after={fmt.space_after_pt:g}pt",
                        expected=f"line={exp_ls:.2f}, after={exp_sa:g}pt",
                        section_index=block.section_index,
                        block_index=block.index,
                        approx_page=block.approx_page,
                        excerpt=text_clean,
                    )

        # --- 3. CAP-005: Sequential caption numbering ---
        self._check_caption_sequence(fig_caption_numbers, "Gambar", add_finding)
        self._check_caption_sequence(tbl_caption_numbers, "Tabel", add_finding)

        # --- 4. BIB-001 & BIB-004: Bibliography sorting & citation matching ---
        if bib_blocks:
            self._evaluate_bibliography_collection(bib_blocks, ir, profile, add_finding)

        # --- 5. NUM Rules (NUM-001..006) ---
        self._evaluate_page_numbering(ir, profile, add_finding)

        # --- 6. TOC, LOF, LOT Rules (TOC-001..005, LOF-001, LOT-001) ---
        self._evaluate_toc_lof_lot(
            ir, profile, resolver, bool(fig_caption_numbers), bool(tbl_caption_numbers), add_finding
        )

        # --- 7. STR Rules (STR-001..004) ---
        self._evaluate_structure(ir, profile, formats, add_finding)

        return findings

    def _evaluate_chapter_heading(
        self,
        block: DocumentBlock,
        fmt: EffectiveFormat,
        role_spec: dict[str, Any],
        ir: DocumentIR,
        tol_line: float,
        tol_spacing: float,
        add_finding: Any,
    ) -> None:
        text_clean = (block.text or "").strip()
        issues: list[str] = []
        expected_parts: list[str] = []

        if role_spec.get("bold", True) and not fmt.bold:
            issues.append("tidak bold")
            expected_parts.append("bold")

        if role_spec.get("all_caps", True) and not (fmt.all_caps or text_clean.isupper()):
            issues.append("tidak huruf kapital semua")
            expected_parts.append("huruf kapital (ALL CAPS)")

        exp_align = str(role_spec.get("alignment", "center"))
        if fmt.alignment != exp_align:
            issues.append(f"rata {fmt.alignment}")
            expected_parts.append(f"rata {exp_align}")

        if "line_spacing" in role_spec:
            exp_ls = float(role_spec["line_spacing"])
            if not is_approx_equal(fmt.line_spacing, exp_ls, tol_line):
                issues.append(f"spasi baris {fmt.line_spacing:.2f}")
                expected_parts.append(f"spasi baris {exp_ls:.2f}")

        if "space_after_pt" in role_spec:
            exp_sa = float(role_spec["space_after_pt"])
            if not is_approx_equal(fmt.space_after_pt, exp_sa, tol_spacing):
                issues.append(f"spasi sesudah {fmt.space_after_pt:g}pt")
                expected_parts.append(f"spasi sesudah {exp_sa:g}pt")

        if issues:
            add_finding(
                "HEAD-001",
                "finding.head.chapter_format",
                actual=", ".join(issues),
                expected=", ".join(expected_parts),
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
                excerpt=text_clean,
            )

        # HEAD-004: keep_with_next
        if role_spec.get("keep_with_next", True) and not fmt.keep_with_next:
            add_finding(
                "HEAD-004",
                "finding.head.keep_with_next",
                actual="keep_with_next=false",
                expected="keep_with_next=true",
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
                excerpt=text_clean,
            )

        # HEAD-005: Chapter starts on a new page
        if block.assigned_role == "chapter_label" and role_spec.get("page_break_before", True):
            starts_new_page = (
                block.index == 0
                or fmt.page_break_before
                or block.has_page_break_run
                or (
                    block.index > 0
                    and ir.blocks[block.index - 1].section_index != block.section_index
                    and ir.sections[block.section_index].section_start_type == "nextPage"
                )
                or (block.index > 0 and ir.blocks[block.index - 1].has_page_break_run)
            )
            if not starts_new_page:
                add_finding(
                    "HEAD-005",
                    "finding.head.page_break_before",
                    actual="Bukan halaman baru",
                    expected="Mulai di halaman baru (pageBreakBefore / section break)",
                    section_index=block.section_index,
                    block_index=block.index,
                    approx_page=block.approx_page,
                    excerpt=text_clean,
                )

    def _evaluate_subheading(
        self,
        block: DocumentBlock,
        fmt: EffectiveFormat,
        role_spec: dict[str, Any],
        tol_line: float,
        tol_spacing: float,
        tol_indent: float,
        add_finding: Any,
    ) -> None:
        text_clean = (block.text or "").strip()
        role = block.assigned_role or "heading_2"
        issues: list[str] = []
        expected_parts: list[str] = []

        if role_spec.get("bold", True) and not fmt.bold:
            issues.append("tidak bold")
            expected_parts.append("bold")

        exp_align = str(role_spec.get("alignment", "left"))
        if fmt.alignment != exp_align:
            issues.append(f"rata {fmt.alignment}")
            expected_parts.append(f"rata {exp_align}")

        if "line_spacing" in role_spec:
            exp_ls = float(role_spec["line_spacing"])
            if not is_approx_equal(fmt.line_spacing, exp_ls, tol_line):
                issues.append(f"spasi baris {fmt.line_spacing:.2f}")
                expected_parts.append(f"spasi baris {exp_ls:.2f}")

        if "space_before_pt" in role_spec:
            exp_sb = float(role_spec["space_before_pt"])
            if not is_approx_equal(fmt.space_before_pt, exp_sb, tol_spacing):
                issues.append(f"spasi sebelum {fmt.space_before_pt:g}pt")
                expected_parts.append(f"spasi sebelum {exp_sb:g}pt")

        if "space_after_pt" in role_spec:
            exp_sa = float(role_spec["space_after_pt"])
            if not is_approx_equal(fmt.space_after_pt, exp_sa, tol_spacing):
                issues.append(f"spasi sesudah {fmt.space_after_pt:g}pt")
                expected_parts.append(f"spasi sesudah {exp_sa:g}pt")

        if "hanging_indent_cm" in role_spec:
            exp_hi = float(role_spec["hanging_indent_cm"])
            if not is_approx_equal(fmt.hanging_indent_cm, exp_hi, tol_indent):
                issues.append(f"hanging indent {fmt.hanging_indent_cm:.2f}cm")
                expected_parts.append(f"hanging indent {exp_hi:.2f}cm")

        if issues:
            add_finding(
                "HEAD-002",
                "finding.head.subheading_format",
                actual=", ".join(issues),
                expected=", ".join(expected_parts),
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
                excerpt=text_clean,
                role=role,
            )

        # HEAD-003: Typed heading number vs automatic numbering
        m_num = re.match(r"^(\d+(?:\.\d+)+)\s+", text_clean)
        if m_num and fmt.num_id is None:
            add_finding(
                "HEAD-003",
                "finding.head.typed_number",
                actual=m_num.group(0).strip(),
                expected=f"Numbering otomatis ({role})",
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
                excerpt=text_clean,
            )

        # HEAD-004: keep_with_next
        if role_spec.get("keep_with_next", True) and not fmt.keep_with_next:
            add_finding(
                "HEAD-004",
                "finding.head.keep_with_next",
                actual="keep_with_next=false",
                expected="keep_with_next=true",
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
                excerpt=text_clean,
            )

    def _evaluate_caption_block(
        self,
        block: DocumentBlock,
        idx: int,
        fmt: EffectiveFormat,
        role_spec: dict[str, Any],
        ir: DocumentIR,
        profile: RuleProfile,
        tol_line: float,
        tol_spacing: float,
        fig_caption_numbers: list[tuple[int, int]],
        tbl_caption_numbers: list[tuple[int, int]],
        add_finding: Any,
    ) -> None:
        text_clean = (block.text or "").strip()
        is_fig = block.assigned_role == "caption_figure"
        cap_cfg = profile.captions.get("figure" if is_fig else "table", {})
        exp_pos = cap_cfg.get("position", "below" if is_fig else "above")

        prev_b = ir.blocks[idx - 1] if idx > 0 else None
        next_b = ir.blocks[idx + 1] if idx + 1 < len(ir.blocks) else None

        # CAP-002: Caption position relative to target figure/table
        if is_fig:
            if exp_pos == "below" and next_b and next_b.images and not (prev_b and prev_b.images):
                add_finding(
                    "CAP-002",
                    "finding.cap.position",
                    actual="di atas gambar (above)",
                    expected="di bawah gambar (below)",
                    section_index=block.section_index,
                    block_index=block.index,
                    approx_page=block.approx_page,
                    excerpt=text_clean,
                )
            elif exp_pos == "above" and prev_b and prev_b.images and not (next_b and next_b.images):
                add_finding(
                    "CAP-002",
                    "finding.cap.position",
                    actual="di bawah gambar (below)",
                    expected="di atas gambar (above)",
                    section_index=block.section_index,
                    block_index=block.index,
                    approx_page=block.approx_page,
                    excerpt=text_clean,
                )
        else:
            if (
                exp_pos == "above"
                and prev_b
                and prev_b.block_type == "table"
                and not (next_b and next_b.block_type == "table")
            ):
                add_finding(
                    "CAP-002",
                    "finding.cap.position",
                    actual="di bawah tabel (below)",
                    expected="di atas tabel (above)",
                    section_index=block.section_index,
                    block_index=block.index,
                    approx_page=block.approx_page,
                    excerpt=text_clean,
                )
            elif (
                exp_pos == "below"
                and next_b
                and next_b.block_type == "table"
                and not (prev_b and prev_b.block_type == "table")
            ):
                add_finding(
                    "CAP-002",
                    "finding.cap.position",
                    actual="di atas tabel (above)",
                    expected="di bawah tabel (below)",
                    section_index=block.section_index,
                    block_index=block.index,
                    approx_page=block.approx_page,
                    excerpt=text_clean,
                )

        # CAP-003: Style and format of caption
        issues: list[str] = []
        exp_parts: list[str] = []
        exp_align = str(role_spec.get("alignment", "center"))
        if fmt.alignment != exp_align:
            issues.append(f"rata {fmt.alignment}")
            exp_parts.append(f"rata {exp_align}")
        if "line_spacing" in role_spec:
            exp_ls = float(role_spec["line_spacing"])
            if not is_approx_equal(fmt.line_spacing, exp_ls, tol_line):
                issues.append(f"spasi baris {fmt.line_spacing:.2f}")
                exp_parts.append(f"spasi baris {exp_ls:.2f}")
        if "space_before_pt" in role_spec:
            exp_sb = float(role_spec["space_before_pt"])
            if not is_approx_equal(fmt.space_before_pt, exp_sb, tol_spacing):
                issues.append(f"before {fmt.space_before_pt:g}pt")
                exp_parts.append(f"before {exp_sb:g}pt")
        if "space_after_pt" in role_spec:
            exp_sa = float(role_spec["space_after_pt"])
            if not is_approx_equal(fmt.space_after_pt, exp_sa, tol_spacing):
                issues.append(f"after {fmt.space_after_pt:g}pt")
                exp_parts.append(f"after {exp_sa:g}pt")
        if role_spec.get("keep_with_next") and not fmt.keep_with_next:
            issues.append("keep_with_next=false")
            exp_parts.append("keep_with_next=true")

        if issues:
            add_finding(
                "CAP-003",
                "finding.cap.format",
                actual=", ".join(issues),
                expected=", ".join(exp_parts),
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
                excerpt=text_clean,
            )

        # CAP-004: Uses SEQ field
        has_seq = any(f.field_type == "SEQ" for f in block.fields)
        if not has_seq:
            add_finding(
                "CAP-004",
                "finding.cap.typed_number",
                actual=text_clean[:35],
                expected=f"Field SEQ {cap_cfg.get('label', 'Gambar' if is_fig else 'Tabel')}",
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
                excerpt=text_clean,
            )

        # Extract trailing sequence number for CAP-005
        m_cap_num = re.match(
            r"^(?:Gambar|Figure|Tabel|Table)\s+(?:\d+[.\-])?(\d+)\b", text_clean, re.IGNORECASE
        )
        if m_cap_num:
            seq_val = int(m_cap_num.group(1))
            if is_fig:
                fig_caption_numbers.append((block.index, seq_val))
            else:
                tbl_caption_numbers.append((block.index, seq_val))

    def _check_caption_sequence(
        self,
        items: list[tuple[int, int]],
        label: str,
        add_finding: Any,
    ) -> None:
        if not items:
            return
        expected_num = 1
        for block_idx, actual_num in items:
            if actual_num == 1 and expected_num > 1:
                # Per-chapter reset to 1 is valid
                expected_num = 2
                continue
            if actual_num != expected_num:
                add_finding(
                    "CAP-005",
                    "finding.cap.sequence",
                    actual=f"{label} #{actual_num}",
                    expected=f"{label} #{expected_num}",
                    section_index=0,
                    block_index=block_idx,
                )
                expected_num = actual_num + 1
            else:
                expected_num += 1

    def _evaluate_figure_block(
        self,
        block: DocumentBlock,
        fmt: EffectiveFormat,
        ir: DocumentIR,
        profile: RuleProfile,
        prev_block: DocumentBlock | None,
        next_block: DocumentBlock | None,
        add_finding: Any,
    ) -> None:
        sect = ir.sections[min(block.section_index, len(ir.sections) - 1)]
        max_w_cm = sect.page_width_cm - sect.left_margin_cm - sect.right_margin_cm
        tol_m = profile.tolerances.get("margin_cm", 0.05)

        # FIG-001: Image alignment
        if fmt.alignment != "center":
            add_finding(
                "FIG-001",
                "finding.fig.alignment",
                actual=fmt.alignment,
                expected="center",
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
            )

        for img in block.images:
            # FIG-003: Floating image
            if img.is_floating:
                add_finding(
                    "FIG-003",
                    "finding.fig.floating",
                    actual="Floating (wp:anchor)",
                    expected="Inline with text (wp:inline)",
                    section_index=block.section_index,
                    block_index=block.index,
                    approx_page=block.approx_page,
                )
            # FIG-002: Image width exceeds text margin
            if img.width_cm > max_w_cm + tol_m:
                add_finding(
                    "FIG-002",
                    "finding.fig.oversized",
                    actual=f"{img.width_cm:.2f} cm",
                    expected=f"<= {max_w_cm:.2f} cm",
                    section_index=block.section_index,
                    block_index=block.index,
                    approx_page=block.approx_page,
                )

        # CAP-001: Every figure has a caption
        has_adj_caption = (
            block.assigned_role == "caption_figure"
            or (prev_block is not None and prev_block.assigned_role == "caption_figure")
            or (next_block is not None and next_block.assigned_role == "caption_figure")
        )
        if not has_adj_caption:
            add_finding(
                "CAP-001",
                "finding.cap.missing",
                actual="Gambar tanpa caption",
                expected="Caption Gambar",
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
            )

    def _evaluate_table_block(
        self,
        block: DocumentBlock,
        ir: DocumentIR,
        profile: RuleProfile,
        resolver: StyleHierarchyResolver,
        prev_block: DocumentBlock | None,
        next_block: DocumentBlock | None,
        add_finding: Any,
    ) -> None:
        tinfo = block.table_info
        if tinfo is None:
            return

        sect = ir.sections[min(block.section_index, len(ir.sections) - 1)]
        max_w_cm = sect.page_width_cm - sect.left_margin_cm - sect.right_margin_cm
        tol_m = profile.tolerances.get("margin_cm", 0.05)

        # TBL-001: Table width exceeds margins
        if tinfo.width_cm > max_w_cm + tol_m:
            add_finding(
                "TBL-001",
                "finding.tbl.oversized",
                actual=f"{tinfo.width_cm:.2f} cm",
                expected=f"<= {max_w_cm:.2f} cm",
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
            )

        # TBL-002: Repeat header row
        if tinfo.row_count >= 2 and not tinfo.has_tbl_header:
            add_finding(
                "TBL-002",
                "finding.tbl.repeat_header",
                actual="tblHeader=false",
                expected="tblHeader=true pada baris judul",
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
            )

        # TBL-003: cantSplit on rows
        if tinfo.row_count >= 1 and not tinfo.all_rows_cant_split:
            add_finding(
                "TBL-003",
                "finding.tbl.cant_split",
                actual="cantSplit=false",
                expected="cantSplit=true pada setiap baris",
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
            )

        # TBL-004: Font & spacing inside table cells (`table_text` role)
        tbl_role_spec = profile.roles.get("table_text", {})
        exp_font = str(tbl_role_spec.get("font_family", profile.text.font_family))
        exp_sz = float(tbl_role_spec.get("font_size_pt", 11.0))
        exp_ls = float(tbl_role_spec.get("line_spacing", 1.0))
        tol_line = profile.tolerances.get("line_spacing", 0.02)

        cell_mismatch: str | None = None
        for p_el in block.raw_element.iter(qn("w:p")):
            if not extract_visible_paragraph_text(p_el).strip():
                continue
            cfmt = resolver.resolve_paragraph(p_el)
            if (
                cfmt.font_family.lower() != exp_font.lower()
                or not is_approx_equal(cfmt.font_size_pt, exp_sz, 0.1)
                or not is_approx_equal(cfmt.line_spacing, exp_ls, tol_line)
            ):
                cell_mismatch = (
                    f"{cfmt.font_family} {cfmt.font_size_pt:g}pt, spasi {cfmt.line_spacing:.2f}"
                )
                break

        if cell_mismatch:
            add_finding(
                "TBL-004",
                "finding.tbl.text_format",
                actual=cell_mismatch,
                expected=f"{exp_font} {exp_sz:g}pt, spasi {exp_ls:.2f}",
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
            )

        # TBL-005: Table alignment
        exp_tbl_align = str(tbl_role_spec.get("table_alignment", "center"))
        if tinfo.alignment != exp_tbl_align:
            add_finding(
                "TBL-005",
                "finding.tbl.alignment",
                actual=tinfo.alignment,
                expected=exp_tbl_align,
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
            )

        # CAP-001: Every table has a caption
        has_adj_caption = (
            prev_block is not None and prev_block.assigned_role == "caption_table"
        ) or (next_block is not None and next_block.assigned_role == "caption_table")
        if not has_adj_caption:
            add_finding(
                "CAP-001",
                "finding.cap.missing",
                actual="Tabel tanpa caption",
                expected="Caption Tabel",
                section_index=block.section_index,
                block_index=block.index,
                approx_page=block.approx_page,
            )

    def _evaluate_bibliography_collection(
        self,
        bib_blocks: list[DocumentBlock],
        ir: DocumentIR,
        profile: RuleProfile,
        add_finding: Any,
    ) -> None:
        bib_spec = profile.roles.get("bibliography_entry", {})
        # BIB-001: Alphabetical sorting
        if bib_spec.get("sorted") == "alphabetical" and len(bib_blocks) >= 2:
            prev_key = (bib_blocks[0].text or "").strip().lower()
            prev_short = (bib_blocks[0].text or "").strip()[:35]
            for b in bib_blocks[1:]:
                curr_text = (b.text or "").strip()
                curr_key = curr_text.lower()
                if curr_key < prev_key:
                    add_finding(
                        "BIB-001",
                        "finding.bib.unsorted",
                        actual=curr_text[:35],
                        expected=prev_short,
                        section_index=b.section_index,
                        block_index=b.index,
                        approx_page=b.approx_page,
                        excerpt=curr_text,
                    )
                else:
                    prev_key = curr_key
                    prev_short = curr_text[:35]

        # BIB-004: Citation check against body text
        body_text_lower = "\n".join(
            (b.text or "").lower()
            for b in ir.blocks
            if b.assigned_role in ("body", "block_quote", "list_item")
        )
        if body_text_lower:
            for b in bib_blocks:
                entry = (b.text or "").strip()
                m_author = re.match(r"^([A-Za-zÀ-ÿ\-']+)", entry)
                if m_author:
                    surname = m_author.group(1).lower()
                    if len(surname) >= 3 and surname not in body_text_lower:
                        add_finding(
                            "BIB-004",
                            "finding.bib.uncited",
                            actual=entry[:40],
                            expected=f"Sitasi '{m_author.group(1)}' di dalam teks isi",
                            section_index=b.section_index,
                            block_index=b.index,
                            approx_page=b.approx_page,
                            excerpt=entry,
                        )

    def _evaluate_page_numbering(
        self,
        ir: DocumentIR,
        profile: RuleProfile,
        add_finding: Any,
    ) -> None:
        pg_cfg = profile.page_numbering
        if not pg_cfg:
            return

        # Check NUM-006 on all sections (typed page numbers in header/footer)
        for sect in ir.sections:
            for hf in (
                sect.header_info,
                sect.footer_info,
                sect.first_header_info,
                sect.first_footer_info,
            ):
                if hf.has_typed_page_number:
                    add_finding(
                        "NUM-006",
                        "finding.num.typed_page",
                        actual=hf.typed_text,
                        expected="Field PAGE otomatis",
                        section_index=sect.index,
                    )
                    break

        # Determine section groups from blocks
        has_thesis_structure = any(
            b.assigned_role in ("cover", "front_title", "chapter_label", "chapter_title")
            for b in ir.blocks
        )
        if not has_thesis_structure and len(ir.sections) <= 1:
            return

        section_roles: dict[int, set[str]] = {s.index: set() for s in ir.sections}
        section_has_chapter: dict[int, bool] = {s.index: False for s in ir.sections}
        for b in ir.blocks:
            if b.assigned_role and b.assigned_role != "other":
                section_roles.setdefault(b.section_index, set()).add(b.assigned_role)
            if b.assigned_role == "chapter_label":
                section_has_chapter[b.section_index] = True

        first_body_checked = False
        for sect in ir.sections:
            roles_in_sec = section_roles.get(sect.index, set())
            is_cover_sec = "cover" in roles_in_sec and not (
                roles_in_sec & {"front_title", "toc_entry", "chapter_label", "chapter_title"}
            )
            has_front = bool(
                roles_in_sec & {"front_title", "toc_entry"}
            ) and not section_has_chapter.get(sect.index, False)
            has_body = section_has_chapter.get(sect.index, False) or (
                bool(roles_in_sec & {"chapter_title", "heading_2", "body"})
                and not is_cover_sec
                and not has_front
            )

            # Mixed front_matter and body in the same section without section break
            if "front_title" in roles_in_sec and section_has_chapter.get(sect.index, False):
                # Check if front_title is actually front matter (not DAFTAR PUSTAKA / LAMPIRAN)
                has_early_front = any(
                    b.section_index == sect.index
                    and b.assigned_role == "front_title"
                    and not re.match(r"^(DAFTAR\s+PUSTAKA|LAMPIRAN)", (b.text or "").strip(), re.I)
                    for b in ir.blocks
                )
                if has_early_front:
                    add_finding(
                        "NUM-001",
                        "finding.num.front_roman",
                        actual="Bagian awal dan bab isi tergabung dalam satu Section",
                        expected="Section terpisah dengan format lowerRoman untuk Bagian Awal",
                        section_index=sect.index,
                    )

            # NUM-005: Cover unnumbered
            if is_cover_sec and pg_cfg.get("cover", {}).get("numbered") is False:
                if sect.page_number_position != "none" and not (
                    sect.different_first_page and sect.first_page_number_position == "none"
                ):
                    add_finding(
                        "NUM-005",
                        "finding.num.cover_unnumbered",
                        actual=sect.page_number_position,
                        expected="Tidak bernomor (none)",
                        section_index=sect.index,
                    )

            # NUM-001 & NUM-003 on Front Matter
            elif has_front:
                fm_cfg = pg_cfg.get("front_matter", {})
                exp_fmt = fm_cfg.get("format", "lowerRoman")
                exp_pos = fm_cfg.get("position", "bottom_center")
                if sect.pg_num_format != exp_fmt:
                    add_finding(
                        "NUM-001",
                        "finding.num.front_roman",
                        actual=sect.pg_num_format or "decimal (default)",
                        expected=exp_fmt,
                        section_index=sect.index,
                    )
                if sect.page_number_position != exp_pos:
                    add_finding(
                        "NUM-003",
                        "finding.num.position",
                        actual=sect.page_number_position,
                        expected=exp_pos,
                        section_index=sect.index,
                    )

            # NUM-002, NUM-003, NUM-004 on Body
            elif has_body:
                body_cfg = pg_cfg.get("body", {})
                exp_fmt = body_cfg.get("format", "decimal")
                exp_start = int(body_cfg.get("start", 1))
                exp_pos = body_cfg.get("position", "top_right")
                first_pg_cfg = body_cfg.get("chapter_first_page", {})
                exp_first_pos = first_pg_cfg.get("position")

                if sect.pg_num_format not in (exp_fmt, None) or (
                    not first_body_checked and sect.pg_num_format != exp_fmt
                ):
                    add_finding(
                        "NUM-002",
                        "finding.num.body_arabic",
                        actual=f"fmt={sect.pg_num_format}, start={sect.pg_num_start}",
                        expected=f"fmt={exp_fmt}, start={exp_start}",
                        section_index=sect.index,
                    )
                elif not first_body_checked and sect.pg_num_start != exp_start:
                    add_finding(
                        "NUM-002",
                        "finding.num.body_arabic",
                        actual=f"start={sect.pg_num_start}",
                        expected=f"start={exp_start}",
                        section_index=sect.index,
                    )
                first_body_checked = True

                if sect.page_number_position != exp_pos:
                    add_finding(
                        "NUM-003",
                        "finding.num.position",
                        actual=sect.page_number_position,
                        expected=exp_pos,
                        section_index=sect.index,
                    )

                if section_has_chapter.get(sect.index, False) and exp_first_pos:
                    if not (
                        sect.different_first_page
                        and sect.first_page_number_position == exp_first_pos
                    ):
                        add_finding(
                            "NUM-004",
                            "finding.num.chapter_first",
                            actual=(
                                f"differentFirstPage={sect.different_first_page}, "
                                f"pos={sect.first_page_number_position}"
                            ),
                            expected=f"differentFirstPage=True, pos={exp_first_pos}",
                            section_index=sect.index,
                        )

    def _evaluate_toc_lof_lot(
        self,
        ir: DocumentIR,
        profile: RuleProfile,
        resolver: StyleHierarchyResolver,
        has_fig_captions: bool,
        has_tbl_captions: bool,
        add_finding: Any,
    ) -> None:
        toc_cfg = profile.toc
        if not toc_cfg:
            return

        has_thesis_structure = any(
            b.assigned_role in ("front_title", "chapter_label") for b in ir.blocks
        )
        toc_fields: list[tuple[DocumentBlock, str]] = []
        lof_fields: list[tuple[DocumentBlock, str]] = []
        lot_fields: list[tuple[DocumentBlock, str]] = []
        typed_toc_blocks: list[DocumentBlock] = []

        for b in ir.blocks:
            for f in b.fields:
                if f.field_type == "TOC":
                    instr_up = f.instr.upper()
                    if '"GAMBAR"' in instr_up or "GAMBAR" in instr_up:
                        lof_fields.append((b, f.instr))
                    elif '"TABEL"' in instr_up or "TABEL" in instr_up:
                        lot_fields.append((b, f.instr))
                    else:
                        toc_fields.append((b, f.instr))
            if b.assigned_role == "toc_entry" and not any(f.field_type == "TOC" for f in b.fields):
                typed_toc_blocks.append(b)

        # TOC-002: Typed TOC detected
        if typed_toc_blocks:
            first_tb = typed_toc_blocks[0]
            add_finding(
                "TOC-002",
                "finding.toc.typed",
                actual=f"{len(typed_toc_blocks)} baris daftar isi ketikan manual",
                expected="Field TOC otomatis Word",
                section_index=first_tb.section_index,
                block_index=first_tb.index,
                approx_page=first_tb.approx_page,
                excerpt=first_tb.text,
            )

        # TOC-001: TOC exists
        if has_thesis_structure and not toc_fields and not typed_toc_blocks:
            add_finding(
                "TOC-001",
                "finding.toc.missing",
                actual="Tidak ada Daftar Isi",
                expected=f"Field TOC ({toc_cfg.get('title', 'DAFTAR ISI')})",
                section_index=0,
                block_index=0,
            )

        if toc_fields:
            toc_block, instr = toc_fields[0]
            exp_levels = int(toc_cfg.get("levels", 3))
            m_lvl = re.search(r'\\o\s*"1-(\d+)"', instr)
            actual_levels = int(m_lvl.group(1)) if m_lvl else 3
            # TOC-003: Levels match profile
            if actual_levels != exp_levels:
                add_finding(
                    "TOC-003",
                    "finding.toc.levels",
                    actual=f"1-{actual_levels}",
                    expected=f"1-{exp_levels}",
                    section_index=toc_block.section_index,
                    block_index=toc_block.index,
                )

            # TOC-004: updateFields enabled in settings.xml
            if not ir.has_update_fields:
                add_finding(
                    "TOC-004",
                    "finding.toc.not_synced",
                    actual="updateFields=false",
                    expected="updateFields=true",
                    section_index=toc_block.section_index,
                    block_index=toc_block.index,
                )

            # TOC-005: Leader dots and right-aligned tab in TOC styles if TOC1 exists
            if toc_cfg.get("right_align_page_numbers", True):
                toc1_style = resolver._style_map.get("TOC1")
                if toc1_style is not None:
                    pPr = toc1_style.find(qn("w:pPr"))
                    tabs = pPr.find(qn("w:tabs")) if pPr is not None else None
                    has_dot_right_tab = False
                    if tabs is not None:
                        for tab in tabs.findall(qn("w:tab")):
                            if tab.get(qn("w:val")) == "right" and tab.get(qn("w:leader")) in (
                                "dot",
                                "dots",
                            ):
                                has_dot_right_tab = True
                                break
                    if not has_dot_right_tab:
                        add_finding(
                            "TOC-005",
                            "finding.toc.entry_format",
                            actual="Style TOC1 belum memiliki tab kanan dengan titik pemandu",
                            expected="w:tab val=right leader=dot",
                            section_index=toc_block.section_index,
                            block_index=toc_block.index,
                        )

        # LOF-001 & LOT-001
        has_lof_heading = any(
            b.assigned_role == "front_title" and "DAFTAR GAMBAR" in (b.text or "").upper()
            for b in ir.blocks
        )
        if (
            toc_cfg.get("list_of_figures", {}).get("enabled")
            and has_fig_captions
            and (has_thesis_structure or has_lof_heading)
            and not lof_fields
        ):
            add_finding(
                "LOF-001",
                "finding.lof.missing",
                actual="Tidak ada field Daftar Gambar",
                expected='Field TOC \\h \\z \\c "Gambar"',
                section_index=0,
                block_index=0,
            )

        has_lot_heading = any(
            b.assigned_role == "front_title" and "DAFTAR TABEL" in (b.text or "").upper()
            for b in ir.blocks
        )
        if (
            toc_cfg.get("list_of_tables", {}).get("enabled")
            and has_tbl_captions
            and (has_thesis_structure or has_lot_heading)
            and not lot_fields
        ):
            add_finding(
                "LOT-001",
                "finding.lot.missing",
                actual="Tidak ada field Daftar Tabel",
                expected='Field TOC \\h \\z \\c "Tabel"',
                section_index=0,
                block_index=0,
            )

    def _evaluate_structure(
        self,
        ir: DocumentIR,
        profile: RuleProfile,
        formats: dict[int, EffectiveFormat],
        add_finding: Any,
    ) -> None:
        struct_cfg = profile.structure
        if not struct_cfg or "sections" not in struct_cfg:
            return

        # Only evaluate structure if the document has at least one thesis heading (chapter_label or front_title)
        has_thesis_headings = any(
            b.assigned_role in ("front_title", "chapter_label", "cover") for b in ir.blocks
        )
        if not has_thesis_headings:
            return

        spec_sections: list[dict[str, Any]] = struct_cfg["sections"]
        matched_positions: dict[str, DocumentBlock] = {}

        for b in ir.blocks:
            if b.block_type != "paragraph":
                continue
            txt = re.sub(r"[ \t\u00a0]+", " ", (b.text or "")).strip()
            if not txt:
                continue
            first_line = txt.splitlines()[0].strip()
            for sdef in spec_sections:
                sid = sdef["id"]
                if sid in matched_positions:
                    continue
                pattern = sdef["match"]
                if re.match(pattern, first_line, re.IGNORECASE) or re.match(
                    pattern, txt, re.IGNORECASE
                ):
                    matched_positions[sid] = b

        # STR-001 & STR-003: Missing required sections / chapters
        for sdef in spec_sections:
            sid = sdef["id"]
            if sdef.get("required") and sid not in matched_positions:
                if sid.startswith("chapter_"):
                    add_finding(
                        "STR-003",
                        "finding.str.missing_chapters",
                        actual="Tidak ditemukan",
                        expected=sdef["id"].upper().replace("_", " "),
                        section_index=0,
                        block_index=0,
                    )
                else:
                    add_finding(
                        "STR-001",
                        "finding.str.missing_section",
                        actual="Tidak ditemukan",
                        expected=sdef["match"].strip("^$").replace("\\s+", " "),
                        section_index=0,
                        block_index=0,
                    )

        # STR-002: Enforce order
        if struct_cfg.get("enforce_order", True):
            for spec_idx, sdef in enumerate(spec_sections):
                sid = sdef["id"]
                if sid not in matched_positions:
                    continue
                blk = matched_positions[sid]
                # Compare block order against all previously matched sections
                for prev_spec_idx in range(spec_idx + 1, len(spec_sections)):
                    later_sid = spec_sections[prev_spec_idx]["id"]
                    if later_sid in matched_positions:
                        later_blk = matched_positions[later_sid]
                        if later_blk.index < blk.index:
                            add_finding(
                                "STR-002",
                                "finding.str.wrong_order",
                                actual=later_blk.text.splitlines()[0].strip(),
                                expected=blk.text.splitlines()[0].strip(),
                                section_index=later_blk.section_index,
                                block_index=later_blk.index,
                                approx_page=later_blk.approx_page,
                            )

        # STR-004: Required section starts on a new page
        for sdef in spec_sections:
            sid = sdef["id"]
            if sid == "cover" or not sdef.get("new_page", True) or sid not in matched_positions:
                continue
            blk = matched_positions[sid]
            if blk.assigned_role == "chapter_label":
                # Already checked by HEAD-005
                continue
            fmt = formats.get(blk.index)
            starts_new_page = (
                blk.index == 0
                or (fmt is not None and fmt.page_break_before)
                or blk.has_page_break_run
                or (
                    blk.index > 0
                    and ir.blocks[blk.index - 1].section_index != blk.section_index
                    and ir.sections[blk.section_index].section_start_type == "nextPage"
                )
                or (blk.index > 0 and ir.blocks[blk.index - 1].has_page_break_run)
            )
            if not starts_new_page:
                add_finding(
                    "STR-004",
                    "finding.str.new_page",
                    actual=blk.text.splitlines()[0].strip(),
                    expected="Mulai pada halaman baru (pageBreakBefore)",
                    section_index=blk.section_index,
                    block_index=blk.index,
                    approx_page=blk.approx_page,
                )


rule_evaluator = RuleEvaluator()
