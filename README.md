# Skripsi Formatter

Tool berbasis web untuk memeriksa dan merapikan format skripsi, tugas akhir, atau laporan mahasiswa dalam file Microsoft Word (`.docx`) sesuai pedoman penulisan kampus/fakultas.

## 🎯 Prinsip Utama
1. **Integritas Teks Terjamin**: Tidak ada isi kata/kalimat yang diubah sedikitpun. Hanya properti format, style, dan layout yang diperbaiki.
2. **File Asli Suci**: Perbaikan selalu dilakukan pada salinan dokumen, file asli tidak tersentuh.
3. **Aturan Sebagai Data**: Aturan spesifik kampus tersimpan dalam profil JSON di `profiles/`, bukan hardcode dalam logika program.
4. **Fitur Word Asli**: Memanfaatkan Styles, Sections, Fields (`TOC`, `PAGE`, `SEQ`), bukan enter berulang atau spasi manual.

## 📂 Struktur Monorepo

```
skripsi-formatter/
├── apps/
│   ├── api/             # Backend FastAPI (Python) untuk parsing docx, evaluator aturan, dan fixer
│   └── web/             # Frontend Next.js (React, TypeScript) dengan Vanilla CSS & modern design
├── profiles/            # Profil aturan kampus (JSON) dan JSON Schema
│   ├── schema/          # JSON Schema validasi profil (profile.schema.json)
│   └── contoh-s1-skripsi.json
├── tests/
│   └── fixtures/        # Korpus dokumen uji sintetis
└── docs/                # Dokumentasi arsitektur, PRD, dan panduan teknis
```

## 🛠️ Tech Stack
- **Backend**: Python 3.9+, FastAPI, `python-docx`, `lxml`, `pydantic` v2, `uvicorn`
- **Frontend**: Next.js 15+ (App Router), TypeScript, Vanilla Modern CSS Design System
- **Render (Opsional/Pratinjau)**: LibreOffice headless untuk render PDF

## 🚀 Panduan Setup (Tanpa Eksekusi Server)

### 1. Backend (apps/api)
```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Frontend (apps/web)
```bash
cd apps/web
npm install
```

## 📖 Dokumentasi Lengkap
- [PRD.md](PRD.md) — Product Requirements Document
- [AGENTS.md](AGENTS.md) — Panduan pengembang & AI coding agent
- [ARCHITECTURE.md](ARCHITECTURE.md) — Arsitektur teknis & pipeline data
- [RULES_SPEC.md](RULES_SPEC.md) — Spesifikasi profil aturan & katalog aturan
- [DOCX_NOTES.md](DOCX_NOTES.md) — Catatan teknis OOXML Word
- [TASKS.md](TASKS.md) — Rencana kerja per fase
- [TESTING.md](TESTING.md) — Strategi pengujian & integritas dokumen
