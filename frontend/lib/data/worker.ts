/*
  Worker data access. Pages call these functions only — never fetch() directly — so the
  offline/local-first implementation (Phase 10) can replace the transport without touching screens.
*/
import { api, ApiError, patchCache } from "../api";
import { isOnline } from "../offline/network";
import { enqueue } from "../offline/sync";
import { setSession } from "../session";
import type { ExtractionResponse, SessionUser, SkillKind, Worker } from "../types";

export type ProfileInput = Partial<Omit<Worker, "id" | "user_id" | "status" | "ncvet_stage" | "data_origin" | "experiences" | "skills">> & { full_name?: string };

export async function registerWorker(input: ProfileInput & { pin: string }) {
  const r = await api<{ worker: Worker; access_token: string | null }>("/workers", { body: input, auth: false });
  if (r.access_token) {
    const me = await fetchMe(r.access_token);
    setSession(r.access_token, me, new Date(Date.now() + 8 * 3600e3).toISOString());
  }
  return r.worker;
}

async function fetchMe(token: string): Promise<SessionUser> {
  const { API_BASE } = await import("../config");
  const res = await fetch(`${API_BASE}/auth/me`, { headers: { Authorization: `Bearer ${token}` } });
  return res.json();
}

export const getWorker = (id: string) => api<Worker>(`/workers/${id}`);
/** Runs `online()`; when offline (or the network drops) runs `offline()` instead — local-first writes. */
async function localFirst<T>(online: () => Promise<T>, offline: () => Promise<T>): Promise<T> {
  if (!isOnline()) return offline();
  try { return await online(); } catch (e) {
    if (e instanceof ApiError && e.isOffline) return offline();
    throw e;
  }
}

export const updateWorker = (id: string, input: ProfileInput) => localFirst(
  () => api<Worker>(`/workers/${id}`, { method: "PUT", body: input }),
  async () => {
    await enqueue({ kind: "json", entity: "worker_profile", op: "update", payload: input as Record<string, unknown>, label: "Profile update" });
    let updated: Worker | undefined;
    await patchCache<Worker>(`/workers/${id}`, (w) => (updated = { ...w, ...input } as Worker));
    if (!updated) throw new ApiError(0, "offline", "No connection to the server.");
    return updated;
  },
);

export const declareExperience = (id: string, raw_text: string, input_mode: "text" | "voice", language: "en" | "hi") => localFirst(
  () => api<{ id: string; version: number }>(`/workers/${id}/experience`, { body: { raw_text, input_mode, language } }),
  async () => {
    const op = await enqueue({ kind: "json", entity: "worker_experience", op: "create", payload: { raw_text, input_mode, language }, label: "Experience declaration" });
    let version = 1;
    await patchCache<Worker>(`/workers/${id}`, (w) => {
      version = (w.experiences.at(-1)?.version ?? 0) + 1;
      return { ...w, experiences: [...w.experiences, { id: op.op_id, version, raw_text, input_mode, language }] };
    });
    return { id: op.op_id, version };
  },
);
export const extractSkills = (id: string, experience_id?: string) =>
  api<ExtractionResponse>(`/workers/${id}/extract-skills`, { body: { experience_id } });
export const confirmSkills = (id: string, body: {
  skills: { kind: SkillKind; label: string; source: "ai" | "worker" | "assessor"; confidence?: number | null }[];
  occupation?: string | null; years_experience?: number | null; ai_observation_id?: string;
}) => api<Worker>(`/workers/${id}/skills`, { method: "PUT", body });
