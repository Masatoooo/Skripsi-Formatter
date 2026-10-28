from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.docx_model import DocumentIR
from app.core.fixers.runner import fix_runner
from app.core.integrity import normalized_text
from app.core.rules.evaluator import rule_evaluator
from app.core.rules.loader import profile_loader
from app.core.rules.models import FixMode
from tests.fixture_builder import ensure_all_fixtures


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_clean_styled_has_zero_findings_and_zero_changes(tmp_path: Path):
    fixtures_dir = ensure_all_fixtures()
    clean_path = fixtures_dir / "clean_styled.docx"
    profile = profile_loader.load("contoh-s1-skripsi")

    ir = DocumentIR.from_docx(str(clean_path))
    findings = rule_evaluator.evaluate(ir, profile)
    assert findings == [], f"Expected 0 findings on clean_styled.docx, got: {findings}"

    out_path = tmp_path / "clean_out.docx"
    changes, remaining = fix_runner.run(clean_path, out_path, profile, mode="all")
    assert changes == []
    assert remaining == []
    assert normalized_text(clean_path) == normalized_text(out_path)


def test_wrong_margins_fixer_idempotence_and_integrity(tmp_path: Path):
    fixtures_dir = ensure_all_fixtures()
    src = fixtures_dir / "wrong_margins.docx"
    orig_hash = _sha256(src)
    profile = profile_loader.load("contoh-s1-skripsi")

    ir_before = DocumentIR.from_docx(str(src))
    findings_before = rule_evaluator.evaluate(ir_before, profile)
    page_rule_ids = {f.rule_id for f in findings_before if f.category == "PAGE"}
    assert "PAGE-002" in page_rule_ids

    fixed_1 = tmp_path / "fixed_1.docx"
    changes_1, remaining_1 = fix_runner.run(src, fixed_1, profile, mode="all")
    assert len(changes_1) >= 4
    assert not any(f.category == "PAGE" and f.fix_mode == FixMode.AUTO for f in remaining_1)

    # Original file must be untouched
    assert _sha256(src) == orig_hash
    # Text integrity must be 100% identical
    assert normalized_text(src) == normalized_text(fixed_1)

    # Idempotence: running fix again produces 0 changes
    fixed_2 = tmp_path / "fixed_2.docx"
    changes_2, remaining_2 = fix_runner.run(fixed_1, fixed_2, profile, mode="all")
    assert changes_2 == []
    assert remaining_2 == remaining_1
    assert normalized_text(fixed_1) == normalized_text(fixed_2)


def test_manual_formatting_fixes_font_para_head_and_idempotence(tmp_path: Path):
    fixtures_dir = ensure_all_fixtures()
    src = fixtures_dir / "manual_formatting.docx"
    orig_hash = _sha256(src)
    profile = profile_loader.load("contoh-s1-skripsi")

    ir_before = DocumentIR.from_docx(str(src))
    findings_before = rule_evaluator.evaluate(ir_before, profile)
    rule_ids = {f.rule_id for f in findings_before}
    assert "FONT-001" in rule_ids
    assert "FONT-002" in rule_ids
    assert "FONT-004" in rule_ids
    assert "PARA-005" in rule_ids
    assert "PARA-006" in rule_ids

    # 1. Auto fixes only: text must be strictly identical
    fixed_auto = tmp_path / "manual_fixed_auto.docx"
    changes_auto, rem_auto = fix_runner.run(src, fixed_auto, profile, mode="all")
    assert len(changes_auto) > 0
    assert _sha256(src) == orig_hash
    assert normalized_text(src) == normalized_text(fixed_auto)

    # Idempotence on auto fixes
    fixed_auto_2 = tmp_path / "manual_fixed_auto_2.docx"
    changes_auto_2, _ = fix_runner.run(fixed_auto, fixed_auto_2, profile, mode="all")
    assert changes_auto_2 == []

    # 2. Approved suggest fixes (PARA-005, PARA-006, HEAD-003)
    fixed_suggest = tmp_path / "manual_fixed_suggest.docx"
    changes_sug, _ = fix_runner.run(
        src,
        fixed_suggest,
        profile,
        mode="all",
        approved_suggest_ids=["PARA-005", "PARA-006", "HEAD-003"],
    )
    applied_rules = {c.rule_id for c in changes_sug}
    assert "PARA-005" in applied_rules
    assert "PARA-006" in applied_rules
    assert "HEAD-003" in applied_rules


