"use client";

import React, { useState, useEffect } from "react";
import { Header } from "@/components/Header";
import { ProfileSelector } from "@/components/ProfileSelector";
import { FileUpload } from "@/components/FileUpload";
import { RoleConfirmationPanel } from "@/components/RoleConfirmationPanel";
import { FindingsReport } from "@/components/FindingsReport";
import { ActionPanel } from "@/components/ActionPanel";
import { ChangeEntry, Finding, RoleItem, RuleProfileSummary } from "@/types";
import { SAMPLE_PROFILES } from "@/lib/constants";
import {
  fetchProfiles,
  uploadDocument,
  analyzeDocument,
  fetchRoles,
  updateRoles,
  fixDocument,
  deleteDocument,
  getDownloadUrl,
  getPreviewUrl,
  getReportUrl,
} from "@/lib/api";

export default function Home() {
  const [profiles, setProfiles] = useState<RuleProfileSummary[]>(SAMPLE_PROFILES);
  const [selectedProfileId, setSelectedProfileId] = useState<string>("contoh-s1-skripsi");
  const [uploadedDocId, setUploadedDocId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [isSavingRoles, setIsSavingRoles] = useState<boolean>(false);
  const [isFixing, setIsFixing] = useState<boolean>(false);
  const [isFixed, setIsFixed] = useState<boolean>(false);
  const [roles, setRoles] = useState<RoleItem[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [changes, setChanges] = useState<ChangeEntry[]>([]);
  const [activeCategoryFilter, setActiveCategoryFilter] = useState<string>("ALL");
  const [selectedFindingIds, setSelectedFindingIds] = useState<string[]>([]);
  const [approvedSuggestIds, setApprovedSuggestIds] = useState<string[]>([]);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Load profiles on mount
  useEffect(() => {
    async function loadData() {
      const remoteProfiles = await fetchProfiles();
      if (remoteProfiles && remoteProfiles.length > 0) {
        setProfiles(remoteProfiles);
        setSelectedProfileId(remoteProfiles[0].profile_id);
      }
    }
    loadData();
  }, []);

  const handleFileSelected = async (file: File) => {
    setIsProcessing(true);
    setStatusMessage("Mengunggah dan memverifikasi dokumen...");
    setIsFixed(false);
    setChanges([]);
    setSelectedFindingIds([]);
    setApprovedSuggestIds([]);

    try {
      // 1. Upload
      const uploadRes = await uploadDocument(file);
      setUploadedDocId(uploadRes.doc_id);
      setStatusMessage("Menganalisis format dokumen terhadap profil pedoman...");

      // 2. Analyze
      const analyzeRes = await analyzeDocument(uploadRes.doc_id, selectedProfileId);
      setFindings(analyzeRes.findings);

      // 3. Fetch classified roles
      const rolesRes = await fetchRoles(uploadRes.doc_id);
      setRoles(rolesRes.roles);

      setStatusMessage(null);
    } catch (err: unknown) {
      const error = err as Error;
      console.warn("API offline or error, providing demo findings preview", error);
      setUploadedDocId("mock-session-id");
      setRoles([
        {
          block_index: 2,
          section_index: 0,
          style_id: "Normal",
          style_name: "Normal",
          role: "chapter_title",
          confidence: 0.62,
          needs_confirmation: true,
          evidence: ["Teks huruf kapital tebal singkat tanpa label BAB"],
          excerpt: "TINJAUAN PUSTAKA",
        },
      ]);
      setFindings([
        {
          id: "finding-demo-page-01",
          rule_id: "PAGE-002",
          category: "PAGE",
          severity: "error",
          location: { block_index: 0, section_index: 0, approx_page: 1 },
          actual: "Top: 2.54 cm, Left: 2.54 cm",
          expected: "Top: 4.00 cm, Left: 4.00 cm (Baku Skripsi)",
          fix_mode: "auto",
          message_id: "finding.page.margin",
          message: "Margin section pertama belum memenuhi standar 4-4-3-3 cm (masih default Word 1 inci/2.54 cm).",
        },
        {
          id: "finding-demo-font-01",
          rule_id: "FONT-001",
          category: "FONT",
          severity: "warning",
          location: { block_index: 4, section_index: 0, approx_page: 2, excerpt: "Penelitian ini bertujuan untuk..." },
          actual: "Calibri 11pt",
          expected: "Times New Roman 12pt",
          fix_mode: "auto",
          message_id: "finding.font.family",
          message: "Paragraf isi menggunakan font Calibri alih-alih Times New Roman 12pt.",
        },
        {
          id: "finding-demo-para-01",
          rule_id: "PARA-001",
          category: "PARA",
          severity: "warning",
          location: { block_index: 8, section_index: 0, approx_page: 2 },
          actual: "Spasi baris 1.15 (Multiple)",
          expected: "Spasi baris 1.50 (Satu Setengah)",
          fix_mode: "auto",
          message_id: "finding.para.spacing",
          message: "Spasi baris paragraf tidak sesuai standar 1.5 spasi.",
        },
        {
          id: "finding-demo-num-01",
          rule_id: "NUM-001",
          category: "NUM",
          severity: "error",
          location: { block_index: 15, section_index: 1, approx_page: 3 },
          actual: "Penomoran halaman dimulai dari cover",
          expected: "Halaman cover tanpa nomor, Bagian Awal angka Romawi kecil (i, ii, iii)",
          fix_mode: "auto",
          message_id: "finding.num.format",
          message: "Bagian awal skripsi belum menggunakan penomoran romawi terpisah dari naskah bab isi.",
        },
        {
          id: "finding-demo-head-01",
          rule_id: "HEAD-006",
          category: "HEAD",
          severity: "warning",
          location: { block_index: 22, section_index: 1, approx_page: 4, excerpt: "1.1 Latar Belakang" },
          actual: "Teks judul sub-bab diketik manual '1.1 Latar Belakang'",
          expected: "Multilevel List Style Heading 2",
          fix_mode: "suggest",
          message_id: "finding.head.typed",
          message: "Nomor sub-bab terdeteksi diketik manual sebagai teks, disarankan dikonversi ke Style Heading bernomor otomatis.",
        },
      ]);
      setStatusMessage(null);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSaveRoles = async (overrides: { block_index: number; role: string }[]) => {
    if (!uploadedDocId) return;
    setIsSavingRoles(true);
    try {
      if (uploadedDocId !== "mock-session-id") {
        const res = await updateRoles(uploadedDocId, overrides, selectedProfileId);
        setFindings(res.findings);
        const rolesRes = await fetchRoles(uploadedDocId);
        setRoles(rolesRes.roles);
      } else {
        setRoles((prev) =>
          prev.map((r) => {
            const match = overrides.find((o) => o.block_index === r.block_index);
            return match ? { ...r, role: match.role, confidence: 1.0, needs_confirmation: false } : r;
          })
        );
      }
    } catch (err: unknown) {
      const error = err as Error;
      alert(error.message || "Gagal menyimpan konfirmasi peran paragraf");
    } finally {
      setIsSavingRoles(false);
    }
  };

  const handleToggleFinding = (findingId: string, fixMode: string) => {
    if (fixMode === "suggest") {
      setApprovedSuggestIds((prev) =>
        prev.includes(findingId) ? prev.filter((id) => id !== findingId) : [...prev, findingId]
      );
    } else {
      setSelectedFindingIds((prev) =>
        prev.includes(findingId) ? prev.filter((id) => id !== findingId) : [...prev, findingId]
      );
    }
  };

  const executeFix = async (mode: "all" | "categories" | "findings", categories: string[] = []) => {
    if (!uploadedDocId) return;
    setIsFixing(true);
    setStatusMessage("Menerapkan perbaikan format dan memverifikasi integritas teks...");

    try {
      if (uploadedDocId !== "mock-session-id") {
        const fixRes = await fixDocument(uploadedDocId, {
          profile_id: selectedProfileId,
          mode,
          categories,
          finding_ids: selectedFindingIds,
          approved_suggest_ids: approvedSuggestIds,
        });
        setChanges(fixRes.changes);
        setFindings(fixRes.remaining_findings);
        setIsFixed(true);
      } else {
        setChanges([
          {
            rule_id: "PAGE-002",
            block_index: 0,
            field: "page.margins_cm",
            before: "2.54 cm",
            after: "top=4.0, left=4.0, bottom=3.0, right=3.0 cm",
            method: "section",
          },
          {
            rule_id: "FONT-001",
            block_index: 4,
            field: "font.family",
            before: "Calibri",
            after: "Times New Roman 12pt",
            method: "style",
          },
        ]);
        setIsFixed(true);
      }
    } catch (err: unknown) {
      const error = err as Error;
      alert(error.message || "Gagal merapikan dokumen");
    } finally {
      setIsFixing(false);
      setStatusMessage(null);
    }
  };

  const handleDownload = (which: "fixed" | "original" = "fixed") => {
    if (uploadedDocId && uploadedDocId !== "mock-session-id") {
      window.location.href = getDownloadUrl(uploadedDocId, which);
    } else {
      alert(`Mode demonstrasi: Berkas skripsi-${which}.docx akan diunduh pada mode backend aktif.`);
    }
  };

  const handleDownloadReport = (format: "html" | "json") => {
    if (uploadedDocId && uploadedDocId !== "mock-session-id") {
      window.open(getReportUrl(uploadedDocId, format), "_blank");
    } else {
      alert(`Mode demonstrasi: Laporan kepatuhan (${format.toUpperCase()}) tersedia saat terhubung ke server API.`);
    }
  };

  const handleDeleteDocument = async () => {
    if (!uploadedDocId) return;
    try {
      if (uploadedDocId !== "mock-session-id") {
        await deleteDocument(uploadedDocId);
      }
      setUploadedDocId(null);
      setFindings([]);
      setRoles([]);
      setChanges([]);
      setIsFixed(false);
      setStatusMessage("Dokumen berhasil dihapus secara permanen dari server.");
    } catch (err: unknown) {
      const error = err as Error;
      alert(error.message || "Gagal menghapus dokumen");
    }
  };

  const autoFixCount = findings.filter((f) => f.fix_mode === "auto").length;
  const previewBeforeUrl =
    uploadedDocId && uploadedDocId !== "mock-session-id"
      ? getPreviewUrl(uploadedDocId, "before")
      : null;
  const previewAfterUrl =
    uploadedDocId && uploadedDocId !== "mock-session-id"
      ? getPreviewUrl(uploadedDocId, "after")
      : null;

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <Header />

      <main style={{ flex: 1, padding: "40px 0" }}>
        <div className="container">
          {/* Hero Section */}
          <div style={{ textAlign: "center", marginBottom: "40px" }}>
            <div style={{ display: "inline-block", marginBottom: "12px" }}>
              <span className="badge badge-primary">Rilis MVP v0.1.0</span>
            </div>
            <h1 style={{
              fontSize: "2.6rem",
              fontWeight: "800",
              letterSpacing: "-0.03em",
              lineHeight: "1.2",
              marginBottom: "14px",
              background: "linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #94a3b8 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}>
              Rapikan Format Skripsi dalam Hitungan Menit.
            </h1>
            <p style={{
              maxWidth: "680px",
              margin: "0 auto",
              fontSize: "1.05rem",
              color: "var(--text-secondary)",
              lineHeight: "1.6",
            }}>
              Otomatis periksa margin, font, spasi paragraf, penomoran halaman romawi/angka,
              dan field Daftar Isi sesuai pedoman kampus Anda. <strong style={{ color: "#ffffff" }}>Tanpa menyentuh isi teks tulisan Anda.</strong>
            </p>
          </div>

          {/* Workflow Steps */}
          <ProfileSelector
            profiles={profiles}
            selectedProfileId={selectedProfileId}
            onSelectProfile={setSelectedProfileId}
          />

          <FileUpload
            onFileSelected={handleFileSelected}
            isLoading={isProcessing}
          />

          {statusMessage && (
            <div style={{
              padding: "16px 20px",
              marginBottom: "24px",
              borderRadius: "var(--radius-md)",
              background: "rgba(56, 189, 248, 0.1)",
              border: "1px solid rgba(56, 189, 248, 0.3)",
              color: "var(--accent-cyan)",
              fontSize: "0.95rem",
              textAlign: "center",
              fontWeight: "500",
            }}>
              {statusMessage}
            </div>
          )}

          {roles.length > 0 && (
            <RoleConfirmationPanel
              roles={roles}
              onSaveRoles={handleSaveRoles}
              isSaving={isSavingRoles}
            />
          )}

          {(findings.length > 0 || isFixed) && (
            <>
              <FindingsReport
                findings={findings}
                selectedFindingIds={selectedFindingIds}
                approvedSuggestIds={approvedSuggestIds}
                onToggleFinding={handleToggleFinding}
                onSelectCategoryForFix={setActiveCategoryFilter}
                activeCategoryFilter={activeCategoryFilter}
              />
              <ActionPanel
                docId={uploadedDocId}
                onFixAll={() => executeFix("all")}
                onFixCategory={(cat) => executeFix("categories", [cat])}
                onFixSelected={() => executeFix("findings")}
                onDownload={handleDownload}
                onDownloadReport={handleDownloadReport}
                onDeleteDocument={handleDeleteDocument}
                previewBeforeUrl={previewBeforeUrl}
                previewAfterUrl={previewAfterUrl}
                isFixing={isFixing}
                isFixed={isFixed}
                autoFixCount={autoFixCount}
                activeCategoryFilter={activeCategoryFilter}
                selectedFindingsCount={selectedFindingIds.length}
                approvedSuggestCount={approvedSuggestIds.length}
                changes={changes}
              />
            </>
          )}
        </div>
      </main>

      {/* Footer */}
      <footer style={{
        borderTop: "1px solid var(--border-subtle)",
        padding: "24px 0",
        background: "rgba(9, 13, 22, 0.9)",
        textAlign: "center",
        fontSize: "0.85rem",
        color: "var(--text-muted)",
      }}>
        <div className="container">
          <p>
            Skripsi Formatter &copy; 2026. File Anda dilindungi retensi singkat 1 jam dan dihapus otomatis setelah sesi berakhir.
          </p>
        </div>
      </footer>
    </div>
  );
}
