from __future__ import annotations

from typing import Any


# Structured error codes for API and observability
class ErrorCode:
    INGEST_INVALID_EXT = "INGEST_INVALID_EXT"
    INGEST_MACRO_DETECTED = "INGEST_MACRO_DETECTED"
    INGEST_LEGACY_DOC = "INGEST_LEGACY_DOC"
    INGEST_FILE_TOO_LARGE = "INGEST_FILE_TOO_LARGE"
    INGEST_EMPTY_FILE = "INGEST_EMPTY_FILE"
    INGEST_INVALID_ZIP = "INGEST_INVALID_ZIP"
    INGEST_TOO_MANY_ENTRIES = "INGEST_TOO_MANY_ENTRIES"
    INGEST_ZIP_BOMB = "INGEST_ZIP_BOMB"
    INGEST_PATH_TRAVERSAL = "INGEST_PATH_TRAVERSAL"
    INGEST_MISSING_DOCUMENT_XML = "INGEST_MISSING_DOCUMENT_XML"
    INGEST_XXE_DETECTED = "INGEST_XXE_DETECTED"
    INGEST_MALFORMED_XML = "INGEST_MALFORMED_XML"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    DOC_NOT_FOUND = "DOC_NOT_FOUND"
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    PROFILE_NOT_FOUND = "PROFILE_NOT_FOUND"
    PROFILE_INVALID = "PROFILE_INVALID"
    FIX_INTEGRITY_FAILED = "FIX_INTEGRITY_FAILED"
    FIX_REOPEN_FAILED = "FIX_REOPEN_FAILED"
    RENDER_TIMEOUT = "RENDER_TIMEOUT"
    RENDER_UNAVAILABLE = "RENDER_UNAVAILABLE"


