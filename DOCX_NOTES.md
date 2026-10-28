# DOCX_NOTES.md — Catatan Teknis OOXML untuk Pengembang

Catatan praktis tentang struktur .docx yang relevan untuk proyek ini. Baca sebelum menulis fixer. Sebelum menganggap sebuah fakta di sini final, **verifikasi dengan tes dan dokumen nyata** (buka di Word dan LibreOffice).

## 1. Satuan

| Besaran | Satuan di XML | Konversi |
|---|---|---|
| Jarak halaman, margin, indentasi, spasi paragraf | twips (1/20 pt) | 1 inci = 1440 twips; 1 cm ≈ 566,93 twips; 1 pt = 20 twips |
| Ukuran font `w:sz` | half-point | 12 pt = 24 |
| Spasi baris `w:line` (rule `auto`) | per 240 | 240 = tunggal, 360 = 1,5, 480 = ganda |
| Spasi baris rule `exact`/`atLeast` | twips | |
| Ukuran gambar (`wp:extent`) | EMU | 1 inci = 914400 EMU; 1 cm = 360000 EMU |
| A4 | 11906 × 16838 twips | 21,0 × 29,7 cm |

Semua konversi hanya di `core/units.py`. Bandingkan dengan toleransi (lihat `RULES_SPEC.md`), jangan dengan kesamaan persis, karena pembulatan twips/EMU.

## 2. Format efektif

Nilai format yang berlaku untuk sebuah run/paragraf berasal dari beberapa lapis. Urutan prioritas dari tertinggi:

1. Properti langsung pada run/paragraf (`w:rPr`, `w:pPr`).
2. Style karakter (untuk run) dan style paragraf, mengikuti rantai `w:basedOn` sampai ujung.
3. Style tabel (bila paragraf di dalam tabel).
4. `w:docDefaults` di `styles.xml`.

Implikasi:
- Jangan membaca hanya properti langsung; hasilnya salah untuk dokumen yang memakai Style.
- Untuk memperbaiki, ubah **style** bila banyak paragraf berperan sama; hanya tambahkan properti langsung pada paragraf yang menyimpang.
- Toggle properties (bold, italic, caps) bisa berlaku bergantian lewat rantai style; hitung dengan benar.

## 3. Style: pakai styleId, bukan nama tampilan

Word berbahasa Indonesia menampilkan "Judul 1" untuk style bawaan, tetapi di XML `w:styleId` tetap `Heading1` dan `w:name` `heading 1`. Deteksi berdasarkan `styleId`/nama XML dan `w:outlineLvl`, bukan teks yang terlihat di UI. Style khusus buatan pengguna bisa berupa apa saja; gunakan `w:basedOn` dan outline level sebagai petunjuk.

## 4. Section, margin, dan penomoran halaman

- Pengaturan halaman ada di `w:sectPr`. **Section terakhir** ada di anak langsung `w:body`; section sebelumnya ada di `w:pPr/w:sectPr` pada paragraf terakhir section tersebut.
- Properti penting di `w:sectPr`: `w:pgSz` (ukuran/orientasi), `w:pgMar` (top, right, bottom, left, header, footer, gutter), `w:pgNumType` (`w:fmt`, `w:start`), `w:titlePg` (halaman pertama section berbeda), `w:type` (jenis section break).
- Format nomor: `lowerRoman`, `upperRoman`, `decimal`.
- Penomoran berbeda untuk bagian awal (romawi) dan isi (angka mulai 1) memerlukan **section break terpisah**.
- Header/footer direferensikan lewat `w:headerReference`/`w:footerReference` (tipe `default`, `first`, `even`). Section tanpa referensi **mewarisi** dari section sebelumnya (linked to previous). Saat mengubah footer satu section, pastikan tidak ikut mengubah section lain secara tak sengaja.
- Nomor halaman = field `PAGE` di footer/header. Nomor yang **diketik** (hanya angka/romawi tanpa field) adalah temuan NUM-006.
- `w:titlePg` bekerja **per section**. Aturan "halaman pertama setiap bab berbeda" (NUM-004) hanya bisa dipenuhi bila **setiap bab menjadi section sendiri** (section break jenis next page). Ini keputusan desain yang harus dibuat eksplisit di fixer.
- Perhatikan juga `w:mirrorMargins`, `w:gutter`, dan `w:evenAndOddHeaders` (settings.xml); jika aktif, aturan margin dan header bisa berbeda.

## 5. Field

Field kompleks tersusun dari beberapa run:

```xml
<w:r><w:fldChar w:fldCharType="begin"/></w:r>
<w:r><w:instrText xml:space="preserve"> PAGE </w:instrText></w:r>
<w:r><w:fldChar w:fldCharType="separate"/></w:r>
<w:r><w:t>1</w:t></w:r>              <!-- hasil tersimpan (cached) -->
<w:r><w:fldChar w:fldCharType="end"/></w:r>
```

Ada juga bentuk sederhana `w:fldSimple w:instr="PAGE"`. Parser harus mengenali keduanya.

Instruksi yang dipakai:

