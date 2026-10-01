"use client";
import { useT } from "@/lib/i18n";

export default function LangToggle() {
  const { lang, setLang, t } = useT();
  return (
    <button type="button" onClick={() => setLang(lang === "en" ? "hi" : "en")}
      className="min-h-10 rounded-[3px] border border-rule-strong px-3 text-sm font-medium hover:border-ink"
      aria-label={lang === "en" ? "हिंदी में देखें" : "View in English"}>
      {t("lang.switch")}
    </button>
  );
}
