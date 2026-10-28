# PRD — Skripsi Formatter

> Versi: 0.1 (draft) · Status: siap dikembangkan · Bahasa dokumen: Indonesia
> Nama kerja produk: **Skripsi Formatter** (boleh diganti)

## 1. Ringkasan

Skripsi Formatter adalah tool berbasis web yang **memeriksa dan merapikan format** skripsi, tugas akhir, atau laporan mahasiswa dalam file Microsoft Word (.docx) sesuai **pedoman penulisan kampus/fakultas**. Tool ini mendeteksi pelanggaran format (margin, font, spasi, penomoran halaman, heading, daftar isi, caption, dan sebagainya), memperbaiki yang bisa diperbaiki secara otomatis, dan melaporkan sisanya untuk diperbaiki manual.

**Fokus produk: perapian format dan layout, bukan pembenahan wording.** Isi tulisan (kata, kalimat, tata bahasa, argumen) tidak diubah sama sekali.

## 2. Masalah

- Mahasiswa menghabiskan waktu berhari-hari merapikan format skripsi secara manual, terutama menjelang pengumpulan.
- Pedoman kampus berupa PDF puluhan halaman; aturannya mudah terlewat atau salah ditafsirkan.
- Dokumen mahasiswa biasanya diformat manual (bold dan ukuran font diatur satu-satu, spasi diatur dengan Enter/Space, nomor halaman diketik) sehingga daftar isi dan penomoran sering rusak.
- Revisi dari dosen pembimbing sering berupa koreksi format yang berulang.
- Tool yang ada (template Word, add-in generik) tidak mengenal aturan spesifik kampus dan tidak menjelaskan *apa yang salah dan di mana*.

## 3. Tujuan dan Non-Tujuan

### 3.1 Tujuan

| ID | Tujuan |
|---|---|
| G1 | Mengurangi waktu perapian format dari hitungan hari menjadi hitungan menit. |
| G2 | Menjamin **tidak ada isi teks yang berubah** akibat proses perapian. |
| G3 | Menjelaskan setiap temuan secara spesifik: aturan mana, lokasi, nilai sekarang, nilai yang diharapkan. |
| G4 | Mendukung banyak kampus tanpa mengubah kode, lewat profil aturan berbentuk JSON. |
| G5 | Menghasilkan file .docx yang tetap bisa diedit mahasiswa dan benar di Microsoft Word. |

### 3.2 Non-tujuan (di luar cakupan)

- Koreksi ejaan, tata bahasa, gaya bahasa, atau parafrase (**wording**).
- Menulis atau menghasilkan isi skripsi.
- Pengecekan plagiarisme atau kebenaran isi dan sitasi.
- Input selain .docx pada MVP (PDF, Google Docs, .doc lama, LaTeX).
- Mengedit halaman sampul dengan desain rumit (disediakan template, bukan diubah otomatis).

## 4. Pengguna

| Persona | Kebutuhan | Catatan |
|---|---|---|
| **Mahasiswa tingkat akhir** (utama) | Upload file, tahu apa yang salah, perbaiki otomatis, unduh hasil. | Biasanya bukan ahli Word; file sering berantakan. |
| **Admin prodi/perpustakaan** | Membuat dan memperbarui profil aturan kampus. | Sekunder; pada MVP profil dibuat oleh developer. |
| **Dosen pembimbing** | Melihat laporan kepatuhan format agar tidak membuang waktu mengoreksi format. | Opsional; laporan bisa dibagikan mahasiswa. |

## 5. Alur Pengguna Utama

1. Mahasiswa membuka web app dan mengunggah file .docx.
2. Memilih profil aturan (kampus, fakultas, jenjang).
3. Sistem menganalisis dan menampilkan **laporan temuan** dikelompokkan per kategori, dengan tingkat keparahan dan status "bisa diperbaiki otomatis / perlu manual".
4. Jika ada paragraf yang peran strukturalnya meragukan (misalnya apakah ini judul sub-bab), sistem meminta konfirmasi.
5. Mahasiswa memilih memperbaiki semua atau sebagian temuan.
6. Sistem menghasilkan file hasil (salinan, file asli tidak diubah), pratinjau PDF sebelum/sesudah, dan daftar perubahan.
7. Mahasiswa mengunduh hasil, membukanya di Word, dan memperbarui field (daftar isi) bila diminta.

