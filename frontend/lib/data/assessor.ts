import { api } from "../api";
import type { Plan } from "./assessment";

export interface CandidateRow {
  plan_id: string; worker_id: string; candidate: string; trade: string; qualification: string | null; qualification_code: string | null;
  experience_years: number | null; ai_match_pct: number | null; assessment_score: number | null; scored: string; tasks_submitted: number;
  evidence_items: number; status: string; ncvet_stage: string; pathway: string | null; recommendation: string | null; decision: string | null;
  data_origin: string; updated_at: string;
}
export interface Dashboard {
  assigned: number; pending_review: number; in_progress: number; completed: number; reassessments: number; approved: number;
  average_score: number | null; score_variance_across_candidates: number | null; evidence_coverage: number | null; ai_assisted_cases: number;
  decision_agreement_with_recommendation: number | null; by_status: Record<string, number>; evidence_items: number; note: string;
}
export interface Results {
  tasks: Record<string, { task_pct: number | null; complete: boolean; scored: number; total: number }>;
  learning_outcomes: Record<string, number | null>; competencies: Record<string, number | null>; dimensions: Record<string, number | null>;
  overall_pct: number | null; scored_criteria: number; total_criteria: number; complete: boolean; safety_flags: string[];
  evidence_coverage: number; evidence_missing: string[]; evidence_items: number; competency_labels: Record<string, string>;
  competency_labels_hi: Record<string, string>; task_titles: Record<string, string>; task_competency: Record<string, string>;
  summary?: { text: string; provider: string; fallback_used: boolean } | null;
}
export interface GapArea { competency_key: string; label: string; label_hi: string; required: number; demonstrated: number | null; gap: number | null; status: "met" | "gap" | "not_assessed"; learning_topics: { topic: string; lo_number: number | null; source: "official" | "suggested"; because: string }[] }
export interface Gaps { required_pct: number; required_source: string; areas: GapArea[]; learning_outcomes: { lo_number: number; title: string; required: number; demonstrated: number | null; gap: number | null }[]; not_assessed_in_prototype: { lo_number: number; title: string }[]; note: string; summary: { text: string; provider: string } }
export interface Rule { rule: string; label: string; passed: boolean; detail: string; source: string }
export interface Recommendation { id: string; outcome: "ELIGIBLE" | "NOT_YET_READY" | "REASSESSMENT_SUGGESTED"; competency_coverage: number; evidence_coverage: number; overall_pct: number | null; rule_trace: Rule[]; flags: string[]; narrative: string | null; narrative_provider: string | null; status_label: string; disclaimer: string; created_at: string }
export interface Decision { id: string; decision: "APPROVE" | "REJECT" | "REASSESS"; comments: string; agrees_with_recommendation: boolean | null; reassess_task_codes: string[]; decided_at: string; assessor: { name: string; code: string } | null }

export const getDashboard = () => api<Dashboard>("/analytics/dashboard");
export const getCandidates = (q: { status?: string; q?: string; page?: number; page_size?: number } = {}) =>
  api<{ total: number; page: number; page_size: number; rows: CandidateRow[] }>(`/assessor/candidates?${new URLSearchParams(Object.entries(q).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => [k, String(v)]))}`);
export const getResults = (planId: string) => api<Results>(`/competencies/${planId}`);
export const getGaps = (planId: string) => api<Gaps>(`/skill-gaps/${planId}`);
export const getRecommendation = (planId: string) => api<Recommendation | null>(`/assessments/${planId}/recommendation`);
export const makeRecommendation = (planId: string) => api<Recommendation>(`/assessments/${planId}/recommendation`, { method: "POST" });
export const getDecision = (planId: string) => api<Decision | null>(`/assessments/${planId}/decision`);
export const recordDecision = (body: { plan_id: string; decision: Decision["decision"]; comments: string; reassess_task_codes: string[] }) =>
  api<{ decision: Decision; plan: Plan }>("/assessor/decision", { body });
export const scoreTask = (planId: string, taskCode: string, scores: { criterion_code: string; final_score: number; assessor_note: string | null }[]) =>
  api<Plan>(`/assessments/${planId}/tasks/${taskCode}/score`, { body: { scores } });
export const getWorkerFull = (workerId: string) => api<import("../types").Worker>(`/workers/${workerId}`);
