from __future__ import annotations

from typing import Any

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from lxml import etree

# OOXML Schema Child Element Ordering (ECMA-376 Part 1)
# Inserting elements in strict schema order prevents Word "unreadable content" warnings.

PPR_ORDER: list[str] = [
    "pStyle",
    "keepNext",
    "keepLines",
    "pageBreakBefore",
    "framePr",
    "widowControl",
    "numPr",
    "suppressLineNumbers",
    "pBdr",
    "shd",
    "tabs",
    "suppressAutoHyphens",
    "kinsoku",
    "wordWrap",
    "overflowPunct",
    "topLinePunct",
    "autoSpaceDE",
    "autoSpaceDN",
    "bidi",
    "adjustRightInd",
    "snapToGrid",
    "spacing",
    "ind",
    "contextualSpacing",
    "mirrorIndents",
    "suppressOverlap",
    "jc",
    "textDirection",
    "textAlignment",
    "textboxTightWrap",
    "outlineLvl",
    "divId",
    "cnfStyle",
    "rPr",
    "sectPr",
    "pPrChange",
]

RPR_ORDER: list[str] = [
    "rStyle",
    "rFonts",
    "b",
    "bCs",
    "i",
    "iCs",
    "caps",
    "smallCaps",
    "strike",
    "dstrike",
    "outline",
    "shadow",
    "emboss",
    "imprint",
    "noProof",
    "snapToGrid",
    "vanish",
    "webHidden",
    "color",
    "spacing",
    "w",
    "kern",
    "position",
    "sz",
    "szCs",
    "highlight",
    "u",
    "effect",
    "bdr",
    "shd",
    "fitText",
    "vertAlign",
    "rtl",
    "cs",
    "em",
    "lang",
    "eastAsianLayout",
    "specVanish",
    "oMath",
    "rPrChange",
]

SECTPR_ORDER: list[str] = [
    "headerReference",
    "footerReference",
    "footnotePr",
    "endnotePr",
    "type",
    "pgSz",
    "pgMar",
    "paperSrc",
    "pgBorders",
    "lnNumType",
    "pgNumType",
    "cols",
    "formProt",
    "vAlign",
    "noEndnote",
    "titlePg",
    "textDirection",
    "bidi",
    "rtlGutter",
    "docGrid",
    "printerSettings",
    "sectPrChange",
]

TBLPR_ORDER: list[str] = [
    "tblStyle",
    "tblpPr",
    "tblOverlap",
    "bidiVisual",
    "tblStyleRowBandSize",
    "tblStyleColBandSize",
    "tblW",
    "jc",
    "tblCellSpacing",
    "tblInd",
    "tblBorders",
    "shd",
    "tblLayout",
    "tblCellMar",
    "tblLook",
    "tblCaption",
    "tblDescription",
    "tblPrChange",
]

TRPR_ORDER: list[str] = [
    "cnfStyle",
    "divId",
    "gridBefore",
    "gridAfter",
    "wBefore",
    "wAfter",
    "cantSplit",
    "trHeight",
    "tblHeader",
    "tblCellSpacing",
    "jc",
    "hidden",
    "ins",
    "del",
    "trPrChange",
]


def local_tag(element: Any) -> str:
    """Returns the local XML tag name without namespace URI."""
    tag = str(element.tag)
    return tag.split("}")[-1] if "}" in tag else tag


def insert_ordered_child(parent: Any, new_child: Any, order_list: list[str]) -> Any:
    """Inserts `new_child` into `parent` preserving strict OOXML schema element order."""
    new_tag = local_tag(new_child)
    if new_tag not in order_list:
        parent.append(new_child)
        return new_child

    target_idx = order_list.index(new_tag)
    for idx, existing in enumerate(parent):
        existing_tag = local_tag(existing)
        if existing_tag in order_list:
            existing_order_idx = order_list.index(existing_tag)
            if existing_order_idx > target_idx:
                parent.insert(idx, new_child)
                return new_child
    parent.append(new_child)
    return new_child


def get_or_add_ordered(parent: Any, tag_name: str, order_list: list[str]) -> Any:
    """Finds child `w:{tag_name}` in `parent` or creates and inserts it in schema order."""
    qualified = qn(f"w:{tag_name}")
    child = parent.find(qualified)
    if child is None:
        child = OxmlElement(f"w:{tag_name}")
        insert_ordered_child(parent, child, order_list)
    return child


def get_or_add_pPr(p_element: Any) -> Any:
    """Gets or creates `w:pPr` as the first child of `w:p`."""
    pPr = p_element.find(qn("w:pPr"))
    if pPr is None:
        pPr = OxmlElement("w:pPr")
        p_element.insert(0, pPr)
    return pPr


