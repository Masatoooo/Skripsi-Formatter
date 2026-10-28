from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from docx.oxml.ns import qn

from app.core.units import (
    half_points_to_pt,
    twips_to_cm,
    twips_to_pt,
    wline_to_line_spacing_multiplier,
)
from app.core.xml_helpers import parse_boolean_el


@dataclass
class EffectiveFormat:
    # Font / Run properties
    font_family: str = "Times New Roman"
    font_ascii: str | None = None
    font_hAnsi: str | None = None
    font_cs: str | None = None
    font_eastAsia: str | None = None
    font_size_pt: float = 12.0
    color_hex: str = "000000"
    bold: bool = False
    italic: bool = False
    all_caps: bool = False

    # Run consistency tracking (for FONT-004 stray fonts, etc.)
    run_fonts: list[str] = field(default_factory=list)
    run_sizes_pt: list[float] = field(default_factory=list)
    run_colors: list[str] = field(default_factory=list)
    has_direct_run_font: bool = False
    has_direct_run_size: bool = False
    has_direct_run_color: bool = False

    # Paragraph properties
    alignment: str = "left"  # "left" | "center" | "right" | "justify"
    line_spacing: float = 1.0  # multiplier (e.g., 1.0, 1.5, 2.0)
    line_spacing_rule: str = "auto"  # "auto" | "exact" | "atLeast"
    space_before_pt: float = 0.0
    space_after_pt: float = 0.0
    left_indent_cm: float = 0.0
    right_indent_cm: float = 0.0
    first_line_indent_cm: float = 0.0
    hanging_indent_cm: float = 0.0
    keep_with_next: bool = False
    page_break_before: bool = False
    widow_control: bool = True
    outline_level: int | None = None
    num_id: int | None = None
    ilvl: int | None = None


def _normalize_alignment(jc_val: str | None) -> str | None:
    if not jc_val:
        return None
    val = jc_val.lower()
    if val in ("both", "distribute", "justify"):
        return "justify"
    if val in ("start", "left"):
        return "left"
    if val in ("end", "right"):
        return "right"
    if val == "center":
        return "center"
    return "left"


