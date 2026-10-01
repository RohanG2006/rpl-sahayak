export type Role = "worker" | "assessor" | "admin";
export type Lang = "en" | "hi";

export interface SessionUser {
  id: string;
  login: string;
  full_name: string;
  role: Role;
  preferred_language: Lang;
  assessor_code?: string | null;
  worker_id?: string | null;
  data_origin: string;
}

export interface ExtractedItem { label: string; source_text?: string | null; confidence: number }

export interface SkillExtraction {
  occupation: string | null;
  experience_years: number | null;
  skills: ExtractedItem[];
  tools: ExtractedItem[];
  tasks: ExtractedItem[];
  equipment: ExtractedItem[];
  safety_practices: ExtractedItem[];
  learning_mode: ExtractedItem[];
  experience_evidence: string[];
  confidence: number;
  missing_information: string[];
}

export interface ExtractionResponse {
  observation_id: string;
  experience_id: string;
  provider: string;
  model: string | null;
  fallback_used: boolean;
  advisory: string;
  applied: boolean;
  extraction: SkillExtraction;
}

export type SkillKind = "skill" | "tool" | "task" | "equipment" | "safety" | "learning_mode";

export interface WorkerSkill {
  id: string; kind: SkillKind; label: string; normalized_label: string | null;
  source: "ai" | "worker" | "assessor"; confirmed: boolean; confidence: number | null;
}

export interface Worker {
  id: string; user_id: string; status: string; ncvet_stage: string; data_origin: string; archetype?: string | null;
  full_name: string; mobile: string | null; age: number | null; gender: string | null;
  state: string | null; district: string | null; locality: string | null; preferred_language: Lang;
  occupation: string | null; years_experience: number | null; current_employer: string | null;
  previous_employers: string[]; informal_training: string | null; education_level: string | null;
  has_science_maths: boolean | null; existing_certificates: string[]; tools: string[]; typical_work: string | null;
  experiences: { id: string; version: number; raw_text: string; input_mode: string; language: string }[];
  skills: WorkerSkill[];
}