## 6. Ruang Lingkup

### 6.1 MVP (rilis 1)

- Pemeriksaan dan perbaikan: ukuran kertas, margin, font, ukuran font, spasi baris, spasi paragraf, indentasi, perataan.
- Format heading bab dan sub-bab, termasuk penomoran bertingkat.
- Penomoran halaman bertahap (romawi untuk bagian awal, angka untuk isi) dan section break.
- Daftar isi, daftar gambar, dan daftar tabel otomatis.
- Caption gambar dan tabel (posisi, style, penomoran otomatis).
- Pengecekan struktur (kelengkapan dan urutan bagian awal, Bab I–V, daftar pustaka, lampiran).
- Laporan temuan, pratinjau PDF, unduh hasil, hapus data otomatis.
- Satu sampai tiga profil kampus contoh.

### 6.2 Rilis berikutnya

- Pengecekan format daftar pustaka dan kecocokan sitasi di teks dengan daftar pustaka (APA, IEEE, Harvard).
- Ekstraksi aturan dari PDF pedoman dengan bantuan AI (hasil selalu ditinjau manusia).
- Word Add-in (Office.js) dan Google Docs Add-on.
- Ekspor laporan kepatuhan untuk dosen pembimbing.
- Dashboard admin untuk profil aturan.

## 7. Kebutuhan Fungsional

Prioritas: **P0** wajib MVP, **P1** sebaiknya MVP, **P2** setelah MVP.

| ID | Kebutuhan | Prioritas | Kriteria penerimaan |
|---|---|---|---|
| FR-01 | Upload file .docx. Tolak ekstensi lain (termasuk .docm dan .doc) dengan pesan jelas. | P0 | File valid diterima; file > batas ukuran, bukan ZIP/OOXML valid, atau berisi macro ditolak dengan alasan. |
| FR-02 | Pilih profil aturan dari daftar profil terdaftar. | P0 | Profil dimuat dan divalidasi terhadap JSON Schema; profil tidak valid tidak muncul. |
| FR-03 | Analisis dokumen dan hasilkan daftar temuan. | P0 | Tiap temuan memuat: `rule_id`, kategori, severity, lokasi (indeks paragraf, section, perkiraan halaman), nilai aktual, nilai diharapkan, `fix_mode`. |
| FR-04 | Klasifikasi peran paragraf (judul bab, sub-bab, isi, caption, kutipan blok, entri pustaka, dan seterusnya) dengan skor keyakinan. | P0 | Style/outline level dipakai lebih dulu; heuristik untuk format manual; keyakinan rendah ditandai untuk konfirmasi. |
| FR-05 | Laporan temuan: ringkasan per kategori, filter, urut per lokasi. | P0 | Laporan bisa diunduh sebagai JSON dan HTML. |
| FR-06 | Perbaikan otomatis selektif (semua, per kategori, atau per temuan). | P0 | Hasil berupa file baru; file asli tidak berubah (hash sama); setiap perubahan tercatat. |
| FR-07 | Perbaikan idempoten. | P0 | Menjalankan perbaikan dua kali menghasilkan dokumen yang sama dengan sekali. |
| FR-08 | Penomoran halaman bertahap dan section break sesuai profil. | P0 | Bagian awal romawi, isi angka mulai 1; posisi nomor sesuai profil; halaman awal bab sesuai profil. |
| FR-09 | Buat atau perbarui daftar isi, daftar gambar, daftar tabel sebagai field Word. | P0 | Field TOC/TOC \c tersisip; dokumen ditandai agar field diperbarui saat dibuka; entri awal terisi bila memungkinkan (lihat DOCX_NOTES.md). |
| FR-10 | Caption gambar/tabel memakai field SEQ, style Caption, posisi sesuai profil. | P0 | Penomoran otomatis berurutan; posisi benar. |
| FR-11 | Pengecekan struktur dokumen. | P1 | Bagian wajib hilang atau salah urut dilaporkan. |
| FR-12 | Pratinjau PDF sebelum dan sesudah. | P1 | PDF dirender via LibreOffice headless; ada peringatan bahwa paginasi bisa berbeda tipis dari Word. |
| FR-13 | Konfirmasi peran paragraf oleh pengguna untuk temuan keyakinan rendah. | P1 | Pilihan pengguna disimpan untuk sesi itu dan memengaruhi perbaikan. |
| FR-14 | Hapus file otomatis. | P0 | File asli dan hasil terhapus dalam batas waktu retensi (default 1 jam) atau saat pengguna menghapus. |
| FR-15 | Pengecekan format daftar pustaka. | P2 | Urutan, hanging indent, kecocokan sitasi dan entri. |
| FR-16 | Ekstraksi aturan dari PDF pedoman dengan AI. | P2 | Keluaran berupa draf profil JSON yang wajib ditinjau dan disetujui admin sebelum aktif. |
| FR-17 | Word Add-in. | P2 | Fitur inti tersedia di dalam Word. |

