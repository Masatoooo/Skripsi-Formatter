from __future__ import annotations

import re

from app.core.docx_model import DocumentBlock, DocumentIR
from app.core.formatting import EffectiveFormat, StyleHierarchyResolver
from app.core.rules.models import RoleAssignment

DEFAULT_CONFIDENCE_THRESHOLD: float = 0.70

FRONT_MATTER_TITLES_RE = re.compile(
    r"^(HALAMAN\s+SAMPUL|HALAMAN\s+JUDUL|LEMBAR\s+PENGESAHAN|HALAMAN\s+PENGESAHAN|"
    r"LEMBAR\s+PERSETUJUAN|PERNYATAAN\s+KEASLIAN|KATA\s+PENGANTAR|UCAPAN\s+TERIMA\s+KASIH|"
    r"ABSTRAK|ABSTRACT|DAFTAR\s+ISI|DAFTAR\s+TABEL|DAFTAR\s+GAMBAR|DAFTAR\s+LAMPIRAN|"
    r"DAFTAR\s+SINGKATAN|DAFTAR\s+LAMBANG|DAFTAR\s+PUSTAKA|LAMPIRAN(\s+[A-Z0-9IVX]+)?)$",
    re.IGNORECASE,
)

CHAPTER_LABEL_RE = re.compile(
    r"^BAB\s+([IVXLCDM]+|\d+)(\s*$|[\s\n:—\-]+.+)",
    re.IGNORECASE,
)

TYPED_TOC_LINE_RE = re.compile(r"^.+?(?:\.{2,}|\t+)\s*([ivxlcdmIVXLCDM]+|\d+)\s*$")


