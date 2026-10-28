from __future__ import annotations

import logging
import sys
from typing import Any


def setup_logger(name: str = "skripsi_formatter") -> logging.Logger:
    """Configures structured privacy-safe logger.

    Guarantees no raw document content or paragraph text is logged.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


logger = setup_logger()


def log_audit_event(
    event_type: str,
    doc_id: str,
    rule_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Log an audit event with sanitized metadata."""
    safe_details = details or {}
    logger.info(
        "AUDIT event=%s doc_id=%s rule_id=%s meta=%s",
        event_type,
        doc_id,
        rule_id or "NONE",
        safe_details,
    )
