from __future__ import annotations

import base64
import io
import json
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, Twips

from app.core.fields import (
    add_field,
    insert_section_break_before_paragraph,
    mark_document_update_fields_on_open,
    set_header_footer_page_field,
    set_section_pg_num_type,
)
from app.core.fixers.toc import TocFixer
from app.core.rules.loader import profile_loader
from app.core.style_manager import (
    assign_style_to_paragraph,
    ensure_doc_defaults,
    ensure_style_for_role,
)
from app.core.units import cm_to_twips, get_paper_dimensions_cm
from app.core.xml_helpers import (
    PPR_ORDER,
    TBLPR_ORDER,
    get_or_add_ordered,
    get_or_add_pPr,
    get_or_add_tblPr,
    set_boolean_prop,
    set_w_val,
)

# 1x1 transparent PNG for synthetic inline image testing
TINY_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _apply_section_geometry(doc: Document, profile_id: str = "contoh-s1-skripsi") -> None:
    profile = profile_loader.load(profile_id)
    w_cm, h_cm = get_paper_dimensions_cm(profile.page.size, profile.page.orientation)
    m = profile.page.margins_cm
    hf = profile.page.header_footer_distance_cm or {"header": 1.25, "footer": 1.25}
    for sect in doc.sections:
        sect.page_width = Twips(cm_to_twips(w_cm))
        sect.page_height = Twips(cm_to_twips(h_cm))
        sect.top_margin = Twips(cm_to_twips(m.top))
        sect.bottom_margin = Twips(cm_to_twips(m.bottom))
        sect.left_margin = Twips(cm_to_twips(m.left))
        sect.right_margin = Twips(cm_to_twips(m.right))
        sect.header_distance = Twips(cm_to_twips(hf["header"]))
        sect.footer_distance = Twips(cm_to_twips(hf["footer"]))


def _add_styled_para(
    doc: Document, text: str, role: str, profile_id: str = "contoh-s1-skripsi"
) -> object:
    profile = profile_loader.load(profile_id)
    style_id = ensure_style_for_role(doc, role, profile)
    p = doc.add_paragraph(text)
    assign_style_to_paragraph(p._p, style_id)
    return p


