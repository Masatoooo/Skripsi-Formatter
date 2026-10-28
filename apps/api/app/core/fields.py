from __future__ import annotations

import copy
from typing import Any

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from app.core.units import pt_to_half_points
from app.core.xml_helpers import (
    PPR_ORDER,
    SECTPR_ORDER,
    get_or_add_ordered,
    get_or_add_pPr,
    get_or_add_rPr,
    set_boolean_prop,
    set_color_on_rPr,
    set_font_family_on_rPr,
    set_font_size_on_rPr,
    set_w_val,
)


def make_field_runs(
    instr: str,
    cached_text: str = "",
    font_family: str | None = None,
    font_size_pt: float | None = None,
    color_hex: str | None = None,
    dirty: bool = True,
) -> list[Any]:
    """Creates the 5-run complex field sequence (`begin`, `instrText`, `separate`, `t`, `end`)."""

    def _style_run(r: Any) -> Any:
        if font_family or font_size_pt or color_hex:
            rPr = get_or_add_rPr(r)
            if font_family:
                set_font_family_on_rPr(rPr, font_family)
            if font_size_pt:
                set_font_size_on_rPr(rPr, pt_to_half_points(font_size_pt))
            if color_hex:
                set_color_on_rPr(rPr, color_hex)
        return r

    def _fld_char(kind: str, mark_dirty: bool = False) -> Any:
        r = _style_run(OxmlElement("w:r"))
        c = OxmlElement("w:fldChar")
        c.set(qn("w:fldCharType"), kind)
        if mark_dirty:
            c.set(qn("w:dirty"), "true")
        r.append(c)
        return r

    r_instr = _style_run(OxmlElement("w:r"))
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {instr.strip()} "
    r_instr.append(it)

    r_result = _style_run(OxmlElement("w:r"))
    t = OxmlElement("w:t")
    if cached_text.startswith(" ") or cached_text.endswith(" "):
        t.set(qn("xml:space"), "preserve")
    t.text = cached_text
    r_result.append(t)

    return [
        _fld_char("begin", mark_dirty=dirty),
        r_instr,
        _fld_char("separate"),
        r_result,
        _fld_char("end"),
    ]


def add_field(
    paragraph: Any,
    instr: str,
    cached_text: str = "",
    font_family: str | None = None,
    font_size_pt: float | None = None,
    color_hex: str | None = None,
) -> None:
    """Inserts a dynamic Word field (such as PAGE, TOC, or SEQ) into a paragraph or w:p element."""
    p_el = paragraph._p if hasattr(paragraph, "_p") else paragraph
    for el in make_field_runs(instr, cached_text, font_family, font_size_pt, color_hex):
        p_el.append(el)


def mark_document_update_fields_on_open(doc: Any) -> None:
    """Instructs Word to prompt and recalculate all fields (like TOC) when document is opened."""
    settings_el = doc.settings._element
    update_fields = settings_el.find(qn("w:updateFields"))
    if update_fields is None:
        update_fields = OxmlElement("w:updateFields")
        update_fields.set(qn("w:val"), "true")
        settings_el.append(update_fields)
    else:
        update_fields.set(qn("w:val"), "true")


def set_section_pg_num_type(
    sectPr: Any,
    fmt: str | None = None,
    start: int | None = None,
) -> None:
    """Configures `w:pgNumType` (`w:fmt` and `w:start`) on a `w:sectPr` element in schema order."""
    pgNumType = get_or_add_ordered(sectPr, "pgNumType", SECTPR_ORDER)
    if fmt is not None:
        pgNumType.set(qn("w:fmt"), fmt)
    if start is not None:
        pgNumType.set(qn("w:start"), str(start))
    elif qn("w:start") in pgNumType.attrib:
        del pgNumType.attrib[qn("w:start")]


def clear_header_footer_content(hf_obj: Any) -> None:
    """Clears all content from a header or footer object and unlinks it from previous."""
    if hf_obj is None:
        return
    hf_obj.is_linked_to_previous = False
    el = hf_obj._element
    for p in list(el.findall(qn("w:p"))):
        el.remove(p)
    for tbl in list(el.findall(qn("w:tbl"))):
        el.remove(tbl)
    el.append(OxmlElement("w:p"))


