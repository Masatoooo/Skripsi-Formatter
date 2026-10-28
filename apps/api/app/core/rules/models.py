from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class FixMode(str, Enum):
    AUTO = "auto"
    SUGGEST = "suggest"
    MANUAL = "manual"


class FixMethod(str, Enum):
    STYLE = "style"
    DIRECT = "direct"


class Location(BaseModel):
    block_index: int = 0
    section_index: int = 0
    approx_page: Optional[int] = None
    excerpt: Optional[str] = None


class Finding(BaseModel):
    id: str
    rule_id: str
    category: str  # PAGE, FONT, PARA, HEAD, NUM, TOC, etc.
    severity: Severity
    location: Location
    actual: Any
    expected: Any
    fix_mode: FixMode
    message_id: str
    message: str


class Change(BaseModel):
    finding_id: str
    rule_id: str
    location: Location
    old_value: Any
    new_value: Any
    method: FixMethod


class RoleAssignment(BaseModel):
    block_index: int
    role: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    user_confirmed: bool = False


# Profile models
class MarginsCm(BaseModel):
    top: float
    left: float
    bottom: float
    right: float


class PageConfig(BaseModel):
    size: str = "A4"
    orientation: str = "portrait"
    margins_cm: MarginsCm
    header_footer_distance_cm: Optional[dict[str, float]] = None


class TextConfig(BaseModel):
    font_family: str = "Times New Roman"
    font_size_pt: float = 12.0
    color_hex: str = "000000"


class RuleOverride(BaseModel):
    id: str
    enabled: bool = True
    severity: Optional[Severity] = None
    fix_mode: Optional[FixMode] = None


class RuleProfile(BaseModel):
    profile_id: str
    name: str
    version: str
    language: str = "id"
    extends: Optional[str] = None
    source: dict[str, str]
    page: PageConfig
    text: TextConfig
    roles: dict[str, dict[str, Any]]
    page_numbering: dict[str, Any]
    structure: dict[str, Any]
    toc: dict[str, Any]
    captions: dict[str, Any]
    tolerances: dict[str, float] = Field(default_factory=dict)
    rules: list[RuleOverride] = Field(default_factory=list)