def build_clean_styled(out_path: Path) -> None:
    """Creates `clean_styled.docx` conforming 100% to `contoh-s1-skripsi` with 0 findings."""
    profile = profile_loader.load("contoh-s1-skripsi")
    doc = Document()
    # Remove initial empty paragraph
    for p in list(doc.paragraphs):
        p._p.getparent().remove(p._p)

    ensure_doc_defaults(doc, profile)
    for role in profile.roles:
        ensure_style_for_role(doc, role, profile)
    ensure_style_for_role(doc, "front_title", profile)
    TocFixer._ensure_toc_styles_with_leaders(doc, profile)
    mark_document_update_fields_on_open(doc)

    # 1. Cover section
    _add_styled_para(doc, "HALAMAN SAMPUL", "front_title")

    # 2. Front matter section
    p_app = _add_styled_para(doc, "LEMBAR PENGESAHAN", "front_title")
    insert_section_break_before_paragraph(doc, p_app._p)  # type: ignore[attr-defined]
    _add_styled_para(
        doc,
        "Skripsi ini telah disetujui dan disahkan oleh tim penguji sesuai pedoman akademik.",
        "body",
    )

    p_pref = _add_styled_para(doc, "KATA PENGANTAR", "front_title")
    set_boolean_prop(get_or_add_pPr(p_pref._p), "pageBreakBefore", True, PPR_ORDER)  # type: ignore[attr-defined]
    _add_styled_para(
        doc,
        "Puji syukur penulis panjatkan atas terselesaikannya penelitian skripsi ini dengan baik.",
        "body",
    )

    p_abs = _add_styled_para(doc, "ABSTRAK", "front_title")
    set_boolean_prop(get_or_add_pPr(p_abs._p), "pageBreakBefore", True, PPR_ORDER)  # type: ignore[attr-defined]
    _add_styled_para(
        doc,
        "Penelitian oleh Pratama (2024) dan Wijaya (2023) membahas perapian dokumen otomatis.",
        "body",
    )

    p_toc_title = _add_styled_para(doc, "DAFTAR ISI", "front_title")
    set_boolean_prop(get_or_add_pPr(p_toc_title._p), "pageBreakBefore", True, PPR_ORDER)  # type: ignore[attr-defined]
    p_toc_field = doc.add_paragraph()
    add_field(
        p_toc_field._p,
        'TOC \\o "1-3" \\h \\z \\u',
        cached_text="BAB I PENDAHULUAN\t1",
        font_family="Times New Roman",
        font_size_pt=12.0,
        color_hex="000000",
    )

    # 3. Chapters I - V (each in its own section for NUM-004 chapter first page bottom_center)
    chapters = [
        ("BAB I", "PENDAHULUAN", "Latar Belakang"),
        ("BAB II", "TINJAUAN PUSTAKA", "Landasan Teori"),
        ("BAB III", "METODOLOGI PENELITIAN", "Tahapan Penelitian"),
        ("BAB IV", "HASIL DAN PEMBAHASAN", "Implementasi Sistem"),
        ("BAB V", "KESIMPULAN DAN SARAN", "Kesimpulan Utama"),
    ]
    for idx, (bab_lbl, bab_ttl, sub_ttl) in enumerate(chapters, start=1):
        p_lbl = _add_styled_para(doc, bab_lbl, "chapter_label")
        insert_section_break_before_paragraph(doc, p_lbl._p)  # type: ignore[attr-defined]
        _add_styled_para(doc, bab_ttl, "chapter_title")

        p_sub = _add_styled_para(doc, sub_ttl, "heading_2")
        pPr_sub = get_or_add_pPr(p_sub._p)  # type: ignore[attr-defined]
        numPr = get_or_add_ordered(pPr_sub, "numPr", PPR_ORDER)
        set_w_val(numPr, "ilvl", "1", ["ilvl", "numId"])
        set_w_val(numPr, "numId", "1", ["ilvl", "numId"])

        _add_styled_para(
            doc,
            f"Pembahasan pada {bab_lbl} mengacu pada studi Pratama (2024) serta Wijaya (2023) mengenai struktur dokumen ilmiah.",
            "body",
        )

    # 4. References (in last chapter section, starting on a new page)
    p_ref = _add_styled_para(doc, "DAFTAR PUSTAKA", "front_title")
    set_boolean_prop(get_or_add_pPr(p_ref._p), "pageBreakBefore", True, PPR_ORDER)  # type: ignore[attr-defined]
    _add_styled_para(
        doc,
        "Pratama, A. (2024). Pemrosesan Dokumen Akademik Berbasis Standar OOXML. Jakarta: Penerbit Kampus.",
        "bibliography_entry",
    )
    _add_styled_para(
        doc,
        "Wijaya, B. (2023). Evaluasi Kepatuhan Format Karya Ilmiah Mahasiswa. Bandung: Pustaka Sains.",
        "bibliography_entry",
    )

    _apply_section_geometry(doc, "contoh-s1-skripsi")

    # Configure section page numbering (0=cover, 1=front_matter, 2..6=chapters I..V)
    for idx, sect in enumerate(doc.sections):
        if idx == 0:
            set_header_footer_page_field(sect, "none")
        elif idx == 1:
            set_section_pg_num_type(sect._sectPr, fmt="lowerRoman", start=1)
            set_header_footer_page_field(sect, "bottom_center")
        else:
            set_section_pg_num_type(sect._sectPr, fmt="decimal", start=1 if idx == 2 else None)
            set_header_footer_page_field(sect, "top_right", is_first_page=False)
            set_header_footer_page_field(sect, "bottom_center", is_first_page=True)

    doc.save(str(out_path))