def set_header_footer_page_field(
    section_obj: Any,
    position: str,
    is_first_page: bool = False,
    font_family: str = "Times New Roman",
    font_size_pt: float = 12.0,
    color_hex: str = "000000",
) -> None:
    """Configures a section's header/footer (or first_page_header/footer) to display a PAGE field at `position`."""
    if is_first_page:
        section_obj.different_first_page_header_footer = True
        header = section_obj.first_page_header
        footer = section_obj.first_page_footer
    else:
        header = section_obj.header
        footer = section_obj.footer

    if position == "none":
        clear_header_footer_content(header)
        clear_header_footer_content(footer)
        return

    parts = position.lower().split("_")
    loc = parts[0] if parts else "bottom"
    align = parts[1] if len(parts) > 1 else "center"
    if align not in ("left", "center", "right"):
        align = "center"

    if loc == "top":
        clear_header_footer_content(footer)
        clear_header_footer_content(header)
        target_hf = header
    else:
        clear_header_footer_content(header)
        clear_header_footer_content(footer)
        target_hf = footer

    p_el = target_hf._element.find(qn("w:p"))
    if p_el is None:
        p_el = OxmlElement("w:p")
        target_hf._element.append(p_el)

    pPr = get_or_add_pPr(p_el)
    set_w_val(pPr, "jc", align, PPR_ORDER)
    add_field(
        p_el,
        "PAGE",
        cached_text="1",
        font_family=font_family,
        font_size_pt=font_size_pt,
        color_hex=color_hex,
    )


def insert_section_break_before_paragraph(doc: Any, target_p_el: Any) -> Any:
    """Splits the section immediately before `target_p_el` by placing a `w:sectPr` on the preceding paragraph.

    Returns the newly created `w:sectPr` (or existing one if already present).
    """
    prev_el = target_p_el.getprevious()
    while prev_el is not None and not prev_el.tag.endswith("}p"):
        prev_el = prev_el.getprevious()

    if prev_el is None:
        return None

    # Remove explicit pageBreakBefore on target_p_el since the section break itself starts a new page
    target_pPr = target_p_el.find(qn("w:pPr"))
    if target_pPr is not None:
        set_boolean_prop(target_pPr, "pageBreakBefore", None, PPR_ORDER)

    prev_pPr = get_or_add_pPr(prev_el)
    existing_sectPr = prev_pPr.find(qn("w:sectPr"))
    if existing_sectPr is not None:
        return existing_sectPr

    # Find the enclosing section's sectPr to clone page size and margins
    body_sectPr = doc.element.body.find(qn("w:sectPr"))
    new_sectPr = OxmlElement("w:sectPr")
    if body_sectPr is not None:
        for tag_to_copy in ("pgSz", "pgMar", "cols", "docGrid"):
            src_child = body_sectPr.find(qn(f"w:{tag_to_copy}"))
            if src_child is not None:
                insert_child = copy.deepcopy(src_child)
                new_sectPr.append(insert_child)

    type_el = get_or_add_ordered(new_sectPr, "type", SECTPR_ORDER)
    type_el.set(qn("w:val"), "nextPage")
    prev_pPr.append(new_sectPr)
    return new_sectPr


def ensure_multilevel_heading_num_id(doc: Any) -> int:
    """Ensures a multilevel decimal numbering definition exists in the document and returns its `numId`."""
    try:
        num_part = doc.part.numbering_part
        num_el = num_part.element
    except Exception:
        # If document has no numbering part, use numId=1 on paragraph numPr after creating via python-docx
        return 1

    # Check if our custom abstractNum already exists
    existing_nums = num_el.findall(qn("w:num"))
    if existing_nums:
        last_num = existing_nums[-1]
        nid = last_num.get(qn("w:numId"))
        if nid and str(nid).isdigit():
            return int(nid)
    return 1
