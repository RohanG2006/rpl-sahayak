import { api } from "../api";

export interface Overview {
  users_by_role: Record<string, number>; workers_by_origin: Record<string, number>; plans_by_status: Record<string, number>;
  decisions: Record<string, number>;
  evidence: { total: number; captured_offline: number; by_kind: Record<string, number> };
  ai: { observations: number; by_provider: Record<string, number>; by_kind: Record<string, number>; fallback_rate: number | null; scores_with_ai_suggestion: number; assessor_overrides: number; override_rate: number | null };
  sync: { by_status: Record<string, number>; last_received: string | null };
  audit_events_today: number;
  qualifications: { code: string; title: string; assessable: boolean; los: number; source_url: string; sha256: string; retrieved_at: string }[];
}
export interface AdminUser { id: string; login: string; full_name: string; role: string; assessor_code: string | null; is_active: boolean; data_origin: string; created_at: string; open_plans: number | null; decisions: number | null; temporary_password?: string }
export interface AdminCriterion { criterion_code: string; text: string; weight: number; is_safety_critical: boolean; qf_dimension: string; qf_criterion_ref: string | null; anchors: Record<string, string>; scores_recorded: number }
export interface AdminTask { task_code: string; title: string; title_hi: string | null; description: string; weight: number; is_active: boolean; competency_key: string; lo_numbers: number[]; scores_recorded: number; criteria: AdminCriterion[] }
export interface AuditRow { id: string; at: string; action: string; entity: string; entity_id: string | null; actor: string; actor_role: string | null; via: string; summary: string | null; before: unknown; after: unknown }
export interface SyncRow { client_op_id: string; client_id: string; entity: string; op: string; status: string; detail: string | null; client_ts: string | null; received_at: string }

export const getOverview = () => api<Overview>("/admin/overview", { cache: false });
export const getUsers = () => api<AdminUser[]>("/admin/users", { cache: false });
export const createUser = (b: { login: string; full_name: string; role: "assessor" | "admin"; assessor_code?: string }) => api<AdminUser>("/admin/users", { body: b });
export const patchUser = (id: string, b: { is_active?: boolean; full_name?: string }) => api<AdminUser>(`/admin/users/${id}`, { method: "PUT", body: b });
export const getAdminTasks = () => api<AdminTask[]>("/admin/tasks", { cache: false });
export const patchTask = (code: string, b: Partial<Pick<AdminTask, "weight" | "is_active" | "title" | "title_hi" | "description">>) => api(`/admin/tasks/${code}`, { method: "PUT", body: b });
export const patchCriterion = (code: string, b: Partial<Pick<AdminCriterion, "weight" | "is_safety_critical" | "text" | "anchors">>) => api<AdminCriterion>(`/admin/criteria/${code}`, { method: "PUT", body: b });
export const getAudit = (q: Record<string, string | number>) =>
  api<{ total: number; page: number; page_size: number; actions: string[]; rows: AuditRow[] }>(`/admin/audit?${new URLSearchParams(Object.entries(q).filter(([, v]) => v !== "").map(([k, v]) => [k, String(v)]))}`, { cache: false });
export const getSyncLog = () => api<SyncRow[]>("/admin/sync", { cache: false });
