# RULES_SPEC.md — Profil Aturan dan Katalog Aturan

Dokumen ini mendefinisikan **format profil aturan** (JSON) dan **katalog aturan** yang dikenali evaluator. Aturan kampus hidup di profil, bukan di kode.

> Semua nilai pada contoh di bawah adalah **CONTOH** untuk menjelaskan format. Itu bukan aturan kampus mana pun. Profil nyata harus mencantumkan sumber (nama pedoman dan halaman) dan dibuat dari pedoman kampus yang sah.

## 1. Konsep

- **Profil**: satu file JSON untuk satu kampus/fakultas/jenjang/jenis dokumen.
- **Nilai spesifikasi**: nilai format yang diharapkan (margin, font, dan seterusnya), dikelompokkan per **peran** paragraf.
- **Aturan**: pemeriksaan bernama (`PAGE-002`, dan seterusnya) yang membandingkan dokumen dengan nilai spesifikasi. Profil dapat menyalakan/mematikan aturan, mengubah severity dan `fix_mode`.
- **Peran (role)**: fungsi struktural paragraf (lihat bagian 4).
- **Fix mode**: `auto` (diperbaiki otomatis), `suggest` (diusulkan, perlu persetujuan per temuan), `manual` (hanya dilaporkan).
- **Severity**: `error`, `warning`, `info`.

## 2. Skema profil (referensi field)

| Field | Tipe | Wajib | Keterangan |
|---|---|---|---|
| `profile_id` | string (slug) | ya | Unik. Huruf kecil, angka, tanda minus. |
| `name` | string | ya | Nama tampilan. |
| `version` | string (semver) | ya | Versi profil. |
| `language` | string | ya | Bahasa pesan, misalnya `id`. |
| `extends` | string | tidak | `profile_id` induk; nilai digabung mendalam (anak menimpa induk). |
| `source` | object | ya | `document`, `edition`, `pages`, `notes`. Asal aturan. |
| `page` | object | ya | Ukuran kertas, orientasi, margin. |
| `text` | object | ya | Font dasar (keluarga, ukuran, warna). |
| `roles` | object | ya | Format per peran (lihat bagian 4). |
| `page_numbering` | object | ya | Penomoran halaman per kelompok bagian. |
| `structure` | object | ya | Bagian wajib, urutan, dan aturan halaman baru. |
| `toc` | object | ya | Daftar isi, daftar gambar, daftar tabel. |
| `captions` | object | ya | Caption gambar dan tabel. |
| `tolerances` | object | tidak | Toleransi pembandingan (misalnya `margin_cm`). |
| `rules` | array | tidak | Penyesuaian per aturan (`enabled`, `severity`, `fix_mode`). |

Satuan di profil: **cm** untuk jarak, **pt** untuk ukuran font dan spasi paragraf, **kelipatan** untuk spasi baris (1.5 = satu setengah). Konversi ke twips/half-point dilakukan hanya di `core/units.py`.

Validasi: `profiles/schema/profile.schema.json` (JSON Schema draft 2020-12). Profil yang gagal validasi tidak dimuat.

## 3. Contoh profil lengkap (CONTOH)