# Centralized Indonesian message templates
MESSAGES_ID: dict[str, str] = {
    # Ingest & System messages
    "ingest.success": "Dokumen berhasil diunggah dan lolos verifikasi keamanan.",
    "ingest.err.docm": "File berekstensi .docm (macro-enabled) ditolak demi keamanan. Harap gunakan format .docx standar.",
    "ingest.err.doc": "File format Word lama (.doc) tidak didukung. Harap simpan ulang dokumen sebagai .docx (Word 2016+).",
    "ingest.err.ext": "Format file '{ext}' tidak didukung. Hanya file Microsoft Word (.docx) yang diizinkan.",
    "ingest.err.size": "Ukuran file melebihi batas maksimum ({max_mb} MB).",
    "ingest.err.empty": "File kosong tidak dapat diproses.",
    "ingest.err.zip_entries": "Dokumen tidak valid: jumlah komponen arsip melebihi batas wajar.",
    "ingest.err.traversal": "Dokumen ditolak: terdeteksi struktur path berbahaya (path traversal).",
    "ingest.err.macro": "Dokumen ditolak: terdeteksi komponen macro aktif (vbaProject.bin).",
    "ingest.err.zip_bomb": "Dokumen ditolak: ukuran setelah diekstrak melebihi batas aman (anti zip-bomb).",
    "ingest.err.no_doc_xml": "File bukan berkas Word (.docx) yang valid: word/document.xml tidak ditemukan.",
    "ingest.err.bad_zip": "File rusak atau bukan arsip ZIP/OOXML yang valid.",
    "ingest.err.xxe": "Dokumen ditolak: terdeteksi deklarasi entitas XML/DTD berbahaya (anti-XXE).",
    "ingest.err.malformed_xml": "Dokumen ditolak: struktur XML di dalam dokumen rusak atau tidak valid.",
    "rate_limit.exceeded": "Terlalu banyak permintaan dalam waktu singkat. Silakan tunggu beberapa saat lagi.",
    # PAGE Findings
    "finding.page.size": "Ukuran kertas pada Section {section} ({actual}) tidak sesuai pedoman ({expected}).",
    "finding.page.margin_top": "Margin atas pada Section {section} ({actual}) tidak sesuai pedoman ({expected}).",
    "finding.page.margin_bottom": "Margin bawah pada Section {section} ({actual}) tidak sesuai pedoman ({expected}).",
    "finding.page.margin_left": "Margin kiri pada Section {section} ({actual}) tidak sesuai pedoman ({expected}).",
    "finding.page.margin_right": "Margin kanan pada Section {section} ({actual}) tidak sesuai pedoman ({expected}).",
    "finding.page.header_dist": "Jarak header dari tepi kertas pada Section {section} ({actual}) tidak sesuai pedoman ({expected}).",
    "finding.page.footer_dist": "Jarak footer dari tepi kertas pada Section {section} ({actual}) tidak sesuai pedoman ({expected}).",
    "finding.page.orientation": "Orientasi halaman pada Section {section} ({actual}) berbeda dari pedoman ({expected}).",
    # FONT Findings
    "finding.font.family": "Keluarga huruf pada paragraf #{block} ({role}) menggunakan '{actual}', seharusnya '{expected}'.",
    "finding.font.size": "Ukuran huruf pada paragraf #{block} ({role}) adalah {actual}, seharusnya {expected}.",
    "finding.font.color": "Warna huruf pada paragraf #{block} ({role}) adalah #{actual}, seharusnya #{expected}.",
    "finding.font.stray": "Terdeteksi font tidak konsisten di tengah paragraf #{block} ({actual}), seharusnya seragam '{expected}'.",
    # PARA Findings
    "finding.para.line_spacing": "Spasi baris pada paragraf #{block} ({role}) adalah {actual}, seharusnya {expected}.",
    "finding.para.space_before": "Spasi sebelum paragraf #{block} ({role}) adalah {actual}, seharusnya {expected}.",
    "finding.para.space_after": "Spasi sesudah paragraf #{block} ({role}) adalah {actual}, seharusnya {expected}.",
    "finding.para.indent_first": "Indentasi baris pertama pada paragraf #{block} ({role}) adalah {actual}, seharusnya {expected}.",
    "finding.para.indent_left": "Indentasi kiri pada paragraf #{block} ({role}) adalah {actual}, seharusnya {expected}.",
    "finding.para.indent_right": "Indentasi kanan pada paragraf #{block} ({role}) adalah {actual}, seharusnya {expected}.",
    "finding.para.indent_hanging": "Hanging indent pada paragraf #{block} ({role}) adalah {actual}, seharusnya {expected}.",
    "finding.para.alignment": "Perataan teks pada paragraf #{block} ({role}) adalah '{actual}', seharusnya '{expected}'.",
    "finding.para.empty_spacing": "Terdeteksi paragraf kosong berulang pada blok #{block} yang dipakai sebagai pengatur jarak.",
    "finding.para.manual_indent": "Paragraf #{block} menggunakan spasi atau tab manual di awal kalimat sebagai pengganti indentasi.",
    "finding.para.manual_linebreak": "Paragraf #{block} menggunakan line break manual (Shift+Enter) untuk mengatur tata letak.",
    "finding.para.widow_control": "Pengaturan widow/orphan control belum aktif pada paragraf #{block}.",
    # HEAD Findings
    "finding.head.chapter_format": "Format judul bab pada paragraf #{block} ({actual}) belum sesuai standar ({expected}).",
    "finding.head.subheading_format": "Format sub-bab ({role}) pada paragraf #{block} ({actual}) belum sesuai standar ({expected}).",
    "finding.head.typed_number": "Penomoran heading pada paragraf #{block} ('{actual}') diketik manual, disarankan menggunakan penomoran otomatis.",
    "finding.head.keep_with_next": "Heading pada paragraf #{block} belum mengaktifkan 'Keep with next' agar tidak terpisah dari paragraf berikutnya.",
    "finding.head.page_break_before": "Bab pada paragraf #{block} belum diatur mulai pada halaman baru.",
    "finding.head.skipped_level": "Hierarki heading pada paragraf #{block} melompat dari level {actual} langsung ke level {expected}.",
    # NUM Findings
    "finding.num.front_roman": "Penomoran halaman bagian awal pada Section {section} menggunakan '{actual}', seharusnya '{expected}'.",
    "finding.num.body_arabic": "Penomoran halaman bagian isi pada Section {section} menggunakan '{actual}', seharusnya '{expected}'.",
    "finding.num.position": "Posisi nomor halaman pada Section {section} berada di '{actual}', seharusnya '{expected}'.",
    "finding.num.chapter_first": "Halaman awal bab pada Section {section} belum mengaktifkan posisi nomor halaman khusus ({expected}).",
    "finding.num.cover_unnumbered": "Halaman sampul (Section 1) menampilkan nomor halaman, seharusnya tidak bernomor.",
    "finding.num.typed_page": "Nomor halaman pada Section {section} ('{actual}') diketik manual sebagai teks biasa, bukan field PAGE otomatis.",
    # TOC, LOF, LOT Findings
    "finding.toc.missing": "Daftar Isi belum ditemukan di dalam dokumen.",
    "finding.toc.typed": "Daftar Isi pada blok #{block} terdeteksi diketik manual, seharusnya menggunakan field TOC otomatis Word.",
    "finding.toc.levels": "Kedalaman level Daftar Isi ({actual}) tidak sesuai pedoman ({expected}).",
    "finding.toc.not_synced": "Dokumen belum ditandai untuk memperbarui field Daftar Isi otomatis saat dibuka (updateFields).",
    "finding.toc.entry_format": "Format entri Daftar Isi belum menggunakan titik pemandu (leader dots) dan nomor halaman rata kanan.",
    "finding.lof.missing": "Dokumen memiliki gambar ber-caption tetapi belum memiliki field Daftar Gambar.",
    "finding.lot.missing": "Dokumen memiliki tabel ber-caption tetapi belum memiliki field Daftar Tabel.",
    # CAP Findings
    "finding.cap.missing": "Elemen {actual} pada blok #{block} belum memiliki caption keterangan.",
    "finding.cap.position": "Posisi caption pada blok #{block} berada di {actual}, seharusnya di {expected}.",
    "finding.cap.format": "Format/style caption pada blok #{block} ({actual}) belum sesuai pedoman ({expected}).",
    "finding.cap.typed_number": "Nomor caption pada blok #{block} ('{actual}') diketik manual, seharusnya menggunakan field SEQ otomatis.",
    "finding.cap.sequence": "Urutan nomor caption pada blok #{block} ({actual}) melompat atau duplikat, seharusnya {expected}.",
    # FIG Findings
    "finding.fig.alignment": "Gambar pada blok #{block} memiliki perataan '{actual}', seharusnya '{expected}'.",
    "finding.fig.oversized": "Lebar gambar pada blok #{block} ({actual}) melewati batas ruang teks ({expected}).",
    "finding.fig.floating": "Gambar mengambang (floating/anchor) pada blok #{block} berisiko mengganggu alur teks; gunakan In Line with Text.",
    # TBL Findings
    "finding.tbl.oversized": "Lebar tabel pada blok #{block} ({actual}) melewati batas ruang teks ({expected}).",
    "finding.tbl.repeat_header": "Tabel pada blok #{block} belum mengaktifkan pengulangan baris judul (Repeat Header Rows).",
    "finding.tbl.cant_split": "Baris pada tabel blok #{block} belum mengaktifkan pencegahan terpotong antarhalaman (cantSplit).",
    "finding.tbl.text_format": "Format teks di dalam tabel blok #{block} ({actual}) belum sesuai peran table_text ({expected}).",
    "finding.tbl.alignment": "Perataan tabel pada blok #{block} adalah '{actual}', seharusnya '{expected}'.",
    # BIB Findings
    "finding.bib.unsorted": "Urutan entri Daftar Pustaka pada blok #{block} ('{actual}') belum terurut secara alfabetis (seharusnya setelah '{expected}').",
    "finding.bib.hanging_indent": "Hanging indent pada entri Daftar Pustaka blok #{block} adalah {actual}, seharusnya {expected}.",
    "finding.bib.spacing": "Spasi pada entri Daftar Pustaka blok #{block} ({actual}) belum sesuai pedoman ({expected}).",
    "finding.bib.uncited": "Entri Daftar Pustaka pada blok #{block} ('{actual}') belum ditemukan rujukan tahun/penulisnya di dalam teks bab.",
    # STR Findings
    "finding.str.missing_section": "Bagian wajib '{expected}' belum ditemukan di dalam dokumen.",
    "finding.str.wrong_order": "Urutan bagian '{actual}' pada blok #{block} muncul sebelum '{expected}' (tidak sesuai urutan baku).",
    "finding.str.missing_chapters": "Kelengkapan bab utama belum terpenuhi: '{expected}' tidak ditemukan.",
    "finding.str.new_page": "Bagian '{actual}' pada blok #{block} belum dimulai pada halaman baru.",
    # Document Advisories (Tracked Changes, Comments, SDT, Textbox)
    "finding.doc.tracked_changes": "Paragraf #{block} memiliki revisi aktif (Tracked Changes). Perbaikan otomatis melewati paragraf ini demi keamanan.",
    "finding.doc.comments": "Paragraf #{block} memuat komentar aktif.",
    "finding.doc.sdt_or_textbox": "Paragraf/elemen #{block} berada di dalam Content Control (w:sdt) atau Textbox; periksa secara manual.",
}


def format_message(message_id: str, **kwargs: Any) -> str:
    """Formats a localized Indonesian message by its message_id."""
    template = MESSAGES_ID.get(message_id, message_id)
    try:
        return template.format(**kwargs)
    except KeyError:
        return template
