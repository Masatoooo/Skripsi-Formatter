"use client";

import React from "react";
import { RuleProfileSummary } from "@/types";

interface ProfileSelectorProps {
  profiles: RuleProfileSummary[];
  selectedProfileId: string;
  onSelectProfile: (id: string) => void;
}

export function ProfileSelector({
  profiles,
  selectedProfileId,
  onSelectProfile,
}: ProfileSelectorProps) {
  const currentProfile = profiles.find((p) => p.profile_id === selectedProfileId) || profiles[0];

  return (
    <div className="glass-panel" style={{ padding: "24px", marginBottom: "24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
        <div>
          <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#ffffff" }}>
            1. Pilih Pedoman Format Kampus
          </h2>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            Aturan format dimuat dari profil pedoman baku (.json)
          </p>
        </div>
        <span className="badge badge-primary">Profil Aktif</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "16px" }}>
        <select
          id="profile-select"
          value={selectedProfileId}
          onChange={(e) => onSelectProfile(e.target.value)}
          style={{
            width: "100%",
            padding: "14px 18px",
            background: "rgba(15, 23, 42, 0.9)",
            border: "1px solid var(--border-active)",
            borderRadius: "var(--radius-md)",
            color: "#ffffff",
            fontSize: "0.95rem",
            fontWeight: "500",
            fontFamily: "inherit",
            outline: "none",
            cursor: "pointer",
          }}
        >
          {profiles.map((p) => (
            <option key={p.profile_id} value={p.profile_id} style={{ background: "#0f172a", color: "#ffffff" }}>
              {p.name}
            </option>
          ))}
        </select>

        {currentProfile && (
          <div style={{
            padding: "16px",
            background: "rgba(255, 255, 255, 0.03)",
            borderRadius: "var(--radius-md)",
            border: "1px solid var(--border-subtle)",
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "12px",
            fontSize: "0.85rem"
          }}>
            <div>
              <span style={{ color: "var(--text-muted)" }}>Dokumen Acuan:</span>
              <p style={{ fontWeight: "600", color: "var(--accent-cyan)", marginTop: "2px" }}>
                {currentProfile.source.document}
              </p>
            </div>
            <div>
              <span style={{ color: "var(--text-muted)" }}>Edisi / Tahun:</span>
              <p style={{ fontWeight: "600", color: "#ffffff", marginTop: "2px" }}>
                {currentProfile.source.edition || "2024"}
              </p>
            </div>
            <div>
              <span style={{ color: "var(--text-muted)" }}>Standar Margin:</span>
              <p style={{ fontWeight: "600", color: "#ffffff", marginTop: "2px" }}>
                Kiri 4cm, Atas 4cm, Kanan 3cm, Bawah 3cm
              </p>
            </div>
            <div>
              <span style={{ color: "var(--text-muted)" }}>Standar Tipografi:</span>
              <p style={{ fontWeight: "600", color: "#ffffff", marginTop: "2px" }}>
                Times New Roman 12pt, Spasi 1.5
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
