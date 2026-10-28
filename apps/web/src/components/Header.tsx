"use client";

import React from "react";

export function Header() {
  return (
    <header style={{
      borderBottom: "1px solid var(--border-subtle)",
      background: "rgba(9, 13, 22, 0.8)",
      backdropFilter: "blur(12px)",
      position: "sticky",
      top: 0,
      zIndex: 50,
      padding: "16px 0"
    }}>
      <div className="container" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
          <div style={{
            width: "42px",
            height: "42px",
            borderRadius: "12px",
            background: "var(--gradient-brand)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 0 20px rgba(99, 102, 241, 0.4)",
            fontSize: "20px"
          }}>
            ✍️
          </div>
          <div>
            <h1 style={{ fontSize: "1.25rem", fontWeight: "800", letterSpacing: "-0.02em", color: "#ffffff" }}>
              Skripsi<span style={{ color: "var(--accent-cyan)" }}>Formatter</span>
            </h1>
            <p style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              Asisten Perapian & Validasi Dokumen Word (.docx)
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span className="badge badge-emerald" style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
            <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#34d399", display: "inline-block" }}></span>
            Isi Teks 100% Aman · Hanya Merapikan Format
          </span>
        </div>
      </div>
    </header>
  );
}
