import { api } from "../api";
import { API_BASE } from "../config";
import { getToken } from "../session";

export interface EvidenceObs {
  id: string; provider: string; model: string | null; fallback_used: boolean; confidence: number | null; advisory: string; simulated: boolean; error?: string | null;
  output: { observed?: string[]; potentially_missing?: string[]; safety_concerns?: string[]; competency_indicators?: string[]; suggested_score?: number | null; suggested_score_reason?: string | null; confidence?: number; analysis_basis?: string; claims?: { label: string; source_text?: string | null; confidence: number }[] };
}
export interface EvidenceItem {
  id: string; plan_id: string | null; worker_id: string; criterion_id: string | null; purpose: "assessment" | "document"; doc_type: string | null;
  kind: string; mime: string; size_bytes: number; sha256: string; caption: string | null; captured_offline: boolean; upload_status: string;
  data_origin: string; created_at: string; file_url: string; extracted_claims: { label: string; source_text?: string | null; confidence: number }[];
  claims_confirmed: boolean; ai_observation?: EvidenceObs; duplicate?: boolean;
}

export function uploadEvidence(f: { file: File; worker_id: string; plan_id?: string; task_code?: string; criterion_code?: string; purpose: "assessment" | "document"; doc_type?: string; caption?: string; captured_offline?: boolean; client_op_id?: string }) {
  const form = new FormData();
  form.append("file", f.file);
  for (const [k, v] of Object.entries(f)) if (k !== "file" && v !== undefined && v !== "") form.append(k, String(v));
  return api<EvidenceItem>("/evidence", { form });
}
export const listEvidence = (q: { plan_id?: string; worker_id?: string }) => api<EvidenceItem[]>(`/evidence?${new URLSearchParams(q as Record<string, string>)}`);
export const analyzeEvidence = (id: string) => api<EvidenceItem>(`/evidence/${id}/analyze`, { method: "POST" });
export const confirmClaims = (id: string, claims: EvidenceItem["extracted_claims"]) => api<EvidenceItem>(`/evidence/${id}/claims`, { method: "PUT", body: { claims } });

/** Evidence files need the bearer token, so fetch as blob and hand back an object URL. */
export async function evidenceBlobUrl(id: string): Promise<string> {
  const res = await fetch(`${API_BASE}/evidence/${id}/file`, { headers: { Authorization: `Bearer ${getToken()}` } });
  if (!res.ok) throw new Error("file");
  return URL.createObjectURL(await res.blob());
}
