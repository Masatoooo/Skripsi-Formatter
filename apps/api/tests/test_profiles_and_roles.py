from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from app.core.docx_model import DocumentIR
from app.core.roles import role_classifier
from app.core.rules.loader import ProfileLoader, profile_loader
from tests.fixture_builder import ensure_all_fixtures


def test_profile_loader_and_extends_inheritance(tmp_path: Path):
    base_profile = profile_loader.load("contoh-s1-skripsi")
    assert base_profile.profile_id == "contoh-s1-skripsi"
    assert base_profile.page.margins_cm.top == 4.0
    assert base_profile.captions["figure"]["numbering"] == "per_chapter"

    child_profile = profile_loader.load("contoh-s1-teknik")
    assert child_profile.profile_id == "contoh-s1-teknik"
    assert child_profile.extends == "contoh-s1-skripsi"
    # Inherited from parent
    assert child_profile.page.margins_cm.top == 4.0
    assert child_profile.text.font_family == "Times New Roman"
    # Overridden in child
    assert child_profile.captions["figure"]["numbering"] == "continuous"


def test_invalid_profile_rejected_and_filtered(tmp_path: Path):
    schema_dir = tmp_path / "schema"
    schema_dir.mkdir(parents=True)
    orig_schema = profile_loader.schema_path.read_text(encoding="utf-8")
    (schema_dir / "profile.schema.json").write_text(orig_schema, encoding="utf-8")

    # Write one valid profile and one invalid profile (missing required fields)
    orig_valid = (profile_loader.profiles_dir / "contoh-s1-skripsi.json").read_text(
        encoding="utf-8"
    )
    (tmp_path / "contoh-s1-skripsi.json").write_text(orig_valid, encoding="utf-8")
    (tmp_path / "bad-profile.json").write_text(
        json.dumps({"profile_id": "bad-profile", "name": "Invalid Missing Fields"}),
        encoding="utf-8",
    )

    loader = ProfileLoader(profiles_dir=tmp_path)
    with pytest.raises(jsonschema.ValidationError):
        loader.load("bad-profile")

    available = loader.list_available_profiles()
    assert len(available) == 1
    assert available[0]["profile_id"] == "contoh-s1-skripsi"


def test_role_classification_on_styled_and_localized_documents():
    fixtures_dir = ensure_all_fixtures()

    ir_local = DocumentIR.from_docx(str(fixtures_dir / "localized_styles.docx"))
    roles_local = role_classifier.classify(ir_local)
    role_map = {r.block_index: r for r in roles_local}

    # Block 0 is "BAB I" with styleId="Heading1" (UI name "Judul 1") -> chapter_label with high confidence
    assert role_map[0].role == "chapter_label"
    assert role_map[0].confidence >= 0.90
    assert role_map[1].role == "chapter_title"
    assert role_map[1].confidence >= 0.90
    assert role_map[2].role == "body"


def test_role_classification_low_confidence_on_no_styles():
    fixtures_dir = ensure_all_fixtures()
    ir_no_styles = DocumentIR.from_docx(str(fixtures_dir / "no_styles.docx"))
    roles = role_classifier.classify(ir_no_styles)

    # In no_styles.docx, "BAB I", "Pendahuluan", and "1.1 Latar Belakang Penelitian" have no style and no bold/center
    assert roles[0].role == "chapter_label"
    assert roles[0].confidence < 0.70  # Flagged for user confirmation
    assert roles[1].role == "chapter_title"
    assert roles[1].confidence < 0.70
    assert roles[2].role == "heading_2"
    assert roles[2].confidence < 0.70
    assert roles[3].role == "body"
    assert roles[3].confidence >= 0.85


def test_role_classification_sdt_and_textboxes_do_not_crash():
    fixtures_dir = ensure_all_fixtures()
    ir_sdt = DocumentIR.from_docx(str(fixtures_dir / "textboxes_sdt.docx"))
    assert ir_sdt.has_sdt is True
    assert ir_sdt.has_textbox is True
    roles = role_classifier.classify(ir_sdt)
    assert len(roles) >= 3