```json
{
  "profile_id": "contoh-s1-skripsi",
  "name": "CONTOH: Skripsi S1 (bukan aturan kampus mana pun)",
  "version": "0.1.0",
  "language": "id",
  "source": {
    "document": "Pedoman Penulisan Skripsi (CONTOH)",
    "edition": "2024",
    "pages": "isi dengan nomor halaman pedoman asli",
    "notes": "Nilai di file ini hanya contoh format."
  },
  "page": {
    "size": "A4",
    "orientation": "portrait",
    "margins_cm": { "top": 4.0, "left": 4.0, "bottom": 3.0, "right": 3.0 },
    "header_footer_distance_cm": { "header": 1.25, "footer": 1.25 }
  },
  "text": {
    "font_family": "Times New Roman",
    "font_size_pt": 12,
    "color_hex": "000000"
  },
  "roles": {
    "body": {
      "line_spacing": 1.5,
      "space_before_pt": 0,
      "space_after_pt": 0,
      "alignment": "justify",
      "first_line_indent_cm": 1.25
    },
    "chapter_label": {
      "text_pattern": "^BAB\\s+[IVXLC]+$",
      "bold": true,
      "all_caps": true,
      "alignment": "center",
      "font_size_pt": 12,
      "line_spacing": 1.5,
      "space_before_pt": 0,
      "space_after_pt": 0,
      "keep_with_next": true,
      "page_break_before": true
    },
    "chapter_title": {
      "bold": true,
      "all_caps": true,
      "alignment": "center",
      "font_size_pt": 12,
      "line_spacing": 1.5,
      "space_before_pt": 0,
      "space_after_pt": 12,
      "keep_with_next": true
    },
    "heading_2": {
      "bold": true,
      "alignment": "left",
      "font_size_pt": 12,
      "line_spacing": 1.5,
      "space_before_pt": 12,
      "space_after_pt": 6,
      "left_indent_cm": 0,
      "hanging_indent_cm": 1.0,
      "numbering": "decimal_dotted",
      "keep_with_next": true
    },
    "heading_3": {
      "bold": true,
      "alignment": "left",
      "font_size_pt": 12,
      "line_spacing": 1.5,
      "space_before_pt": 6,
      "space_after_pt": 6,
      "left_indent_cm": 0,
      "hanging_indent_cm": 1.25,
      "numbering": "decimal_dotted",
      "keep_with_next": true
    },
    "caption_figure": {
      "alignment": "center",
      "font_size_pt": 11,
      "line_spacing": 1.0,
      "space_before_pt": 6,
      "space_after_pt": 12
    },
    "caption_table": {
      "alignment": "center",
      "font_size_pt": 11,
      "line_spacing": 1.0,
      "space_before_pt": 12,
      "space_after_pt": 6,
      "keep_with_next": true
    },
    "block_quote": {
      "line_spacing": 1.0,
      "left_indent_cm": 1.25,
      "right_indent_cm": 1.25,
      "first_line_indent_cm": 0,
      "alignment": "justify",
      "space_after_pt": 12
    },
    "table_text": {
      "font_size_pt": 11,
      "line_spacing": 1.0,
      "space_before_pt": 0,
      "space_after_pt": 0
    },
    "bibliography_entry": {
      "line_spacing": 1.0,
      "space_after_pt": 12,
      "alignment": "left",
      "hanging_indent_cm": 1.25,
      "sorted": "alphabetical"
    }
  },
  "page_numbering": {
    "cover": { "numbered": false },
    "front_matter": {
      "format": "lowerRoman",
      "start": 1,
      "position": "bottom_center"
    },
    "body": {
      "format": "decimal",
      "start": 1,
      "position": "top_right",
      "chapter_first_page": { "position": "bottom_center" }
    }
  },
  "structure": {
    "sections": [
      { "id": "cover", "match": "^HALAMAN SAMPUL$", "group": "cover", "required": true, "new_page": true },
      { "id": "approval", "match": "^LEMBAR PENGESAHAN$", "group": "front_matter", "required": true, "new_page": true },
      { "id": "preface", "match": "^KATA PENGANTAR$", "group": "front_matter", "required": true, "new_page": true },
      { "id": "abstract", "match": "^ABSTRAK$", "group": "front_matter", "required": true, "new_page": true },
      { "id": "toc", "match": "^DAFTAR ISI$", "group": "front_matter", "required": true, "new_page": true },
      { "id": "list_tables", "match": "^DAFTAR TABEL$", "group": "front_matter", "required": false, "new_page": true },
      { "id": "list_figures", "match": "^DAFTAR GAMBAR$", "group": "front_matter", "required": false, "new_page": true },
      { "id": "chapter_1", "match": "^BAB\\s+I$", "group": "body", "required": true, "new_page": true },
      { "id": "chapter_2", "match": "^BAB\\s+II$", "group": "body", "required": true, "new_page": true },
      { "id": "chapter_3", "match": "^BAB\\s+III$", "group": "body", "required": true, "new_page": true },
      { "id": "chapter_4", "match": "^BAB\\s+IV$", "group": "body", "required": true, "new_page": true },
      { "id": "chapter_5", "match": "^BAB\\s+V$", "group": "body", "required": true, "new_page": true },
      { "id": "references", "match": "^DAFTAR PUSTAKA$", "group": "body", "required": true, "new_page": true },
      { "id": "appendix", "match": "^LAMPIRAN", "group": "body", "required": false, "new_page": true }
    ],
    "enforce_order": true
  },
  "toc": {
    "title": "DAFTAR ISI",
    "levels": 3,
    "leader": "dots",
    "right_align_page_numbers": true,
    "list_of_figures": { "enabled": true, "title": "DAFTAR GAMBAR" },
    "list_of_tables": { "enabled": true, "title": "DAFTAR TABEL" }
  },
  "captions": {
    "figure": {
      "label": "Gambar",
      "position": "below",
      "numbering": "per_chapter",
      "separator": "."
    },
    "table": {
      "label": "Tabel",
      "position": "above",
      "numbering": "per_chapter",
      "separator": "."
    }
  },
  "tolerances": {
    "margin_cm": 0.05,
    "indent_cm": 0.05,
    "font_size_pt": 0,
    "spacing_pt": 0.5,
    "line_spacing": 0.02
  },
  "rules": [
    { "id": "HEAD-003", "fix_mode": "suggest", "severity": "warning" },
    { "id": "BIB-001", "fix_mode": "suggest", "severity": "warning" },
    { "id": "PARA-005", "enabled": true, "fix_mode": "suggest" }
  ]
}
```

