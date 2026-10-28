from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi import HTTPException, status
from lxml import etree

from app.config import settings
from app.core.messages import ErrorCode, format_message
from app.core.xml_helpers import safe_parse_xml_bytes


class IngestValidator:
    """Validates incoming document uploads for integrity and security."""

    @staticmethod
    def _raise_error(status_code: int, code: str, message_id: str, **kwargs: object) -> None:
        raise HTTPException(
            status_code=status_code,
            detail=format_message(message_id, **kwargs),
            headers={"X-Error-Code": code},
        )

    @classmethod
    def validate_file(cls, filename: str, content: bytes) -> None:
        """Thoroughly inspects uploaded content for security and format validity."""
        # 1. Extension check
        ext = Path(filename).suffix.lower()
        if ext != ".docx":
            if ext == ".docm":
                cls._raise_error(
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.INGEST_MACRO_DETECTED,
                    "ingest.err.docm",
                )
            elif ext == ".doc":
                cls._raise_error(
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.INGEST_LEGACY_DOC,
                    "ingest.err.doc",
                )
            else:
                cls._raise_error(
                    status.HTTP_400_BAD_REQUEST,
                    ErrorCode.INGEST_INVALID_EXT,
                    "ingest.err.ext",
                    ext=ext or "unknown",
                )

        # 2. File size check
        if len(content) > settings.max_upload_size_bytes:
            cls._raise_error(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                ErrorCode.INGEST_FILE_TOO_LARGE,
                "ingest.err.size",
                max_mb=settings.max_upload_size_bytes // (1024 * 1024),
            )

        if len(content) == 0:
            cls._raise_error(
                status.HTTP_400_BAD_REQUEST,
                ErrorCode.INGEST_EMPTY_FILE,
                "ingest.err.empty",
            )

        # 3. ZIP integrity, zip-bomb, path traversal, macro, and XXE checks
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                entries = zf.infolist()
                if len(entries) > settings.max_zip_entries:
                    cls._raise_error(
                        status.HTTP_400_BAD_REQUEST,
                        ErrorCode.INGEST_TOO_MANY_ENTRIES,
                        "ingest.err.zip_entries",
                    )

                total_uncompressed = 0
                has_word_document = False

                for entry in entries:
                    norm_name = entry.filename.replace("\\", "/")
                    # Anti-Path Traversal
                    if (
                        norm_name.startswith("/")
                        or ".." in norm_name.split("/")
                        or ".." in entry.filename
                    ):
                        cls._raise_error(
                            status.HTTP_400_BAD_REQUEST,
                            ErrorCode.INGEST_PATH_TRAVERSAL,
                            "ingest.err.traversal",
                        )

                    # Macro detection
                    lower_name = norm_name.lower()
                    if "vbaproject.bin" in lower_name or lower_name.endswith("vbaproject.bin"):
                        cls._raise_error(
                            status.HTTP_400_BAD_REQUEST,
                            ErrorCode.INGEST_MACRO_DETECTED,
                            "ingest.err.macro",
                        )

                    if norm_name == "word/document.xml":
                        has_word_document = True

                    total_uncompressed += entry.file_size
                    if total_uncompressed > settings.max_uncompressed_bytes:
                        cls._raise_error(
                            status.HTTP_400_BAD_REQUEST,
                            ErrorCode.INGEST_ZIP_BOMB,
                            "ingest.err.zip_bomb",
                        )

                if not has_word_document:
                    cls._raise_error(
                        status.HTTP_400_BAD_REQUEST,
                        ErrorCode.INGEST_MISSING_DOCUMENT_XML,
                        "ingest.err.no_doc_xml",
                    )

                # 4. Safe XML parsing (anti-XXE / DTD / macro content-type check)
                for entry in entries:
                    norm_name = entry.filename.replace("\\", "/")
                    if norm_name.endswith(".xml") or norm_name.endswith(".rels"):
                        raw_xml = zf.read(entry.filename)
                        try:
                            safe_parse_xml_bytes(raw_xml)
                        except ValueError:
                            cls._raise_error(
                                status.HTTP_400_BAD_REQUEST,
                                ErrorCode.INGEST_XXE_DETECTED,
                                "ingest.err.xxe",
                            )
                        except etree.XMLSyntaxError:
                            cls._raise_error(
                                status.HTTP_400_BAD_REQUEST,
                                ErrorCode.INGEST_MALFORMED_XML,
                                "ingest.err.malformed_xml",
                            )

                        if norm_name == "[Content_Types].xml":
                            xml_str = raw_xml.decode("utf-8", errors="ignore").lower()
                            if "macroenabled" in xml_str or "vnd.ms-office.vbaproject" in xml_str:
                                cls._raise_error(
                                    status.HTTP_400_BAD_REQUEST,
                                    ErrorCode.INGEST_MACRO_DETECTED,
                                    "ingest.err.macro",
                                )

        except zipfile.BadZipFile:
            cls._raise_error(
                status.HTTP_400_BAD_REQUEST,
                ErrorCode.INGEST_INVALID_ZIP,
                "ingest.err.bad_zip",
            )


validator = IngestValidator()
