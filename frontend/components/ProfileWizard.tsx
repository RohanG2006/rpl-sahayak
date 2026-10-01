"use client";
import { useState } from "react";
import { Button, Choice, ListInput, Meter, Notice, SelectField, TextArea, TextField } from "./ui";
import { useT, type TKey } from "@/lib/i18n";
import { ApiError } from "@/lib/api";
import { EDUCATION, STATES } from "@/lib/geo";
import type { ProfileInput } from "@/lib/data/worker";
import type { Worker } from "@/lib/types";

type Form = ProfileInput & { pin?: string };
type Errors = Partial<Record<keyof Form, string>>;

const STEPS: TKey[] = ["reg.s1", "reg.s2", "reg.s3", "reg.s4", "reg.s5"];

export default function ProfileWizard({ initial, mode, onSave }: {
  initial?: Partial<Worker>; mode: "register" | "edit"; onSave: (f: Form) => Promise<void>;
}) {
  const { t, lang } = useT();
  const [step, setStep] = useState(0);
  const [f, setF] = useState<Form>({
    full_name: initial?.full_name ?? "", mobile: initial?.mobile ?? "", age: initial?.age ?? null, gender: initial?.gender ?? null,
    state: initial?.state ?? "", district: initial?.district ?? "", locality: initial?.locality ?? "",
    preferred_language: initial?.preferred_language ?? lang, occupation: initial?.occupation ?? "",
    years_experience: initial?.years_experience ?? null, current_employer: initial?.current_employer ?? "",
    previous_employers: initial?.previous_employers ?? [], informal_training: initial?.informal_training ?? "",
    education_level: initial?.education_level ?? null, has_science_maths: initial?.has_science_maths ?? null,
    existing_certificates: initial?.existing_certificates ?? [], tools: initial?.tools ?? [], typical_work: initial?.typical_work ?? "",
    pin: "",
  });
  const [errors, setErrors] = useState<Errors>({});
  const [busy, setBusy] = useState(false);
  const [serverErr, setServerErr] = useState<string | null>(null);
  const set = <K extends keyof Form>(k: K, v: Form[K]) => setF((p) => ({ ...p, [k]: v }));

  function validate(s: number): boolean {
    const e: Errors = {};
    const req = lang === "hi" ? "यह भरना ज़रूरी है" : "Required";
    if (s === 0) {
      if (!f.full_name || f.full_name.trim().length < 2) e.full_name = req;
      if (mode === "register") {
        if (!/^[6-9]\d{9}$/.test((f.mobile ?? "").replace(/\D/g, "").slice(-10))) e.mobile = lang === "hi" ? "10 अंकों का मोबाइल नंबर लिखें" : "Enter a 10-digit mobile number";
        if (!/^\d{4,6}$/.test(f.pin ?? "")) e.pin = lang === "hi" ? "4 से 6 अंक" : "4 to 6 digits";
      }
      if (f.age == null || f.age < 14 || f.age > 80) e.age = lang === "hi" ? "उम्र 14 से 80 के बीच" : "Age must be 14–80";
    }
    if (s === 1) { if (!f.state) e.state = req; if (!f.district) e.district = req; }
    if (s === 2) { if (!f.occupation) e.occupation = req; if (f.years_experience == null) e.years_experience = req; }
    if (s === 3) { if (!f.education_level) e.education_level = req; }
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function save() {
    setBusy(true);
    setServerErr(null);
    try {
      const clean: Form = { ...f, mobile: f.mobile || null, locality: f.locality || null, current_employer: f.current_employer || null, informal_training: f.informal_training || null, typical_work: f.typical_work || null };
      if (mode === "edit") delete clean.pin;
      await onSave(clean);
    } catch (e) {
      setServerErr(e instanceof ApiError ? (e.isOffline ? t("err.offline") : e.message) : t("err.generic"));
    } finally {
      setBusy(false);
    }
  }

  const next = () => { if (validate(step)) setStep((s) => Math.min(s + 1, STEPS.length - 1)); };
  const numOrNull = (v: string) => (v === "" ? null : Number(v));

  return (
    <div className="flex flex-col gap-5">
      <div>
        <p className="label">{t("common.step", { n: step + 1, total: STEPS.length })}</p>
        <h2 className="mt-1 text-xl font-semibold">{t(STEPS[step])}</h2>
        <div className="mt-3"><Meter value={step + 1} max={STEPS.length} label={t("common.step", { n: step + 1, total: STEPS.length })} /></div>
      </div>

      {step === 0 && (
        <div className="flex flex-col gap-4">
          <TextField label={t("f.full_name")} value={f.full_name ?? ""} onChange={(e) => set("full_name", e.target.value)} error={errors.full_name} autoComplete="name" />
          {mode === "register" && <>
            <TextField label={t("f.mobile")} inputMode="numeric" value={f.mobile ?? ""} onChange={(e) => set("mobile", e.target.value)} error={errors.mobile} autoComplete="tel" />
            <TextField label={t("f.pin")} hint={t("f.pin_hint")} inputMode="numeric" type="password" maxLength={6} value={f.pin ?? ""} onChange={(e) => set("pin", e.target.value.replace(/\D/g, ""))} error={errors.pin} autoComplete="new-password" />
          </>}
          <TextField label={t("f.age")} inputMode="numeric" value={f.age ?? ""} onChange={(e) => set("age", numOrNull(e.target.value.replace(/\D/g, "")))} error={errors.age} />
          <Choice label={t("f.gender")} value={f.gender} onChange={(v) => set("gender", v)}
            options={(["female", "male", "other", "prefer_not"] as const).map((g) => ({ value: g, label: t(`f.gender.${g}` as TKey) }))} />
          <Choice label={t("f.language")} value={f.preferred_language} onChange={(v) => set("preferred_language", v as "en" | "hi")}
            options={[{ value: "hi", label: "हिंदी" }, { value: "en", label: "English" }]} />
        </div>
      )}

      {step === 1 && (
        <div className="flex flex-col gap-4">
          <SelectField label={t("f.state")} value={f.state ?? ""} onChange={(e) => set("state", e.target.value)} error={errors.state} options={STATES.map((s) => ({ value: s, label: s }))} />
          <TextField label={t("f.district")} value={f.district ?? ""} onChange={(e) => set("district", e.target.value)} error={errors.district} />
          <TextField label={t("f.locality")} optional value={f.locality ?? ""} onChange={(e) => set("locality", e.target.value)} />
        </div>
      )}

      {step === 2 && (
        <div className="flex flex-col gap-4">
          <TextField label={t("f.occupation")} value={f.occupation ?? ""} onChange={(e) => set("occupation", e.target.value)} error={errors.occupation} list="occupations" />
          <datalist id="occupations"><option value="Electrician" /><option value="Wireman" /><option value="Electrician Helper" /></datalist>
          <TextField label={t("f.years")} inputMode="decimal" value={f.years_experience ?? ""} onChange={(e) => set("years_experience", numOrNull(e.target.value.replace(/[^\d.]/g, "")))} error={errors.years_experience} />
          <TextField label={t("f.employer")} hint={t("f.employer_hint")} optional value={f.current_employer ?? ""} onChange={(e) => set("current_employer", e.target.value)} />
          <ListInput label={t("f.prev_employers")} optional values={f.previous_employers ?? []} onChange={(v) => set("previous_employers", v)} />
          <TextArea label={t("f.informal")} hint={t("f.informal_hint")} optional rows={2} value={f.informal_training ?? ""} onChange={(e) => set("informal_training", e.target.value)} />
          <ListInput label={t("f.tools")} optional values={f.tools ?? []} onChange={(v) => set("tools", v)} />
          <TextArea label={t("f.typical")} optional rows={3} value={f.typical_work ?? ""} onChange={(e) => set("typical_work", e.target.value)} />
        </div>
      )}

      {step === 3 && (
        <div className="flex flex-col gap-4">
          <Choice label={t("f.education")} value={f.education_level} onChange={(v) => set("education_level", v)}
            options={EDUCATION.map((e) => ({ value: e, label: t(`f.edu.${e}` as TKey) }))} />
          {errors.education_level && <p className="text-sm text-bad">{errors.education_level}</p>}
          {f.education_level && ["10th", "12th", "iti", "diploma", "graduate"].includes(f.education_level) && (
            <Choice label={t("f.sci_maths")} value={f.has_science_maths == null ? null : String(f.has_science_maths)} onChange={(v) => set("has_science_maths", v === "true")}
              options={[{ value: "true", label: t("common.yes") }, { value: "false", label: t("common.no") }]} />
          )}
          <ListInput label={t("f.certs")} optional values={f.existing_certificates ?? []} onChange={(v) => set("existing_certificates", v)} />
        </div>
      )}

      {step === 4 && (
        <dl className="sheet divide-y divide-rule">
          {([
            ["f.full_name", f.full_name], ["f.age", f.age], ["f.state", f.state], ["f.district", f.district], ["f.locality", f.locality],
            ["f.occupation", f.occupation], ["f.years", f.years_experience], ["f.employer", f.current_employer],
            ["f.education", f.education_level ? t(`f.edu.${f.education_level}` as TKey) : null], ["f.tools", (f.tools ?? []).join(", ")],
          ] as [TKey, unknown][]).map(([k, v]) => (
            <div key={k} className="grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-3 px-3 py-2.5 text-[0.9375rem]">
              <dt className="text-ink-3">{t(k)}</dt><dd className="font-medium break-words">{v === null || v === "" || v === undefined ? "—" : String(v)}</dd>
            </div>
          ))}
        </dl>
      )}

      {serverErr && <Notice tone="bad">{serverErr}</Notice>}

      <div className={`sticky ${mode === "register" ? "bottom-0" : "bottom-16"} z-10 -mx-4 flex gap-2 border-t border-rule bg-paper px-4 py-3`}>
        {step > 0 && <Button variant="secondary" size="lg" onClick={() => setStep(step - 1)}>{t("common.back")}</Button>}
        {step < STEPS.length - 1
          ? <Button size="lg" block onClick={next}>{t("common.next")}</Button>
          : <Button size="lg" block disabled={busy} onClick={save}>{busy ? t("common.saving") : t("common.save")}</Button>}
      </div>
    </div>
  );
}
