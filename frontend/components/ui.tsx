"use client";
import { useId, useState, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { useT } from "@/lib/i18n";

/* ----- Buttons ----------------------------------------------------------------------------- */
type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" | "danger"; size?: "md" | "lg"; block?: boolean };
export function Button({ variant = "primary", size = "md", block, className = "", ...p }: BtnProps) {
  const base = "inline-flex items-center justify-center gap-2 font-semibold rounded-[3px] border transition-colors disabled:opacity-50 disabled:cursor-not-allowed select-none";
  const sizes = { md: "min-h-11 px-4 text-[0.9375rem]", lg: "min-h-14 px-5 text-base" };
  const variants = {
    primary: "bg-ink text-sheet border-ink hover:bg-ink-2",
    secondary: "bg-sheet text-ink border-rule-strong hover:border-ink",
    ghost: "bg-transparent text-ink border-transparent hover:bg-black/5",
    danger: "bg-bad text-white border-bad hover:opacity-90",
  };
  return <button className={`${base} ${sizes[size]} ${variants[variant]} ${block ? "w-full" : ""} ${className}`} {...p} />;
}

/* ----- Stamps (provenance markers) ----------------------------------------------------------- */
export function Stamp({ kind, children }: { kind: "ai" | "human" | "official" | "synthetic"; children?: ReactNode }) {
  const { t } = useT();
  const label = { ai: t("stamp.ai"), human: t("stamp.assessor"), official: t("stamp.official"), synthetic: t("stamp.synthetic") }[kind];
  return (
    <span className={`stamp stamp-${kind}`}>
      {kind === "ai" && <svg width="10" height="10" viewBox="0 0 10 10" aria-hidden><path d="M5 0l1.3 3.7L10 5 6.3 6.3 5 10 3.7 6.3 0 5l3.7-1.3z" fill="currentColor" /></svg>}
      {children ?? label}
    </span>
  );
}

export function AdvisoryNote({ provider, fallback }: { provider?: string; fallback?: boolean }) {
  const { t } = useT();
  return (
    <p className="text-sm text-ai flex flex-wrap items-center gap-2" role="note">
      <Stamp kind="ai" /> <span>{t("ai.advisory")}</span>
      {provider === "rules" && !fallback && <span className="text-ink-3">· {t("ai.rules")}</span>}
      {fallback && <span className="text-ink-3">· {t("ai.fallback")}</span>}
    </p>
  );
}

/* ----- Form fields ------------------------------------------------------------------------- */
function FieldShell({ label, hint, error, optional, htmlFor, children }: { label: string; hint?: string; error?: string; optional?: boolean; htmlFor: string; children: ReactNode }) {
  const { t } = useT();
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={htmlFor} className="text-[0.9375rem] font-medium text-ink">
        {label}{optional && <span className="ml-1.5 text-sm font-normal text-ink-3">({t("common.optional")})</span>}
      </label>
      {hint && <p className="text-sm text-ink-3 -mt-0.5">{hint}</p>}
      {children}
      {error && <p className="text-sm text-bad" role="alert">{error}</p>}
    </div>
  );
}

const inputCls = "w-full min-h-12 rounded-[3px] border border-rule-strong bg-sheet px-3 text-base text-ink placeholder:text-ink-3 focus:border-ink";

export function TextField({ label, hint, error, optional, ...p }: InputHTMLAttributes<HTMLInputElement> & { label: string; hint?: string; error?: string; optional?: boolean }) {
  const id = useId();
  return <FieldShell label={label} hint={hint} error={error} optional={optional} htmlFor={id}><input id={id} className={inputCls} aria-invalid={!!error} {...p} /></FieldShell>;
}

export function TextArea({ label, hint, error, optional, ...p }: TextareaHTMLAttributes<HTMLTextAreaElement> & { label: string; hint?: string; error?: string; optional?: boolean }) {
  const id = useId();
  return <FieldShell label={label} hint={hint} error={error} optional={optional} htmlFor={id}><textarea id={id} className={`${inputCls} py-2.5 leading-relaxed`} aria-invalid={!!error} {...p} /></FieldShell>;
}

