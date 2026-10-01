"use client";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import en, { type TKey } from "./en";
import hi from "./hi";
import type { Lang } from "../types";

const DICTS = { en, hi } as const;
const KEY = "rpl.lang";

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (k: TKey, vars?: Record<string, string | number>) => string };
const I18nCtx = createContext<Ctx | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY) as Lang | null;
      if (saved === "en" || saved === "hi") setLangState(saved);
    } catch { /* storage blocked */ }
  }, []);
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try { localStorage.setItem(KEY, l); } catch { /* ignore */ }
  }, []);
  const t = useCallback((k: TKey, vars?: Record<string, string | number>) => {
    let s: string = DICTS[lang][k] ?? en[k] ?? k;
    if (vars) for (const [name, v] of Object.entries(vars)) s = s.replaceAll(`{${name}}`, String(v));
    return s;
  }, [lang]);
  return <I18nCtx.Provider value={{ lang, setLang, t }}>{children}</I18nCtx.Provider>;
}

export function useT() {
  const c = useContext(I18nCtx);
  if (!c) throw new Error("useT outside I18nProvider");
  return c;
}

export type { TKey };
