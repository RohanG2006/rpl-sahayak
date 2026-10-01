import { api } from "../api";

export interface MatchSkill { label: string; kind: string; similarity: number; lo_number: number | null; lo_title: string | null; nos: string[]; status: "matched" | "partial" | "unclear" }
export interface LORow { lo_number: number; title: string; nos: string[]; status: "matched" | "partial" | "not_evidenced"; similarity: number; matched_by: string | null; skill_hours: number | null }
export interface EligCheck { key: string; label: string; result: "pass" | "fail" | "unknown"; score: number; detail: string; source: string }
export type Component = "skill" | "task" | "experience" | "occupation" | "eligibility";
export interface MatchResult {
  rank: number; qualification_id: string; qualification_code: string; title: string; nsqf_level: number; is_assessable: boolean;
  source_url: string; final_score: number; final_pct: number; components: Record<Component, number>; weights: Record<Component, number>;
  contributions: Record<Component, number>; task_basis: string; matched_skills: MatchSkill[]; unclear_skills: MatchSkill[];
  supporting_evidence: { label: string; kind: string }[];
  lo_coverage: { matched: number; partial: number; total: number; pct: number }; learning_outcomes: LORow[];
  areas_not_evidenced: { lo_number: number; title: string }[]; eligibility: EligCheck[];
}
export interface MatchResponse { worker_id: string; method: string; label: string; thresholds: { matched: number; partial: number }; results: MatchResult[] }

export interface Criterion {
  id: string; criterion_code: string; text: string; weight: number; is_safety_critical: boolean; qf_dimension: string;
  qf_criterion_ref: string | null; anchors: Record<string, string>; evidence_hint: string | null; evidence_ids: string[];
  score: null | { final_score: number | null; confirmed: boolean; ai_suggested_score: number | null; ai_observation_id: string | null; overrode_ai: boolean | null; assessor_note: string | null; confirmed_at: string | null };
}
export interface PlanTask {
  id: string; task_code: string; title: string; title_hi: string | null; description: string; description_hi: string | null;
  competency_key: string; lo_numbers: number[]; weight: number; steps: { en: string; hi: string }[];
  evidence_required: { kind: string; what: string; criterion: string }[]; safety_requirements: string[]; source_ref: Record<string, unknown>;
  criteria: Criterion[];
  attempt: null | { id: string; status: string; checklist_state: Record<string, boolean>; worker_note: string | null; started_at: string | null; completed_at: string | null };
}
export interface Plan {
  id: string; status: string; ncvet_stage: string; pathway: string | null; data_origin: string;
  worker: { id: string; full_name: string; status: string; years_experience: number | null; occupation: string | null; data_origin: string };
  qualification: { id: string; title: string; qualification_code: string; ncvet_code: string | null; nsqf_level: number; source_url: string };
  assessor: { id: string; name: string; code: string } | null;
  match_snapshot: MatchResult; self_assessment: Record<string, string>; readiness: Readiness | Record<string, never>;
  tasks: PlanTask[]; evidence_count: number; created_at: string; updated_at: string;
  scope_los: { lo_number: number; title: string; criteria: string[]; nos: string[] }[]; lo_total: number;
}

export const runMatch = (worker_id: string) => api<MatchResponse>("/qualifications/match", { body: { worker_id } });
export const createPlan = (worker_id: string, qualification_id: string) => api<Plan>("/assessments", { body: { worker_id, qualification_id } });
export const getPlan = (id: string) => api<Plan>(`/assessments/${id}`);
export const listPlans = () => api<{ id: string; status: string; qualification_id: string; worker_id: string; ncvet_stage: string; updated_at: string }[]>("/assessments");

export interface Readiness {
  scope_los: number[]; rows: { lo_number: number; claim: string; declaration_evidence: string; corroborated: boolean; needs_probe: boolean }[];
  claimed_share: number; weighted_coverage: number; corroborated_share: number; threshold: number; threshold_source: string;
  pathway: "DIRECT_ASSESSMENT" | "UPSKILLING_SUGGESTED"; eligibility_flags: string[]; probe_los: number[]; reasons: string[]; note: string;
}
export type ScopeLO = { lo_number: number; title: string; criteria: string[]; nos: string[] };

export const selfAssess = (planId: string, responses: Record<number, "regularly" | "sometimes" | "never">) =>
  api<{ readiness: Readiness; status: string }>(`/assessments/${planId}/self-assessment`, { body: { responses } });
export const startPlan = (planId: string) => api<Plan>(`/assessments/${planId}/start`, { method: "POST" });
export const saveTaskProgress = (planId: string, taskCode: string, body: { checklist_state: Record<string, boolean>; worker_note?: string | null; status: "IN_PROGRESS" | "SUBMITTED" }) =>
  api<Plan>(`/assessments/${planId}/tasks/${taskCode}/progress`, { method: "PUT", body });

/** The worker's most recent open plan, or null. */
export async function currentPlan(): Promise<Plan | null> {
  const list = await listPlans();
  const open = list.find((p) => !["DECIDED", "REPORT_ISSUED"].includes(p.status)) ?? list[0];
  return open ? getPlan(open.id) : null;
}
