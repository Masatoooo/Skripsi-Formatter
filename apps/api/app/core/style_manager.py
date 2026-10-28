from __future__ import annotations

from typing import Any

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.core.rules.models import RuleProfile
from app.core.units import (
    cm_to_twips,
    line_spacing_multiplier_to_wline,
    pt_to_half_points,
    pt_to_twips,
)
from app.core.xml_helpers import (
    PPR_ORDER,
    RPR_ORDER,
    get_or_add_ordered,
    get_or_add_pPr,
    set_boolean_prop,
    set_color_on_rPr,
    set_font_family_on_rPr,
    set_font_size_on_rPr,
    set_w_val,
)

ROLE_TO_STYLE_ID: dict[str, tuple[str, str, int | None]] = {
    "body": ("Normal", "Normal", None),
    "chapter_label": ("Heading1", "heading 1", 0),
    "chapter_title": ("SkripsiChapterTitle", "Skripsi Chapter Title", 0),
    "front_title": ("SkripsiFrontTitle", "Skripsi Front Title", 0),
    "heading_2": ("Heading2", "heading 2", 1),
    "heading_3": ("Heading3", "heading 3", 2),
    "heading_4": ("Heading4", "heading 4", 3),
    "caption_figure": ("Caption", "caption", None),
    "caption_table": ("SkripsiCaptionTable", "Skripsi Caption Table", None),
    "block_quote": ("Quote", "Quote", None),
    "bibliography_entry": ("Bibliography", "Bibliography", None),
    "table_text": ("SkripsiTableText", "Skripsi Table Text", None),
}


def apply_role_spec_to_pPr_and_rPr(
    pPr: Any,
    rPr: Any,
    role_spec: dict[str, Any],
    profile: RuleProfile,
    outline_lvl: int | None = None,
) -> None:
    """Writes formatting properties from `role_spec` and `profile.text` onto `w:pPr` and `w:rPr`."""
    # Font properties
    font_family = str(role_spec.get("font_family", profile.text.font_family))
    font_size_pt = float(role_spec.get("font_size_pt", profile.text.font_size_pt))
    color_hex = str(role_spec.get("color_hex", profile.text.color_hex))

    set_font_family_on_rPr(rPr, font_family)
    set_font_size_on_rPr(rPr, pt_to_half_points(font_size_pt))
    set_color_on_rPr(rPr, color_hex)

    if "bold" in role_spec:
        b_flag = bool(role_spec["bold"])
        set_boolean_prop(rPr, "b", b_flag, RPR_ORDER)
        set_boolean_prop(rPr, "bCs", b_flag, RPR_ORDER)
    else:
        set_boolean_prop(rPr, "b", False, RPR_ORDER)
        set_boolean_prop(rPr, "bCs", False, RPR_ORDER)

    if "italic" in role_spec:
        i_flag = bool(role_spec["italic"])
        set_boolean_prop(rPr, "i", i_flag, RPR_ORDER)
        set_boolean_prop(rPr, "iCs", i_flag, RPR_ORDER)

    if "all_caps" in role_spec:
        set_boolean_prop(rPr, "caps", bool(role_spec["all_caps"]), RPR_ORDER)

    # Alignment
    if "alignment" in role_spec:
        al = str(role_spec["alignment"])
        jc_val = "both" if al == "justify" else al
        set_w_val(pPr, "jc", jc_val, PPR_ORDER)

    # Spacing
    spacing = get_or_add_ordered(pPr, "spacing", PPR_ORDER)
    before_pt = float(role_spec.get("space_before_pt", 0.0))
    after_pt = float(role_spec.get("space_after_pt", 0.0))
    line_mult = float(role_spec.get("line_spacing", 1.5))
    spacing.set(qn("w:before"), str(pt_to_twips(before_pt)))
    spacing.set(qn("w:after"), str(pt_to_twips(after_pt)))
    spacing.set(qn("w:line"), str(line_spacing_multiplier_to_wline(line_mult)))
    spacing.set(qn("w:lineRule"), "auto")

    # Indentation
    ind = get_or_add_ordered(pPr, "ind", PPR_ORDER)
    left_cm = float(role_spec.get("left_indent_cm", 0.0))
    right_cm = float(role_spec.get("right_indent_cm", 0.0))
    first_cm = float(role_spec.get("first_line_indent_cm", 0.0))
    hanging_cm = float(role_spec.get("hanging_indent_cm", 0.0))

    ind.set(qn("w:left"), str(cm_to_twips(left_cm)))
    ind.set(qn("w:right"), str(cm_to_twips(right_cm)))
    if hanging_cm > 0:
        if qn("w:firstLine") in ind.attrib:
            del ind.attrib[qn("w:firstLine")]
        ind.set(qn("w:hanging"), str(cm_to_twips(hanging_cm)))
    else:
        if qn("w:hanging") in ind.attrib:
            del ind.attrib[qn("w:hanging")]
        ind.set(qn("w:firstLine"), str(cm_to_twips(first_cm)))

    # Pagination flags
    if "keep_with_next" in role_spec:
        set_boolean_prop(pPr, "keepNext", bool(role_spec["keep_with_next"]), PPR_ORDER)
    if "page_break_before" in role_spec:
        set_boolean_prop(pPr, "pageBreakBefore", bool(role_spec["page_break_before"]), PPR_ORDER)

    set_boolean_prop(pPr, "widowControl", True, PPR_ORDER)

    if outline_lvl is not None:
        set_w_val(pPr, "outlineLvl", str(outline_lvl), PPR_ORDER)


