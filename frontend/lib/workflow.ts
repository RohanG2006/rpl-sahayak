// Mirrors backend app/services/workflow.py — full RPL lifecycle used for honest progress figures.
export const WORKER_STATES = ["REGISTERED", "PROFILE_COMPLETE", "EXPERIENCE_DECLARED", "SKILLS_EXTRACTED", "SKILLS_CONFIRMED", "QUALIFICATION_MATCHED", "QUALIFICATION_CONFIRMED"] as const;
export const PLAN_STATES = ["PLAN_CREATED", "SELF_ASSESSED", "READINESS_EVALUATED", "TASKS_IN_PROGRESS", "EVIDENCE_SUBMITTED", "AI_EVIDENCE_REVIEWED", "ASSESSOR_SCORING", "SCORED", "RECOMMENDATION_GENERATED", "UNDER_ASSESSOR_REVIEW", "DECIDED", "REPORT_ISSUED"] as const;
export const LIFECYCLE = [...WORKER_STATES, ...PLAN_STATES] as const;
export type State = (typeof LIFECYCLE)[number];

/** Share of the full lifecycle completed, 0–100. A plan state, when present, supersedes the worker state. */
export function lifecycleProgress(workerStatus: string, planStatus?: string | null): number {
  const s = planStatus ?? workerStatus;
  const i = LIFECYCLE.indexOf(s as State);
  return i < 0 ? 0 : Math.round(((i + 1) / LIFECYCLE.length) * 100);
}

export const STATE_LABEL: Record<State, { en: string; hi: string }> = {
  REGISTERED: { en: "Registered", hi: "पंजीकृत" },
  PROFILE_COMPLETE: { en: "Profile complete", hi: "प्रोफ़ाइल पूरी" },
  EXPERIENCE_DECLARED: { en: "Experience declared", hi: "अनुभव दर्ज" },
  SKILLS_EXTRACTED: { en: "Skills found (to confirm)", hi: "कौशल मिले (पुष्टि बाकी)" },
  SKILLS_CONFIRMED: { en: "Skills confirmed", hi: "कौशल की पुष्टि" },
  QUALIFICATION_MATCHED: { en: "Qualification matched", hi: "योग्यता मिलान हुआ" },
  QUALIFICATION_CONFIRMED: { en: "Qualification confirmed", hi: "योग्यता चुनी" },
  PLAN_CREATED: { en: "Assessment plan created", hi: "मूल्यांकन योजना बनी" },
  SELF_ASSESSED: { en: "Self-assessment done", hi: "स्व-मूल्यांकन पूरा" },
  READINESS_EVALUATED: { en: "Readiness checked", hi: "तैयारी जाँची गई" },
  TASKS_IN_PROGRESS: { en: "Practical tasks in progress", hi: "प्रायोगिक कार्य जारी" },
  EVIDENCE_SUBMITTED: { en: "Evidence submitted", hi: "सबूत जमा" },
  AI_EVIDENCE_REVIEWED: { en: "AI evidence notes ready", hi: "AI सबूत टिप्पणी तैयार" },
  ASSESSOR_SCORING: { en: "Assessor scoring", hi: "मूल्यांकनकर्ता अंक दे रहे हैं" },
  SCORED: { en: "Scored", hi: "अंक दिए गए" },
  RECOMMENDATION_GENERATED: { en: "Recommendation prepared", hi: "सिफ़ारिश तैयार" },
  UNDER_ASSESSOR_REVIEW: { en: "Under assessor review", hi: "मूल्यांकनकर्ता की समीक्षा में" },
  DECIDED: { en: "Assessor decision recorded", hi: "मूल्यांकनकर्ता का निर्णय दर्ज" },
  REPORT_ISSUED: { en: "Report issued", hi: "रिपोर्ट जारी" },
};

// NCVET RPL Guidelines (Gazette 19-Jun-2024) Annexure-1, Flowchart 3 stage names
export const NCVET_STAGE_HI: Record<string, string> = {
  "Enrolment": "नामांकन",
  "Orientation": "अभिविन्यास (ओरिएंटेशन)",
  "Assignment of RPL assessor": "RPL मूल्यांकनकर्ता का आवंटन",
  "Assessment (practical skills)": "मूल्यांकन (प्रायोगिक कौशल)",
  "Certification & Feedback": "प्रमाणन और प्रतिक्रिया",
};
