export const CATEGORY_LABELS: Record<string, { label: string; icon: string; desc: string }> = {
  PAGE: { label: "Halaman & Margin", icon: "📄", desc: "Ukuran kertas A4, margin 4-4-3-3 cm, orientasi" },
  FONT: { label: "Font & Tipografi", icon: "🔤", desc: "Jenis font, ukuran, warna teks standar" },
  PARA: { label: "Spasi & Paragraf", icon: "📑", desc: "Spasi 1.5, first-line indent, perataan justify" },
  HEAD: { label: "Bab & Sub-bab", icon: "🏷️", desc: "Heading 1-3, bold, all-caps, penomoran bertingkat" },
  NUM: { label: "Penomoran Halaman", icon: "🔢", desc: "Romawi untuk bagian awal, angka mulai Bab I" },
  TOC: { label: "Daftar Isi", icon: "📚", desc: "Field TOC otomatis Word, level heading 1-3" },
  LOF: { label: "Daftar Gambar", icon: "🖼️", desc: "Field daftar gambar otomatis" },
  LOT: { label: "Daftar Tabel", icon: "📊", desc: "Field daftar tabel otomatis" },
  CAP: { label: "Caption Gambar/Tabel", icon: "📌", desc: "Format dan posisi caption dengan field SEQ" },
  FIG: { label: "Gambar Ilustrasi", icon: "📐", desc: "Posisi center dan ukuran gambar dalam batas margin" },
  TBL: { label: "Tabel Data", icon: "📋", desc: "Format garis tabel, teks tabel, ukuran font tabel" },
  BIB: { label: "Daftar Pustaka", icon: "📖", desc: "Hanging indent 1.25 cm, urutan abjad" },
  STR: { label: "Struktur Dokumen", icon: "🗂️", desc: "Kelengkapan urutan Kata Pengantar, Abstrak, Bab I-V" },
  DOC: { label: "Peringatan Dokumen", icon: "⚠️", desc: "Revisi Tracked Changes atau komentar aktif" },
};

export const ROLE_OPTIONS: { value: string; label: string }[] = [
  { value: "cover", label: "Halaman Sampul (cover)" },
  { value: "front_title", label: "Judul Bagian Awal / Lampiran (front_title)" },
  { value: "chapter_label", label: "Label Bab (BAB I, BAB II)" },
  { value: "chapter_title", label: "Judul Bab (PENDAHULUAN, dst.)" },
  { value: "heading_2", label: "Sub-bab Level 2 (1.1)" },
  { value: "heading_3", label: "Sub-bab Level 3 (1.1.1)" },
  { value: "heading_4", label: "Sub-bab Level 4 (1.1.1.1)" },
  { value: "body", label: "Paragraf Isi (body)" },
  { value: "list_item", label: "Butir Daftar (list_item)" },
  { value: "block_quote", label: "Kutipan Panjang (block_quote)" },
  { value: "caption_figure", label: "Caption Gambar (caption_figure)" },
  { value: "caption_table", label: "Caption Tabel (caption_table)" },
  { value: "bibliography_entry", label: "Entri Daftar Pustaka (bibliography_entry)" },
  { value: "toc_entry", label: "Entri Daftar Isi (toc_entry)" },
  { value: "footnote_text", label: "Catatan Kaki (footnote_text)" },
  { value: "other", label: "Lainnya (other)" },
];

export const SAMPLE_PROFILES = [
  {
    profile_id: "contoh-s1-skripsi",
    name: "CONTOH: Skripsi S1 (Pedoman Umum Kampus Indonesia)",
    version: "0.1.0",
    language: "id",
    source: {
      document: "Pedoman Penulisan Skripsi Standard",
      edition: "2024",
      pages: "1-50",
      notes: "A4, Margin Kiri 4cm, Atas 4cm, Kanan 3cm, Bawah 3cm, Times New Roman 12pt, Spasi 1.5",
    },
  },
];