## 4. Peran (role)

| Role | Keterangan |
|---|---|
| `cover` | Halaman sampul |
| `front_title` | Judul bagian awal (KATA PENGANTAR, DAFTAR ISI, dan seterusnya) |
| `chapter_label` | Baris "BAB I" |
| `chapter_title` | Judul bab (baris setelah label) |
| `heading_2`, `heading_3`, `heading_4` | Sub-bab bertingkat |
| `body` | Paragraf isi |
| `list_item` | Butir daftar (bullet/nomor) |
| `block_quote` | Kutipan blok |
| `caption_figure`, `caption_table` | Keterangan gambar/tabel |
| `table_text` | Teks dalam tabel |
| `bibliography_entry` | Entri daftar pustaka |
| `toc_entry` | Entri daftar isi/gambar/tabel (jangan dianggap `body`) |
| `footnote_text` | Teks catatan kaki |
| `other` | Tidak diketahui; tidak diperiksa |

Peran dengan keyakinan di bawah ambang (`confidence < 0.7`, dapat dikonfigurasi) ditandai untuk konfirmasi pengguna. Paragraf berperan `other` tidak diperiksa dan tidak diubah.

## 5. Katalog aturan

`fix` = fix mode bawaan. Profil boleh menimpanya lewat `rules[]`.

### PAGE — Halaman

| ID | Aturan | Fix |
|---|---|---|
| PAGE-001 | Ukuran kertas sesuai profil | auto |
| PAGE-002 | Margin atas/bawah/kiri/kanan sesuai profil (per section) | auto |
| PAGE-003 | Jarak header/footer sesuai profil | auto |
| PAGE-004 | Orientasi halaman sesuai profil (landscape hanya bila diizinkan) | suggest |

### FONT — Huruf

| ID | Aturan | Fix |
|---|---|---|
| FONT-001 | Keluarga font sesuai profil (ascii, hAnsi, cs, eastAsia) | auto |
| FONT-002 | Ukuran font sesuai peran | auto |
| FONT-003 | Warna teks sesuai profil | auto |
| FONT-004 | Tidak ada font nyasar di tengah dokumen | auto |

### PARA — Paragraf

| ID | Aturan | Fix |
|---|---|---|
| PARA-001 | Spasi baris sesuai peran | auto |
| PARA-002 | Spasi sebelum/sesudah paragraf | auto |
| PARA-003 | Indentasi baris pertama/kiri/kanan/hanging | auto |
| PARA-004 | Perataan teks (rata kiri/tengah/justify) | auto |
| PARA-005 | Paragraf kosong berulang dipakai sebagai jarak | suggest |
| PARA-006 | Spasi atau tab berulang dipakai sebagai indentasi | suggest |
| PARA-007 | Line break manual dipakai untuk layout | suggest |
| PARA-008 | Widow/orphan control aktif | auto |

### HEAD — Heading

| ID | Aturan | Fix |
|---|---|---|
| HEAD-001 | Format judul bab (label dan judul): huruf kapital, bold, perataan, spasi | auto |
| HEAD-002 | Format heading level 2 dan seterusnya | auto |
| HEAD-003 | Penomoran heading memakai numbering otomatis, bukan ketikan | suggest |
| HEAD-004 | Heading tidak terpisah dari paragraf sesudahnya (keep with next) | auto |
| HEAD-005 | Bab dimulai di halaman baru | auto |
| HEAD-006 | Hierarki heading tidak melompat level | manual |

### NUM — Penomoran halaman

| ID | Aturan | Fix |
|---|---|---|
| NUM-001 | Bagian awal memakai angka romawi | auto |
| NUM-002 | Bagian isi memakai angka arab, mulai dari nomor sesuai profil | auto |
| NUM-003 | Posisi nomor halaman sesuai profil | auto |
| NUM-004 | Halaman pertama bab memakai aturan khusus sesuai profil | auto |
| NUM-005 | Sampul tidak bernomor | auto |
| NUM-006 | Nomor halaman diketik manual, bukan field PAGE | suggest |

### TOC, LOF, LOT — Daftar isi, gambar, tabel

| ID | Aturan | Fix |
|---|---|---|
| TOC-001 | Daftar isi ada | auto |
| TOC-002 | Daftar isi berupa field, bukan ketikan | suggest |
| TOC-003 | Kedalaman level sesuai profil | auto |
| TOC-004 | Daftar isi sinkron dengan heading (ditandai agar diperbarui) | auto |
| TOC-005 | Format entri: titik pemandu, nomor halaman rata kanan | auto |
| LOF-001 | Daftar gambar ada bila ada gambar ber-caption | auto |
| LOT-001 | Daftar tabel ada bila ada tabel ber-caption | auto |

### CAP — Caption