| Kebutuhan | Instruksi |
|---|---|
| Nomor halaman | `PAGE` |
| Jumlah halaman | `NUMPAGES` |
| Daftar isi (heading level 1–3, hyperlink) | `TOC \o "1-3" \h \z \u` |
| Daftar gambar/tabel | `TOC \h \z \c "Gambar"` dan `TOC \h \z \c "Tabel"` |
| Nomor caption | `SEQ Gambar \* ARABIC`, `SEQ Tabel \* ARABIC` |
| Reset nomor per bab | tambahkan `\s 1` pada SEQ (reset setelah Heading 1) |
| Referensi silang | `REF` |

Contoh helper (python-docx + lxml); uji sebelum dipakai:

```python
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def add_field(paragraph, instr: str, cached_text: str = "") -> None:
    def fld(kind: str):
        r = OxmlElement("w:r")
        c = OxmlElement("w:fldChar")
        c.set(qn("w:fldCharType"), kind)
        r.append(c)
        return r

    r_instr = OxmlElement("w:r")
    it = OxmlElement("w:instrText")
    it.set(qn("xml:space"), "preserve")
    it.text = f" {instr} "
    r_instr.append(it)

    r_result = OxmlElement("w:r")
    t = OxmlElement("w:t")
    t.text = cached_text
    r_result.append(t)

    for el in (fld("begin"), r_instr, fld("separate"), r_result, fld("end")):
        paragraph._p.append(el)
```

### Memperbarui field (daftar isi dan nomor halaman)

Word menghitung hasil field, bukan library Python. Opsi:

1. **Tandai untuk diperbarui saat dibuka** (MVP): tambahkan `<w:updateFields w:val="true"/>` di `settings.xml`. Word akan menampilkan dialog meminta izin memperbarui field saat dokumen dibuka. Alternatif: atribut `w:dirty="true"` pada `w:fldChar` bertipe `begin`. Beri tahu pengguna di UI cara menjawab dialog itu.
2. **Isi hasil awal (cached) dari render**: render PDF dengan LibreOffice, ambil nomor halaman tiap heading/caption, lalu tulis entri daftar isi sebagai hasil field awal. Pengguna tetap melihat daftar isi terisi sebelum Word memperbarui. Tambahkan setelah MVP dan beri catatan bahwa nomor halaman dari LibreOffice bisa meleset dari Word.
3. **Perbarui lewat LibreOffice (UNO) lalu simpan sebagai .docx**: hindari untuk file hasil akhir, karena simpan-ulang lewat LibreOffice dapat mengubah fidelitas dokumen (style, numbering, field). Gunakan hanya untuk pratinjau.

## 6. Penomoran heading dan daftar

- Penomoran otomatis ada di `numbering.xml` (`w:abstractNum` → `w:lvl`) dan dipakai paragraf lewat `w:numPr` (`w:ilvl`, `w:numId`), langsung atau lewat style.
- Penomoran heading bertingkat yang benar: satu `abstractNum` multilevel yang menautkan tiap level ke style heading (`w:pStyle` pada `w:lvl`, dan `w:numPr` pada style).
- Label "BAB I" dapat dibuat otomatis dengan `w:numFmt = upperRoman` dan `w:lvlText = "BAB %1"`. Itu cara paling benar, tetapi mengubah teks yang terlihat (label menjadi nomor otomatis), jadi masuk kategori `suggest` dan memerlukan persetujuan.
- Nomor yang diketik ("1.1", "BAB I") tampak seperti teks biasa. Deteksi dengan regex; konversi ke penomoran otomatis = HEAD-003 (lihat catatan integritas teks di `RULES_SPEC.md`).

**Peringatan caption per bab.** Nomor seperti "Gambar 2.1" dengan reset per bab bergantung pada nomor bab yang nyata. `SEQ ... \s 1` mereset berdasarkan Heading 1, tetapi menampilkan nomor bab di caption memerlukan nomor bab yang otomatis (mis. lewat `STYLEREF`) dan tidak langsung cocok bila label bab berupa teks "BAB I" yang diketik atau berformat romawi. Rencana: dukung penomoran **berkelanjutan** (`continuous`) lebih dulu; implementasikan `per_chapter` sesudahnya dengan tes khusus.

## 7. Tabel dan gambar

- Baris judul berulang antarhalaman: `w:trPr/w:tblHeader` pada baris pertama.
- Cegah baris terpotong: `w:trPr/w:cantSplit`.
- Lebar tabel: `w:tblW` (type `dxa`/`pct`/`auto`), indentasi `w:tblInd`, perataan `w:jc` di `w:tblPr`. Tabel yang melebihi lebar teks (lebar halaman dikurangi margin kiri/kanan) adalah temuan TBL-001.
- Gambar inline: `wp:inline` dengan `wp:extent cx cy` (EMU) dan, di dalam `a:graphic`, `a:ext` pada `pic:spPr`. Saat mengecilkan gambar, ubah **kedua** lokasi itu dan jaga rasio. Lebar maksimum = lebar halaman − margin kiri − margin kanan (konversi ke EMU).
- Gambar mengambang (`wp:anchor`) mengubah alur teks; pada MVP laporkan saja (FIG-003), jangan ubah otomatis.

