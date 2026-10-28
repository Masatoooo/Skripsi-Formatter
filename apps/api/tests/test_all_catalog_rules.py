from __future__ import annotations

import io
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.shared import Cm, Twips

from app.core.docx_model import DocumentIR
from app.core.fixers.runner import fix_runner
from app.core.integrity import normalized_text
from app.core.rules.evaluator import rule_evaluator
from app.core.rules.loader import profile_loader
from app.core.units import cm_to_twips
from app.core.xml_helpers import PPR_ORDER, get_or_add_pPr, set_boolean_prop
from tests.fixture_builder import TINY_PNG_BYTES, _apply_section_geometry


def test_margin_tolerance_boundary(tmp_path: Path):
    """Tests PAGE-002 exact tolerance boundary (4.00 cm +/- 0.05 cm)."""
    profile = profile_loader.load("contoh-s1-skripsi")

    # Within tolerance: 3.97 cm (diff 0.03 cm <= 0.05 cm tolerance) -> PASS
    doc_pass = Document()
    _apply_section_geometry(doc_pass)
    doc_pass.sections[0].top_margin = Twips(cm_to_twips(3.97))
    p_pass = tmp_path / "tol_pass.docx"
    doc_pass.save(str(p_pass))

    ir_pass = DocumentIR.from_docx(str(p_pass))
    f_pass = rule_evaluator.evaluate(ir_pass, profile)
    assert not any(f.rule_id == "PAGE-002" for f in f_pass)

    # Outside tolerance: 3.90 cm (diff 0.10 cm > 0.05 cm tolerance) -> FAIL
    doc_fail = Document()
    _apply_section_geometry(doc_fail)
    doc_fail.sections[0].top_margin = Twips(cm_to_twips(3.90))
    p_fail = tmp_path / "tol_fail.docx"
    doc_fail.save(str(p_fail))

    ir_fail = DocumentIR.from_docx(str(p_fail))
    f_fail = rule_evaluator.evaluate(ir_fail, profile)
    assert any(f.rule_id == "PAGE-002" for f in f_fail)


def test_page_size_and_orientation_rules(tmp_path: Path):
    """Tests PAGE-001 (size), PAGE-003 (header/footer distance), and PAGE-004 (orientation)."""
    profile = profile_loader.load("contoh-s1-skripsi")
    doc = Document()
    _apply_section_geometry(doc)
    sect = doc.sections[0]
    # Landscape Letter size with wrong header/footer distance
    sect.page_width = Twips(cm_to_twips(27.94))
    sect.page_height = Twips(cm_to_twips(21.59))
    sect.header_distance = Twips(cm_to_twips(2.5))
    sect.footer_distance = Twips(cm_to_twips(2.5))
    doc.add_paragraph("Isi paragraf dengan orientasi landscape dan ukuran Letter.")
    src = tmp_path / "page_rules.docx"
    doc.save(str(src))

    ir = DocumentIR.from_docx(str(src))
    findings = rule_evaluator.evaluate(ir, profile)
    rids = {f.rule_id for f in findings}
    assert "PAGE-001" in rids
    assert "PAGE-003" in rids
    assert "PAGE-004" in rids

    out = tmp_path / "page_fixed.docx"
    changes, rem = fix_runner.run(src, out, profile, mode="all", approved_suggest_ids=["PAGE-004"])
    applied = {c.rule_id for c in changes}
    assert {"PAGE-001", "PAGE-003", "PAGE-004"}.issubset(applied)
    assert not any(f.category == "PAGE" for f in rem)
    assert normalized_text(src) == normalized_text(out)


def test_bibliography_rules_bib001_to_bib004(tmp_path: Path):
    """Tests BIB-001 (sorting), BIB-002 (hanging indent), BIB-003 (spacing), BIB-004 (uncited)."""
    profile = profile_loader.load("contoh-s1-skripsi")
    doc = Document()
    _apply_section_geometry(doc)
    doc.add_paragraph("BAB I")
    doc.add_paragraph("PENDAHULUAN")
    doc.add_paragraph("Penelitian ini merujuk pada karya Pratama (2024) tentang dokumen ilmiah.")
    doc.add_paragraph("DAFTAR PUSTAKA")
    # Unsorted (Zulkarnain before Pratama) + Zulkarnain uncited in body + no hanging indent
    doc.add_paragraph("Zulkarnain, Z. (2022). Sistem Informasi Kampus. Surabaya: Airlangga Press.")
    doc.add_paragraph("Pratama, A. (2024). Pemrosesan OOXML. Jakarta: UI Press.")

    src = tmp_path / "bib.docx"
    doc.save(str(src))

    ir = DocumentIR.from_docx(str(src))
    findings = rule_evaluator.evaluate(ir, profile)
    rids = {f.rule_id for f in findings}
    assert "BIB-001" in rids
    assert "BIB-002" in rids
    assert "BIB-003" in rids
    assert "BIB-004" in rids

    out = tmp_path / "bib_fixed.docx"
    changes, rem = fix_runner.run(src, out, profile, mode="all", approved_suggest_ids=["BIB-001"])
    applied = {c.rule_id for c in changes}
    assert "BIB-001" in applied
    assert "BIB-002" in applied
    assert "BIB-003" in applied
    rem_rids = {f.rule_id for f in rem}
    assert "BIB-001" not in rem_rids
    assert "BIB-002" not in rem_rids
    assert "BIB-003" not in rem_rids

    # Idempotence
    out2 = tmp_path / "bib_fixed_2.docx"
    changes2, _ = fix_runner.run(out, out2, profile, mode="all", approved_suggest_ids=["BIB-001"])
    assert changes2 == []


