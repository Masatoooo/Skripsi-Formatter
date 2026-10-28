from __future__ import annotations

import re

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.core.docx_model import DocumentIR
from app.core.fields import make_field_runs
from app.core.fixers.base import BaseFixer
from app.core.rules.models import Change, Finding, FixMethod, RuleProfile
from app.core.style_manager import assign_style_to_paragraph, ensure_style_for_role
from app.core.units import (
    line_spacing_multiplier_to_wline,
    pt_to_twips,
)
from app.core.xml_helpers import (
    PPR_ORDER,
    get_or_add_ordered,
    get_or_add_pPr,
    set_boolean_prop,
    set_w_val,
)


class CaptionFixer(BaseFixer):
    """Fixes caption position, style/format, SEQ field conversion, and sequential numbering."""

    category = "CAP"

    def __init__(self) -> None:
        self.replaced_pairs: list[tuple[str, str]] = []

    def apply(
        self,
        ir: DocumentIR,
        findings: list[Finding],
        profile: RuleProfile,
    ) -> list[Change]:
        cap_findings = [f for f in findings if f.category == "CAP"]
        if not cap_findings:
            return []

        ensured_roles: dict[str, str] = {}
        changes: list[Change] = []

        for f in cap_findings:
            blk_idx = f.location.block_index
            if blk_idx < 0 or blk_idx >= len(ir.blocks):
                continue
            block = ir.blocks[blk_idx]
            if block.block_type != "paragraph" or block.has_tracked_changes:
                continue

            role = block.assigned_role or "caption_figure"
            is_fig = role == "caption_figure"
            role_spec = profile.roles.get(role, {})
            cap_cfg = profile.captions.get("figure" if is_fig else "table", {})
            label = str(cap_cfg.get("label", "Gambar" if is_fig else "Tabel"))

            if role not in ensured_roles:
                ensured_roles[role] = ensure_style_for_role(ir.doc, role, profile)
            style_id = ensured_roles[role]

            p_el = block.raw_element
            pPr = get_or_add_pPr(p_el)

            if f.rule_id == "CAP-002":
                exp_pos = cap_cfg.get("position", "below" if is_fig else "above")
                prev_b = ir.blocks[blk_idx - 1] if blk_idx > 0 else None
                next_b = ir.blocks[blk_idx + 1] if blk_idx + 1 < len(ir.blocks) else None

                if is_fig and exp_pos == "below" and next_b and next_b.images:
                    next_b.raw_element.addnext(p_el)
                    changes.append(
                        Change(
                            finding_id=f.id,
                            rule_id=f.rule_id,
                            location=f.location,
                            old_value=f.actual,
                            new_value="di bawah gambar (below)",
                            method=FixMethod.DIRECT,
                        )
                    )
                elif not is_fig and exp_pos == "above" and prev_b and prev_b.block_type == "table":
                    prev_b.raw_element.addprevious(p_el)
                    changes.append(
                        Change(
                            finding_id=f.id,
                            rule_id=f.rule_id,
                            location=f.location,
                            old_value=f.actual,
                            new_value="di atas tabel (above)",
                            method=FixMethod.DIRECT,
                        )
                    )

            elif f.rule_id == "CAP-003":
                assign_style_to_paragraph(p_el, style_id)
                block.style_id = style_id
                exp_al = str(role_spec.get("alignment", "center"))
                jc_val = "both" if exp_al == "justify" else exp_al
                set_w_val(pPr, "jc", jc_val, PPR_ORDER)

                spacing = get_or_add_ordered(pPr, "spacing", PPR_ORDER)
                spacing.set(
                    qn("w:before"), str(pt_to_twips(float(role_spec.get("space_before_pt", 6.0))))
                )
                spacing.set(
                    qn("w:after"), str(pt_to_twips(float(role_spec.get("space_after_pt", 6.0))))
                )
                spacing.set(
                    qn("w:line"),
                    str(
                        line_spacing_multiplier_to_wline(float(role_spec.get("line_spacing", 1.0)))
                    ),
                )
                spacing.set(qn("w:lineRule"), "auto")

                if role_spec.get("keep_with_next"):
                    set_boolean_prop(pPr, "keepNext", True, PPR_ORDER)

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

            elif f.rule_id == "CAP-004":
                # Convert typed caption number into a SEQ field preserving the displayed number
                self._convert_caption_to_seq_field(
                    p_el=p_el,
                    label=label,
                    numbering_mode=str(cap_cfg.get("numbering", "continuous")),
                    font_family=str(role_spec.get("font_family", profile.text.font_family)),
                    font_size_pt=float(role_spec.get("font_size_pt", 11.0)),
                    color_hex=str(role_spec.get("color_hex", profile.text.color_hex)),
                )
                changes.append(
                    Change(
                        finding_id=f.id,
                        rule_id=f.rule_id,
                        location=f.location,
                        old_value=f.actual,
                        new_value=f"Field SEQ {label}",
                        method=FixMethod.DIRECT,
                    )
                )

            elif f.rule_id == "CAP-005":
                # Update cached number to expected sequence
                m_exp = re.search(r"#(\d+)", str(f.expected))
                if m_exp:
                    new_seq_str = m_exp.group(1)
                    old_line = (block.text or "").strip()
                    self._update_caption_number_text(p_el, new_seq_str)
                    new_line = re.sub(
                        r"^(\s*(?:Gambar|Figure|Tabel|Table)\s+(?:\d+[.\-])?)\d+\b",
                        rf"\g<1>{new_seq_str}",
                        old_line,
                        count=1,
                        flags=re.IGNORECASE,
                    )
                    if old_line != new_line:
                        self.replaced_pairs.append((old_line, new_line))
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

    @staticmethod
    def _convert_caption_to_seq_field(
        p_el: object,
        label: str,
        numbering_mode: str,
        font_family: str,
        font_size_pt: float,
        color_hex: str,
    ) -> None:
        text_runs = p_el.findall(qn("w:r"))  # type: ignore[attr-defined]
        full_txt = "".join(t.text or "" for r in text_runs for t in r.findall(qn("w:t")))
        m = re.match(
            r"^(\s*(?:Gambar|Figure|Tabel|Table)\s+(?:\d+[.\-])?)(\d+)(.*)$",
            full_txt,
            re.IGNORECASE | re.DOTALL,
        )
        if not m:
            return

        prefix_str, num_str, suffix_str = m.group(1), m.group(2), m.group(3)
        for r in list(text_runs):
            p_el.remove(r)  # type: ignore[attr-defined]

        # 1. Prefix run ("Gambar " or "Gambar 1.")
        r_pre = OxmlElement("w:r")
        t_pre = OxmlElement("w:t")
        t_pre.set(qn("xml:space"), "preserve")
        t_pre.text = prefix_str
        r_pre.append(t_pre)
        p_el.append(r_pre)  # type: ignore[attr-defined]

        # 2. SEQ field runs
        seq_instr = f"SEQ {label} \\* ARABIC"
        if numbering_mode == "per_chapter":
            seq_instr += " \\s 1"
        for el in make_field_runs(
            seq_instr,
            cached_text=num_str,
            font_family=font_family,
            font_size_pt=font_size_pt,
            color_hex=color_hex,
        ):
            p_el.append(el)  # type: ignore[attr-defined]

        # 3. Suffix run (" Judul caption")
        if suffix_str:
            r_suf = OxmlElement("w:r")
            t_suf = OxmlElement("w:t")
            t_suf.set(qn("xml:space"), "preserve")
            t_suf.text = suffix_str
            r_suf.append(t_suf)
            p_el.append(r_suf)  # type: ignore[attr-defined]

    @staticmethod
    def _update_caption_number_text(p_el: object, new_seq_str: str) -> None:
        for r in p_el.findall(qn("w:r")):  # type: ignore[attr-defined]
            for t in r.findall(qn("w:t")):
                if t.text:
                    new_t, count = re.subn(
                        r"^(\s*(?:Gambar|Figure|Tabel|Table)\s+(?:\d+[.\-])?)\d+\b",
                        rf"\g<1>{new_seq_str}",
                        t.text,
                        count=1,
                        flags=re.IGNORECASE,
                    )
                    if count > 0:
                        t.text = new_t
                        return
                    if t.text.strip().isdigit():
                        t.text = new_seq_str
                        return
