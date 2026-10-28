from __future__ import annotations

from app.core.fixers.base import BaseFixer
from app.core.fixers.bibliography import BibliographyFixer
from app.core.fixers.caption import CaptionFixer
from app.core.fixers.figure import FigureFixer
from app.core.fixers.font import FontFixer
from app.core.fixers.heading import HeadingFixer
from app.core.fixers.numbering import NumberingFixer
from app.core.fixers.page import PageFixer
from app.core.fixers.para import ParaFixer
from app.core.fixers.runner import FixRunner, fix_runner
from app.core.fixers.structure import StructureFixer
from app.core.fixers.table import TableFixer
from app.core.fixers.toc import TocFixer

__all__ = [
    "BaseFixer",
    "BibliographyFixer",
    "CaptionFixer",
    "FigureFixer",
    "FixRunner",
    "FontFixer",
    "HeadingFixer",
    "NumberingFixer",
    "PageFixer",
    "ParaFixer",
    "StructureFixer",
    "TableFixer",
    "TocFixer",
    "fix_runner",
]
