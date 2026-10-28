"use client";

import React, { useState, useRef } from "react";

interface FileUploadProps {
  onFileSelected: (file: File) => void;
  isLoading: boolean;
}

export function FileUpload({ onFileSelected, isLoading }: FileUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    setErrorMsg(null);
    if (!file.name.toLowerCase().endsWith(".docx")) {
      setErrorMsg("Hanya file Microsoft Word berformat .docx yang didukung. Format .doc dan .docm tidak diizinkan.");
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setErrorMsg("Ukuran file melebihi 50 MB.");
      return;
    }
    setFileName(file.name);
    onFileSelected(file);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: "32px", marginBottom: "24px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "20px" }}>
        <div>
          <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#ffffff" }}>
            2. Unggah Dokumen Skripsi (.docx)
          </h2>
          <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            File asli aman dan tidak akan diubah. Semua perapian dibuat pada salinan dokumen.
          </p>
        </div>
        <span className="badge badge-emerald">Enkripsi & TTL 1 Jam</span>
      </div>

      <div
        id="file-dropzone"
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: `2px dashed ${isDragOver ? "var(--accent-cyan)" : "var(--border-active)"}`,
          borderRadius: "var(--radius-lg)",
          padding: "48px 24px",
          textAlign: "center",
          cursor: isLoading ? "wait" : "pointer",
          background: isDragOver ? "rgba(56, 189, 248, 0.08)" : "rgba(15, 23, 42, 0.5)",
          transition: "all var(--transition-fast)",
        }}
      >
        <input
          type="file"
          ref={fileInputRef}
          accept=".docx"
          style={{ display: "none" }}
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              handleFile(e.target.files[0]);
            }
          }}
          disabled={isLoading}
        />

        <div style={{
          width: "64px",
          height: "64px",
          margin: "0 auto 16px",
          borderRadius: "16px",
          background: "rgba(99, 102, 241, 0.15)",
          border: "1px solid rgba(99, 102, 241, 0.3)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "28px",
        }}>
          📁
        </div>

        {fileName ? (
          <div>
            <p style={{ fontSize: "1.05rem", fontWeight: "600", color: "var(--accent-cyan)" }}>
              {fileName}
            </p>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "4px" }}>
              Klik atau seret file lain untuk mengganti
            </p>
          </div>
        ) : (
          <div>
            <p style={{ fontSize: "1.05rem", fontWeight: "600", color: "#ffffff" }}>
              Seret dan lepaskan file skripsi Anda ke sini
            </p>
            <p style={{ fontSize: "0.85rem", color: "var(--text-secondary)", marginTop: "6px" }}>
              Atau klik untuk memilih file dari komputer (maks. 50 MB)
            </p>
          </div>
        )}

        {isLoading && (
          <div style={{ marginTop: "16px", color: "var(--accent-cyan)", fontSize: "0.9rem", fontWeight: "500" }}>
            ⏳ Sedang memproses dan memverifikasi dokumen...
          </div>
        )}
      </div>

      {errorMsg && (
        <div style={{
          marginTop: "16px",
          padding: "12px 16px",
          borderRadius: "var(--radius-md)",
          background: "rgba(244, 63, 94, 0.15)",
          border: "1px solid rgba(244, 63, 94, 0.3)",
          color: "#fb7185",
          fontSize: "0.88rem",
          display: "flex",
          alignItems: "center",
          gap: "8px",
        }}>
          ⚠️ {errorMsg}
        </div>
      )}
    </div>
  );
}