| ID | Aturan | Fix |
|---|---|---|
| CAP-001 | Setiap gambar/tabel punya caption | manual |
| CAP-002 | Posisi caption sesuai profil (gambar di bawah, tabel di atas, atau sesuai profil) | auto |
| CAP-003 | Style dan format caption sesuai profil | auto |
| CAP-004 | Penomoran caption memakai field SEQ, bukan ketikan | suggest |
| CAP-005 | Nomor caption berurutan tanpa lompatan atau duplikat | auto |

### FIG — Gambar

| ID | Aturan | Fix |
|---|---|---|
| FIG-001 | Gambar rata tengah (atau sesuai profil) | auto |
| FIG-002 | Gambar tidak melewati margin (skala proporsional) | auto |
| FIG-003 | Gambar mengambang (floating) mengganggu alur teks | manual |

### TBL — Tabel

| ID | Aturan | Fix |
|---|---|---|
| TBL-001 | Tabel tidak melewati margin | auto |
| TBL-002 | Baris judul tabel berulang di halaman berikutnya | auto |
| TBL-003 | Baris tabel tidak terpotong antarhalaman | auto |
| TBL-004 | Font/spasi teks dalam tabel sesuai peran `table_text` | auto |
| TBL-005 | Perataan tabel sesuai profil | auto |

### BIB — Daftar pustaka

| ID | Aturan | Fix |
|---|---|---|
| BIB-001 | Entri terurut sesuai profil (misalnya alfabetis) | suggest |
| BIB-002 | Hanging indent sesuai profil | auto |
| BIB-003 | Spasi dalam dan antar-entri sesuai profil | auto |
| BIB-004 | Sitasi di teks cocok dengan entri pustaka (P2) | manual |

### STR — Struktur

| ID | Aturan | Fix |
|---|---|---|
| STR-001 | Bagian wajib ada | manual |
| STR-002 | Bagian tampil dalam urutan yang benar | manual |
| STR-003 | Bab I sampai V (atau sesuai profil) lengkap | manual |
| STR-004 | Bagian wajib dimulai di halaman baru | auto |

## 6. Catatan penting tentang integritas teks

Beberapa aturan `suggest` dapat menyentuh teks yang terlihat:

- **HEAD-003**: mengubah nomor heading ketikan ("1.1 Latar Belakang") menjadi numbering otomatis berarti **menghapus awalan nomor yang diketik**. Hanya dilakukan setelah persetujuan pengguna per temuan dan dicatat di change log. Tes integritas teks membandingkan teks **setelah mengecualikan awalan yang disetujui**.
- **CAP-004**: mengganti nomor caption ketikan dengan field SEQ harus mempertahankan hasil tampilan yang sama bila urutannya sudah benar. Bila nomor lama salah, perubahan nomor dilaporkan sebagai perubahan teks yang terlihat.
- **PARA-005/006/007**: menghapus paragraf kosong atau spasi/tab untuk indentasi tidak mengubah kata-kata, tetapi mengubah karakter spasi. Selalu `suggest`, dan tes integritas membandingkan teks setelah normalisasi spasi.
- **BIB-001**: mengurutkan ulang entri mengubah urutan paragraf, bukan isinya. Selalu `suggest`.

Aturan `auto` tidak boleh mengubah satu karakter pun teks.

## 7. Evaluasi dan temuan

1. Evaluator memuat profil (gabungan `extends` bila ada), lalu memilih aturan yang `enabled`.
2. Untuk tiap paragraf/section/tabel/gambar dengan peran yang relevan, hitung **format efektif** dan bandingkan dengan nilai profil memakai toleransi dari `tolerances`.
3. Setiap penyimpangan menjadi satu **temuan** dengan ID stabil: hash dari `rule_id` + lokasi + nilai aktual.
4. Temuan mengikuti `severity` dan `fix_mode` dari profil (jika ada), kalau tidak dari katalog.
5. Perbaikan berlaku untuk temuan yang dipilih; sisanya tetap dilaporkan.

## 8. Menambah aturan atau profil baru

**Profil baru:**
1. Salin profil contoh, ubah `profile_id`, `name`, `source`.
2. Isi nilai dari pedoman kampus; aturan yang ambigu → set `fix_mode: "manual"`.
3. Jalankan validasi skema dan tes profil.
4. Tambahkan dokumen uji dan golden findings untuk profil itu.

**Aturan baru:**
1. Tambahkan baris di katalog bagian 5 dengan ID baru (kategori + nomor berikutnya).
2. Implementasikan pemeriksa (dan fixer bila `auto`/`suggest`) di `core/rules` dan `core/fixers`.
3. Tambahkan kunci pesan Indonesia.
4. Tambahkan tes: kasus lolos, kasus melanggar, idempotensi, integritas teks.
5. Jangan mengubah arti ID aturan yang sudah dipakai profil.
