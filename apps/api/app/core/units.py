from __future__ import annotations

# Paper dimensions in cm (portrait: width x height)
PAPER_SIZES_CM: dict[str, tuple[float, float]] = {
    "A4": (21.0, 29.7),
    "Letter": (21.59, 27.94),
    "Legal": (21.59, 35.56),
}

# Fundamental OOXML Conversion Constants
TWIPS_PER_INCH: float = 1440.0
CM_PER_INCH: float = 2.54
TWIPS_PER_CM: float = TWIPS_PER_INCH / CM_PER_INCH  # ~566.929133858
TWIPS_PER_PT: float = 20.0
EMU_PER_INCH: float = 914400.0
EMU_PER_CM: float = EMU_PER_INCH / CM_PER_INCH  # 360000.0
EMU_PER_PT: float = EMU_PER_INCH / 72.0  # 12700.0

HALF_POINTS_PER_PT: float = 2.0
LINE_SPACING_UNIT: float = 240.0  # w:line="240" is 1.0 (single)


def cm_to_twips(cm: float) -> int:
    """Converts centimeters to OOXML twips."""
    return int(round(cm * TWIPS_PER_CM))


def twips_to_cm(twips: int | float) -> float:
    """Converts OOXML twips to centimeters."""
    return float(twips) / TWIPS_PER_CM


def pt_to_twips(pt: float) -> int:
    """Converts typography points (pt) to twips."""
    return int(round(pt * TWIPS_PER_PT))


def twips_to_pt(twips: int | float) -> float:
    """Converts OOXML twips to typography points."""
    return float(twips) / TWIPS_PER_PT


def pt_to_half_points(pt: float) -> int:
    """Converts font size in pt to OOXML half-points (w:sz)."""
    return int(round(pt * HALF_POINTS_PER_PT))


def half_points_to_pt(half_pts: int | float) -> float:
    """Converts OOXML half-points (w:sz) to font size in pt."""
    return float(half_pts) / HALF_POINTS_PER_PT


def cm_to_emu(cm: float) -> int:
    """Converts centimeters to OOXML EMU (English Metric Units)."""
    return int(round(cm * EMU_PER_CM))


def emu_to_cm(emu: int | float) -> float:
    """Converts OOXML EMU to centimeters."""
    return float(emu) / EMU_PER_CM


def line_spacing_multiplier_to_wline(multiplier: float) -> int:
    """Converts line spacing multiplier (e.g. 1.5) to OOXML w:line auto value (e.g. 360)."""
    return int(round(multiplier * LINE_SPACING_UNIT))


def wline_to_line_spacing_multiplier(w_line: int | float) -> float:
    """Converts OOXML w:line value to line spacing multiplier."""
    return float(w_line) / LINE_SPACING_UNIT


def get_paper_dimensions_cm(size_name: str, orientation: str = "portrait") -> tuple[float, float]:
    """Returns (width_cm, height_cm) for a given paper size and orientation."""
    w, h = PAPER_SIZES_CM.get(size_name, PAPER_SIZES_CM["A4"])
    if orientation.lower() == "landscape":
        return (max(w, h), min(w, h))
    return (min(w, h), max(w, h))


def is_approx_equal(actual: float, expected: float, tolerance: float = 0.05) -> bool:
    """Checks if two float values are equal within an allowable tolerance."""
    return abs(actual - expected) <= tolerance