class StyleHierarchyResolver:
    """Resolves effective formatting across direct properties, style chains, and docDefaults."""

    def __init__(self, doc: Any) -> None:
        self.doc = doc
        self.styles_el = doc.styles.element
        self._style_map: dict[str, Any] = {}
        self._default_para_style_id: str = "Normal"

        for s in self.styles_el.findall(qn("w:style")):
            sid = s.get(qn("w:styleId"))
            if sid:
                self._style_map[sid] = s
                if (
                    s.get(qn("w:type")) == "paragraph"
                    and parse_boolean_el(s) is None
                    and s.get(qn("w:default")) in ("1", "true")
                ):
                    self._default_para_style_id = sid

        self.doc_defaults_pPr: Any = None
        self.doc_defaults_rPr: Any = None
        doc_defaults = self.styles_el.find(qn("w:docDefaults"))
        if doc_defaults is not None:
            pPrDef = doc_defaults.find(qn("w:pPrDefault"))
            if pPrDef is not None:
                self.doc_defaults_pPr = pPrDef.find(qn("w:pPr"))
            rPrDef = doc_defaults.find(qn("w:rPrDefault"))
            if rPrDef is not None:
                self.doc_defaults_rPr = rPrDef.find(qn("w:rPr"))

    def get_style_chain(self, style_id: str | None) -> list[Any]:
        """Returns list of `w:style` elements from most specific (child) to root (`basedOn`)."""
        chain: list[Any] = []
        visited: set[str] = set()
        curr_id: str | None = style_id or self._default_para_style_id

        while curr_id and curr_id not in visited:
            visited.add(curr_id)
            st_el = self._style_map.get(curr_id)
            if st_el is None:
                break
            chain.append(st_el)
            based_on = st_el.find(qn("w:basedOn"))
            curr_id = based_on.get(qn("w:val")) if based_on is not None else None

        # Ensure default paragraph style is at the end of the chain if not already visited
        if (
            self._default_para_style_id not in visited
            and self._default_para_style_id in self._style_map
        ):
            chain.append(self._style_map[self._default_para_style_id])

        return chain

    @staticmethod
    def _extract_pPr_dict(pPr: Any) -> dict[str, Any]:
        res: dict[str, Any] = {}
        if pPr is None:
            return res

        jc = pPr.find(qn("w:jc"))
        if jc is not None:
            norm_jc = _normalize_alignment(jc.get(qn("w:val")))
            if norm_jc:
                res["alignment"] = norm_jc

        spacing = pPr.find(qn("w:spacing"))
        if spacing is not None:
            before = spacing.get(qn("w:before"))
            if before is not None and str(before).lstrip("-").isdigit():
                res["space_before_pt"] = twips_to_pt(int(before))
            after = spacing.get(qn("w:after"))
            if after is not None and str(after).lstrip("-").isdigit():
                res["space_after_pt"] = twips_to_pt(int(after))
            line = spacing.get(qn("w:line"))
            line_rule = spacing.get(qn("w:lineRule")) or "auto"
            if line is not None and str(line).lstrip("-").isdigit():
                line_int = int(line)
                res["line_spacing_rule"] = line_rule
                if line_rule == "auto":
                    res["line_spacing"] = wline_to_line_spacing_multiplier(line_int)
                else:
                    # Convert twips to approximate multiplier against 12pt (240 twips)
                    res["line_spacing"] = wline_to_line_spacing_multiplier(line_int)

        ind = pPr.find(qn("w:ind"))
        if ind is not None:
            left = ind.get(qn("w:left")) or ind.get(qn("w:start"))
            if left is not None and str(left).lstrip("-").isdigit():
                res["left_indent_cm"] = twips_to_cm(int(left))
            right = ind.get(qn("w:right")) or ind.get(qn("w:end"))
            if right is not None and str(right).lstrip("-").isdigit():
                res["right_indent_cm"] = twips_to_cm(int(right))
            hanging = ind.get(qn("w:hanging"))
            first_line = ind.get(qn("w:firstLine"))
            if hanging is not None and str(hanging).lstrip("-").isdigit():
                res["hanging_indent_cm"] = twips_to_cm(int(hanging))
                res["first_line_indent_cm"] = 0.0
            elif first_line is not None and str(first_line).lstrip("-").isdigit():
                res["first_line_indent_cm"] = twips_to_cm(int(first_line))
                res["hanging_indent_cm"] = 0.0

        keep_next = parse_boolean_el(pPr.find(qn("w:keepNext")))
        if keep_next is not None:
            res["keep_with_next"] = keep_next

        pg_break = parse_boolean_el(pPr.find(qn("w:pageBreakBefore")))
        if pg_break is not None:
            res["page_break_before"] = pg_break

        widow = parse_boolean_el(pPr.find(qn("w:widowControl")))
        if widow is not None:
            res["widow_control"] = widow

        outline = pPr.find(qn("w:outlineLvl"))
        if outline is not None:
            ov = outline.get(qn("w:val"))
            if ov is not None and str(ov).isdigit():
                res["outline_level"] = int(ov)

        numPr = pPr.find(qn("w:numPr"))
        if numPr is not None:
            numId_el = numPr.find(qn("w:numId"))
            ilvl_el = numPr.find(qn("w:ilvl"))
            if (
                numId_el is not None
                and numId_el.get(qn("w:val"))
                and str(numId_el.get(qn("w:val"))).isdigit()
            ):
                nid = int(numId_el.get(qn("w:val")))
                if nid > 0:
                    res["num_id"] = nid
            if (
                ilvl_el is not None
                and ilvl_el.get(qn("w:val"))
                and str(ilvl_el.get(qn("w:val"))).isdigit()
            ):
                res["ilvl"] = int(ilvl_el.get(qn("w:val")))

        return res

    @staticmethod
    def _extract_rPr_dict(rPr: Any) -> dict[str, Any]:
        res: dict[str, Any] = {}
        if rPr is None:
            return res

        rFonts = rPr.find(qn("w:rFonts"))
        if rFonts is not None:
            ascii_f = rFonts.get(qn("w:ascii"))
            hAnsi_f = rFonts.get(qn("w:hAnsi"))
            cs_f = rFonts.get(qn("w:cs"))
            ea_f = rFonts.get(qn("w:eastAsia"))
            if ascii_f:
                res["font_ascii"] = ascii_f
                res["font_family"] = ascii_f
            elif hAnsi_f:
                res["font_family"] = hAnsi_f
            if hAnsi_f:
                res["font_hAnsi"] = hAnsi_f
            if cs_f:
                res["font_cs"] = cs_f
            if ea_f:
                res["font_eastAsia"] = ea_f

        sz = rPr.find(qn("w:sz"))
        if sz is not None:
            val = sz.get(qn("w:val"))
            if val is not None and str(val).isdigit():
                res["font_size_pt"] = half_points_to_pt(int(val))

        color = rPr.find(qn("w:color"))
        if color is not None:
            cval = color.get(qn("w:val"))
            if cval:
                res["color_hex"] = "000000" if cval.lower() == "auto" else cval.upper()

        b_val = parse_boolean_el(rPr.find(qn("w:b")))
        if b_val is not None:
            res["bold"] = b_val

        i_val = parse_boolean_el(rPr.find(qn("w:i")))
        if i_val is not None:
            res["italic"] = i_val

        caps_val = parse_boolean_el(rPr.find(qn("w:caps")))
        if caps_val is not None:
            res["all_caps"] = caps_val

        return res

    def resolve_paragraph(
        self, p_element: Any, table_style_id: str | None = None
    ) -> EffectiveFormat:
        """Computes the effective format of a `w:p` element."""
        fmt = EffectiveFormat()

        pPr = p_element.find(qn("w:pPr"))
        style_id: str | None = None
        if pPr is not None:
            pStyle = pPr.find(qn("w:pStyle"))
            if pStyle is not None:
                style_id = pStyle.get(qn("w:val"))

        # Build hierarchy from lowest priority (docDefaults) to highest (direct pPr)
        p_layers: list[dict[str, Any]] = []
        r_layers: list[dict[str, Any]] = []

        if self.doc_defaults_pPr is not None:
            p_layers.append(self._extract_pPr_dict(self.doc_defaults_pPr))
        if self.doc_defaults_rPr is not None:
            r_layers.append(self._extract_rPr_dict(self.doc_defaults_rPr))

        if table_style_id and table_style_id in self._style_map:
            t_style = self._style_map[table_style_id]
            p_layers.append(self._extract_pPr_dict(t_style.find(qn("w:pPr"))))
            r_layers.append(self._extract_rPr_dict(t_style.find(qn("w:rPr"))))

        # Style chain from root to child
        style_chain = list(reversed(self.get_style_chain(style_id)))
        for st_el in style_chain:
            p_layers.append(self._extract_pPr_dict(st_el.find(qn("w:pPr"))))
            r_layers.append(self._extract_rPr_dict(st_el.find(qn("w:rPr"))))

        # Direct pPr and pPr/rPr
        if pPr is not None:
            p_layers.append(self._extract_pPr_dict(pPr))
            r_layers.append(self._extract_rPr_dict(pPr.find(qn("w:rPr"))))

        # Merge paragraph properties
        merged_p: dict[str, Any] = {}
        for layer in p_layers:
            merged_p.update(layer)

        # Merge base run properties (from docDefaults -> style -> pPr/rPr)
        merged_r: dict[str, Any] = {}
        for layer in r_layers:
            merged_r.update(layer)

        for k, v in merged_p.items():
            setattr(fmt, k, v)
        for k, v in merged_r.items():
            setattr(fmt, k, v)

        # Inspect non-empty visible runs inside the paragraph
        runs = p_element.findall(qn("w:r"))
        visible_run_dicts: list[dict[str, Any]] = []
        for r in runs:
            if r.find(qn("w:fldChar")) is not None or r.find(qn("w:instrText")) is not None:
                continue
            rPr = r.find(qn("w:rPr"))
            if rPr is not None and parse_boolean_el(rPr.find(qn("w:vanish"))) is True:
                continue
            # Check if run has visible text
            run_text = "".join(t.text or "" for t in r.findall(qn("w:t")))
            if not run_text.strip():
                continue

            # Resolve character style if present
            char_layer: dict[str, Any] = {}
            if rPr is not None:
                rStyle = rPr.find(qn("w:rStyle"))
                if rStyle is not None and rStyle.get(qn("w:val")) in self._style_map:
                    c_style = self._style_map[rStyle.get(qn("w:val"))]
                    char_layer = self._extract_rPr_dict(c_style.find(qn("w:rPr")))

            direct_r = self._extract_rPr_dict(rPr)
            if "font_family" in direct_r:
                fmt.has_direct_run_font = True
            if "font_size_pt" in direct_r:
                fmt.has_direct_run_size = True
            if "color_hex" in direct_r:
                fmt.has_direct_run_color = True

            eff_r = dict(merged_r)
            eff_r.update(char_layer)
            eff_r.update(direct_r)
            visible_run_dicts.append(eff_r)

        if visible_run_dicts:
            first_r = visible_run_dicts[0]
            fmt.font_family = first_r.get("font_family", fmt.font_family)
            fmt.font_ascii = first_r.get("font_ascii", fmt.font_ascii)
            fmt.font_hAnsi = first_r.get("font_hAnsi", fmt.font_hAnsi)
            fmt.font_cs = first_r.get("font_cs", fmt.font_cs)
            fmt.font_eastAsia = first_r.get("font_eastAsia", fmt.font_eastAsia)
            fmt.font_size_pt = float(first_r.get("font_size_pt", fmt.font_size_pt))
            fmt.color_hex = str(first_r.get("color_hex", fmt.color_hex))

            # Bold, italic, all_caps are True on the paragraph if True across all visible runs
            fmt.bold = all(bool(rd.get("bold", fmt.bold)) for rd in visible_run_dicts)
            fmt.italic = all(bool(rd.get("italic", fmt.italic)) for rd in visible_run_dicts)
            fmt.all_caps = all(bool(rd.get("all_caps", fmt.all_caps)) for rd in visible_run_dicts)

            for rd in visible_run_dicts:
                ff = str(rd.get("font_family", fmt.font_family))
                if ff not in fmt.run_fonts:
                    fmt.run_fonts.append(ff)
                fs = float(rd.get("font_size_pt", fmt.font_size_pt))
                if fs not in fmt.run_sizes_pt:
                    fmt.run_sizes_pt.append(fs)
                fc = str(rd.get("color_hex", fmt.color_hex))
                if fc not in fmt.run_colors:
                    fmt.run_colors.append(fc)
        else:
            fmt.run_fonts = [fmt.font_family]
            fmt.run_sizes_pt = [fmt.font_size_pt]
            fmt.run_colors = [fmt.color_hex]

        return fmt
