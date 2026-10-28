"use client";

import React, { useState } from "react";
import { Finding } from "@/types";
import { CATEGORY_LABELS } from "@/lib/constants";

interface FindingsReportProps {
  findings: Finding[];
  selectedFindingIds: string[];
  approvedSuggestIds: string[];
  onToggleFinding: (findingId: string, fixMode: string) => void;
  onSelectCategoryForFix: (category: string) => void;
  activeCategoryFilter: string;
}

export function FindingsReport({
  findings,
  selectedFindingIds,
  approvedSuggestIds,
  onToggleFinding,
  onSelectCategoryForFix,
  activeCategoryFilter,
}: FindingsReportProps) {
  const [selectedSeverity, setSelectedSeverity] = useState<string>("ALL");
  const [selectedFixMode, setSelectedFixMode] = useState<string>("ALL");

  const categories = Array.from(new Set(findings.map((f) => f.category)));

  const filteredFindings = findings.filter((f) => {
    const matchesCategory = activeCategoryFilter === "ALL" || f.category === activeCategoryFilter;
    const matchesSeverity = selectedSeverity === "ALL" || f.severity === selectedSeverity;
    const matchesFixMode = selectedFixMode === "ALL" || f.fix_mode === selectedFixMode;
    return matchesCategory && matchesSeverity && matchesFixMode;
  });

  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "error":
        return <span className="badge badge-rose">Pelanggaran</span>;
      case "warning":
        return <span className="badge badge-amber">Peringatan</span>;
      default:
        return <span className="badge badge-primary">Info</span>;
    }
  };

  const getFixModeBadge = (fixMode: string) => {
    switch (fixMode) {
      case "auto":
        return <span className="badge badge-emerald">Bisa Diperbaiki Otomatis</span>;
      case "suggest":
        return <span className="badge badge-amber">Perlu Persetujuan (Suggest)</span>;
      default:
        return <span className="badge badge-primary">Koreksi Manual</span>;
    }
  };

  return (
    <div className="glass-panel" style={{ padding: "28px", marginBottom: "24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "1.2rem", fontWeight: "700", color: "#ffffff" }}>
            3. Laporan Analisis Kepatuhan Format
          </h2>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            Ditemukan total {findings.length} penyimpangan format dari pedoman kampus
          </p>
        </div>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <span className="badge badge-rose">
            {findings.filter((f) => f.severity === "error").length} Error
          </span>
          <span className="badge badge-amber">
            {findings.filter((f) => f.severity === "warning").length} Peringatan
          </span>
          <span className="badge badge-emerald">
            {findings.filter((f) => f.fix_mode === "auto").length} Auto-Fix
          </span>
        </div>
      </div>

      {/* Category Filter Bar */}
      <div style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "8px",
        marginBottom: "14px",
      }}>
        <button
          onClick={() => onSelectCategoryForFix("ALL")}
          className={`btn ${activeCategoryFilter === "ALL" ? "btn-primary" : "btn-secondary"}`}
          style={{ padding: "6px 14px", fontSize: "0.82rem" }}
        >
          Semua Kategori ({findings.length})
        </button>
        {categories.map((cat) => {
          const catInfo = CATEGORY_LABELS[cat] || { label: cat, icon: "📌" };
          const count = findings.filter((f) => f.category === cat).length;
          return (
            <button
              key={cat}
              onClick={() => onSelectCategoryForFix(cat)}
              className={`btn ${activeCategoryFilter === cat ? "btn-primary" : "btn-secondary"}`}
              style={{ padding: "6px 14px", fontSize: "0.82rem" }}
            >
              {catInfo.icon} {catInfo.label} ({count})
            </button>
          );
        })}
      </div>

      {/* Severity & FixMode Filter Bar */}
      <div style={{
        display: "flex",
        flexWrap: "wrap",
        gap: "16px",
        marginBottom: "20px",
        paddingBottom: "16px",
        borderBottom: "1px solid var(--border-subtle)",
        fontSize: "0.82rem",
        alignItems: "center",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ color: "var(--text-muted)" }}>Tingkat:</span>
          {["ALL", "error", "warning", "info"].map((sev) => (
            <button
              key={sev}
              onClick={() => setSelectedSeverity(sev)}
              className={`btn ${selectedSeverity === sev ? "btn-primary" : "btn-secondary"}`}
              style={{ padding: "4px 10px", fontSize: "0.76rem" }}
            >
              {sev === "ALL" ? "Semua" : sev.toUpperCase()}
            </button>
          ))}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ color: "var(--text-muted)" }}>Mode Perbaikan:</span>
          {[
            { id: "ALL", label: "Semua" },
            { id: "auto", label: "Otomatis (Auto)" },
            { id: "suggest", label: "Konfirmasi (Suggest)" },
            { id: "manual", label: "Manual" },
          ].map((fm) => (
            <button
              key={fm.id}
              onClick={() => setSelectedFixMode(fm.id)}
              className={`btn ${selectedFixMode === fm.id ? "btn-primary" : "btn-secondary"}`}
              style={{ padding: "4px 10px", fontSize: "0.76rem" }}
            >
              {fm.label}
            </button>
          ))}
        </div>
      </div>

      {/* Findings List */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {filteredFindings.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-muted)" }}>
            Tidak ada temuan pada filter ini.
          </div>
        ) : (
          filteredFindings.map((finding) => {
            const catInfo = CATEGORY_LABELS[finding.category] || { label: finding.category, icon: "📌" };
            const isSelectable = finding.fix_mode === "auto" || finding.fix_mode === "suggest";
            const isChecked =
              selectedFindingIds.includes(finding.id) || approvedSuggestIds.includes(finding.id);

            return (
              <div
                key={finding.id}
                style={{
                  background: "rgba(15, 23, 42, 0.6)",
                  border: `1px solid ${isChecked ? "var(--accent-cyan)" : "var(--border-subtle)"}`,
                  borderRadius: "var(--radius-md)",
                  padding: "18px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                    {isSelectable && (
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => onToggleFinding(finding.id, finding.fix_mode)}
                        title={
                          finding.fix_mode === "suggest"
                            ? "Setujui saran perbaikan ini"
                            : "Pilih temuan ini untuk dirapikan"
                        }
                        style={{ width: "16px", height: "16px", cursor: "pointer" }}
                      />
                    )}
                    <span style={{ fontSize: "1.1rem" }}>{catInfo.icon}</span>
                    <span style={{ fontWeight: "700", color: "#ffffff", fontSize: "0.95rem" }}>
                      [{finding.rule_id}] {catInfo.label}
                    </span>
                    <span style={{ color: "var(--text-muted)", fontSize: "0.8rem", fontFamily: "var(--font-mono)" }}>
                      Section {finding.location.section_index + 1} &bull; Blok #{finding.location.block_index}
                      {finding.location.approx_page ? ` • Hal. ~${finding.location.approx_page}` : ""}
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: "6px" }}>
                    {getSeverityBadge(finding.severity)}
                    {getFixModeBadge(finding.fix_mode)}
                  </div>
                </div>

                <p style={{ color: "var(--text-main)", fontSize: "0.9rem" }}>
                  {finding.message}
                </p>

                {finding.location.excerpt && (
                  <p style={{
                    fontSize: "0.8rem",
                    color: "var(--text-secondary)",
                    fontStyle: "italic",
                    background: "rgba(255,255,255,0.03)",
                    padding: "6px 10px",
                    borderRadius: "var(--radius-sm)",
                    borderLeft: "3px solid var(--accent-indigo)",
                  }}>
                    Kutipan: &ldquo;{finding.location.excerpt}&rdquo;
                  </p>
                )}

                <div style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "12px",
                  marginTop: "4px",
                  background: "rgba(0, 0, 0, 0.25)",
                  padding: "10px 14px",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "0.82rem",
                  fontFamily: "var(--font-mono)",
                }}>
                  <div>
                    <span style={{ color: "#fb7185", fontWeight: "600" }}>Nilai Dokumen Saat Ini:</span>
                    <p style={{ color: "var(--text-secondary)", marginTop: "2px" }}>{finding.actual}</p>
                  </div>
                  <div>
                    <span style={{ color: "#34d399", fontWeight: "600" }}>Nilai Sesuai Pedoman:</span>
                    <p style={{ color: "var(--text-secondary)", marginTop: "2px" }}>{finding.expected}</p>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
