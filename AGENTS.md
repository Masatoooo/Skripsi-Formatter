# AGENTS.md — Skripsi Formatter

Instruksi untuk AI coding agent (Claude Code, Codex, Cursor, dan sejenisnya) yang mengembangkan proyek ini. Baca file ini sebelum mengubah kode. Dokumen pendukung: `PRD.md`, `ARCHITECTURE.md`, `RULES_SPEC.md`, `DOCX_NOTES.md`, `TASKS.md`, `TESTING.md`.

## 1. Apa proyek ini

Web app yang memeriksa dan merapikan **format** skripsi/laporan di file .docx sesuai pedoman kampus (margin, font, spasi, heading, penomoran halaman, daftar isi, caption, struktur). Aturan kampus hidup di **profil JSON**, bukan di kode.

**Di luar cakupan: koreksi wording (ejaan, tata bahasa, gaya bahasa), penulisan isi, plagiarisme.** Jangan menambahkan fitur itu.

## 2. Aturan emas (tidak boleh dilanggar)

1. **Jangan pernah mengubah teks isi.** Perbaikan hanya menyentuh properti format dan struktur. Setiap perbaikan harus lolos tes integritas teks (lihat `TESTING.md`).
2. **File asli tidak boleh dimodifikasi.** Selalu bekerja pada salinan.
3. **LLM tidak pernah menulis ke dokumen.** LLM hanya boleh dipakai untuk interpretasi (misalnya klasifikasi peran paragraf yang ambigu, atau draf ekstraksi aturan dari PDF), dan keluarannya diperlakukan sebagai saran yang divalidasi kode. Pengubahan dokumen dilakukan kode deterministik.
4. **Perbaikan harus idempoten.** `fix(fix(x)) == fix(x)`.
5. **Ragu berarti tanya.** Peran paragraf dengan keyakinan rendah ditandai untuk konfirmasi pengguna, tidak ditebak diam-diam.
6. **Aturan adalah data.** Jangan menulis nilai spesifik kampus (misalnya "margin kiri 4 cm") di dalam kode. Semua dari profil JSON.
7. **Gunakan fitur Word asli**: Style, field (TOC, PAGE, SEQ), section, dan numbering. Jangan meniru dengan teks ketikan, spasi, atau Enter berulang.
8. **Privasi dokumen.** Isi dokumen tidak boleh masuk log, telemetri, atau layanan pihak ketiga tanpa keputusan eksplisit dari pemilik proyek.

## 3. Tech stack (usulan, sesuaikan jika pemilik proyek memutuskan lain)

| Lapisan | Pilihan |
|---|---|
| Backend | Python 3.11+, FastAPI |
| Pemrosesan DOCX | `python-docx` + `lxml` untuk manipulasi XML tingkat rendah |
| Render/pratinjau | LibreOffice headless (konversi ke PDF, pembaruan field) |
| Frontend | Next.js (React, TypeScript) |
| Validasi | Pydantic v2, JSON Schema untuk profil aturan |
| Antrian tugas | Mulai dengan background task sederhana, naik ke Redis + RQ bila perlu |
| Tes | `pytest`, `hypothesis` (properti), Playwright (UI) |

## 4. Struktur repo (target)

```
skripsi-formatter/
├─ AGENTS.md  CLAUDE.md  PRD.md  ARCHITECTURE.md  RULES_SPEC.md
├─ DOCX_NOTES.md  TASKS.md  TESTING.md
├─ apps/
│  ├─ api/                  # FastAPI
│  │  └─ app/
│  │     ├─ main.py
│  │     ├─ routers/        # HTTP endpoint tipis
│  │     ├─ services/       # orkestrasi alur (analyze, fix, render)
│  │     └─ core/
│  │        ├─ units.py         # konversi satuan (cm, twips, pt, half-point)
│  │        ├─ docx_model.py    # IR dokumen
│  │        ├─ formatting.py    # resolusi format efektif
│  │        ├─ roles.py         # klasifikasi peran paragraf
│  │        ├─ rules/           # loader profil, evaluator aturan
│  │        ├─ fixers/          # satu modul per kategori
│  │        ├─ fields.py        # TOC, PAGE, SEQ
│  │        └─ render.py        # LibreOffice
│  └─ web/                  # Next.js
├─ profiles/                # profil aturan JSON + schema
├─ tests/
│  ├─ fixtures/             # .docx uji (bersih, berantakan, tanpa style, dst.)
│  └─ ...
└─ docs/
```

