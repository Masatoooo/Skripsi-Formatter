export type Severity = "error" | "warning" | "info";
export type FixMode = "auto" | "suggest" | "manual";
export type CategoryCode =
  | "PAGE"
  | "FONT"
  | "PARA"
  | "HEAD"
  | "NUM"
  | "TOC"
  | "LOF"
  | "LOT"
  | "CAP"
  | "FIG"
  | "TBL"
  | "BIB"
  | "STR"
  | "DOC";

export interface Location {
  block_index: number;
  section_index: number;
  approx_page?: number | null;
  excerpt?: string | null;
}

export interface Finding {
  id: string;
  rule_id: string;
  category: CategoryCode;
  severity: Severity;
  location: Location;
  actual: string;
  expected: string;
  fix_mode: FixMode;
  message_id: string;
  message: string;
}

export interface RuleProfileSummary {
  profile_id: string;
  name: string;
  version: string;
  language: string;
  source: {
    document: string;
    edition: string;
    pages?: string;
    notes?: string;
  };
}

export interface UploadResponse {
  doc_id: string;
  filename: string;
  size_bytes?: number;
  message: string;
}

export interface AnalyzeResponse {
  doc_id: string;
  job_id?: string;
  status?: string;
  profile_id: string;
  total_findings: number;
  low_confidence_roles_count?: number;
  findings: Finding[];
}

export interface RoleItem {
  block_index: number;
  section_index: number;
  style_id?: string | null;
  style_name: string;
  role: string;
  confidence: number;
  needs_confirmation: boolean;
  evidence: string[];
  excerpt: string;
}

export interface RolesResponse {
  doc_id: string;
  roles: RoleItem[];
}

export interface FixRequestPayload {
  profile_id?: string;
  mode: "all" | "categories" | "findings";
  categories?: string[];
  finding_ids?: string[];
  approved_suggest_ids?: string[];
}

export interface ChangeEntry {
  rule_id: string;
  block_index: number;
  field: string;
  before: string;
  after: string;
  method: "style" | "direct" | "section" | "field";
}

export interface FixResponse {
  doc_id: string;
  job_id?: string;
  status: string;
  profile_id: string;
  applied_changes_count: number;
  remaining_findings_count: number;
  changes: ChangeEntry[];
  remaining_findings: Finding[];
}

export interface ChangelogResponse {
  doc_id: string;
  total_changes: number;
  changes: ChangeEntry[];
}

export interface JobStatusResponse {
  job_id: string;
  doc_id: string;
  job_type: string;
  status: "queued" | "running" | "done" | "failed";
  error?: string | null;
  result?: Record<string, unknown> | null;
}