class RoleClassifier:
    """Classifies structural roles of document blocks with confidence and evidence."""

    def __init__(self, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD) -> None:
        self.confidence_threshold = confidence_threshold

    def classify(
        self,
        ir: DocumentIR,
        resolver: StyleHierarchyResolver | None = None,
        user_overrides: dict[int, str] | None = None,
    ) -> list[RoleAssignment]:
        if resolver is None:
            resolver = StyleHierarchyResolver(ir.doc)

        overrides = user_overrides or {}
        assignments: list[RoleAssignment] = []

        # Track document region context as we walk top-to-bottom
        current_region = (
            "initial"  # "cover" | "front_matter" | "toc" | "body" | "bibliography" | "appendix"
        )
        prev_role: str | None = None

        # Pre-compute effective formatting for paragraphs
        formats: dict[int, EffectiveFormat] = {}
        for block in ir.blocks:
            if block.block_type == "paragraph":
                formats[block.index] = resolver.resolve_paragraph(block.raw_element)

        total_blocks = len(ir.blocks)

        for idx, block in enumerate(ir.blocks):
            # 1. User confirmed override takes top precedence
            if block.index in overrides:
                role = overrides[block.index]
                block.assigned_role = role
                block.confidence = 1.0
                block.evidence = ["Dikonfirmasi langsung oleh pengguna"]
                block.user_confirmed = True
                assignments.append(
                    RoleAssignment(
                        block_index=block.index,
                        role=role,
                        confidence=1.0,
                        evidence=block.evidence,
                        user_confirmed=True,
                    )
                )
                prev_role = role
                current_region = self._update_region(current_region, role, block.text)
                continue

            # 2. Table block
            if block.block_type == "table":
                block.assigned_role = "table_text"
                block.confidence = 1.0
                block.evidence = ["Elemen tabel OOXML (w:tbl)"]
                assignments.append(
                    RoleAssignment(
                        block_index=block.index,
                        role="table_text",
                        confidence=1.0,
                        evidence=block.evidence,
                    )
                )
                prev_role = "table_text"
                continue

            text_raw = block.text or ""
            text_clean = re.sub(r"[ \t\u00a0]+", " ", text_raw).strip()
            fmt = formats[block.index]

            # 3. TOC Field paragraph
            if any(f.field_type == "TOC" for f in block.fields):
                block.assigned_role = "toc_entry"
                block.confidence = 1.0
                block.evidence = ["Memuat field TOC otomatis Word"]
                assignments.append(
                    RoleAssignment(
                        block_index=block.index,
                        role="toc_entry",
                        confidence=1.0,
                        evidence=block.evidence,
                    )
                )
                prev_role = "toc_entry"
                continue

            # 4. Empty or image-only paragraph
            if not text_clean:
                block.assigned_role = "other"
                block.confidence = 1.0
                ev = ["Paragraf gambar inline"] if block.images else ["Paragraf kosong"]
                block.evidence = ev
                assignments.append(
                    RoleAssignment(
                        block_index=block.index,
                        role="other",
                        confidence=1.0,
                        evidence=ev,
                    )
                )
                continue

            # 5. Classify via style, outline level, regex heuristics, and positional context
            role, conf, evidence = self._classify_paragraph(
                block=block,
                text_clean=text_clean,
                fmt=fmt,
                prev_role=prev_role,
                current_region=current_region,
                prev_block=ir.blocks[idx - 1] if idx > 0 else None,
                next_block=ir.blocks[idx + 1] if idx + 1 < total_blocks else None,
            )

            block.assigned_role = role
            block.confidence = round(conf, 2)
            block.evidence = evidence
            assignments.append(
                RoleAssignment(
                    block_index=block.index,
                    role=role,
                    confidence=block.confidence,
                    evidence=evidence,
                )
            )
            prev_role = role
            current_region = self._update_region(current_region, role, text_clean)

        return assignments

    def _update_region(self, current_region: str, role: str, text_clean: str) -> str:
        upper = text_clean.upper().strip()
        if re.match(r"^HALAMAN\s+SAMPUL$", upper):
            return "cover"
        if role == "front_title":
            if "DAFTAR PUSTAKA" in upper:
                return "bibliography"
            if upper.startswith("LAMPIRAN"):
                return "appendix"
            if "DAFTAR ISI" in upper or "DAFTAR GAMBAR" in upper or "DAFTAR TABEL" in upper:
                return "toc"
            return "front_matter"
        if role in ("chapter_label", "chapter_title", "heading_2", "heading_3", "heading_4"):
            return "body"
        return current_region

    def _classify_paragraph(
        self,
        block: DocumentBlock,
        text_clean: str,
        fmt: EffectiveFormat,
        prev_role: str | None,
        current_region: str,
        prev_block: DocumentBlock | None,
        next_block: DocumentBlock | None,
    ) -> tuple[str, float, list[str]]:
        evidence: list[str] = []
        style_key = re.sub(r"[\s_\-]+", "", (block.style_id or "")).lower()
        style_name_key = re.sub(r"[\s_\-]+", "", (block.style_name or "")).lower()
        combined_styles = {style_key, style_name_key}

        upper_text = text_clean.upper()

        # --- Layer 1: Explicit Special Styles (TOC, Footnote, Bibliography, Quote, Caption) ---
        if any(
            s.startswith("toc") or s in ("tableoffigures", "tableofauthorities")
            for s in combined_styles
            if s
        ):
            return "toc_entry", 0.98, [f"Menggunakan style daftar isi ({block.style_id})"]

        if any("footnote" in s for s in combined_styles if s):
            return "footnote_text", 0.98, [f"Menggunakan style catatan kaki ({block.style_id})"]

        if any("bibliography" in s or "pustaka" in s for s in combined_styles if s):
            return "bibliography_entry", 0.96, [f"Menggunakan style pustaka ({block.style_id})"]

        if any(
            s in ("quote", "intensequote", "blocktext", "blockquote", "kutipan")
            for s in combined_styles
            if s
        ):
            return "block_quote", 0.95, [f"Menggunakan style kutipan ({block.style_id})"]

        if any("caption" in s for s in combined_styles if s):
            if re.match(r"^(tabel|table)\b", text_clean, re.IGNORECASE):
                return (
                    "caption_table",
                    0.96,
                    [f"Style Caption ({block.style_id}) dengan awalan 'Tabel'"],
                )
            return "caption_figure", 0.96, [f"Style Caption ({block.style_id})"]

        # --- Layer 2: Heading Styles & Outline Levels ---
        is_h1_style = (
            any(s in ("heading1", "judul1", "bab") for s in combined_styles)
            or fmt.outline_level == 0
        )
        is_h2_style = (
            any(s in ("heading2", "judul2", "subbab") for s in combined_styles)
            or fmt.outline_level == 1
        )
        is_h3_style = (
            any(s in ("heading3", "judul3", "anaksubbab") for s in combined_styles)
            or fmt.outline_level == 2
        )
        is_h4_style = (
            any(s in ("heading4", "judul4") for s in combined_styles) or fmt.outline_level == 3
        )

        # Check front-matter / back-matter titles (e.g. KATA PENGANTAR, DAFTAR ISI, DAFTAR PUSTAKA)
        if FRONT_MATTER_TITLES_RE.match(text_clean):
            if re.match(r"^HALAMAN\s+SAMPUL$", upper_text):
                return "cover", 0.96, ["Teks cocok dengan penanda Halaman Sampul"]
            if is_h1_style:
                return (
                    "front_title",
                    0.98,
                    [f"Style Heading 1 ({block.style_id}) dan pola judul bagian '{text_clean}'"],
                )
            conf = 0.62
            evidence.append(f"Pola teks judul bagian baku ('{text_clean}')")
            if fmt.bold:
                conf += 0.18
                evidence.append("Huruf tebal (bold)")
            if fmt.alignment == "center":
                conf += 0.15
                evidence.append("Rata tengah (center)")
            return "front_title", min(0.95, conf), evidence

        # Check BAB label (`BAB I`, `BAB II`, etc.)
        if CHAPTER_LABEL_RE.match(text_clean):
            if is_h1_style:
                return (
                    "chapter_label",
                    0.98,
                    [f"Style Heading 1 ({block.style_id}) dan pola label BAB"],
                )
            conf = 0.60
            evidence.append(f"Pola teks label bab ('{text_clean.splitlines()[0]}')")
            if fmt.bold:
                conf += 0.20
                evidence.append("Huruf tebal (bold)")
            if fmt.alignment == "center":
                conf += 0.15
                evidence.append("Rata tengah (center)")
            return "chapter_label", min(0.95, conf), evidence

        # If styled as Heading 1, check if it's chapter_title
        if is_h1_style:
            return (
                "chapter_title",
                0.95,
                [f"Menggunakan style Heading 1 / outline level 1 ({block.style_id})"],
            )

        if is_h2_style:
            return (
                "heading_2",
                0.95,
                [f"Menggunakan style Heading 2 / outline level 2 ({block.style_id})"],
            )

        if is_h3_style:
            return (
                "heading_3",
                0.95,
                [f"Menggunakan style Heading 3 / outline level 3 ({block.style_id})"],
            )

        if is_h4_style:
            return (
                "heading_4",
                0.95,
                [f"Menggunakan style Heading 4 / outline level 4 ({block.style_id})"],
            )

        # --- Layer 3: Positional & Pattern Heuristics (when no Heading style is applied) ---

        # 3a. Immediately after `chapter_label`: likely `chapter_title`
        if prev_role == "chapter_label" and len(text_clean) <= 140 and not text_clean.endswith("."):
            conf = 0.58
            evidence.append("Berada tepat setelah baris label BAB")
            if fmt.bold:
                conf += 0.20
                evidence.append("Huruf tebal (bold)")
            if fmt.alignment == "center" or text_clean.isupper():
                conf += 0.15
                evidence.append("Rata tengah / huruf kapital semua")
            return "chapter_title", min(0.94, conf), evidence

        # 3b. Cover section paragraphs
        if current_region == "cover":
            return "cover", 0.90, ["Berada pada bagian Halaman Sampul"]

        # 3c. Typed TOC lines (either in `toc` region or matching `Title ....... 12`)
        if TYPED_TOC_LINE_RE.match(text_clean):
            return (
                "toc_entry",
                0.90,
                ["Pola baris Daftar Isi dengan titik pemandu dan nomor halaman"],
            )
        if current_region == "toc" and re.search(r"\s([ivxlcdmIVXLCDM]+|\d+)\s*$", text_clean):
            return (
                "toc_entry",
                0.85,
                ["Berada di bawah bagian Daftar Isi dan diakhiri nomor halaman"],
            )

        # 3d. Captions (Figure & Table)
        if re.match(r"^(Gambar|Figure|Grafik|Bagan)\s+\d+([.\-]\d+)?\b", text_clean, re.IGNORECASE):
            conf = 0.88
            evidence.append("Pola teks diawali label 'Gambar' diikuti nomor")
            if (prev_block and prev_block.images) or (next_block and next_block.images):
                conf = 0.94
                evidence.append("Berada berdampingan langsung dengan elemen gambar")
            return "caption_figure", conf, evidence

        if re.match(r"^(Tabel|Table)\s+\d+([.\-]\d+)?\b", text_clean, re.IGNORECASE):
            conf = 0.88
            evidence.append("Pola teks diawali label 'Tabel' diikuti nomor")
            if (prev_block and prev_block.block_type == "table") or (
                next_block and next_block.block_type == "table"
            ):
                conf = 0.94
                evidence.append("Berada berdampingan langsung dengan elemen tabel")
            return "caption_table", conf, evidence

        # Positional candidate caption without standard label (low confidence -> asks user)
        if (
            prev_block
            and prev_block.images
            and len(text_clean) <= 120
            and fmt.alignment == "center"
        ):
            return (
                "caption_figure",
                0.62,
                ["Berada tepat di bawah gambar dan rata tengah, namun tanpa awalan 'Gambar' baku"],
            )

        # 3e. Numbered Sub-headings (e.g. `1.1 Latar Belakang`, `1.1.1 Rumusan`)
        if len(text_clean) <= 140 and not text_clean.endswith("."):
            if re.match(r"^\d+\.\d+\.\d+\.\d+\s+[A-Za-z]", text_clean):
                conf = 0.64 + (0.22 if fmt.bold else 0.0)
                evidence.append("Pola penomoran sub-bab 4 tingkat (x.x.x.x)")
                if fmt.bold:
                    evidence.append("Huruf tebal (bold)")
                return "heading_4", conf, evidence

            if re.match(r"^\d+\.\d+\.\d+\s+[A-Za-z]", text_clean):
                conf = 0.64 + (0.22 if fmt.bold else 0.0)
                evidence.append("Pola penomoran sub-bab 3 tingkat (x.x.x)")
                if fmt.bold:
                    evidence.append("Huruf tebal (bold)")
                return "heading_3", conf, evidence

            if re.match(r"^\d+\.\d+\s+[A-Za-z]", text_clean):
                conf = 0.64 + (0.22 if fmt.bold else 0.0)
                evidence.append("Pola penomoran sub-bab 2 tingkat (x.x)")
                if fmt.bold:
                    evidence.append("Huruf tebal (bold)")
                return "heading_2", conf, evidence

        # 3f. Bibliography entries (inside `DAFTAR PUSTAKA` region)
        if current_region == "bibliography":
            conf = 0.88
            evidence.append("Berada di dalam bagian Daftar Pustaka")
            if re.search(r"\(\d{4}[a-z]?\)|\b(19|20)\d{2}\b", text_clean):
                conf = 0.94
                evidence.append("Memuat pola tahun publikasi ilmiah")
            return "bibliography_entry", conf, evidence

        # 3g. Block quote heuristics (indented on left & right, or single-spaced indented block)
        if fmt.left_indent_cm >= 0.8 and (fmt.right_indent_cm >= 0.8 or fmt.line_spacing <= 1.15):
            if len(text_clean) >= 80:
                return (
                    "block_quote",
                    0.84,
                    ["Memiliki indentasi blok kiri/kanan dan spasi rapat seperti kutipan langsung"],
                )

        # 3h. List item (numbered/bulleted list not matching heading)
        if (
            any("list" in s for s in combined_styles if s)
            or fmt.num_id is not None
            or re.match(r"^([•\-–*]|\([a-z0-9]+\)|[a-z]\.)\s+", text_clean)
        ):
            return "list_item", 0.86, ["Menggunakan penomoran daftar atau simbol butir (list item)"]

        # 3i. Ambiguous short bold line in body -> low-confidence heading candidate
        if (
            current_region == "body"
            and fmt.bold
            and len(text_clean) <= 85
            and not text_clean.endswith(".")
            and fmt.alignment == "left"
        ):
            return (
                "heading_2",
                0.58,
                [
                    "Baris pendek bercetak tebal di bagian isi tanpa nomor sub-bab (perlu konfirmasi)"
                ],
            )

        # 3j. Default: Body paragraph
        return "body", 0.90, ["Paragraf narasi teks isi"]


role_classifier = RoleClassifier()