Struktur ini boleh disesuaikan, tetapi perubahan besar dicatat di `ARCHITECTURE.md`.

## 5. Perintah (sesuaikan setelah scaffold ada)

```bash
# backend
cd apps/api
pip install -e ".[dev]"
pytest -q
ruff check . && ruff format --check .
mypy app
uvicorn app.main:app --reload

# frontend
cd apps/web
npm install
npm run dev
npm run lint && npm run typecheck && npm test
```

Jika perintah di atas tidak cocok dengan scaffold yang sebenarnya, perbarui bagian ini, jangan biarkan usang.

## 6. Konvensi kode

- Python: type hints wajib pada fungsi publik; `ruff` dan `mypy` harus bersih; fungsi kecil dan murni bila memungkinkan.
- Semua konversi satuan lewat `core/units.py`. Dilarang menaruh angka ajaib twips/half-point di tempat lain.
- Satu fixer per kategori aturan; fixer menerima IR + temuan + profil dan mengembalikan daftar perubahan.
- Setiap fixer mencatat perubahan: `rule_id`, lokasi, nilai lama, nilai baru.
- Manipulasi XML OOXML lewat helper terpusat; jangan menyebar potongan `lxml` ke banyak tempat.
- Endpoint HTTP tipis: logika di `services/` dan `core/`.
- Pesan untuk pengguna dalam bahasa Indonesia, disimpan di satu tempat (bukan hardcode tersebar). Identifier, komentar, dan commit message dalam bahasa Inggris.
- Jangan menambah dependensi besar tanpa alasan; sebutkan alasannya di PR/commit.

## 7. Cara bekerja pada tugas

1. Baca `TASKS.md`, ambil tugas berikutnya yang belum selesai, dan baca bagian relevan di `PRD.md` serta `RULES_SPEC.md`.
2. Tulis atau perbarui tes lebih dulu atau bersamaan (lihat `TESTING.md`).
3. Implementasikan perubahan terkecil yang memenuhi kriteria penerimaan.
4. Jalankan lint, typecheck, dan tes. Semua harus hijau.
5. Perbarui dokumentasi yang terpengaruh (aturan baru masuk `RULES_SPEC.md`, keputusan arsitektur ke `ARCHITECTURE.md`).
6. Centang tugas di `TASKS.md`.

### Definition of Done

- [ ] Kriteria penerimaan tugas terpenuhi.
- [ ] Tes baru ada dan lulus; tes lama tidak rusak.
- [ ] Tes integritas teks dan idempotensi lulus untuk fixer yang disentuh.
- [ ] Dokumen hasil terbuka tanpa error di python-docx dan LibreOffice.
- [ ] Lint, format, dan typecheck bersih.
- [ ] Dokumentasi diperbarui.

## 8. Tanyakan dulu sebelum

- Mengubah skema profil aturan (`RULES_SPEC.md`) dengan cara yang tidak kompatibel.
- Menambah layanan eksternal, terutama yang menerima isi dokumen (termasuk API LLM).
- Mengubah kebijakan retensi atau penyimpanan file.
- Menghapus atau mengganti tes yang ada.
- Menambah fitur yang tidak ada di `PRD.md` (terutama koreksi wording).

## 9. Jangan lakukan

- Jangan mengedit file di `tests/fixtures/` yang sudah ada (tambahkan fixture baru).
- Jangan commit dokumen mahasiswa asli atau data pribadi. Fixture harus sintetis atau sudah dianonimkan dengan izin.
- Jangan mengarang aturan kampus. Setiap profil harus mencantumkan sumber (nama dokumen pedoman dan halaman). Aturan yang tidak jelas diberi `fix_mode: "manual"`.
- Jangan menyembunyikan error pemrosesan: gagal ya gagal, dengan pesan yang bisa ditindaklanjuti.
- Jangan menyimpulkan bahwa pagination LibreOffice sama dengan Word. Beri peringatan di UI pratinjau.

## 10. Pegangan cepat DOCX

Detail ada di `DOCX_NOTES.md`. Ringkasnya:

- Format efektif = properti langsung > style paragraf (rantai `basedOn`) > `docDefaults`. Selalu hitung format efektif sebelum membandingkan dengan aturan.
- Satuan: 1 inci = 1440 twips; ukuran font disimpan dalam half-point; spasi baris `w:line` 240 = tunggal.
- Penomoran halaman berbeda per bagian memerlukan **section break** terpisah.
- Daftar isi adalah field yang dihitung Word; MVP menandai dokumen agar diperbarui saat dibuka.
