import {
  AnalyzeResponse,
  ChangelogResponse,
  FixRequestPayload,
  FixResponse,
  JobStatusResponse,
  RolesResponse,
  RuleProfileSummary,
  UploadResponse,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

function extractErrorMessage(errorData: Record<string, unknown>, fallback: string): string {
  const detail = errorData?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && "message" in detail) {
    return String((detail as Record<string, unknown>).message);
  }
  return fallback;
}

export async function fetchProfiles(): Promise<RuleProfileSummary[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/v1/profiles`);
    if (!res.ok) throw new Error("Gagal mengambil profil aturan");
    return await res.json();
  } catch (err) {
    console.warn("Backend API not reachable, using fallback profiles", err);
    return [];
  }
}

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/v1/documents`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(errorData, "Gagal mengunggah dokumen"));
  }

  return await res.json();
}

export async function analyzeDocument(docId: string, profileId: string): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE_URL}/v1/documents/${docId}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile_id: profileId }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(errorData, "Gagal menganalisis dokumen"));
  }

  return await res.json();
}

export async function fetchRoles(docId: string): Promise<RolesResponse> {
  const res = await fetch(`${API_BASE_URL}/v1/documents/${docId}/roles`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(errorData, "Gagal mengambil peran paragraf"));
  }
  return await res.json();
}

export async function updateRoles(
  docId: string,
  overrides: { block_index: number; role: string }[],
  profileId?: string
): Promise<AnalyzeResponse> {
  const res = await fetch(`${API_BASE_URL}/v1/documents/${docId}/roles`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ overrides, profile_id: profileId }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(errorData, "Gagal menyimpan konfirmasi peran paragraf"));
  }

  return await res.json();
}

export async function fixDocument(docId: string, payload: FixRequestPayload): Promise<FixResponse> {
  const res = await fetch(`${API_BASE_URL}/v1/documents/${docId}/fix`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(errorData, "Gagal menerapkan perapian dokumen"));
  }

  return await res.json();
}

export async function fetchChangelog(docId: string): Promise<ChangelogResponse> {
  const res = await fetch(`${API_BASE_URL}/v1/documents/${docId}/changelog`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(errorData, "Gagal mengambil riwayat perubahan"));
  }
  return await res.json();
}

export async function fetchJobStatus(jobId: string): Promise<JobStatusResponse> {
  const res = await fetch(`${API_BASE_URL}/v1/jobs/${jobId}`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(errorData, "Gagal memeriksa status proses"));
  }
  return await res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/v1/documents/${docId}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(extractErrorMessage(errorData, "Gagal menghapus dokumen"));
  }
}

export function getDownloadUrl(docId: string, which: "original" | "fixed" = "fixed"): string {
  return `${API_BASE_URL}/v1/documents/${docId}/download?which=${which}`;
}

export function getPreviewUrl(docId: string, which: "before" | "after" = "after"): string {
  return `${API_BASE_URL}/v1/documents/${docId}/preview?which=${which}`;
}

export function getReportUrl(docId: string, format: "html" | "json" = "html"): string {
  return `${API_BASE_URL}/v1/documents/${docId}/report?format=${format}`;
}