def build_wrong_margins(out_path: Path) -> None:
    """Creates `wrong_margins.docx` with wrong margins (2.54 cm instead of 4-4-3-3 cm)."""
    doc = Document()
    for p in list(doc.paragraphs):
        p._p.getparent().remove(p._p)
    profile = profile_loader.load("contoh-s1-skripsi")
    ensure_doc_defaults(doc, profile)
    ensure_style_for_role(doc, "body", profile)
    _add_styled_para(
        doc,
        "Paragraf pertama pada dokumen dengan margin halaman yang belum sesuai standar kampus.",
        "body",
    )
    _add_styled_para(
        doc,
        "Paragraf kedua digunakan untuk memvalidasi perbaikan margin otomatis pada seluruh section.",
        "body",
    )
    for sect in doc.sections:
        sect.page_width = Twips(cm_to_twips(21.0))
        sect.page_height = Twips(cm_to_twips(29.7))
        sect.top_margin = Twips(cm_to_twips(2.54))
        sect.left_margin = Twips(cm_to_twips(2.54))
        sect.bottom_margin = Twips(cm_to_twips(2.54))
        sect.right_margin = Twips(cm_to_twips(2.54))
        sect.header_distance = Twips(cm_to_twips(1.25))
        sect.footer_distance = Twips(cm_to_twips(1.25))
    doc.save(str(out_path))


def build_manual_formatting(out_path: Path) -> None:
    """Creates `manual_formatting.docx` where all paragraphs use Normal style with manual bold/font/spacing."""
    doc = Document()
    _apply_section_geometry(doc)

    p1 = doc.add_paragraph()
    r1 = p1.add_run("BAB I")
    r1.bold = True
    r1.font.name = "Arial"
    r1.font.size = Pt(14)

    p2 = doc.add_paragraph()
    r2 = p2.add_run("PENDAHULUAN")
    r2.bold = True
    r2.font.name = "Arial"
    r2.font.size = Pt(14)

    p3 = doc.add_paragraph()
    r3 = p3.add_run("1.1 Latar Belakang")
    r3.bold = True
    r3.font.name = "Calibri"
    r3.font.size = Pt(12)

    p4 = doc.add_paragraph()
    r4a = p4.add_run("    Dokumen ini diformat secara manual menggunakan spasi awal dan font ")
    r4a.font.name = "Calibri"
    r4a.font.size = Pt(11)
    r4b = p4.add_run("Courier New nyasar ")
    r4b.font.name = "Courier New"
    r4b.font.size = Pt(11)
    r4c = p4.add_run("di tengah kalimat.")
    r4c.font.name = "Calibri"
    r4c.font.size = Pt(11)

    # Consecutive empty paragraphs used for vertical spacing (PARA-005)
    doc.add_paragraph("")
    doc.add_paragraph("")

    doc.add_paragraph("Paragraf kedua setelah baris kosong berulang.")
    doc.save(str(out_path))


def build_no_styles(out_path: Path) -> None:
    """Creates `no_styles.docx` where all paragraphs are plain `Normal` without bold/centering -> low confidence."""
    doc = Document()
    _apply_section_geometry(doc)
    doc.add_paragraph("BAB I")
    doc.add_paragraph("Pendahuluan")
    doc.add_paragraph("1.1 Latar Belakang Penelitian")
    doc.add_paragraph(
        "Paragraf isi ini ditulis dengan style Normal tanpa pemformatan khusus pada judul bab maupun sub-bab."
    )
    doc.save(str(out_path))


def build_typed_numbers(out_path: Path) -> None:
    """Creates `typed_numbers.docx` with typed heading numbers (HEAD-003), typed page number (NUM-006), and typed caption (CAP-004)."""
    doc = Document()
    _apply_section_geometry(doc)

    # Typed page number in footer ("1") without PAGE field -> NUM-006
    sect = doc.sections[0]
    sect.footer.is_linked_to_previous = False
    sect.footer.paragraphs[0].text = "1"

    doc.add_paragraph("BAB I")
    doc.add_paragraph("PENDAHULUAN")

    p_sub = doc.add_paragraph("1.1 Latar Belakang Masalah")
    for r in p_sub.runs:
        r.bold = True

    doc.add_paragraph(
        "Uraian latar belakang masalah penelitian yang memuat gambar ilustrasi dengan nomor caption ketikan manual."
    )

    p_img = doc.add_paragraph()
    r_img = p_img.add_run()
    r_img.add_picture(io.BytesIO(TINY_PNG_BYTES), width=Cm(8.0), height=Cm(5.0))

    doc.add_paragraph("Gambar 1.1 Diagram Alir Sistem")
    doc.save(str(out_path))