export function SelectField({ label, hint, error, optional, options, ...p }: SelectHTMLAttributes<HTMLSelectElement> & { label: string; hint?: string; error?: string; optional?: boolean; options: { value: string; label: string }[] }) {
  const id = useId();
  return (
    <FieldShell label={label} hint={hint} error={error} optional={optional} htmlFor={id}>
      <select id={id} className={inputCls} {...p}>
        <option value="">—</option>
        {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
      </select>
    </FieldShell>
  );
}

/** Large touch-friendly single choice (radio group). */
export function Choice({ label, value, onChange, options, columns = 2 }: { label: string; value: string | null | undefined; onChange: (v: string) => void; options: { value: string; label: string }[]; columns?: number }) {
  const name = useId();
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-[0.9375rem] font-medium mb-1.5">{label}</legend>
      <div className="grid gap-2" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }}>
        {options.map((o) => {
          const on = value === o.value;
          return (
            <label key={o.value} className={`flex min-h-12 cursor-pointer items-center gap-2.5 rounded-[3px] border px-3 text-[0.9375rem] ${on ? "border-ink bg-ink text-sheet" : "border-rule-strong bg-sheet hover:border-ink"}`}>
              <input type="radio" className="sr-only" name={name} value={o.value} checked={on} onChange={() => onChange(o.value)} />
              <span aria-hidden className={`h-4 w-4 shrink-0 rounded-full border-2 ${on ? "border-sheet bg-sheet [box-shadow:inset_0_0_0_3px_var(--ink)]" : "border-ink-3"}`} />
              {o.label}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

/** Editable list of short strings (tools, employers, certificates). */
export function ListInput({ label, values, onChange, placeholder, optional }: { label: string; values: string[]; onChange: (v: string[]) => void; placeholder?: string; optional?: boolean }) {
  const { t } = useT();
  const id = useId();
  const [draft, setDraft] = useState("");
  const add = () => {
    const v = draft.trim();
    if (v && !values.includes(v)) onChange([...values, v]);
    setDraft("");
  };
  return (
    <FieldShell label={label} optional={optional} htmlFor={id}>
      {values.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {values.map((v) => (
            <li key={v} className="flex items-center gap-1 rounded-[3px] border border-rule-strong bg-sheet pl-2.5 text-sm">
              {v}
              <button type="button" className="min-h-9 min-w-9 text-ink-3 hover:text-bad" aria-label={`${t("common.remove")} ${v}`} onClick={() => onChange(values.filter((x) => x !== v))}>×</button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <input id={id} className={inputCls} value={draft} placeholder={placeholder ?? t("f.add_item")} onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }} />
        <Button type="button" variant="secondary" onClick={add}>{t("common.add")}</Button>
      </div>
    </FieldShell>
  );
}

/* ----- Feedback ---------------------------------------------------------------------------- */
export function Notice({ tone = "info", children }: { tone?: "info" | "ok" | "warn" | "bad"; children: ReactNode }) {
  const tones = { info: "border-accent bg-accent-wash text-accent-ink", ok: "border-ok bg-ok-wash text-ok", warn: "border-warn bg-warn-wash text-warn", bad: "border-bad bg-bad-wash text-bad" };
  return <div role={tone === "bad" ? "alert" : "status"} className={`border-l-4 px-3 py-2.5 text-[0.9375rem] ${tones[tone]}`}>{children}</div>;
}

export function Meter({ value, max = 100, label, tone = "ink" }: { value: number; max?: number; label?: string; tone?: "ink" | "ok" | "warn" | "bad" | "accent" }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const fills = { ink: "bg-ink", ok: "bg-ok", warn: "bg-warn", bad: "bg-bad", accent: "bg-accent" };
  return (
    <div className="h-2 w-full bg-rule/70" role="meter" aria-valuemin={0} aria-valuemax={max} aria-valuenow={Math.round(value)} aria-label={label}>
      <div className={`h-full ${fills[tone]}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export function Spinner({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-ink-2" role="status">
      <span aria-hidden className="h-4 w-4 animate-spin rounded-full border-2 border-rule-strong border-t-ink" />
      {label}
    </span>
  );
}
