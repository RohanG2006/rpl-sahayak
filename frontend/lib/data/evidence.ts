import { api, ApiError, patchCache } from "../api";
import { db } from "../offline/db";
import { isOnline } from "../offline/network";
import { enqueue } from "../offline/sync";
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

type UploadIn = { file: File; worker_id: string; plan_id?: string; task_code?: string; criterion_code?: string; purpose: "assessment" | "document"; doc_type?: string; caption?: string; captured_offline?: boolean; client_op_id?: string; criterion_id?: string };

/** Store the file on the device and queue it; it appears immediately in the list as 'pending'. */
async function uploadOffline(f: UploadIn): Promise<EvidenceItem> {
  const fields: Record<string, string> = {};
  for (const k of ["worker_id", "plan_id", "task_code", "criterion_code", "purpose", "doc_type", "caption"] as const) if (f[k]) fields[k] = String(f[k]);
  const op = await enqueue({ op_id: f.client_op_id, kind: "evidence", entity: "evidence", op: "upload", payload: { ...fields, size: f.file.size }, label: `Evidence ${f.criterion_code ?? f.doc_type ?? ""} (${Math.round(f.file.size / 1024)} KB)` },
    { blob: f.file, name: f.file.name, mime: f.file.type, fields });
  const item: EvidenceItem = {
    id: op.op_id, plan_id: f.plan_id ?? null, worker_id: f.worker_id, criterion_id: f.criterion_id ?? null, purpose: f.purpose, doc_type: f.doc_type ?? null,
    kind: f.file.type.startsWith("image/") ? "image" : f.file.type.startsWith("video/") ? "video" : "document", mime: f.file.type, size_bytes: f.file.size,
    sha256: "", caption: f.caption ?? null, captured_offline: true, upload_status: "pending", data_origin: "user", created_at: new Date().toISOString(),
    file_url: "", extracted_claims: [], claims_confirmed: false,
  };
  await patchCache<EvidenceItem[]>(`/evidence?${new URLSearchParams({ worker_id: f.worker_id })}`, (xs) => [item, ...xs]);
  if (f.plan_id) await patchCache<EvidenceItem[]>(`/evidence?${new URLSearchParams({ plan_id: f.plan_id })}`, (xs) => [item, ...xs]);
  return item;
}

export async function uploadEvidence(f: UploadIn): Promise<EvidenceItem> {
  const client_op_id = f.client_op_id ?? crypto.randomUUID();
  if (!isOnline()) return uploadOffline({ ...f, client_op_id });
  const form = new FormData();
  form.append("file", f.file);
  for (const [k, v] of Object.entries({ ...f, client_op_id })) if (k !== "file" && k !== "criterion_id" && v !== undefined && v !== "") form.append(k, String(v));
  try { return await api<EvidenceItem>("/evidence", { form }); }
  catch (e) { if (e instanceof ApiError && e.isOffline) return uploadOffline({ ...f, client_op_id }); throw e; }
}
export const listEvidence = (q: { plan_id?: string; worker_id?: string }) => api<EvidenceItem[]>(`/evidence?${new URLSearchParams(q as Record<string, string>)}`);
export const analyzeEvidence = (id: string) => api<EvidenceItem>(`/evidence/${id}/analyze`, { method: "POST" });
export const confirmClaims = (id: string, claims: EvidenceItem["extracted_claims"]) => api<EvidenceItem>(`/evidence/${id}/claims`, { method: "PUT", body: { claims } });

/** Evidence files need the bearer token, so fetch as blob and hand back an object URL. */
export async function evidenceBlobUrl(id: string): Promise<string> {
  try {
    const local = await db().evidence.get(id); // captured offline, not yet uploaded
    if (local) return URL.createObjectURL(local.blob);
  } catch { /* IndexedDB unavailable */ }
  const res = await fetch(`${API_BASE}/evidence/${id}/file`, { headers: { Authorization: `Bearer ${getToken()}` } });
  if (!res.ok) throw new Error("file");
  return URL.createObjectURL(await res.blob());
}
