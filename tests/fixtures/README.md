# Korpus Dokumen Uji (Test Fixtures)

Direktori ini memuat dokumen uji sintetis untuk pengujian otomatis Skripsi Formatter.

> **PENTING (Privasi):**
> Dilarang melakukan commit dokumen mahasiswa asli atau dokumen dengan data pribadi.
> Semua berkas di direktori ini harus merupakan dokumen sintetis atau dokumen yang telah dianonimkan dengan izin.

## Daftar Rencana Dokumen Fixture:
1. `clean_styled.docx` — Dokumen dengan style baku sesuai profil (seharusnya 0 temuan).
2. `wrong_margins.docx` — Margin salah di satu/beberapa section (untuk pengujian PAGE-002).
3. `manual_formatting.docx` — Dokumen format manual (bold, spasi, enter berulang) tanpa Style.
4. `no_styles.docx` — Semua paragraf berstatus Normal, judul bab diketik manual.
5. `typed_numbers.docx` — Nomor bab dan halaman diketik teks biasa (HEAD-003, NUM-006).
6. `multi_section.docx` — Terdiri dari section romawi dan arabik bertingkat.
7. `with_tables_figures.docx` — Memuat gambar, tabel, dan caption yang belum standar.
