from __future__ import annotations

from dataclasses import dataclass

from app.core.rules.models import FixMode, RuleProfile, Severity


@dataclass(frozen=True)
class RuleDefinition:
    id: str
    category: str
    description: str
    default_severity: Severity
    default_fix_mode: FixMode


RULE_CATALOG: dict[str, RuleDefinition] = {
    # PAGE
    "PAGE-001": RuleDefinition(
        "PAGE-001", "PAGE", "Ukuran kertas sesuai profil", Severity.ERROR, FixMode.AUTO
    ),
    "PAGE-002": RuleDefinition(
        "PAGE-002",
        "PAGE",
        "Margin atas/bawah/kiri/kanan sesuai profil",
        Severity.ERROR,
        FixMode.AUTO,
    ),
    "PAGE-003": RuleDefinition(
        "PAGE-003", "PAGE", "Jarak header/footer sesuai profil", Severity.WARNING, FixMode.AUTO
    ),
    "PAGE-004": RuleDefinition(
        "PAGE-004", "PAGE", "Orientasi halaman sesuai profil", Severity.WARNING, FixMode.SUGGEST
    ),
    # FONT
    "FONT-001": RuleDefinition(
        "FONT-001", "FONT", "Keluarga font sesuai profil", Severity.ERROR, FixMode.AUTO
    ),
    "FONT-002": RuleDefinition(
        "FONT-002", "FONT", "Ukuran font sesuai peran", Severity.ERROR, FixMode.AUTO
    ),
    "FONT-003": RuleDefinition(
        "FONT-003", "FONT", "Warna teks sesuai profil", Severity.WARNING, FixMode.AUTO
    ),
    "FONT-004": RuleDefinition(
        "FONT-004",
        "FONT",
        "Tidak ada font nyasar di tengah paragraf",
        Severity.WARNING,
        FixMode.AUTO,
    ),
    # PARA
    "PARA-001": RuleDefinition(
        "PARA-001", "PARA", "Spasi baris sesuai peran", Severity.ERROR, FixMode.AUTO
    ),
    "PARA-002": RuleDefinition(
        "PARA-002", "PARA", "Spasi sebelum/sesudah paragraf", Severity.WARNING, FixMode.AUTO
    ),
    "PARA-003": RuleDefinition(
        "PARA-003",
        "PARA",
        "Indentasi baris pertama/kiri/kanan/hanging",
        Severity.WARNING,
        FixMode.AUTO,
    ),
    "PARA-004": RuleDefinition(
        "PARA-004", "PARA", "Perataan teks sesuai peran", Severity.ERROR, FixMode.AUTO
    ),
    "PARA-005": RuleDefinition(
        "PARA-005",
        "PARA",
        "Paragraf kosong berulang dipakai sebagai jarak",
        Severity.WARNING,
        FixMode.SUGGEST,
    ),
    "PARA-006": RuleDefinition(
        "PARA-006",
        "PARA",
        "Spasi atau tab berulang dipakai sebagai indentasi",
        Severity.WARNING,
        FixMode.SUGGEST,
    ),
    "PARA-007": RuleDefinition(
        "PARA-007",
        "PARA",
        "Line break manual dipakai untuk layout",
        Severity.WARNING,
        FixMode.SUGGEST,
    ),
    "PARA-008": RuleDefinition(
        "PARA-008", "PARA", "Widow/orphan control aktif", Severity.INFO, FixMode.AUTO
    ),
    # HEAD
    "HEAD-001": RuleDefinition(
        "HEAD-001", "HEAD", "Format judul bab (label dan judul)", Severity.ERROR, FixMode.AUTO
    ),
    "HEAD-002": RuleDefinition(
        "HEAD-002", "HEAD", "Format heading level 2 dan seterusnya", Severity.ERROR, FixMode.AUTO
    ),
    "HEAD-003": RuleDefinition(
        "HEAD-003",
        "HEAD",
        "Penomoran heading memakai numbering otomatis",
        Severity.WARNING,
        FixMode.SUGGEST,
    ),
    "HEAD-004": RuleDefinition(
        "HEAD-004",
        "HEAD",
        "Heading tidak terpisah dari paragraf sesudahnya (keep with next)",
        Severity.WARNING,
        FixMode.AUTO,
    ),
    "HEAD-005": RuleDefinition(
        "HEAD-005", "HEAD", "Bab dimulai di halaman baru", Severity.ERROR, FixMode.AUTO
    ),
    "HEAD-006": RuleDefinition(
        "HEAD-006",
        "HEAD",
        "Hierarki heading tidak melompat level",
        Severity.WARNING,
        FixMode.MANUAL,
    ),
    # NUM
    "NUM-001": RuleDefinition(
        "NUM-001", "NUM", "Bagian awal memakai angka romawi", Severity.ERROR, FixMode.AUTO
    ),
    "NUM-002": RuleDefinition(
        "NUM-002",
        "NUM",
        "Bagian isi memakai angka arab mulai sesuai profil",
        Severity.ERROR,
        FixMode.AUTO,
    ),
    "NUM-003": RuleDefinition(
        "NUM-003", "NUM", "Posisi nomor halaman sesuai profil", Severity.WARNING, FixMode.AUTO
    ),
    "NUM-004": RuleDefinition(
        "NUM-004",
        "NUM",
        "Halaman pertama bab memakai aturan khusus sesuai profil",
        Severity.WARNING,
        FixMode.AUTO,
    ),
    "NUM-005": RuleDefinition(
        "NUM-005", "NUM", "Sampul tidak bernomor", Severity.ERROR, FixMode.AUTO
    ),
    "NUM-006": RuleDefinition(
        "NUM-006",
        "NUM",
        "Nomor halaman memakai field PAGE, bukan diketik manual",
        Severity.WARNING,
        FixMode.SUGGEST,
    ),
    # TOC, LOF, LOT
    "TOC-001": RuleDefinition("TOC-001", "TOC", "Daftar isi ada", Severity.ERROR, FixMode.AUTO),
    "TOC-002": RuleDefinition(
        "TOC-002",
        "TOC",
        "Daftar isi berupa field, bukan ketikan",
        Severity.WARNING,
        FixMode.SUGGEST,
    ),
    "TOC-003": RuleDefinition(
        "TOC-003", "TOC", "Kedalaman level daftar isi sesuai profil", Severity.WARNING, FixMode.AUTO
    ),
    "TOC-004": RuleDefinition(
        "TOC-004",
        "TOC",
        "Daftar isi sinkron dengan heading (updateFields)",
        Severity.WARNING,
        FixMode.AUTO,
    ),
    "TOC-005": RuleDefinition(
        "TOC-005",
        "TOC",
        "Format entri daftar isi: titik pemandu dan nomor rata kanan",
        Severity.WARNING,
        FixMode.AUTO,
    ),
    "LOF-001": RuleDefinition(
        "LOF-001",
        "LOF",
        "Daftar gambar ada bila ada gambar ber-caption",
        Severity.WARNING,
        FixMode.AUTO,
    ),
    "LOT-001": RuleDefinition(
        "LOT-001",
        "LOT",
        "Daftar tabel ada bila ada tabel ber-caption",
        Severity.WARNING,
        FixMode.AUTO,
    ),
    # CAP
    "CAP-001": RuleDefinition(
        "CAP-001", "CAP", "Setiap gambar/tabel punya caption", Severity.WARNING, FixMode.MANUAL
    ),
    "CAP-002": RuleDefinition(
        "CAP-002", "CAP", "Posisi caption sesuai profil", Severity.ERROR, FixMode.AUTO
    ),
    "CAP-003": RuleDefinition(
        "CAP-003", "CAP", "Style dan format caption sesuai profil", Severity.WARNING, FixMode.AUTO
    ),
    "CAP-004": RuleDefinition(
        "CAP-004", "CAP", "Penomoran caption memakai field SEQ", Severity.WARNING, FixMode.SUGGEST
    ),
    "CAP-005": RuleDefinition(
        "CAP-005",
        "CAP",
        "Nomor caption berurutan tanpa lompatan atau duplikat",
        Severity.ERROR,
        FixMode.AUTO,
    ),
    # FIG
    "FIG-001": RuleDefinition(
        "FIG-001", "FIG", "Gambar rata tengah (atau sesuai profil)", Severity.WARNING, FixMode.AUTO
    ),
    "FIG-002": RuleDefinition(
        "FIG-002", "FIG", "Gambar tidak melewati margin", Severity.ERROR, FixMode.AUTO
    ),
    "FIG-003": RuleDefinition(
        "FIG-003",
        "FIG",
        "Gambar mengambang (floating) mengganggu alur teks",
        Severity.WARNING,
        FixMode.MANUAL,
    ),
    # TBL
    "TBL-001": RuleDefinition(
        "TBL-001", "TBL", "Tabel tidak melewati margin", Severity.ERROR, FixMode.AUTO
    ),
    "TBL-002": RuleDefinition(
        "TBL-002",
        "TBL",
        "Baris judul tabel berulang di halaman berikutnya",
        Severity.WARNING,
        FixMode.AUTO,
    ),
    "TBL-003": RuleDefinition(
        "TBL-003", "TBL", "Baris tabel tidak terpotong antarhalaman", Severity.WARNING, FixMode.AUTO
    ),
    "TBL-004": RuleDefinition(
        "TBL-004",
        "TBL",
        "Font/spasi teks dalam tabel sesuai peran table_text",
        Severity.WARNING,
        FixMode.AUTO,
    ),
    "TBL-005": RuleDefinition(
        "TBL-005", "TBL", "Perataan tabel sesuai profil", Severity.WARNING, FixMode.AUTO
    ),
    # BIB
    "BIB-001": RuleDefinition(
        "BIB-001",
        "BIB",
        "Entri daftar pustaka terurut sesuai profil",
        Severity.WARNING,
        FixMode.SUGGEST,
    ),
    "BIB-002": RuleDefinition(
        "BIB-002",
        "BIB",
        "Hanging indent daftar pustaka sesuai profil",
        Severity.WARNING,
        FixMode.AUTO,
    ),
    "BIB-003": RuleDefinition(
        "BIB-003",
        "BIB",
        "Spasi dalam dan antar-entri daftar pustaka sesuai profil",
        Severity.WARNING,
        FixMode.AUTO,
    ),
    "BIB-004": RuleDefinition(
        "BIB-004", "BIB", "Sitasi di teks cocok dengan entri pustaka", Severity.INFO, FixMode.MANUAL
    ),
    # STR
    "STR-001": RuleDefinition(
        "STR-001", "STR", "Bagian wajib ada", Severity.WARNING, FixMode.MANUAL
    ),
    "STR-002": RuleDefinition(
        "STR-002", "STR", "Bagian tampil dalam urutan yang benar", Severity.WARNING, FixMode.MANUAL
    ),
    "STR-003": RuleDefinition(
        "STR-003", "STR", "Bab I sampai V lengkap", Severity.WARNING, FixMode.MANUAL
    ),
    "STR-004": RuleDefinition(
        "STR-004", "STR", "Bagian wajib dimulai di halaman baru", Severity.WARNING, FixMode.AUTO
    ),
}


def resolve_rule_config(rule_id: str, profile: RuleProfile) -> tuple[bool, Severity, FixMode, str]:
    """Returns `(enabled, severity, fix_mode, category)` for a rule under the given profile."""
    base = RULE_CATALOG.get(rule_id)
    if base is None:
        return True, Severity.WARNING, FixMode.MANUAL, rule_id.split("-")[0]

    enabled = True
    severity = base.default_severity
    fix_mode = base.default_fix_mode

    for override in profile.rules:
        if override.id == rule_id:
            enabled = override.enabled
            if override.severity is not None:
                severity = override.severity
            if override.fix_mode is not None:
                fix_mode = override.fix_mode
            break

    return enabled, severity, fix_mode, base.category
