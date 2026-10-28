from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from app.core.units import emu_to_cm, twips_to_cm
from app.core.xml_helpers import local_tag, parse_boolean_el

WP_NS = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
A_NS = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
PIC_NS = "{http://schemas.openxmlformats.org/drawingml/2006/picture}"


@dataclass
class FieldInfo:
    field_type: str  # "PAGE", "NUMPAGES", "TOC", "SEQ", "REF", etc.
    instr: str
    cached_result: str = ""
    is_simple: bool = False


@dataclass
class HeaderFooterInfo:
    is_linked_to_previous: bool = True
    has_page_field: bool = False
    has_typed_page_number: bool = False
    typed_text: str = ""
    alignment: str = "left"  # "left" | "center" | "right"


@dataclass
class InlineImageInfo:
    index: int
    block_index: int
    width_cm: float
    height_cm: float
    cx_emu: int
    cy_emu: int
    is_floating: bool = False
    raw_drawing: Any = None


@dataclass
class TableInfo:
    index: int
    block_index: int
    width_cm: float
    alignment: str  # "left" | "center" | "right"
    has_tbl_header: bool
    all_rows_cant_split: bool
    row_count: int
    col_count: int
    raw_tbl: Any = None


@dataclass
class DocumentSection:
    index: int
    top_margin_cm: float
    bottom_margin_cm: float
    left_margin_cm: float
    right_margin_cm: float
    header_distance_cm: float
    footer_distance_cm: float
    page_width_cm: float
    page_height_cm: float
    orientation: str
    pg_num_format: str | None = None
    pg_num_start: int | None = None
    different_first_page: bool = False
    section_start_type: str = "nextPage"
    header_info: HeaderFooterInfo = field(default_factory=HeaderFooterInfo)
    footer_info: HeaderFooterInfo = field(default_factory=HeaderFooterInfo)
    first_header_info: HeaderFooterInfo = field(default_factory=HeaderFooterInfo)
    first_footer_info: HeaderFooterInfo = field(default_factory=HeaderFooterInfo)
    page_number_position: str = "none"  # e.g. "top_right", "bottom_center", "none"
    first_page_number_position: str = "none"
    raw_sectPr: Any = None
    section_obj: Any = None


@dataclass
class DocumentBlock:
    index: int
    block_type: str  # "paragraph" | "table"
    text: str
    section_index: int
    raw_element: Any
    approx_page: int = 1
    style_id: str | None = None
    style_name: str | None = None
    assigned_role: str | None = None
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    user_confirmed: bool = False
    fields: list[FieldInfo] = field(default_factory=list)
    images: list[InlineImageInfo] = field(default_factory=list)
    table_info: TableInfo | None = None
    has_tracked_changes: bool = False
    has_comments: bool = False
    has_sdt: bool = False
    has_textbox: bool = False
    has_manual_line_break: bool = False
    has_page_break_run: bool = False
    leading_whitespace: str = ""


def extract_fields_from_element(element: Any) -> list[FieldInfo]:
    """Extracts both simple (`w:fldSimple`) and complex (`w:fldChar`) fields from an XML element."""
    fields: list[FieldInfo] = []

    # 1. w:fldSimple
    for simple in element.iter(qn("w:fldSimple")):
        instr = (simple.get(qn("w:instr")) or "").strip()
        cached_parts: list[str] = []
        for t in simple.iter(qn("w:t")):
            if t.text:
                cached_parts.append(t.text)
        ftype = instr.split()[0].upper() if instr else "UNKNOWN"
        fields.append(
            FieldInfo(
                field_type=ftype,
                instr=instr,
                cached_result="".join(cached_parts),
                is_simple=True,
            )
        )

    # 2. Complex fields (w:fldChar begin -> instrText -> separate -> w:t -> end)
    state = "outside"
    current_instr: list[str] = []
    current_result: list[str] = []

    for run in element.iter(qn("w:r")):
        fld_char = run.find(qn("w:fldChar"))
        if fld_char is not None:
            char_type = fld_char.get(qn("w:fldCharType"))
            if char_type == "begin":
                state = "instr"
                current_instr = []
                current_result = []
            elif char_type == "separate" and state == "instr":
                state = "result"
            elif char_type == "end" and state in ("instr", "result"):
                instr_str = "".join(current_instr).strip()
                if instr_str:
                    ftype = instr_str.split()[0].upper()
                    fields.append(
                        FieldInfo(
                            field_type=ftype,
                            instr=instr_str,
                            cached_result="".join(current_result),
                            is_simple=False,
                        )
                    )
                state = "outside"
            continue

        if state == "instr":
            for it in run.findall(qn("w:instrText")):
                if it.text:
                    current_instr.append(it.text)
        elif state == "result":
            for t in run.findall(qn("w:t")):
                if t.text:
                    current_result.append(t.text)

    return fields