def build_typed_toc(out_path: Path) -> None:
    """Creates `typed_toc.docx` with manually typed Table of Contents lines (TOC-002)."""
    doc = Document()
    _apply_section_geometry(doc)
    doc.add_paragraph("DAFTAR ISI")
    doc.add_paragraph("KATA PENGANTAR ........................................ i")
    doc.add_paragraph("ABSTRAK ............................................... ii")
    doc.add_paragraph("BAB I PENDAHULUAN ..................................... 1")
    doc.add_paragraph("1.1 Latar Belakang .................................... 1")
    doc.add_paragraph("BAB I")
    doc.add_paragraph("PENDAHULUAN")
    doc.add_paragraph("Paragraf isi bab pertama setelah daftar isi ketikan manual.")
    doc.save(str(out_path))


def build_multi_section(out_path: Path) -> None:
    """Creates `multi_section.docx` with cover, front matter, and body sections with wrong numbering."""
    doc = Document()
    _apply_section_geometry(doc)
    doc.add_paragraph("HALAMAN SAMPUL")

    p_fm = doc.add_paragraph("KATA PENGANTAR")
    insert_section_break_before_paragraph(doc, p_fm._p)
    doc.add_paragraph("Isi kata pengantar pada section bagian awal.")

    p_b1 = doc.add_paragraph("BAB I")
    insert_section_break_before_paragraph(doc, p_b1._p)
    doc.add_paragraph("PENDAHULUAN")
    doc.add_paragraph("Isi bab pertama pada section isi utama.")

    # Intentionally set wrong page numbering on sections (e.g. cover has page number, front matter has decimal)
    set_header_footer_page_field(doc.sections[0], "bottom_center")
    set_section_pg_num_type(doc.sections[1]._sectPr, fmt="decimal", start=1)
    set_header_footer_page_field(doc.sections[1], "top_right")
    set_section_pg_num_type(doc.sections[2]._sectPr, fmt="lowerRoman", start=2)
    set_header_footer_page_field(doc.sections[2], "bottom_center")

    doc.save(str(out_path))


def build_with_tables_figures(out_path: Path) -> None:
    """Creates `with_tables_figures.docx` with oversized figure/table and misplaced captions."""
    doc = Document()
    _apply_section_geometry(doc)
    doc.add_paragraph("BAB IV")
    doc.add_paragraph("HASIL DAN PEMBAHASAN")

    # Misplaced figure caption ABOVE oversized figure (should be BELOW and <= 14.0 cm)
    doc.add_paragraph("Gambar 4.1 Arsitektur Pengujian")
    p_img = doc.add_paragraph()
    r_img = p_img.add_run()
    r_img.add_picture(io.BytesIO(TINY_PNG_BYTES), width=Cm(17.5), height=Cm(9.0))

    # Oversized table without tblHeader/cantSplit and with caption BELOW (should be ABOVE)
    tbl = doc.add_table(rows=3, cols=2)
    tblPr = get_or_add_tblPr(tbl._tbl)
    tblW = get_or_add_ordered(tblPr, "tblW", TBLPR_ORDER)
    tblW.set(qn("w:w"), str(cm_to_twips(17.5)))
    tblW.set(qn("w:type"), "dxa")

    tbl.cell(0, 0).text = "Komponen"
    tbl.cell(0, 1).text = "Keterangan"
    tbl.cell(1, 0).text = "Parser OOXML"
    tbl.cell(1, 1).text = "Membaca elemen paragraf dan tabel"
    tbl.cell(2, 0).text = "Fixer"
    tbl.cell(2, 1).text = "Merapikan style dan ukuran"

    doc.add_paragraph("Tabel 4.1 Ringkasan Komponen")
    doc.save(str(out_path))


