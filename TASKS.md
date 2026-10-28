# TASKS.md — Rencana Kerja

Daftar kerja berurutan untuk agent pengembang. Ambil tugas dari atas yang belum selesai. Centang saat Definition of Done (lihat `AGENTS.md`) terpenuhi. Tambahkan tugas baru di bagian akhir fase yang relevan, jangan hanya di percakapan.

Legenda prioritas: **P0** MVP wajib · **P1** sebaiknya MVP · **P2** setelah MVP.

## Fase 0 — Fondasi repo

- [x] P0 Scaffold monorepo sesuai `AGENTS.md` (apps/api, apps/web, profiles, tests, docs).
- [x] P0 Siapkan backend FastAPI minimal (`/health`), konfigurasi, struktur logging tanpa isi dokumen.
- [x] P0 Siapkan lint, format, typecheck, dan test runner; CI sederhana yang menjalankannya.
- [x] P0 `core/units.py` + tes konversi (cm ↔ twips ↔ EMU, pt ↔ half-point).
- [x] P0 Siapkan korpus fixture awal (lihat `TESTING.md`): minimal 3 dokumen sintetis (bersih, berantakan, tanpa style).

## Fase 1 — Ingest dan model dokumen

- [x] P0 Validasi file: ekstensi, ukuran, integritas ZIP, batas terurai, tolak `.docm`/macro, parser XML aman.
- [x] P0 Penyimpanan sementara dengan TTL + job pembersih + endpoint hapus.
- [x] P0 `docx_model.py`: parse ke IR (paragraf, tabel, gambar inline, section, header/footer, field).
- [x] P0 `formatting.py`: format efektif (properti langsung → style `basedOn` → `docDefaults`).
- [x] P0 Helper teks ternormalisasi + tes integritas (dipakai fase berikutnya).
- [x] P0 Endpoint `POST /v1/documents`.

## Fase 2 — Profil dan evaluator

- [x] P0 JSON Schema profil + loader + dukungan `extends` + tes validasi.
- [x] P0 Profil contoh dari `RULES_SPEC.md` (ditandai CONTOH).
- [x] P0 Kerangka evaluator aturan + format temuan + ID temuan stabil.
- [x] P0 Aturan PAGE-001..003, FONT-001..004, PARA-001..004, PARA-008.
- [x] P0 Endpoint `analyze`, `jobs`, `findings`, `report` (JSON dan HTML).

## Fase 3 — Fixer dasar

- [x] P0 Kerangka fixer (kontrak `apply`, change log, idempotensi).
- [x] P0 Fixer PAGE (ukuran, margin, jarak header/footer) per section.
- [x] P0 Fixer FONT dan PARA lewat Style (ubah/buat style) + properti langsung hanya untuk penyimpangan.
- [x] P0 Tes integritas teks dan idempotensi untuk semua fixer di atas.
- [x] P0 Endpoint `fix`, `download`, `changelog`.
- [x] P0 Validasi buka-ulang hasil (python-docx dan LibreOffice) otomatis pada setiap perbaikan.

## Fase 4 — Klasifikasi peran

- [x] P0 Peran berbasis style/outline level.
- [x] P0 Heuristik format manual (pola BAB/numbering, kapital, rata tengah, bold, ukuran).
- [x] P0 Skor keyakinan + bukti (`evidence`) + ambang konfigurasi.
- [x] P1 Konteks posisi (kandidat caption, entri pustaka, entri daftar isi).
- [x] P1 Endpoint `GET/PUT roles` untuk konfirmasi pengguna.
- [ ] P2 Opsi LLM untuk kasus ambigu (setelah persetujuan pemilik proyek; lihat `AGENTS.md` bagian 8).

## Fase 5 — Heading, penomoran halaman, section

- [x] P0 Aturan dan fixer HEAD-001, HEAD-002, HEAD-004, HEAD-005.
- [x] P0 Pembuatan section break bagian awal / isi.
- [x] P0 Aturan dan fixer NUM-001..005 (romawi/angka, posisi, sampul tidak bernomor).
- [x] P1 NUM-004 (halaman pertama bab berbeda) dengan strategi section per bab.
- [x] P1 NUM-006 dan HEAD-003 (konversi ketikan ke otomatis) sebagai `suggest` dengan persetujuan per temuan dan pengecualian di tes integritas.

## Fase 6 — Daftar isi, caption, gambar, tabel

- [x] P0 TOC-001, TOC-003..005: sisip/rapikan field TOC; tandai `updateFields`.
- [x] P0 LOF-001, LOT-001 (daftar gambar/tabel).
- [x] P0 CAP-002, CAP-003, CAP-005; caption berkelanjutan (`continuous`) dengan SEQ.
- [x] P1 CAP-004 (ketikan → SEQ).
- [x] P1 Caption `per_chapter` (lihat peringatan di `DOCX_NOTES.md` bagian 6).
- [x] P0 FIG-001, FIG-002, TBL-001..005.
- [x] P1 Isi entri awal daftar isi dari nomor halaman hasil render (opsi 2 di `DOCX_NOTES.md`).
- [x] P0 TOC-002 (daftar isi diketik → field) sebagai `suggest`.

## Fase 7 — Struktur dan pratinjau

- [x] P1 STR-001..004 (kelengkapan, urutan, halaman baru).
- [x] P1 `render.py`: LibreOffice headless, profil per worker, timeout, penanganan gagal.
- [x] P1 Endpoint `preview?which=before|after` + peringatan perbedaan paginasi.
- [x] P1 Pasang font metrik-kompatibel di image/server.

## Fase 8 — Frontend

- [x] P0 Halaman upload + pilih profil.
- [x] P0 Laporan temuan: kelompok per kategori, filter severity/fix mode, lokasi dan nilai aktual vs diharapkan.
- [x] P1 Alur konfirmasi peran paragraf.
- [x] P0 Pilih perbaikan (semua/kategori/temuan) + status job.
- [x] P1 Pratinjau sebelum/sesudah dan unduh (.docx hasil, change log, laporan).
- [x] P0 Instruksi memperbarui field di Word (dialog "update fields").
- [x] P0 Tampilan privasi: kebijakan retensi dan tombol hapus.

## Fase 9 — Pengerasan

- [x] P0 Rate limit, batas ukuran, tes keamanan parser (zip bomb, XXE, path traversal).
- [x] P0 Tes performa terhadap target NFR-03 (dokumen 100 halaman).
- [x] P0 Tes kompatibilitas: buka hasil di Word 2016+ dan LibreOffice tanpa peringatan.
- [x] P1 Penanganan tracked changes, komentar, `w:sdt`, kotak teks (deteksi dan peringatan).
- [x] P1 Observabilitas: metrik per tahap, kode error terstruktur.
- [ ] P1 Uji pengguna dengan beberapa mahasiswa; catat temuan sebagai tugas baru.

## Setelah MVP

- [x] P2 BIB-001..004 (pustaka: urutan, hanging indent, kecocokan sitasi).
- [ ] P2 Ekstraksi aturan dari PDF pedoman dengan AI (hasil ditinjau manusia sebelum aktif).
- [ ] P2 Dashboard admin untuk profil.
- [ ] P2 Word Add-in (Office.js) memakai ulang `core` lewat API.
- [ ] P2 Google Docs Add-on.
- [ ] P2 Laporan kepatuhan untuk dosen pembimbing.
