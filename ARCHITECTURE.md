# ARCHITECTURE.md — Skripsi Formatter

Dokumen ini menjelaskan arsitektur usulan. Jika keputusan berubah, perbarui dokumen ini.

## 1. Prinsip arsitektur

1. **Pipeline deterministik.** Parse → klasifikasi → evaluasi → perbaikan → render → validasi ulang.
2. **Aturan sebagai data.** Evaluator generik membaca profil JSON.
3. **Pemisahan tanggung jawab.** Router HTTP tipis, logika di `services/` dan `core/`.
4. **Salinan, bukan edit di tempat.** File asli tidak pernah ditulis.
5. **AI opsional dan terisolasi.** Sistem harus tetap berfungsi penuh tanpa LLM (peran paragraf ambigu → tanya pengguna).

## 2. Diagram alur data

```
Browser ──upload .docx──▶ API ──▶ [1] Validasi file
                                       │
                                       ▼
                                  [2] Parse → IR (docx_model)
                                       │
                                       ▼
                                  [3] Format efektif (formatting)
                                       │
                                       ▼
                                  [4] Klasifikasi peran (roles)
                                       │   keyakinan rendah ─▶ minta konfirmasi pengguna
                                       ▼
        profil JSON ───────────▶  [5] Evaluasi aturan ─▶ Temuan (findings)
                                       │
                          pengguna memilih temuan untuk diperbaiki
                                       ▼
                                  [6] Fixer (pada salinan) ─▶ Change log
                                       │
                                       ▼
                                  [7] Pasca-proses field + render PDF (LibreOffice)
                                       │
                                       ▼
                                  [8] Validasi ulang + tes integritas teks
                                       │
                                       ▼
Browser ◀── laporan, pratinjau PDF, unduh .docx, change log
```

## 3. Komponen

### 3.1 Validasi file (`services/ingest`)
- Cek ekstensi, MIME, ukuran, dan integritas ZIP.
- Batasi ukuran terurai dan jumlah entri (anti zip bomb); tolak path traversal di entri ZIP.
- Tolak `.docm` dan dokumen dengan `vbaProject.bin`.
- Parser XML dengan entity expansion/DTD dimatikan (anti XXE).
- Hasilkan `doc_id` acak (UUID v4), simpan di penyimpanan sementara dengan TTL.

### 3.2 Model dokumen / IR (`core/docx_model.py`)
Representasi internal ringan dari .docx: daftar blok (paragraf, tabel, gambar inline), section, style, numbering, header/footer, field. IR menyimpan **referensi** ke elemen XML asli (bukan salinan teks) agar fixer bisa memodifikasi tepat sasaran.

### 3.3 Format efektif (`core/formatting.py`)
Menghitung properti efektif paragraf/run dengan urutan: properti langsung → style paragraf (rantai `basedOn`) → `docDefaults`; ditambah style karakter dan style tabel bila relevan. Semua nilai dinormalisasi lewat `core/units.py` (cm, pt, twips).

### 3.4 Klasifikasi peran (`core/roles.py`)
Penentu peran paragraf, berurutan dari yang paling andal:
1. Style/outline level (`Heading 1..n`, `Caption`, style khusus).
2. Heuristik pola: `^BAB\s+[IVXLC]+`, `^\d+(\.\d+)+\s`, huruf kapital semua, rata tengah, bold, ukuran font.
3. Konteks posisi: setelah gambar/tabel (kandidat caption), di bagian setelah "DAFTAR PUSTAKA" (kandidat entri pustaka).
4. (Opsional) LLM untuk kasus ambigu, hanya sebagai saran dengan keyakinan.

Keluaran: `role`, `confidence` (0–1), `evidence` (alasan yang bisa ditampilkan). Ambang keyakinan dikonfigurasi; di bawah ambang → minta konfirmasi.

### 3.5 Profil dan evaluator aturan (`core/rules`)
- Loader memvalidasi profil terhadap JSON Schema (`profiles/schema/profile.schema.json`).
- Evaluator memetakan aturan ke pemeriksa per kategori dan menghasilkan temuan.
- Spesifikasi profil dan katalog aturan: `RULES_SPEC.md`.

### 3.6 Fixer (`core/fixers`)
- Satu modul per kategori: `page`, `font`, `para`, `heading`, `numbering`, `toc`, `caption`, `figure`, `table`.
- Kontrak: `apply(ir, findings, profile) -> list[Change]`; idempoten; tidak menyentuh teks.
- Perubahan diprioritaskan lewat **Style** (ubah/buat style sesuai profil) bukan format langsung di tiap paragraf, kecuali paragraf yang menyimpang dari style-nya. Ini membuat hasil tetap rapi bila mahasiswa menyunting lagi.

### 3.7 Field dan section (`core/fields.py`)
- Menyisipkan/menyusun field TOC, TOC `\c` (daftar gambar/tabel), PAGE, SEQ.
- Mengatur section break, `pgNumType`, header/footer.
- Menandai dokumen agar field diperbarui saat dibuka (lihat `DOCX_NOTES.md`).

