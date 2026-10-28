from __future__ import annotations

from abc import ABC, abstractmethod

from app.core.docx_model import DocumentIR
from app.core.rules.models import Change, Finding, RuleProfile


class BaseFixer(ABC):
    """Abstract base class for all category fixers."""

    category: str = "BASE"

    @abstractmethod
    def apply(
        self,
        ir: DocumentIR,
        findings: list[Finding],
        profile: RuleProfile,
    ) -> list[Change]:
        """Applies fixes to the document IR and returns records of changes made."""
        raise NotImplementedError