def extract_visible_paragraph_text(p_element: Any) -> str:
    """Extracts visible text from a paragraph, ignoring hidden text (`w:vanish`) and `w:instrText`."""
    parts: list[str] = []
    for child in p_element.iter():
        tag = local_tag(child)
        if tag == "r":
            rPr = child.find(qn("w:rPr"))
            if rPr is not None and parse_boolean_el(rPr.find(qn("w:vanish"))) is True:
                continue
            for sub in child:
                sub_tag = local_tag(sub)
                if sub_tag == "t" and sub.text:
                    parts.append(sub.text)
                elif sub_tag == "tab":
                    parts.append("\t")
                elif sub_tag == "br":
                    br_type = sub.get(qn("w:type"))
                    if br_type not in ("page", "column"):
                        parts.append("\n")
    return "".join(parts)


def _inspect_header_footer(hf_obj: Any) -> HeaderFooterInfo:
    info = HeaderFooterInfo()
    if hf_obj is None:
        return info
    try:
        info.is_linked_to_previous = bool(hf_obj.is_linked_to_previous)
        el = hf_obj._element
    except Exception:
        return info

    fields = extract_fields_from_element(el)
    info.has_page_field = any(f.field_type == "PAGE" for f in fields)

    texts: list[str] = []
    jc_val = "left"
    for p in el.findall(qn("w:p")):
        pPr = p.find(qn("w:pPr"))
        if pPr is not None:
            jc = pPr.find(qn("w:jc"))
            if jc is not None and jc.get(qn("w:val")):
                raw_jc = jc.get(qn("w:val"))
                if raw_jc in ("center", "right", "left"):
                    jc_val = raw_jc
                elif raw_jc == "end":
                    jc_val = "right"
                elif raw_jc == "start":
                    jc_val = "left"
        p_text = extract_visible_paragraph_text(p).strip()
        if p_text:
            texts.append(p_text)

    combined = " ".join(texts).strip()
    info.alignment = jc_val
    if not info.has_page_field and combined:
        if re.match(r"^([0-9]{1,4}|[ivxlcdmIVXLCDM]{1,8})$", combined):
            info.has_typed_page_number = True
            info.typed_text = combined

    return info


def _resolve_page_num_position(header_info: HeaderFooterInfo, footer_info: HeaderFooterInfo) -> str:
    if header_info.has_page_field or header_info.has_typed_page_number:
        return f"top_{header_info.alignment}"
    if footer_info.has_page_field or footer_info.has_typed_page_number:
        return f"bottom_{footer_info.alignment}"
    return "none"


