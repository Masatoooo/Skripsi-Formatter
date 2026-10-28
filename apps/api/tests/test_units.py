from __future__ import annotations

from app.core.units import (
    cm_to_emu,
    cm_to_twips,
    emu_to_cm,
    half_points_to_pt,
    is_approx_equal,
    line_spacing_multiplier_to_wline,
    pt_to_half_points,
    pt_to_twips,
    twips_to_cm,
    twips_to_pt,
    wline_to_line_spacing_multiplier,
)


def test_cm_twips_conversions():
    # 2.54 cm is exactly 1 inch = 1440 twips
    assert cm_to_twips(2.54) == 1440
    assert abs(twips_to_cm(1440) - 2.54) < 1e-4

    # A4 margins: 4.0 cm ~ 2268 twips
    twips_4cm = cm_to_twips(4.0)
    assert abs(twips_to_cm(twips_4cm) - 4.0) < 0.01


def test_pt_conversions():
    # 1 pt = 20 twips
    assert pt_to_twips(12.0) == 240
    assert twips_to_pt(240) == 12.0

    # 12 pt font = 24 half-points in OOXML
    assert pt_to_half_points(12.0) == 24
    assert half_points_to_pt(24) == 12.0


def test_emu_conversions():
    # 1 cm = 360,000 EMU
    assert cm_to_emu(1.0) == 360000
    assert emu_to_cm(360000) == 1.0


def test_line_spacing_conversions():
    # Single spacing (1.0) is 240
    assert line_spacing_multiplier_to_wline(1.0) == 240
    assert wline_to_line_spacing_multiplier(240) == 1.0

    # 1.5 spacing is 360
    assert line_spacing_multiplier_to_wline(1.5) == 360
    assert wline_to_line_spacing_multiplier(360) == 1.5


def test_tolerance_equality():
    assert is_approx_equal(4.01, 4.0, tolerance=0.05) is True
    assert is_approx_equal(4.10, 4.0, tolerance=0.05) is False
