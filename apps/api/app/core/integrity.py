from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from docx import Document
from docx.oxml.ns import qn

from app.core.xml_helpers import local_tag, parse_boolean_el


def _extract_paragraph_user_text(p_el: Any) -> str:
    """Extracts user-authored visible text from a paragraph.

    Ignores hidden text (`w:vanish`), field instructions (`w:instrText`),
    and dynamic TOC/PAGE/NUMPAGES field cached results so inserting TOC/PAGE
    fields does not alter user content integrity. Keeps SEQ field cached
    values so caption numbers remain part of the text check.
    """
    parts: list[str] = []
    field_stack: list[dict[str, str]] = []

    for child in p_el.iter():
        tag = local_tag(child)
        if tag == "fldSimple":
            instr = (child.get(qn("w:instr")) or "").strip().upper()
            if instr.startswith("TOC") or instr.startswith("PAGE") or instr.startswith("NUMPAGES"):
                continue
        elif tag == "r":
            parent = child.getparent()
            if parent is not None and local_tag(parent) == "fldSimple":
                instr = (parent.get(qn("w:instr")) or "").strip().upper()
                if (
                    instr.startswith("TOC")
                    or instr.startswith("PAGE")
                    or instr.startswith("NUMPAGES")
                ):
                    continue

            rPr = child.find(qn("w:rPr"))
            if rPr is not None and parse_boolean_el(rPr.find(qn("w:vanish"))) is True:
                continue

            fld_char = child.find(qn("w:fldChar"))
            if fld_char is not None:
                ctype = fld_char.get(qn("w:fldCharType"))
                if ctype == "begin":
                    field_stack.append({"state": "instr", "instr": ""})
                elif ctype == "separate" and field_stack:
                    field_stack[-1]["state"] = "result"
                elif ctype == "end" and field_stack:
                    field_stack.pop()
                continue

            if field_stack:
                top = field_stack[-1]
                if top["state"] == "instr":
                    for it in child.findall(qn("w:instrText")):
                        if it.text:
                            top["instr"] += it.text
                    continue
                elif top["state"] == "result":
                    instr_upper = top["instr"].strip().upper()
                    if (
                        instr_upper.startswith("TOC")
                        or instr_upper.startswith("PAGE")
                        or instr_upper.startswith("NUMPAGES")
                    ):
                        continue

            for sub in child:
                sub_tag = local_tag(sub)
                if sub_tag == "t" and sub.text:
                    parts.append(sub.text)
                elif sub_tag == "tab":
                    parts.append("\t")
                elif sub_tag == "br":
                    br_type = sub.get(qn("w:type"))
                    if br_type not in ("page", "column"):
                        parts.append("\n")

    return "".join(parts)


def extract_document_lines(doc_or_path: Any) -> list[str]:
    """Extracts user text lines (body paragraphs, table cells, footnotes)."""
    doc = Document(str(doc_or_path)) if isinstance(doc_or_path, (str, Path)) else doc_or_path
    para_lines: list[str] = []
    table_lines: list[str] = []

    def _visit_body_child(elem: Any) -> None:
        tag = local_tag(elem)
        if tag == "sdt":
            sdt_content = elem.find(qn("w:sdtContent"))
            if sdt_content is not None:
                for ch in sdt_content:
                    _visit_body_child(ch)
        elif tag == "p":
            txt = _extract_paragraph_user_text(elem)
            norm = re.sub(r"[ \t\u00a0]+", " ", txt).strip()
            if norm:
                para_lines.append(norm)
        elif tag == "tbl":
            for tr in elem.findall(qn("w:tr")):
                for tc in tr.findall(qn("w:tc")):
                    for p_el in tc.findall(qn("w:p")):
                        txt = _extract_paragraph_user_text(p_el)
                        norm = re.sub(r"[ \t\u00a0]+", " ", txt).strip()
                        if norm:
                            table_lines.append(norm)

    for child in doc.element.body:
        _visit_body_child(child)

    footnote_lines: list[str] = []
    try:
        for rel in doc.part.rels.values():
            if "footnotes" in rel.reltype:
                fn_el = rel.target_part.element
                for p_el in fn_el.iter(qn("w:p")):
                    txt = _extract_paragraph_user_text(p_el)
                    norm = re.sub(r"[ \t\u00a0]+", " ", txt).strip()
                    if norm:
                        footnote_lines.append(norm)
    except Exception:
        pass

    return para_lines + table_lines + footnote_lines


def normalized_text(doc_or_path: Any) -> str:
    """Returns canonical normalized text of the document."""
    lines = extract_document_lines(doc_or_path)
    joined = "\n".join(lines)
    return re.sub(r"[ \t\u00a0]+", " ", joined).strip()


def verify_text_integrity(
    before_doc_or_path: Any,
    after_doc_or_path: Any,
    approved_rule_ids: set[str] | None = None,
    excluded_prefixes: list[str] | None = None,
    excluded_lines: list[str] | None = None,
    replaced_pairs: list[tuple[str, str]] | None = None,
) -> tuple[bool, str]:
    """Verifies that fixing a document did not alter any user content.

    For `auto` rules (when no `suggest` rules are approved), normalized text
    before and after must be 100% identical.
    For approved `suggest` rules (HEAD-003, TOC-002, BIB-001, PARA-007), compares
    after applying the exact approved exclusions.
    """
    approved = approved_rule_ids or set()
    prefixes = excluded_prefixes or []
    removed_lines = set(excluded_lines or [])
    pairs = dict(replaced_pairs or [])

    if not approved and not prefixes and not removed_lines and not pairs:
        before_norm = normalized_text(before_doc_or_path)
        after_norm = normalized_text(after_doc_or_path)
        if before_norm == after_norm:
            return True, "OK"
        return False, f"Text mismatch: length before={len(before_norm)}, after={len(after_norm)}"

    before_lines = extract_document_lines(before_doc_or_path)
    after_lines = extract_document_lines(after_doc_or_path)

    def _clean_lines(raw_lines: list[str]) -> list[str]:
        cleaned: list[str] = []
        for ln in raw_lines:
            if "PARA-007" in approved:
                ln = re.sub(r"\s*\n\s*", " ", ln).strip()
            if ln in pairs:
                ln = pairs[ln]
            if ln in removed_lines:
                continue
            for pfx in prefixes:
                if ln.startswith(pfx):
                    ln = ln[len(pfx) :].strip()
                    break
            if ln:
                cleaned.append(ln)
        return cleaned

    c_before = _clean_lines(before_lines)
    c_after = _clean_lines(after_lines)

    if "BIB-001" in approved:
        if sorted(c_before) == sorted(c_after):
            return True, "OK (order-independent match)"
        return False, "Text mismatch after order-independent comparison"

    if c_before == c_after:
        return True, "OK"
    return (
        False,
        f"Text mismatch after exclusions: before={len(c_before)} lines, after={len(c_after)} lines",
    )