def test_structure_rules_str001_to_str004_and_head006_cap005(tmp_path: Path):
    """Tests STR-001..004, HEAD-006 (skipped heading level), CAP-005 (non-sequential caption), LOF-001, LOT-001."""
    profile = profile_loader.load("contoh-s1-skripsi")
    doc = Document()
    _apply_section_geometry(doc)

    # Wrong order: BAB I appears before KATA PENGANTAR, and missing BAB II..V
    doc.add_paragraph("BAB I")
    doc.add_paragraph("PENDAHULUAN")
    # Skipped heading level: directly from BAB I (level 1) to 1.1.1 (level 3) -> HEAD-006
    p_h3 = doc.add_paragraph("1.1.1 Sub-bab Melompat Level")
    for r in p_h3.runs:
        r.bold = True

    doc.add_paragraph("KATA PENGANTAR")

    # Non-sequential captions: Gambar 1.1 followed by Gambar 1.3 (skips 2) -> CAP-005
    p_img1 = doc.add_paragraph()
    p_img1.add_run().add_picture(io.BytesIO(TINY_PNG_BYTES), width=Cm(5.0), height=Cm(4.0))
    doc.add_paragraph("Gambar 1.1 Gambar Pertama")

    p_img2 = doc.add_paragraph()
    p_img2.add_run().add_picture(io.BytesIO(TINY_PNG_BYTES), width=Cm(5.0), height=Cm(4.0))
    doc.add_paragraph("Gambar 1.3 Gambar Lompat Nomor")

    src = tmp_path / "struct_cap.docx"
    doc.save(str(src))

    ir = DocumentIR.from_docx(str(src))
    findings = rule_evaluator.evaluate(ir, profile)
    rids = {f.rule_id for f in findings}
    assert "STR-001" in rids
    assert "STR-002" in rids
    assert "STR-003" in rids
    assert "STR-004" in rids
    assert "HEAD-006" in rids
    assert "CAP-005" in rids
    assert "LOF-001" in rids

    out = tmp_path / "struct_cap_fixed.docx"
    changes, rem = fix_runner.run(src, out, profile, mode="all")
    applied = {c.rule_id for c in changes}
    assert "STR-004" in applied
    assert "CAP-005" in applied
    assert "LOF-001" in applied

    rem_rids = {f.rule_id for f in rem}
    assert "STR-004" not in rem_rids
    assert "CAP-005" not in rem_rids
    assert "LOF-001" not in rem_rids


def test_para007_manual_linebreak_and_para008_widow_control(tmp_path: Path):
    """Tests PARA-007 (manual line break Shift+Enter) and PARA-008 (widowControl disabled)."""
    profile = profile_loader.load("contoh-s1-skripsi")
    doc = Document()
    _apply_section_geometry(doc)

    p = doc.add_paragraph()
    pPr = get_or_add_pPr(p._p)
    set_boolean_prop(pPr, "widowControl", False, PPR_ORDER)
    r = p.add_run("Kalimat baris pertama")
    br = OxmlElement("w:br")
    r._r.append(br)
    t2 = OxmlElement("w:t")
    t2.text = "kalimat baris kedua dengan shift enter."
    r._r.append(t2)

    src = tmp_path / "para78.docx"
    doc.save(str(src))

    ir = DocumentIR.from_docx(str(src))
    findings = rule_evaluator.evaluate(ir, profile)
    rids = {f.rule_id for f in findings}
    assert "PARA-007" in rids
    assert "PARA-008" in rids

    out = tmp_path / "para78_fixed.docx"
    changes, rem = fix_runner.run(src, out, profile, mode="all", approved_suggest_ids=["PARA-007"])
    applied = {c.rule_id for c in changes}
    assert "PARA-007" in applied
    assert "PARA-008" in applied
    assert not any(f.rule_id in ("PARA-007", "PARA-008") for f in rem)