def test_with_tables_figures_and_captions_fixer(tmp_path: Path):
    fixtures_dir = ensure_all_fixtures()
    src = fixtures_dir / "with_tables_figures.docx"
    profile = profile_loader.load("contoh-s1-skripsi")

    ir_before = DocumentIR.from_docx(str(src))
    findings_before = rule_evaluator.evaluate(ir_before, profile)
    rule_ids = {f.rule_id for f in findings_before}
    assert "FIG-001" in rule_ids
    assert "FIG-002" in rule_ids
    assert "TBL-001" in rule_ids
    assert "TBL-002" in rule_ids
    assert "TBL-003" in rule_ids
    assert "CAP-002" in rule_ids

    fixed_1 = tmp_path / "tbl_fig_fixed_1.docx"
    changes_1, rem_1 = fix_runner.run(
        src,
        fixed_1,
        profile,
        mode="all",
        approved_suggest_ids=["CAP-004"],
    )
    assert len(changes_1) > 0
    assert normalized_text(src) == normalized_text(fixed_1)

    rem_rule_ids = {f.rule_id for f in rem_1}
    assert "FIG-001" not in rem_rule_ids
    assert "FIG-002" not in rem_rule_ids
    assert "TBL-001" not in rem_rule_ids
    assert "TBL-002" not in rem_rule_ids
    assert "TBL-003" not in rem_rule_ids
    assert "CAP-002" not in rem_rule_ids
    assert "CAP-004" not in rem_rule_ids

    # Idempotence check
    fixed_2 = tmp_path / "tbl_fig_fixed_2.docx"
    changes_2, _ = fix_runner.run(
        fixed_1,
        fixed_2,
        profile,
        mode="all",
        approved_suggest_ids=["CAP-004"],
    )
    assert changes_2 == []


def test_multi_section_and_page_numbering_fixer(tmp_path: Path):
    fixtures_dir = ensure_all_fixtures()
    src = fixtures_dir / "multi_section.docx"
    profile = profile_loader.load("contoh-s1-skripsi")

    ir_before = DocumentIR.from_docx(str(src))
    findings_before = rule_evaluator.evaluate(ir_before, profile)
    rule_ids = {f.rule_id for f in findings_before}
    assert "NUM-001" in rule_ids
    assert "NUM-002" in rule_ids
    assert "NUM-003" in rule_ids
    assert "NUM-005" in rule_ids

    fixed_1 = tmp_path / "multi_sec_fixed_1.docx"
    changes_1, rem_1 = fix_runner.run(src, fixed_1, profile, mode="all")
    assert len(changes_1) > 0
    assert normalized_text(src) == normalized_text(fixed_1)

    rem_num_rules = {f.rule_id for f in rem_1 if f.category == "NUM" and f.fix_mode == FixMode.AUTO}
    assert rem_num_rules == set()

    # Idempotence
    fixed_2 = tmp_path / "multi_sec_fixed_2.docx"
    changes_2, _ = fix_runner.run(fixed_1, fixed_2, profile, mode="all")
    assert changes_2 == []


def test_typed_toc_and_typed_numbers_suggest_fixers(tmp_path: Path):
    fixtures_dir = ensure_all_fixtures()
    profile = profile_loader.load("contoh-s1-skripsi")

    # 1. typed_toc.docx -> TOC-002 suggest conversion to TOC field
    src_toc = fixtures_dir / "typed_toc.docx"
    ir_toc = DocumentIR.from_docx(str(src_toc))
    f_toc = rule_evaluator.evaluate(ir_toc, profile)
    assert any(f.rule_id == "TOC-002" for f in f_toc)

    out_toc = tmp_path / "toc_fixed.docx"
    changes_toc, rem_toc = fix_runner.run(
        src_toc, out_toc, profile, mode="all", approved_suggest_ids=["TOC-002"]
    )
    assert any(c.rule_id == "TOC-002" for c in changes_toc)
    assert not any(f.rule_id == "TOC-002" for f in rem_toc)

    # 2. typed_numbers.docx -> HEAD-003, NUM-006, CAP-004
    src_num = fixtures_dir / "typed_numbers.docx"
    ir_num = DocumentIR.from_docx(str(src_num))
    f_num = rule_evaluator.evaluate(ir_num, profile)
    num_rule_ids = {f.rule_id for f in f_num}
    assert "HEAD-003" in num_rule_ids
    assert "NUM-006" in num_rule_ids
    assert "CAP-004" in num_rule_ids

    out_num = tmp_path / "num_fixed.docx"
    changes_num, rem_num = fix_runner.run(
        src_num,
        out_num,
        profile,
        mode="all",
        approved_suggest_ids=["HEAD-003", "NUM-006", "CAP-004"],
    )
    applied = {c.rule_id for c in changes_num}
    assert "HEAD-003" in applied
    assert "NUM-006" in applied
    assert "CAP-004" in applied


def test_tracked_changes_detected_and_protected(tmp_path: Path):
    fixtures_dir = ensure_all_fixtures()
    src = fixtures_dir / "tracked_changes.docx"
    profile = profile_loader.load("contoh-s1-skripsi")

    ir = DocumentIR.from_docx(str(src))
    assert ir.has_tracked_changes is True
    assert ir.has_comments is True

    findings = rule_evaluator.evaluate(ir, profile)
    assert any(f.rule_id == "DOC-001" for f in findings)

    out = tmp_path / "tc_fixed.docx"
    _, _ = fix_runner.run(src, out, profile, mode="all")
    assert normalized_text(src) == normalized_text(out)
