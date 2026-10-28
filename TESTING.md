# TESTING.md — Strategi Pengujian

Tujuan: memastikan tool **tidak merusak dokumen**, **tidak mengubah isi**, dan **menghasilkan format yang benar**. Pengujian bukan tambahan; ia bagian dari Definition of Done (`AGENTS.md`).

## 1. Piramida tes

| Lapis | Isi | Alat |
|---|---|---|
| Unit | Konversi satuan, format efektif, regex peran, pemeriksa aturan, helper XML | `pytest` |
| Properti | Idempotensi, integritas teks, stabilitas ID temuan | `hypothesis` |
| Integrasi | Pipeline lengkap pada fixture: parse → analisis → perbaikan → validasi ulang | `pytest` + fixture .docx |
| Kontrak API | Endpoint, kode error, alur job | `pytest` + `httpx` |
| E2E UI | Upload → laporan → perbaikan → unduh | Playwright |
| Kompatibilitas | Hasil terbuka di LibreOffice (otomatis) dan Word (manual berkala) | skrip + checklist |
| Keamanan | Zip bomb, XXE, path traversal, `.docm` | `pytest` + fixture berbahaya |
| Performa | Waktu pada dokumen besar | skrip benchmark |

## 2. Korpus fixture

Letakkan di `tests/fixtures/`. **Sintetis atau dianonimkan dengan izin.** Jangan commit dokumen mahasiswa asli. Jangan mengedit fixture yang sudah ada; tambahkan yang baru.

| Fixture | Karakteristik | Tujuan |
|---|---|---|
| `clean_styled.docx` | Memakai Style benar, format sesuai profil contoh | Tidak boleh ada temuan; tidak boleh ada perubahan |
| `wrong_margins.docx` | Margin salah di satu atau beberapa section | PAGE-002 |
| `manual_formatting.docx` | Bold/ukuran diatur manual, tanpa Style | Format efektif dan peran heuristik |
| `no_styles.docx` | Semua paragraf `Normal`, judul bab hanya diketik | Klasifikasi peran dan keyakinan rendah |
| `typed_numbers.docx` | Nomor heading, nomor halaman, caption diketik | HEAD-003, NUM-006, CAP-004 |
| `typed_toc.docx` | Daftar isi diketik manual | TOC-002 |
| `multi_section.docx` | Beberapa section, header/footer tertaut | NUM-001..005, tidak merusak tautan |
| `with_tables_figures.docx` | Tabel lebar, gambar besar, caption di posisi salah | TBL, FIG, CAP |
| `tracked_changes.docx` | Ada `w:ins`/`w:del` dan komentar | Deteksi dan peringatan |
| `textboxes_sdt.docx` | Kotak teks dan content control | Traversal tidak crash |
| `localized_styles.docx` | Dibuat dari Word berbahasa Indonesia (style "Judul 1") | Deteksi lewat `styleId` |
| `large_100pages.docx` | ~100 halaman | Performa |
| `bad_zip_bomb.docx`, `bad_xxe.docx`, `bad_traversal.docx`, `macro.docm` | Berbahaya | Penolakan aman |

Tiap fixture punya berkas pendamping `*.expected.json` (golden findings) bila relevan.

## 3. Tes wajib untuk setiap fixer

1. **Integritas teks.** Teks ternormalisasi sebelum dan sesudah identik persis untuk aturan `auto`. Untuk `suggest`, bandingkan setelah mengecualikan perubahan yang disetujui.
2. **Idempotensi.** `fix(fix(doc)) == fix(doc)` (bandingkan XML dokumen atau ringkasan format efektif seluruh paragraf).
3. **File asli tidak berubah.** Hash file asli sama sebelum dan sesudah proses.
4. **Temuan hilang setelah perbaikan.** Analisis ulang hasil perbaikan tidak lagi menghasilkan temuan `auto` yang diperbaiki.
5. **Tidak ada regresi di tempat lain.** Properti paragraf yang tidak terkait temuan tidak berubah.
6. **Dokumen valid.** Hasil terbuka di `python-docx` tanpa error dan terkonversi di LibreOffice tanpa error.
7. **Change log akurat.** Setiap perubahan tercatat (aturan, lokasi, nilai lama, nilai baru), dan jumlahnya cocok dengan perbedaan nyata.

