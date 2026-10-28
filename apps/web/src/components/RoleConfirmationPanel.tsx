"use client";

import React, { useState } from "react";
import { RoleItem } from "@/types";
import { ROLE_OPTIONS } from "@/lib/constants";

interface RoleConfirmationPanelProps {
  roles: RoleItem[];
  onSaveRoles: (overrides: { block_index: number; role: string }[]) => Promise<void>;
  isSaving: boolean;
}

export function RoleConfirmationPanel({
  roles,
  onSaveRoles,
  isSaving,
}: RoleConfirmationPanelProps) {
  const [showAll, setShowAll] = useState<boolean>(false);
  const [editedRoles, setEditedRoles] = useState<Record<number, string>>({});

  const lowConfidenceRoles = roles.filter((r) => r.needs_confirmation || r.confidence < 0.7);
  const displayedRoles = showAll ? roles : lowConfidenceRoles;

  if (roles.length === 0) return null;

  const handleRoleChange = (blockIndex: number, newRole: string) => {
    setEditedRoles((prev) => ({
      ...prev,
      [blockIndex]: newRole,
    }));
  };

  const handleApplyOverrides = async () => {
    const overrides = Object.entries(editedRoles).map(([blockIdx, role]) => ({
      block_index: Number(blockIdx),
      role,
    }));
    // Also include low-confidence items that user confirmed as-is
    for (const item of lowConfidenceRoles) {
      if (!(item.block_index in editedRoles)) {
        overrides.push({
          block_index: item.block_index,
          role: item.role,
        });
      }
    }
    if (overrides.length > 0) {
      await onSaveRoles(overrides);
      setEditedRoles({});
    }
  };

  if (lowConfidenceRoles.length === 0 && !showAll) {
    return (
      <div className="glass-panel" style={{ padding: "18px 24px", marginBottom: "24px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span className="badge badge-emerald">Klasifikasi Peran Yakin</span>
          <span style={{ fontSize: "0.88rem", color: "var(--text-secondary)" }}>
            Seluruh {roles.length} paragraf berhasil diklasifikasikan dengan keyakinan tinggi (&ge; 70%).
          </span>
        </div>
        <button
          onClick={() => setShowAll(true)}
          className="btn btn-secondary"
          style={{ padding: "6px 14px", fontSize: "0.8rem" }}
        >
          Tinjau Semua Peran Paragraf ({roles.length})
        </button>
      </div>
    );
  }

  return (
    <div className="glass-panel" style={{ padding: "24px", marginBottom: "24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#ffffff" }}>
            Konfirmasi Peran Paragraf Ambigu
          </h2>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            Terdapat {lowConfidenceRoles.length} paragraf dengan keyakinan klasifikasi &lt; 70%. Konfirmasi peran agar aturan dievaluasi secara akurat.
          </p>
        </div>
        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <button
            onClick={() => setShowAll(!showAll)}
            className="btn btn-secondary"
            style={{ padding: "6px 12px", fontSize: "0.8rem" }}
          >
            {showAll ? `Hanya Ambigu (${lowConfidenceRoles.length})` : `Tampilkan Semua (${roles.length})`}
          </button>
          <button
            id="btn-confirm-roles"
            onClick={handleApplyOverrides}
            disabled={isSaving}
            className="btn btn-primary"
            style={{ padding: "8px 16px", fontSize: "0.85rem" }}
          >
            {isSaving ? "⏳ Menyimpan..." : "✓ Simpan & Evaluasi Ulang"}
          </button>
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px", maxHeight: "340px", overflowY: "auto", paddingRight: "4px" }}>
        {displayedRoles.map((item) => {
          const currentVal = editedRoles[item.block_index] ?? item.role;
          return (
            <div
              key={item.block_index}
              style={{
                background: "rgba(15, 23, 42, 0.65)",
                border: `1px solid ${item.needs_confirmation ? "rgba(245, 158, 11, 0.45)" : "var(--border-subtle)"}`,
                borderRadius: "var(--radius-md)",
                padding: "12px 16px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "16px",
                flexWrap: "wrap",
              }}
            >
              <div style={{ flex: "1 1 320px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                  <span style={{ fontSize: "0.78rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                    Blok #{item.block_index} (Sec {item.section_index + 1})
                  </span>
                  <span className={`badge ${item.confidence < 0.7 ? "badge-amber" : "badge-emerald"}`}>
                    Keyakinan: {Math.round(item.confidence * 100)}%
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    Style: {item.style_name}
                  </span>
                </div>
                <p style={{ fontSize: "0.88rem", color: "#ffffff", fontWeight: "500" }}>
                  &ldquo;{item.excerpt || "(Paragraf kosong)"}&rdquo;
                </p>
                {item.evidence && item.evidence.length > 0 && (
                  <p style={{ fontSize: "0.76rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                    Alasan: {item.evidence.join(", ")}
                  </p>
                )}
              </div>

              <div style={{ flex: "0 0 260px" }}>
                <select
                  aria-label={`Peran untuk blok ${item.block_index}`}
                  value={currentVal}
                  onChange={(e) => handleRoleChange(item.block_index, e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    background: "rgba(9, 13, 22, 0.9)",
                    border: "1px solid var(--border-active)",
                    borderRadius: "var(--radius-sm)",
                    color: "#ffffff",
                    fontSize: "0.84rem",
                  }}
                >
                  {ROLE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value} style={{ background: "#0f172a", color: "#ffffff" }}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