def ensure_doc_defaults(doc: Any, profile: RuleProfile) -> None:
    """Updates `w:docDefaults` in `styles.xml` to match profile base font and size."""
    styles_el = doc.styles.element
    doc_defaults = styles_el.find(qn("w:docDefaults"))
    if doc_defaults is None:
        doc_defaults = OxmlElement("w:docDefaults")
        styles_el.insert(0, doc_defaults)

    rPrDef = doc_defaults.find(qn("w:rPrDefault"))
    if rPrDef is None:
        rPrDef = OxmlElement("w:rPrDefault")
        doc_defaults.insert(0, rPrDef)

    rPr = rPrDef.find(qn("w:rPr"))
    if rPr is None:
        rPr = OxmlElement("w:rPr")
        rPrDef.append(rPr)

    set_font_family_on_rPr(rPr, profile.text.font_family)
    set_font_size_on_rPr(rPr, pt_to_half_points(profile.text.font_size_pt))
    set_color_on_rPr(rPr, profile.text.color_hex)


def ensure_style_for_role(doc: Any, role: str, profile: RuleProfile) -> str:
    """Ensures a paragraph style exists in `styles.xml` configured for `role` and returns its `styleId`."""
    style_id, style_name, outline_lvl = ROLE_TO_STYLE_ID.get(role, ("Normal", "Normal", None))
    role_spec = dict(profile.roles.get(role, {}))
    if role == "front_title" and not role_spec:
        role_spec = dict(profile.roles.get("chapter_title", {}))

    styles_el = doc.styles.element
    target_style = None
    for st in styles_el.findall(qn("w:style")):
        if st.get(qn("w:styleId")) == style_id:
            target_style = st
            break

    if target_style is None:
        target_style = OxmlElement("w:style")
        target_style.set(qn("w:type"), "paragraph")
        target_style.set(qn("w:styleId"), style_id)
        name_el = OxmlElement("w:name")
        name_el.set(qn("w:val"), style_name)
        target_style.append(name_el)
        if style_id != "Normal":
            based_on = OxmlElement("w:basedOn")
            based_on.set(qn("w:val"), "Normal")
            target_style.append(based_on)
        styles_el.append(target_style)

    pPr = target_style.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        target_style.append(pPr)

    rPr = target_style.find(qn("w:rPr"))
    if rPr is None:
        rPr = OxmlElement("w:rPr")
        target_style.append(rPr)

    apply_role_spec_to_pPr_and_rPr(pPr, rPr, role_spec, profile, outline_lvl=outline_lvl)
    return style_id


def assign_style_to_paragraph(p_element: Any, style_id: str) -> None:
    """Assigns `<w:pStyle w:val="{style_id}"/>` on `p_element` in schema order."""
    pPr = get_or_add_pPr(p_element)
    set_w_val(pPr, "pStyle", style_id, PPR_ORDER)
