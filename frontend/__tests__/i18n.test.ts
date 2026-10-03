import { describe, expect, it } from "vitest";
import en from "@/lib/i18n/en";
import hi from "@/lib/i18n/hi";

const vars = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe("Hindi translation parity", () => {
  it("has exactly the English keys", () => {
    expect(Object.keys(hi).sort()).toEqual(Object.keys(en).sort());
  });
  it("uses the same {placeholders} as English in every string", () => {
    const bad = (Object.keys(en) as (keyof typeof en)[]).filter((k) => JSON.stringify(vars(en[k])) !== JSON.stringify(vars(hi[k])));
    expect(bad).toEqual([]);
  });
  it("has no empty or untranslated worker-facing strings", () => {
    const empty = Object.entries(hi).filter(([, v]) => !v.trim()).map(([k]) => k);
    expect(empty).toEqual([]);
    // brand/technical tokens may legitimately be identical; everything else should differ from English
    const same = (Object.keys(en) as (keyof typeof en)[]).filter((k) => en[k] === hi[k] && !/^(ITI|LO|f\.edu\.iti|match\.lo)$/.test(String(k)) && !/^[A-Z0-9 .·{}/-]+$/.test(en[k]));
    expect(same).toEqual([]);
  });
});
