from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from app.core.docx_model import DocumentIR

PAGINATION_WARNING_ID = (
    "Pratinjau dirender menggunakan LibreOffice headless. Jumlah halaman dan pemenggalan baris "
    "dapat sedikit berbeda dari tampilan akhir di Microsoft Word."
)


def find_soffice_binary() -> str | None:
    """Locates the LibreOffice (`soffice` or `libreoffice`) binary if installed."""
    for cmd in ("soffice", "libreoffice"):
        found = shutil.which(cmd)
        if found:
            return found
    mac_path = Path("/Applications/LibreOffice.app/Contents/MacOS/soffice")
    if mac_path.exists():
        return str(mac_path)
    return None


def _generate_minimal_fallback_pdf(docx_path: Path, pdf_path: Path) -> None:
    """Generates a valid minimal PDF 1.4 summary when LibreOffice is not installed on the host."""
    try:
        ir = DocumentIR.from_docx(str(docx_path))
        sec = ir.sections[0] if ir.sections else None
        margin_info = (
            f"Margin: Top {sec.top_margin_cm:.1f}cm, Left {sec.left_margin_cm:.1f}cm, "
            f"Bottom {sec.bottom_margin_cm:.1f}cm, Right {sec.right_margin_cm:.1f}cm"
            if sec
            else "Margin: N/A"
        )
        block_count = len(ir.blocks)
    except Exception:
        margin_info = "Margin: Standard"
        block_count = 0

    lines = [
        "Skripsi Formatter - Pratinjau PDF",
        f"File: {docx_path.name} ({block_count} blok, {margin_info})",
        "Catatan: Paginasi pratinjau dapat berbeda tipis dari Microsoft Word.",
    ]

    content_ops = ["BT", "/F1 12 Tf", "50 760 Td"]
    for idx, line in enumerate(lines):
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if idx > 0:
            content_ops.append("0 -22 Td")
        content_ops.append(f"({safe}) Tj")
    content_ops.append("ET")
    stream_bytes = "\n".join(content_ops).encode("latin-1", errors="replace")

    objs: list[bytes] = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        f"5 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
        + stream_bytes
        + b"\nendstream\nendobj\n",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for obj in objs:
        offsets.append(len(out))
        out.extend(obj)

    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for off in offsets:
        out.extend(f"{off:010d} 00000 n \n".encode("ascii"))
    out.extend(
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode(
            "ascii"
        )
    )
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(bytes(out))


def render_docx_to_pdf(
    docx_path: str | Path,
    output_pdf_path: str | Path,
    timeout_seconds: int = 30,
) -> tuple[bool, str]:
    """Converts a .docx file to PDF using LibreOffice headless with isolated worker profile.

    Returns `(used_libreoffice, status_note)`. Never raises an exception that would
    break the document fix pipeline; falls back to a valid summary PDF if `soffice`
    is unavailable.
    """
    in_path = Path(docx_path).resolve()
    out_pdf = Path(output_pdf_path).resolve()
    out_pdf.parent.mkdir(parents=True, exist_ok=True)

    soffice = find_soffice_binary()
    if soffice is None:
        _generate_minimal_fallback_pdf(in_path, out_pdf)
        return False, "FALLBACK_PDF_NO_LIBREOFFICE"

    worker_id = uuid.uuid4().hex[:10]
    profile_dir = Path(tempfile.gettempdir()) / f"lo-profile-{worker_id}"
    out_tmp_dir = Path(tempfile.gettempdir()) / f"lo-out-{worker_id}"
    profile_dir.mkdir(parents=True, exist_ok=True)
    out_tmp_dir.mkdir(parents=True, exist_ok=True)

    try:
        user_install_uri = profile_dir.as_uri()
        cmd = [
            soffice,
            "--headless",
            "--norestore",
            f"-env:UserInstallation={user_install_uri}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_tmp_dir),
            str(in_path),
        ]
        subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout_seconds,
            check=True,
        )
        generated_pdf = out_tmp_dir / f"{in_path.stem}.pdf"
        if generated_pdf.exists():
            shutil.copy2(generated_pdf, out_pdf)
            return True, "OK"

        _generate_minimal_fallback_pdf(in_path, out_pdf)
        return False, "RENDER_OUTPUT_MISSING"
    except subprocess.TimeoutExpired:
        _generate_minimal_fallback_pdf(in_path, out_pdf)
        return False, "RENDER_TIMEOUT"
    except Exception:
        _generate_minimal_fallback_pdf(in_path, out_pdf)
        return False, "RENDER_FAILED"
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)
        shutil.rmtree(out_tmp_dir, ignore_errors=True)