## 8. Kebutuhan Non-Fungsional

| ID | Kebutuhan | Target (usulan, validasi saat pengujian) |
|---|---|---|
| NFR-01 | Integritas isi | Teks isi (urutan karakter paragraf) sebelum dan sesudah perbaikan identik. Dites otomatis pada setiap perbaikan. |
| NFR-02 | Determinisme | Tidak ada LLM yang menulis ke dokumen. Input sama dan profil sama menghasilkan output yang sama. |
| NFR-03 | Kinerja | p95 analisis < 30 detik dan perbaikan + pratinjau < 90 detik untuk dokumen 100 halaman. |
| NFR-04 | Privasi | Dokumen skripsi belum dipublikasikan: enkripsi saat transit, retensi singkat, tidak dipakai untuk pelatihan model, log tanpa isi dokumen. |
| NFR-05 | Keamanan | Validasi ZIP (batas ukuran terkompresi/terurai, anti zip bomb, anti path traversal), tolak macro, parsing XML aman dari XXE, batas ukuran upload. |
| NFR-06 | Kompatibilitas | Hasil terbuka tanpa peringatan korupsi di Word 2016+ dan LibreOffice. |
| NFR-07 | Keterlacakan | Setiap perubahan tercatat: aturan, lokasi, nilai lama, nilai baru. |
| NFR-08 | Ekstensibilitas | Menambah kampus = menambah satu file profil JSON, tanpa perubahan kode. |
| NFR-09 | Aksesibilitas UI | UI dapat dipakai dengan keyboard; kontras memadai; bahasa Indonesia sebagai bawaan. |

## 9. Katalog Aturan (ringkas)

Rincian lengkap dan skema JSON ada di `RULES_SPEC.md`. Kategori: `PAGE`, `FONT`, `PARA`, `HEAD`, `NUM`, `TOC`, `LOF`, `LOT`, `CAP`, `FIG`, `TBL`, `BIB`, `STR`. Tiap aturan punya `fix_mode`:

- `auto`: dicek dan diperbaiki otomatis.
- `suggest`: dicek, perbaikan diusulkan dan perlu persetujuan per temuan.
- `manual`: hanya dilaporkan.

## 10. Prinsip Desain Produk

1. **Jangan pernah mengubah isi.** Hanya properti format dan struktur yang disentuh.
2. **File asli suci.** Semua perbaikan dilakukan pada salinan.
3. **Jelaskan, jangan sulap.** Setiap temuan dan perubahan harus bisa dibaca manusia.
4. **Ragu berarti tanya.** Keyakinan rendah = minta konfirmasi, bukan menebak.
5. **Aturan adalah data, bukan kode.** Perbedaan kampus hidup di profil JSON.
6. **Pakai fitur Word yang benar.** Style, field, section, dan numbering asli, supaya hasilnya tetap rapi saat mahasiswa menyunting lagi.