def get_or_add_rPr(r_element: Any) -> Any:
    """Gets or creates `w:rPr` as the first child of `w:r`."""
    rPr = r_element.find(qn("w:rPr"))
    if rPr is None:
        rPr = OxmlElement("w:rPr")
        r_element.insert(0, rPr)
    return rPr


def get_or_add_tblPr(tbl_element: Any) -> Any:
    """Gets or creates `w:tblPr` as the first child of `w:tbl`."""
    tblPr = tbl_element.find(qn("w:tblPr"))
    if tblPr is None:
        tblPr = OxmlElement("w:tblPr")
        tbl_element.insert(0, tblPr)
    return tblPr


def get_or_add_trPr(tr_element: Any) -> Any:
    """Gets or creates `w:trPr` in `w:tr`."""
    trPr = tr_element.find(qn("w:trPr"))
    if trPr is None:
        trPr = OxmlElement("w:trPr")
        tr_element.insert(0, trPr)
    return trPr


def set_w_val(parent: Any, tag_name: str, val: str | int | None, order_list: list[str]) -> Any:
    """Sets `<w:{tag_name} w:val="{val}"/>` on `parent` in schema order, or removes if None."""
    qualified = qn(f"w:{tag_name}")
    existing = parent.find(qualified)
    if val is None:
        if existing is not None:
            parent.remove(existing)
        return None
    el = get_or_add_ordered(parent, tag_name, order_list)
    el.set(qn("w:val"), str(val))
    return el


def set_boolean_prop(
    parent: Any, tag_name: str, enabled: bool | None, order_list: list[str]
) -> None:
    """Sets or removes an OOXML boolean property (e.g., keepNext, pageBreakBefore, widowControl, b, i, caps)."""
    qualified = qn(f"w:{tag_name}")
    existing = parent.find(qualified)
    if enabled is None:
        if existing is not None:
            parent.remove(existing)
        return
    el = get_or_add_ordered(parent, tag_name, order_list)
    if enabled:
        # In OOXML, <w:b/> or <w:b w:val="true"/> means True; removing w:val is cleanest
        if qn("w:val") in el.attrib:
            del el.attrib[qn("w:val")]
    else:
        el.set(qn("w:val"), "0")


def parse_boolean_el(el: Any) -> bool | None:
    """Parses an OOXML boolean element (`<w:b/>`, `<w:b w:val="1"/>`, `<w:b w:val="0"/>`)."""
    if el is None:
        return None
    val = el.get(qn("w:val"))
    if val is None:
        return True
    return str(val).lower() not in ("0", "false", "off", "none")


def set_font_family_on_rPr(rPr: Any, font_family: str) -> None:
    """Sets all 4 font family attributes (ascii, hAnsi, cs, eastAsia) on `w:rFonts`."""
    rFonts = get_or_add_ordered(rPr, "rFonts", RPR_ORDER)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rFonts.set(qn(attr), font_family)
    # Remove theme font attributes that might override explicit font family
    for theme_attr in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if qn(theme_attr) in rFonts.attrib:
            del rFonts.attrib[qn(theme_attr)]


def set_font_size_on_rPr(rPr: Any, half_points: int) -> None:
    """Sets both `w:sz` and `w:szCs` in half-points on `w:rPr`."""
    set_w_val(rPr, "sz", str(half_points), RPR_ORDER)
    set_w_val(rPr, "szCs", str(half_points), RPR_ORDER)


def set_color_on_rPr(rPr: Any, color_hex: str) -> None:
    """Sets `<w:color w:val="..."/>` on `w:rPr`."""
    clean_hex = color_hex.lstrip("#").upper()
    color_el = get_or_add_ordered(rPr, "color", RPR_ORDER)
    color_el.set(qn("w:val"), clean_hex)
    for attr in ("w:themeColor", "w:themeTint", "w:themeShade"):
        if qn(attr) in color_el.attrib:
            del color_el.attrib[qn(attr)]


def safe_parse_xml_bytes(xml_bytes: bytes) -> etree._Element:
    """Safely parses XML bytes with XXE / DTD / entity expansion disabled.

    Raises ValueError if DOCTYPE or ENTITY declarations are present.
    """
    head_sample = xml_bytes[:4096].upper()
    if b"<!DOCTYPE" in head_sample or b"<!ENTITY" in head_sample:
        raise ValueError("XXE_OR_DTD_DETECTED")

    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        dtd_validation=False,
        load_dtd=False,
        recover=False,
    )
    return etree.fromstring(xml_bytes, parser=parser)
