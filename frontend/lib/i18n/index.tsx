"use client";
import { createContext, useCallback, useContext, useEffect, useSyncExternalStore, type ReactNode } from "react";
import en, { type TKey } from "./en";
import hi from "./hi";
import type { Lang } from "../types";

const DICTS = { en, hi } as const;
const KEY = "rpl.lang";

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (k: TKey, vars?: Record<string, string | number>) => string };
const I18nCtx = createContext<Ctx | null>(null);

// Language preference lives in localStorage; read it as an external store (SSR snapshot = "en").
const langListeners = new Set<() => void>();
let memLang: Lang = "en"; // used when storage is blocked (private mode), so switching still works this session
function readLang(): Lang {
  try {
    const saved = localStorage.getItem(KEY);
    return saved === "hi" || saved === "en" ? saved : memLang;
  } catch { return memLang; }
}
function subscribeLang(fn: () => void) {
  langListeners.add(fn);
  return () => { langListeners.delete(fn); };
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const lang = useSyncExternalStore(subscribeLang, readLang, () => "en" as Lang);
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  const setLang = useCallback((l: Lang) => {
    memLang = l;
    try { localStorage.setItem(KEY, l); } catch { /* storage blocked: remembered in memory only */ }
    langListeners.forEach((f) => f());
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