## 11. Metrik Keberhasilan (usulan target)

| Metrik | Target |
|---|---|
| Waktu dari upload sampai file rapi | < 5 menit untuk dokumen tipikal |
| Persentase temuan `auto` yang diperbaiki dengan benar pada korpus uji | ≥ 90% |
| Kasus isi teks berubah | 0 |
| Temuan salah (false positive) pada korpus uji | < 5% |
| Dokumen hasil yang terbuka tanpa peringatan di Word | 100% pada korpus uji |
| Kepuasan pengguna uji (skala 1–5) | ≥ 4 |

## 12. Risiko dan Mitigasi

| Risiko | Dampak | Mitigasi |
|---|---|---|
| Dokumen berantakan, format manual, tanpa Style | Salah deteksi peran paragraf | Heuristik berlapis, skor keyakinan, konfirmasi pengguna, korpus uji berantakan. |
| Paginasi Word dan LibreOffice berbeda | Pratinjau tidak persis | Peringatan jelas; font metrik-kompatibel (Liberation Serif untuk Times New Roman); hasil akhir tetap dinilai di Word. |
| Field daftar isi baru terisi saat dibuka di Word | Pengguna melihat daftar isi kosong/lama | Tandai agar diperbarui saat dibuka; isi entri awal dari hasil render; beri instruksi singkat di UI. |
| Aturan kampus ambigu atau berubah | Perbaikan tidak sesuai harapan | Profil memuat sumber (dokumen dan halaman) dan versi; aturan ambigu diberi `fix_mode: manual`. |
| Perbaikan merusak dokumen | Kehilangan kepercayaan pengguna | Salinan, tes idempotensi, tes integritas isi, validasi buka-ulang, tombol unduh file asli selalu ada. |
| Kebocoran dokumen belum dipublikasikan | Risiko privasi | Retensi singkat, hapus otomatis, tanpa log isi, tanpa pelatihan model. |
| Tracked changes dan komentar di dokumen | Perbaikan menimpa revisi | Deteksi dan peringatkan; mode aman: jangan ubah paragraf dengan revisi aktif tanpa persetujuan. |

## 13. Asumsi

- Pengguna utama menulis di Microsoft Word dan menyerahkan .docx.
- Satu profil aturan berlaku untuk satu dokumen.
- Profil awal dibuat developer dari PDF pedoman kampus yang sah.
- Bahasa UI dan laporan: Indonesia (Inggris dapat ditambahkan kemudian).

## 14. Pertanyaan Terbuka

- [ ] Target awal: satu kampus atau banyak kampus? (memengaruhi jumlah profil MVP)
- [ ] Apakah ada akun pengguna pada MVP, atau sesi anonim dengan hapus otomatis?
- [ ] Model bisnis: gratis, kuota, atau berlangganan?
- [ ] Batas ukuran file dan jumlah halaman maksimum.
- [ ] Tech stack final (usulan di `ARCHITECTURE.md`).
- [ ] Apakah halaman sampul disediakan sebagai template per kampus?

## 15. Rencana Rilis

Ringkas: fondasi → pemeriksa + perbaikan dasar → penomoran/section → daftar isi dan caption → klasifikasi peran → UI web → pengerasan. Rincian tugas ada di `TASKS.md`.

## 16. Glosarium

| Istilah | Arti |
|---|---|
| Profil aturan | File JSON berisi aturan format satu kampus/fakultas/jenjang. |
| Temuan (finding) | Satu pelanggaran aturan pada satu lokasi dokumen. |
| Peran (role) | Fungsi struktural paragraf: judul bab, isi, caption, dan seterusnya. |
| Fix mode | `auto`, `suggest`, atau `manual`. |
| Field | Elemen dinamis Word (TOC, PAGE, SEQ) yang dihitung ulang oleh Word. |
| Section | Bagian dokumen Word dengan pengaturan halaman sendiri (margin, penomoran, header/footer). |
| IR | Intermediate Representation: model dokumen internal hasil parsing .docx. |