### 3.8 Render (`core/render.py`)
- LibreOffice headless untuk konversi ke PDF (pratinjau) dan, bila dipakai, pembaruan field.
- Satu proses `soffice` per worker dengan profil pengguna terpisah (`-env:UserInstallation=...`); LibreOffice tidak aman dipakai paralel dalam satu profil.
- Timeout keras per konversi; kegagalan render tidak menggagalkan perbaikan (pratinjau saja yang hilang).
- Font: pasang font metrik-kompatibel (Liberation Serif/Sans) agar paginasi dekat dengan Word.

### 3.9 Penyimpanan sementara
- Sistem file lokal atau object storage dengan TTL (default 1 jam).
- Job pembersih berkala menghapus file kedaluwarsa.
- Tidak ada isi dokumen di log.

### 3.10 API (FastAPI)

| Metode | Path | Fungsi |
|---|---|---|
| POST | `/v1/documents` | Upload .docx → `doc_id` |
| GET | `/v1/profiles` | Daftar profil aturan |
| POST | `/v1/documents/{id}/analyze` | Mulai analisis dengan `profile_id` → `job_id` |
| GET | `/v1/jobs/{job_id}` | Status job |
| GET | `/v1/documents/{id}/findings` | Daftar temuan (filter kategori/severity) |
| GET | `/v1/documents/{id}/roles` | Peran paragraf + keyakinan |
| PUT | `/v1/documents/{id}/roles` | Konfirmasi/ubah peran oleh pengguna |
| POST | `/v1/documents/{id}/fix` | Terapkan perbaikan (`finding_ids` atau `categories` atau `all`) |
| GET | `/v1/documents/{id}/preview?which=before\|after` | PDF pratinjau |
| GET | `/v1/documents/{id}/download` | .docx hasil |
| GET | `/v1/documents/{id}/changelog` | Daftar perubahan |
| GET | `/v1/documents/{id}/report?format=json\|html` | Laporan temuan |
| DELETE | `/v1/documents/{id}` | Hapus dokumen dan turunan |

Operasi lama (analyze, fix, render) berjalan sebagai job; klien melakukan polling status.

### 3.11 Frontend (Next.js)
Halaman: Upload → Pilih profil → Laporan temuan (filter, kelompok, lokasi) → Konfirmasi peran → Perbaiki → Pratinjau sebelum/sesudah → Unduh. Tampilkan peringatan: paginasi pratinjau bisa sedikit berbeda dari Word, dan cara memperbarui daftar isi di Word.

## 4. Model data inti (ringkas)

```
Finding {
  id, rule_id, category, severity,        # "error" | "warning" | "info"
  location { block_index, section_index, approx_page?, excerpt? },
  actual, expected, fix_mode,             # "auto" | "suggest" | "manual"
  message_id                              # kunci pesan Indonesia
}

Change {
  finding_id, rule_id, location,
  old_value, new_value, method            # "style" | "direct"
}

RoleAssignment { block_index, role, confidence, evidence[] }
```

Detail skema profil: `RULES_SPEC.md`.

## 5. Keputusan dan trade-off

| Keputusan | Alasan | Konsekuensi |
|---|---|---|
| Web app dahulu, add-in kemudian | Mayoritas file dari Word desktop; MVP cepat tanpa review store | Add-in memakai ulang `core` melalui API |
| `python-docx` + `lxml` | Cukup untuk style, section, field; ekosistem matang | Banyak operasi tingkat XML manual (section, field) |
| LibreOffice hanya untuk pratinjau (dan opsional pembaruan field) | Menyimpan ulang .docx lewat LibreOffice berisiko mengubah fidelitas | Paginasi pratinjau tidak identik dengan Word |
| Perbaikan lewat Style | Hasil rapi saat diedit ulang | Perlu logika pembuatan/penyesuaian style yang hati-hati |
| LLM opsional | Menjaga determinisme dan privasi | Heuristik harus cukup kuat tanpa LLM |

## 6. Keamanan dan privasi

- Semua koneksi HTTPS; batas ukuran upload; rate limit per IP/sesi.
- Parser aman (XXE, zip bomb, path traversal); tidak mengeksekusi konten dokumen.
- Retensi singkat dan penghapusan otomatis; endpoint hapus eksplisit.
- Log hanya metadata (ID, durasi, kode aturan), tidak memuat isi dokumen.
- Jika LLM dipakai: kirim potongan sekecil mungkin (misalnya teks satu paragraf pendek dan fitur formatnya), tanpa data identitas, dengan persetujuan pemilik proyek dan penyedia yang tidak melatih model dari data.

## 7. Observabilitas

Metrik: durasi per tahap, jumlah temuan per aturan, tingkat kegagalan parse/render, ukuran dokumen. Error terstruktur dengan kode (misalnya `INGEST_INVALID_ZIP`, `RENDER_TIMEOUT`).

## 8. Penskalaan (nanti)

Worker terpisah untuk job berat, antrian Redis, beberapa instance LibreOffice, penyimpanan objek. Tidak diperlukan untuk MVP.