def build_tracked_changes(out_path: Path) -> None:
    """Creates `tracked_changes.docx` containing `w:ins`, `w:del`, and comment markers."""
    doc = Document()
    _apply_section_geometry(doc)
    doc.add_paragraph("Paragraf normal tanpa revisi.")

    p_tc = doc.add_paragraph("Paragraf dengan revisi aktif ")
    ins = OxmlElement("w:ins")
    ins.set(qn("w:id"), "1")
    ins.set(qn("w:author"), "Dosen Pembimbing")
    r_ins = OxmlElement("w:r")
    t_ins = OxmlElement("w:t")
    t_ins.text = "tambahan revisi"
    r_ins.append(t_ins)
    ins.append(r_ins)
    p_tc._p.append(ins)

    c_start = OxmlElement("w:commentRangeStart")
    c_start.set(qn("w:id"), "0")
    p_tc._p.insert(0, c_start)

    doc.save(str(out_path))


def build_textboxes_sdt(out_path: Path) -> None:
    """Creates `textboxes_sdt.docx` containing `w:sdt` content control and `w:txbxContent`."""
    doc = Document()
    _apply_section_geometry(doc)
    doc.add_paragraph("Paragraf pembuka di luar content control.")

    sdt = OxmlElement("w:sdt")
    sdt_content = OxmlElement("w:sdtContent")
    p_in_sdt = OxmlElement("w:p")
    r_in_sdt = OxmlElement("w:r")
    t_in_sdt = OxmlElement("w:t")
    t_in_sdt.text = "Paragraf di dalam Structured Document Tag (w:sdt)."
    r_in_sdt.append(t_in_sdt)
    p_in_sdt.append(r_in_sdt)
    sdt_content.append(p_in_sdt)
    sdt.append(sdt_content)
    doc.element.body.insert(1, sdt)

    p_tbx = doc.add_paragraph("Paragraf dengan kotak teks.")
    r_tbx = OxmlElement("w:r")
    txbx = OxmlElement("w:txbxContent")
    p_inner = OxmlElement("w:p")
    r_inner = OxmlElement("w:r")
    t_inner = OxmlElement("w:t")
    t_inner.text = "Teks di dalam kotak teks"
    r_inner.append(t_inner)
    p_inner.append(r_inner)
    txbx.append(p_inner)
    r_tbx.append(txbx)
    p_tbx._p.append(r_tbx)

    doc.save(str(out_path))


def build_localized_styles(out_path: Path) -> None:
    """Creates `localized_styles.docx` with Indonesian UI style names ('Judul 1') mapped to XML `Heading1`."""
    doc = Document()
    _apply_section_geometry(doc)
    styles_el = doc.styles.element
    for st in styles_el.findall(qn("w:style")):
        if st.get(qn("w:styleId")) == "Heading1":
            name_el = st.find(qn("w:name"))
            if name_el is not None:
                name_el.set(qn("w:val"), "Judul 1")

    p0 = doc.add_paragraph("BAB I")
    assign_style_to_paragraph(p0._p, "Heading1")

    p1 = doc.add_paragraph("PENDAHULUAN")
    assign_style_to_paragraph(p1._p, "Heading1")

    doc.add_paragraph("Paragraf isi di bawah style berbahasa lokal Indonesia.")
    doc.save(str(out_path))


