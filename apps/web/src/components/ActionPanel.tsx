"use client";

import React, { useState } from "react";
import { ChangeEntry } from "@/types";
import { CATEGORY_LABELS } from "@/lib/constants";

interface ActionPanelProps {
  docId: string | null;
  onFixAll: () => void;
  onFixCategory: (category: string) => void;
  onFixSelected: () => void;
  onDownload: (which: "fixed" | "original") => void;
  onDownloadReport: (format: "html" | "json") => void;
  onDeleteDocument: () => void;
  previewBeforeUrl: string | null;
  previewAfterUrl: string | null;
  isFixing: boolean;
  isFixed: boolean;
  autoFixCount: number;
  activeCategoryFilter: string;
  selectedFindingsCount: number;
  approvedSuggestCount: number;
  changes: ChangeEntry[];
}

export function ActionPanel({
  docId,
  onFixAll,
  onFixCategory,
  onFixSelected,
  onDownload,
  onDownloadReport,
  onDeleteDocument,
  previewBeforeUrl,
  previewAfterUrl,
  isFixing,
  isFixed,
  autoFixCount,
  activeCategoryFilter,
  selectedFindingsCount,
  approvedSuggestCount,
  changes,
}: ActionPanelProps) {
  const [showPreview, setShowPreview] = useState<boolean>(false);
  const [showChangelog, setShowChangelog] = useState<boolean>(false);

  const totalSelectedCount = selectedFindingsCount + approvedSuggestCount;
  const activeCatLabel =
    activeCategoryFilter !== "ALL"
      ? CATEGORY_LABELS[activeCategoryFilter]?.label || activeCategoryFilter
      : null;

  return (
    <div className="glass-panel" style={{ padding: "28px", marginBottom: "32px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "1.2rem", fontWeight: "700", color: "#ffffff" }}>
            4. Eksekusi Perapian &amp; Unduh Hasil
          </h2>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            Perapian diterapkan secara idempoten melalui Style Word asli tanpa mengubah isi teks
          </p>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          {isFixed && <span className="badge badge-emerald">Dokumen Siap Diunduh ({changes.length} Perubahan)</span>}
        </div>
      </div>

      {/* Fix Action Buttons */}
      <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "20px" }}>
        <button
          id="btn-fix-all"
          onClick={onFixAll}
          disabled={isFixing || (autoFixCount === 0 && approvedSuggestCount === 0)}
          className="btn btn-primary"
          style={{ minWidth: "220px" }}
        >
          {isFixing
            ? "⏳ Sedang Merapikan..."
            : `✨ Rapikan Semua Otomatis (${autoFixCount}${approvedSuggestCount > 0 ? ` + ${approvedSuggestCount} Disetujui` : ""})`}
        </button>

        {activeCatLabel && (
          <button
            id="btn-fix-category"
            onClick={() => onFixCategory(activeCategoryFilter)}
            disabled={isFixing}
            className="btn btn-secondary"
          >
            🔧 Rapikan Kategori: {activeCatLabel}
          </button>
        )}

        {totalSelectedCount > 0 && (
          <button
            id="btn-fix-selected"
            onClick={onFixSelected}
            disabled={isFixing}
            className="btn btn-secondary"
            style={{ borderColor: "var(--accent-cyan)", color: "var(--accent-cyan)" }}
          >
            🎯 Rapikan Temuan Terpilih ({totalSelectedCount})
          </button>
        )}
      </div>

      {/* Download & Preview Bar */}
      <div style={{
        display: "flex",
        gap: "12px",
        flexWrap: "wrap",
        marginBottom: "24px",
        paddingTop: "16px",
        borderTop: "1px solid var(--border-subtle)",
      }}>
        {isFixed && (
          <button
            id="btn-download-docx"
            onClick={() => onDownload("fixed")}
            className="btn btn-secondary"
            style={{
              borderColor: "var(--accent-emerald)",
              color: "#34d399",
              background: "rgba(16, 185, 129, 0.12)",
            }}
          >
            📥 Unduh Skripsi Rapi (.docx)
          </button>
        )}

        <button
          id="btn-download-original"
          onClick={() => onDownload("original")}
          className="btn btn-secondary"
        >
          📄 Unduh File Asli (.docx)
        </button>

        <button
          id="btn-download-report-html"
          onClick={() => onDownloadReport("html")}
          className="btn btn-secondary"
        >
          📊 Laporan Kepatuhan (HTML)
        </button>

        <button
          id="btn-download-report-json"
          onClick={() => onDownloadReport("json")}
          className="btn btn-secondary"
        >
          🧾 Laporan (JSON)
        </button>

        {isFixed && (
          <>
            <button
              id="btn-toggle-preview"
              onClick={() => setShowPreview(!showPreview)}
              className="btn btn-secondary"
            >
              {showPreview ? "🙈 Tutup Pratinjau PDF" : "👁️ Pratinjau Sebelum / Sesudah (PDF)"}
            </button>
            <button
              id="btn-toggle-changelog"
              onClick={() => setShowChangelog(!showChangelog)}
              className="btn btn-secondary"
            >
              {showChangelog ? "📋 Tutup Riwayat Perubahan" : `📋 Riwayat Perubahan (${changes.length})`}
            </button>
          </>
        )}
      </div>

      {/* Before / After Preview Section */}
      {showPreview && isFixed && previewBeforeUrl && previewAfterUrl && (
        <div style={{
          marginBottom: "24px",
          padding: "16px",
          borderRadius: "var(--radius-md)",
          background: "rgba(15, 23, 42, 0.75)",
          border: "1px solid var(--border-subtle)",
        }}>
          <div style={{
            padding: "10px 14px",
            marginBottom: "14px",
            borderRadius: "var(--radius-sm)",
            background: "rgba(245, 158, 11, 0.12)",
            border: "1px solid rgba(245, 158, 11, 0.35)",
            color: "#fbbf24",
            fontSize: "0.83rem",
          }}>
            ⚠️ <strong>Catatan Pratinjau:</strong> Pratinjau dirender dengan LibreOffice; jumlah halaman dan posisi pemutus halaman dapat sedikit berbeda dari Microsoft Word.
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "16px" }}>
            <div>
              <h4 style={{ fontSize: "0.9rem", fontWeight: "600", color: "var(--text-secondary)", marginBottom: "8px" }}>
                Sebelum Perapian (Asli)
              </h4>
              <iframe
                title="Pratinjau Sebelum"
                src={previewBeforeUrl}
                style={{ width: "100%", height: "420px", borderRadius: "var(--radius-sm)", border: "1px solid var(--border-subtle)", background: "#ffffff" }}
              />
            </div>
            <div>
              <h4 style={{ fontSize: "0.9rem", fontWeight: "600", color: "#34d399", marginBottom: "8px" }}>
                Sesudah Perapian (Rapi)
              </h4>
              <iframe
                title="Pratinjau Sesudah"
                src={previewAfterUrl}
                style={{ width: "100%", height: "420px", borderRadius: "var(--radius-sm)", border: "1px solid var(--accent-emerald)", background: "#ffffff" }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Changelog Viewer */}
      {showChangelog && changes.length > 0 && (
        <div style={{
          marginBottom: "24px",
          padding: "16px",
          borderRadius: "var(--radius-md)",
          background: "rgba(15, 23, 42, 0.75)",
          border: "1px solid var(--border-subtle)",
          maxHeight: "300px",
          overflowY: "auto",
        }}>
          <h4 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#ffffff", marginBottom: "12px" }}>
            Log Perubahan Format ({changes.length} item)
          </h4>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.8rem", fontFamily: "var(--font-mono)" }}>
            {changes.map((ch, idx) => (
              <div
                key={`${ch.rule_id}-${ch.block_index}-${idx}`}
                style={{
                  padding: "8px 12px",
                  borderRadius: "var(--radius-sm)",
                  background: "rgba(0,0,0,0.3)",
                  display: "flex",
                  justifyContent: "space-between",
                  gap: "12px",
                  flexWrap: "wrap",
                }}
              >
                <div>
                  <span style={{ color: "var(--accent-cyan)", fontWeight: "700" }}>[{ch.rule_id}]</span>{" "}
                  <span style={{ color: "var(--text-muted)" }}>Blok #{ch.block_index} ({ch.method})</span>{" "}
                  <span style={{ color: "#ffffff" }}>{ch.field}:</span>
                </div>
                <div>
                  <span style={{ color: "#fb7185" }}>{ch.before}</span>{" "}
                  <span style={{ color: "var(--text-muted)" }}>&rarr;</span>{" "}
                  <span style={{ color: "#34d399" }}>{ch.after}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Word Field Update Guidance Notice */}
      <div style={{
        background: "rgba(99, 102, 241, 0.08)",
        border: "1px solid rgba(99, 102, 241, 0.25)",
        borderRadius: "var(--radius-md)",
        padding: "16px 20px",
        marginBottom: "20px",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "8px" }}>
          <span style={{ fontSize: "1.1rem" }}>💡</span>
          <h4 style={{ fontSize: "0.92rem", fontWeight: "700", color: "var(--accent-cyan)" }}>
            Panduan Penting Saat Membuka File di Microsoft Word
          </h4>
        </div>
        <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", lineHeight: "1.6" }}>
          Saat pertama kali membuka file hasil perapian di Microsoft Word, akan muncul dialog konfirmasi:
          <strong style={{ color: "#ffffff" }}> &quot;This document contains fields that may refer to other files. Do you want to update the fields in this document?&quot;</strong>.
          Pilih <strong style={{ color: "var(--accent-emerald)" }}>&quot;Yes&quot;</strong> (atau tekan <code style={{ color: "#ffffff" }}>Ctrl+A</code> lalu <code style={{ color: "#ffffff" }}>F9</code>) agar Microsoft Word otomatis menghitung nomor halaman dan menyusun Daftar Isi secara sempurna.
        </p>
      </div>

      {/* Privacy Retention & Immediate Delete */}
      {docId && (
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
          padding: "14px 18px",
          borderRadius: "var(--radius-md)",
          background: "rgba(244, 63, 94, 0.07)",
          border: "1px solid rgba(244, 63, 94, 0.25)",
        }}>
          <div style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>
            🔒 <strong style={{ color: "#ffffff" }}>Jaminan Privasi:</strong> Dokumen hanya disimpan sementara selama maksimal <strong>1 jam (TTL)</strong> dan tidak pernah dikirim ke pihak ketiga. Anda dapat menghapus berkas dari server sekarang juga.
          </div>
          <button
            id="btn-delete-document"
            onClick={onDeleteDocument}
            className="btn btn-secondary"
            style={{
              padding: "6px 14px",
              fontSize: "0.8rem",
              borderColor: "rgba(244, 63, 94, 0.5)",
              color: "#fb7185",
            }}
          >
            🗑️ Hapus Dokumen Sekarang
          </button>
        </div>
      )}
    </div>
  );
}
