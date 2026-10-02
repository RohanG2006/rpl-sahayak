"use client";
import { useEffect, type ReactNode } from "react";
import { I18nProvider } from "@/lib/i18n";

export default function Providers({ children }: { children: ReactNode }) {
  useEffect(() => {
    // Service worker only in production builds (it would fight the dev server's hot reload).
    if (process.env.NODE_ENV === "production" && "serviceWorker" in navigator) {
      navigator.serviceWorker.register("/sw.js").catch(() => { /* offline shell unavailable; app still works online */ });
    }
  }, []);
  return <I18nProvider>{children}</I18nProvider>;
}
