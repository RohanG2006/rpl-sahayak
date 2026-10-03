import { describe, expect, it } from "vitest";
import { LIFECYCLE, NCVET_STAGE_HI, STATE_LABEL, lifecycleProgress } from "@/lib/workflow";

describe("lifecycle progress", () => {
  it("covers the full 19-state RPL lifecycle", () => {
    expect(LIFECYCLE).toHaveLength(19);
    expect(lifecycleProgress("REGISTERED")).toBe(5);
    expect(lifecycleProgress("SKILLS_CONFIRMED")).toBe(26); // honest: onboarding is not 'most' of the assessment
    expect(lifecycleProgress("QUALIFICATION_CONFIRMED", "REPORT_ISSUED")).toBe(100);
  });
  it("prefers the plan state over the worker state and tolerates unknown states", () => {
    expect(lifecycleProgress("QUALIFICATION_CONFIRMED", "TASKS_IN_PROGRESS")).toBe(lifecycleProgress("TASKS_IN_PROGRESS"));
    expect(lifecycleProgress("SOMETHING_NEW")).toBe(0);
  });
  it("labels every state in English and Hindi, and every NCVET stage in Hindi", () => {
    for (const s of LIFECYCLE) expect(STATE_LABEL[s].en && STATE_LABEL[s].hi).toBeTruthy();
    expect(Object.keys(NCVET_STAGE_HI)).toHaveLength(5);
  });
});