Contoh helper integritas teks (sketsa):

```python
import re
from docx import Document

def normalized_text(path: str) -> str:
    doc = Document(path)
    parts = []
    for p in doc.paragraphs:
        parts.append(p.text)
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                parts.append(cell.text)
    text = "\n".join(parts)
    return re.sub(r"[ \t\u00a0]+", " ", text).strip()
```

Perluas untuk header/footer, catatan kaki, dan urutan dokumen yang benar (tabel di antara paragraf) sebelum dipakai sebagai gerbang rilis; sketsa di atas belum mengurutkan paragraf dan tabel secara berselang.

## 4. Tes properti (hypothesis)

- Hasilkan dokumen sintetis dengan variasi acak: margin, font, spasi, indentasi, susunan run, jumlah section.
- Properti: integritas teks, idempotensi, dan "tidak crash" untuk semua kombinasi.
- Tes `units`: konversi bolak-balik berada dalam toleransi pembulatan.

## 5. Tes aturan

Untuk setiap aturan di `RULES_SPEC.md` minimal:
- satu kasus lolos (tidak ada temuan),
- satu kasus melanggar (temuan dengan nilai aktual/diharapkan benar),
- satu kasus di batas toleransi,
- bila `auto`/`suggest`: tes perbaikan, idempotensi, integritas teks.

Tes profil: profil contoh lolos validasi skema; profil dengan field salah ditolak dengan pesan jelas; `extends` menggabungkan dengan benar.

## 6. Tes klasifikasi peran

- Dataset berlabel kecil (dokumen sintetis dengan peran yang diketahui).
- Metrik: akurasi per peran dan **tingkat kesalahan pada keyakinan tinggi**. Kesalahan dengan keyakinan tinggi lebih berbahaya daripada kasus ragu yang ditanyakan ke pengguna.
- Tes bahwa peran keyakinan rendah memang ditandai untuk konfirmasi.

## 7. Tes API

- Alur job: `queued → running → done|failed`, pesan error terstruktur.
- Upload tidak valid ditolak dengan kode yang tepat.
- Penghapusan: setelah `DELETE`, semua turunan hilang; setelah TTL, file dibersihkan.
- Tidak ada isi dokumen di log (tes dengan penanda unik di dokumen uji lalu cari di keluaran log).

## 8. Tes keamanan

- Zip bomb: ditolak sebelum terurai penuh.
- Path traversal pada entri ZIP: ditolak.
- XXE/DTD: tidak diproses.
- `.docm`/macro: ditolak.
- File besar di atas batas: ditolak dengan pesan jelas.
- Rate limit berfungsi.

## 9. Tes kompatibilitas

- Otomatis: konversi hasil ke PDF di LibreOffice tanpa error; python-docx dapat membuka.
- Manual berkala (checklist rilis): buka beberapa hasil di Word 2016+ dan Word terbaru:
  - [ ] Tidak ada peringatan "konten tidak terbaca".
  - [ ] Margin, font, spasi sesuai profil (periksa langsung di Word).
  - [ ] Penomoran halaman benar per bagian.
  - [ ] Dialog update field muncul dan daftar isi terisi benar setelah dijawab.
  - [ ] Caption dan daftar gambar/tabel benar.
  - [ ] Hasil masih mudah disunting (style tersambung, tidak ada format langsung berlebihan).

## 10. Regresi visual (opsional, P2)

Render PDF sebelum/sesudah ke gambar (misalnya `pdf2image`) dan bandingkan halaman kunci. Perbedaan tipis akibat paginasi LibreOffice dimaklumi; gunakan ambang dan tinjau manual.

## 11. Performa

Target (usulan; validasi): p95 analisis < 30 detik dan perbaikan + pratinjau < 90 detik untuk dokumen 100 halaman. Skrip benchmark menjalankan `large_100pages.docx` dan melaporkan durasi per tahap.

## 12. Gerbang rilis

Rilis hanya jika:
- semua tes otomatis hijau,
- tes integritas teks dan idempotensi lulus untuk semua fixer,
- checklist kompatibilitas manual diisi untuk versi tersebut,
- tidak ada temuan keamanan terbuka,
- target performa terpenuhi atau penyimpangan dicatat dan disetujui.