@dataclass
class DocumentIR:
    file_path: str
    doc: Any  # python-docx Document instance
    sections: list[DocumentSection] = field(default_factory=list)
    blocks: list[DocumentBlock] = field(default_factory=list)
    has_tracked_changes: bool = False
    has_comments: bool = False
    has_sdt: bool = False
    has_textbox: bool = False
    has_update_fields: bool = False

    @classmethod
    def from_docx(cls, file_path: str) -> DocumentIR:
        """Builds a complete IR representation from a .docx file."""
        doc = Document(file_path)
        ir = cls(file_path=file_path, doc=doc)

        # Check settings.xml for updateFields
        settings_el = doc.settings._element
        upd = settings_el.find(qn("w:updateFields"))
        if upd is not None and parse_boolean_el(upd) is True:
            ir.has_update_fields = True

        # Parse sections
        for idx, sect in enumerate(doc.sections):
            sectPr = sect._sectPr
            top_cm = twips_to_cm(sect.top_margin.twips) if sect.top_margin else 2.54
            bottom_cm = twips_to_cm(sect.bottom_margin.twips) if sect.bottom_margin else 2.54
            left_cm = twips_to_cm(sect.left_margin.twips) if sect.left_margin else 2.54
            right_cm = twips_to_cm(sect.right_margin.twips) if sect.right_margin else 2.54
            header_cm = twips_to_cm(sect.header_distance.twips) if sect.header_distance else 1.25
            footer_cm = twips_to_cm(sect.footer_distance.twips) if sect.footer_distance else 1.25
            width_cm = twips_to_cm(sect.page_width.twips) if sect.page_width else 21.0
            height_cm = twips_to_cm(sect.page_height.twips) if sect.page_height else 29.7
            orientation = "landscape" if width_cm > height_cm else "portrait"

            # pgNumType
            pg_num_fmt: str | None = None
            pg_num_start: int | None = None
            pgNumType = sectPr.find(qn("w:pgNumType"))
            if pgNumType is not None:
                pg_num_fmt = pgNumType.get(qn("w:fmt"))
                start_attr = pgNumType.get(qn("w:start"))
                if start_attr is not None and str(start_attr).isdigit():
                    pg_num_start = int(start_attr)

            # section type
            sect_type_el = sectPr.find(qn("w:type"))
            sect_start_type = (
                sect_type_el.get(qn("w:val")) if sect_type_el is not None else "nextPage"
            ) or "nextPage"

            diff_first = bool(sect.different_first_page_header_footer)
            h_info = _inspect_header_footer(sect.header)
            f_info = _inspect_header_footer(sect.footer)
            fh_info = (
                _inspect_header_footer(sect.first_page_header) if diff_first else HeaderFooterInfo()
            )
            ff_info = (
                _inspect_header_footer(sect.first_page_footer) if diff_first else HeaderFooterInfo()
            )

            pos = _resolve_page_num_position(h_info, f_info)
            first_pos = _resolve_page_num_position(fh_info, ff_info) if diff_first else pos

            ir.sections.append(
                DocumentSection(
                    index=idx,
                    top_margin_cm=top_cm,
                    bottom_margin_cm=bottom_cm,
                    left_margin_cm=left_cm,
                    right_margin_cm=right_cm,
                    header_distance_cm=header_cm,
                    footer_distance_cm=footer_cm,
                    page_width_cm=width_cm,
                    page_height_cm=height_cm,
                    orientation=orientation,
                    pg_num_format=pg_num_fmt,
                    pg_num_start=pg_num_start,
                    different_first_page=diff_first,
                    section_start_type=sect_start_type,
                    header_info=h_info,
                    footer_info=f_info,
                    first_header_info=fh_info,
                    first_footer_info=ff_info,
                    page_number_position=pos,
                    first_page_number_position=first_pos,
                    raw_sectPr=sectPr,
                    section_obj=sect,
                )
            )

        # Parse body blocks in document order
        block_idx = 0
        current_section = 0
        approx_page = 1
        char_accum = 0
        img_counter = 0
        tbl_counter = 0

        def _process_body_child(elem: Any, inside_sdt: bool = False) -> None:
            nonlocal block_idx, current_section, approx_page, char_accum, img_counter, tbl_counter

            tag = local_tag(elem)
            if tag == "sdt":
                ir.has_sdt = True
                sdt_content = elem.find(qn("w:sdtContent"))
                if sdt_content is not None:
                    for child in sdt_content:
                        _process_body_child(child, inside_sdt=True)
                return

            if tag == "p":
                p = Paragraph(elem, doc)
                pPr = elem.find(qn("w:pPr"))

                # Resolve XML styleId as primary identifier (DOCX_NOTES.md section 3)
                xml_style_id: str | None = None
                if pPr is not None:
                    pStyle = pPr.find(qn("w:pStyle"))
                    if pStyle is not None:
                        xml_style_id = pStyle.get(qn("w:val"))
                if xml_style_id is None and p.style is not None:
                    xml_style_id = p.style.style_id

                style_name = p.style.name if p.style else None
                vis_text = extract_visible_paragraph_text(elem)

                # Leading whitespace detection (spaces/tabs used as manual indent)
                m_ws = re.match(r"^([ \t]+)", vis_text)
                leading_ws = m_ws.group(1) if m_ws else ""

                # Fields
                p_fields = extract_fields_from_element(elem)

                # Images inside paragraph
                p_images: list[InlineImageInfo] = []
                for drawing in elem.iter(qn("w:drawing")):
                    for inline in drawing.findall(f"{WP_NS}inline"):
                        extent = inline.find(f"{WP_NS}extent")
                        if extent is not None:
                            cx = int(extent.get("cx") or 0)
                            cy = int(extent.get("cy") or 0)
                            p_images.append(
                                InlineImageInfo(
                                    index=img_counter,
                                    block_index=block_idx,
                                    width_cm=emu_to_cm(cx),
                                    height_cm=emu_to_cm(cy),
                                    cx_emu=cx,
                                    cy_emu=cy,
                                    is_floating=False,
                                    raw_drawing=drawing,
                                )
                            )
                            img_counter += 1
                    for anchor in drawing.findall(f"{WP_NS}anchor"):
                        extent = anchor.find(f"{WP_NS}extent")
                        cx = int(extent.get("cx") or 0) if extent is not None else 0
                        cy = int(extent.get("cy") or 0) if extent is not None else 0
                        p_images.append(
                            InlineImageInfo(
                                index=img_counter,
                                block_index=block_idx,
                                width_cm=emu_to_cm(cx),
                                height_cm=emu_to_cm(cy),
                                cx_emu=cx,
                                cy_emu=cy,
                                is_floating=True,
                                raw_drawing=drawing,
                            )
                        )
                        img_counter += 1

                # Advisories (tracked changes, comments, sdt, textbox, breaks)
                has_tc = (
                    elem.find(f".//{qn('w:ins')}") is not None
                    or elem.find(f".//{qn('w:del')}") is not None
                    or elem.find(f".//{qn('w:rPrChange')}") is not None
                    or elem.find(f".//{qn('w:pPrChange')}") is not None
                )
                has_comm = (
                    elem.find(f".//{qn('w:commentRangeStart')}") is not None
                    or elem.find(f".//{qn('w:commentReference')}") is not None
                )
                has_p_sdt = inside_sdt or (elem.find(f".//{qn('w:sdt')}") is not None)
                has_tbx = elem.find(f".//{qn('w:txbxContent')}") is not None

                if has_tc:
                    ir.has_tracked_changes = True
                if has_comm:
                    ir.has_comments = True
                if has_p_sdt:
                    ir.has_sdt = True
                if has_tbx:
                    ir.has_textbox = True

                has_manual_lb = False
                has_pg_br = False
                for br in elem.iter(qn("w:br")):
                    btype = br.get(qn("w:type"))
                    if btype == "page":
                        has_pg_br = True
                    elif btype not in ("column",):
                        has_manual_lb = True

                if pPr is not None and parse_boolean_el(pPr.find(qn("w:pageBreakBefore"))) is True:
                    if block_idx > 0:
                        approx_page += 1
                        char_accum = 0

                if has_pg_br:
                    approx_page += 1
                    char_accum = 0
                else:
                    char_accum += len(vis_text) + 60
                    if char_accum > 2200:
                        approx_page += 1
                        char_accum = 0

                sec_idx = min(current_section, max(0, len(ir.sections) - 1))
                ir.blocks.append(
                    DocumentBlock(
                        index=block_idx,
                        block_type="paragraph",
                        text=vis_text,
                        section_index=sec_idx,
                        approx_page=approx_page,
                        raw_element=elem,
                        style_id=xml_style_id,
                        style_name=style_name,
                        fields=p_fields,
                        images=p_images,
                        has_tracked_changes=has_tc,
                        has_comments=has_comm,
                        has_sdt=has_p_sdt,
                        has_textbox=has_tbx,
                        has_manual_line_break=has_manual_lb,
                        has_page_break_run=has_pg_br,
                        leading_whitespace=leading_ws,
                    )
                )
                block_idx += 1

                # Check if this paragraph ends a section (`w:pPr/w:sectPr`)
                if pPr is not None and pPr.find(qn("w:sectPr")) is not None:
                    current_section += 1
                    approx_page += 1
                    char_accum = 0

            elif tag == "tbl":
                tbl = Table(elem, doc)
                tblPr = elem.find(qn("w:tblPr"))
                tbl_jc = "left"
                tbl_width_cm = 0.0

                if tblPr is not None:
                    jc_el = tblPr.find(qn("w:jc"))
                    if jc_el is not None and jc_el.get(qn("w:val")):
                        val = jc_el.get(qn("w:val"))
                        if val in ("center", "right", "left"):
                            tbl_jc = val

                    tblW = tblPr.find(qn("w:tblW"))
                    if tblW is not None and tblW.get(qn("w:type")) in ("dxa", None):
                        w_val = tblW.get(qn("w:w"))
                        if w_val and str(w_val).isdigit():
                            tbl_width_cm = twips_to_cm(int(w_val))

                if tbl_width_cm <= 0.0:
                    tblGrid = elem.find(qn("w:tblGrid"))
                    if tblGrid is not None:
                        total_twips = 0
                        for gc in tblGrid.findall(qn("w:gridCol")):
                            w_val = gc.get(qn("w:w"))
                            if w_val and str(w_val).isdigit():
                                total_twips += int(w_val)
                        if total_twips > 0:
                            tbl_width_cm = twips_to_cm(total_twips)

                rows = elem.findall(qn("w:tr"))
                has_header = False
                all_cant_split = True
                if rows:
                    first_trPr = rows[0].find(qn("w:trPr"))
                    if first_trPr is not None:
                        hdr_el = first_trPr.find(qn("w:tblHeader"))
                        if parse_boolean_el(hdr_el) is True:
                            has_header = True
                    for r_el in rows:
                        trPr = r_el.find(qn("w:trPr"))
                        if (
                            trPr is None
                            or parse_boolean_el(trPr.find(qn("w:cantSplit"))) is not True
                        ):
                            all_cant_split = False
                            break
                else:
                    all_cant_split = False

                col_count = len(tbl.columns) if tbl.rows else 0
                t_info = TableInfo(
                    index=tbl_counter,
                    block_index=block_idx,
                    width_cm=tbl_width_cm,
                    alignment=tbl_jc,
                    has_tbl_header=has_header,
                    all_rows_cant_split=all_cant_split,
                    row_count=len(rows),
                    col_count=col_count,
                    raw_tbl=elem,
                )
                tbl_counter += 1

                cell_texts: list[str] = []
                for r_el in rows:
                    for tc_el in r_el.findall(qn("w:tc")):
                        for p_el in tc_el.findall(qn("w:p")):
                            cell_texts.append(extract_visible_paragraph_text(p_el).strip())
                tbl_text = "\n".join(t for t in cell_texts if t)

                sec_idx = min(current_section, max(0, len(ir.sections) - 1))
                ir.blocks.append(
                    DocumentBlock(
                        index=block_idx,
                        block_type="table",
                        text=tbl_text,
                        section_index=sec_idx,
                        approx_page=approx_page,
                        raw_element=elem,
                        table_info=t_info,
                        has_sdt=inside_sdt,
                    )
                )
                block_idx += 1

        for child in doc.element.body:
            _process_body_child(child)

        return ir