## 8. Urutan elemen XML wajib

Skema OOXML mengharuskan **urutan anak elemen** tertentu. Word bisa menolak atau menampilkan peringatan "konten tidak terbaca" bila urutan salah. `python-docx` menjaga urutan untuk properti yang diekspos; untuk elemen yang Anda sisipkan sendiri, gunakan helper yang menyisipkan pada posisi skema yang benar.

Urutan umum (ringkas, cek spesifikasi untuk daftar lengkap):

- `w:pPr`: `pStyle`, `keepNext`, `keepLines`, `pageBreakBefore`, …, `numPr`, …, `pBdr`, `shd`, `tabs`, …, `spacing`, `ind`, …, `jc`, …, `outlineLvl`, …, `rPr`, `sectPr`.
- `w:sectPr`: `headerReference`/`footerReference`, `footnotePr`, `endnotePr`, `type`, `pgSz`, `pgMar`, …, `pgNumType`, `cols`, …, `titlePg`, …, `docGrid`.

Selalu tes dengan membuka hasil di Word dan LibreOffice.

## 9. Jebakan umum pada dokumen mahasiswa

| Jebakan | Penanganan |
|---|---|
| Satu paragraf terpecah menjadi banyak run | Gunakan teks gabungan paragraf untuk regex; jangan anggap satu run = satu kata. |
| Format manual di mana-mana | Hitung format efektif; klasifikasi peran lewat heuristik; jangan andalkan style saja. |
| Judul bab diketik "BAB I" lalu judul di baris/paragraf terpisah | Dukung pola dua paragraf (`chapter_label` + `chapter_title`) dan satu paragraf dengan line break. |
| Spasi/tab/Enter untuk layout | Deteksi (PARA-005/006/007), usulkan perbaikan, jangan hapus diam-diam. |
| Konten dalam `w:sdt` (content control), kotak teks (`w:txbxContent`), `mc:AlternateContent` | Traversal harus mengenali; jika tidak yakin, lewati dan laporkan. |
| Tracked changes (`w:ins`, `w:del`) dan komentar | Deteksi dan beri peringatan; jangan mengubah paragraf dengan revisi aktif tanpa persetujuan. |
| Catatan kaki/akhir | Ada di part terpisah (`footnotes.xml`, `endnotes.xml`); style `FootnoteText` punya aturan sendiri. |
| Daftar isi yang diketik manual | Deteksi pola "judul ... nomor" dengan tab/titik; usulkan ganti ke field (TOC-002). |
| Teks tersembunyi (`w:vanish`) | Jangan hitung sebagai konten visual; jangan ubah. |
| Mode kompatibilitas lama | `settings.xml` `w:compat` memengaruhi tata letak; catat di laporan. |
| Font tidak ada di server (mis. Times New Roman di Linux) | Pasang font metrik-kompatibel (Liberation Serif) untuk render; jangan mengganti font di dokumen hanya karena render. |
| Nama style berbahasa lokal | Pakai `styleId` dan outline level (bagian 3). |

## 10. Integritas isi

- Ekstrak "teks ternormalisasi" dokumen sebelum dan sesudah: gabungan teks paragraf dalam urutan dokumen, termasuk tabel, header/footer, dan catatan kaki, dengan spasi dinormalisasi.
- Untuk aturan `auto`, teks harus **identik persis**.
- Untuk aturan `suggest`, bandingkan setelah mengecualikan perubahan yang disetujui pengguna (lihat `RULES_SPEC.md` bagian 6).
- Implementasikan sebagai helper tes dan juga sebagai pemeriksaan runtime setelah perbaikan; jika gagal, batalkan perbaikan dan laporkan error.

## 11. LibreOffice headless

```bash
soffice --headless --norestore \
  -env:UserInstallation=file:///tmp/lo-profile-worker1 \
  --convert-to pdf --outdir /tmp/out /tmp/in/dokumen.docx
```

- Gunakan satu profil pengguna (`-env:UserInstallation`) per worker; satu profil tidak aman dipakai oleh beberapa proses paralel.
- Beri timeout keras; proses yang menggantung harus dimatikan.
- Field TOC yang belum diperbarui ditampilkan dengan hasil tersimpan; render tidak otomatis memperbarui kecuali dilakukan lewat UNO.
- Paginasi LibreOffice bisa berbeda tipis dari Word (metrik font, justifikasi, penanganan spasi, tabel). Tampilkan peringatan di pratinjau.

## 12. Sumber rujukan yang disarankan

- ECMA-376 / ISO 29500 (spesifikasi OOXML), terutama WordprocessingML.
- Dokumentasi `python-docx` (bagian styles, sections) dan sumber kodenya untuk pola penyisipan elemen berurutan.
- Hasil eksperimen langsung: buat dokumen kecil di Word, simpan, lalu bongkar ZIP-nya untuk melihat XML aktual.