def build_large_100pages(out_path: Path) -> None:
    """Creates `large_100pages.docx` (~100 pages / ~400 paragraphs) for NFR-03 performance testing."""
    doc = Document()
    _apply_section_geometry(doc)
    doc.add_paragraph("BAB I")
    doc.add_paragraph("PENDAHULUAN")

    sample_paragraph = (
        "Penelitian ini menguji kinerja pemrosesan dokumen berukuran besar sekitar seratus halaman "
        "untuk memastikan waktu analisis dan perapian memenuhi target kebutuhan non-fungsional NFR-03. "
        "Setiap paragraf dievaluasi format efektifnya secara deterministik tanpa mengubah isi teks sedikit pun. "
    ) * 2

    for i in range(1, 350):
        if i % 70 == 0:
            chap_num = (i // 70) + 1
            roman = ["I", "II", "III", "IV", "V"][min(chap_num - 1, 4)]
            doc.add_paragraph(f"BAB {roman}")
            doc.add_paragraph(f"JUDUL BAB BAGIAN {roman}")
        elif i % 15 == 0:
            doc.add_paragraph(f"1.{i // 15} Sub-bab Pembahasan Bagian Ke-{i // 15}")
        else:
            doc.add_paragraph(sample_paragraph)

    doc.save(str(out_path))


def build_security_fixtures(fixtures_dir: Path) -> None:
    """Creates malicious security test fixtures (`bad_xxe.docx`, `bad_traversal.docx`, `macro.docm`, `bad_zip_bomb.docx`)."""
    # 1. macro.docm
    macro_path = fixtures_dir / "macro.docm"
    doc = Document()
    doc.add_paragraph("Dokumen dengan ekstensi .docm")
    doc.save(str(macro_path))

    # 2. bad_xxe.docx (contains <!DOCTYPE and <!ENTITY in word/document.xml)
    buf = io.BytesIO()
    doc.save(buf)
    orig_bytes = buf.getvalue()

    xxe_path = fixtures_dir / "bad_xxe.docx"
    with (
        zipfile.ZipFile(io.BytesIO(orig_bytes), "r") as zin,
        zipfile.ZipFile(xxe_path, "w") as zout,
    ):
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                xxe_header = (
                    b'<?xml version="1.0" encoding="UTF-8"?>\n'
                    b'<!DOCTYPE foo [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>\n'
                )
                # Strip existing xml declaration if present
                if data.startswith(b"<?xml"):
                    data = data.split(b"?>", 1)[-1].lstrip()
                data = xxe_header + data
            zout.writestr(item, data)

    # 3. bad_traversal.docx (contains `../../evil.xml` entry)
    traversal_path = fixtures_dir / "bad_traversal.docx"
    with (
        zipfile.ZipFile(io.BytesIO(orig_bytes), "r") as zin,
        zipfile.ZipFile(traversal_path, "w") as zout,
    ):
        for item in zin.infolist():
            zout.writestr(item, zin.read(item.filename))
        zout.writestr("../../evil.txt", b"malicious traversal")

    # 4. bad_zip_bomb.docx (contains >500 entries to trigger zip-bomb / entry limit guard fast)
    bomb_path = fixtures_dir / "bad_zip_bomb.docx"
    with (
        zipfile.ZipFile(io.BytesIO(orig_bytes), "r") as zin,
        zipfile.ZipFile(bomb_path, "w", compression=zipfile.ZIP_DEFLATED) as zout,
    ):
        for item in zin.infolist():
            zout.writestr(item, zin.read(item.filename))
        for idx in range(520):
            zout.writestr(f"word/extra_{idx}.xml", b"<root/>")


def ensure_all_fixtures(fixtures_dir: Path | None = None) -> Path:
    if fixtures_dir is None:
        fixtures_dir = Path(__file__).resolve().parent.parent.parent.parent / "tests" / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)

    builders = {
        "clean_styled.docx": build_clean_styled,
        "wrong_margins.docx": build_wrong_margins,
        "manual_formatting.docx": build_manual_formatting,
        "no_styles.docx": build_no_styles,
        "typed_numbers.docx": build_typed_numbers,
        "typed_toc.docx": build_typed_toc,
        "multi_section.docx": build_multi_section,
        "with_tables_figures.docx": build_with_tables_figures,
        "tracked_changes.docx": build_tracked_changes,
        "textboxes_sdt.docx": build_textboxes_sdt,
        "localized_styles.docx": build_localized_styles,
        "large_100pages.docx": build_large_100pages,
    }

    for name, fn in builders.items():
        target = fixtures_dir / name
        if not target.exists():
            fn(target)

    if not (fixtures_dir / "bad_xxe.docx").exists():
        build_security_fixtures(fixtures_dir)

    # Golden expected files
    clean_exp = fixtures_dir / "clean_styled.expected.json"
    if not clean_exp.exists():
        clean_exp.write_text(
            json.dumps(
                {
                    "fixture": "clean_styled.docx",
                    "expected_total_findings": 0,
                    "expected_rules": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    margins_exp = fixtures_dir / "wrong_margins.expected.json"
    if not margins_exp.exists():
        margins_exp.write_text(
            json.dumps(
                {"fixture": "wrong_margins.docx", "expected_rules": ["PAGE-002"]},
                indent=2,
            ),
            encoding="utf-8",
        )

    return fixtures_dir


if __name__ == "__main__":
    path = ensure_all_fixtures()
    print(f"Fixtures generated in {path}")
