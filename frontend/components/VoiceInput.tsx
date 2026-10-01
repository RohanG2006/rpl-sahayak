"use client";
import { useEffect, useRef, useState } from "react";
import { Button } from "./ui";
import { useT } from "@/lib/i18n";

/* Optional voice input via the browser's Web Speech API (on-device/browser service; nothing sent to our server
   except the resulting text). Hidden gracefully where unsupported. */
type SR = { lang: string; continuous: boolean; interimResults: boolean; start(): void; stop(): void;
  onresult: ((e: { resultIndex: number; results: ArrayLike<{ 0: { transcript: string }; isFinal: boolean }> }) => void) | null;
  onend: (() => void) | null; onerror: (() => void) | null };

export default function VoiceInput({ onText }: { onText: (text: string) => void }) {
  const { t, lang } = useT();
  const [supported, setSupported] = useState(false);
  const [on, setOn] = useState(false);
  const rec = useRef<SR | null>(null);

  useEffect(() => {
    const w = window as unknown as { SpeechRecognition?: new () => SR; webkitSpeechRecognition?: new () => SR };
    setSupported(!!(w.SpeechRecognition || w.webkitSpeechRecognition));
  }, []);

  function toggle() {
    if (on) { rec.current?.stop(); return; }
    const w = window as unknown as { SpeechRecognition?: new () => SR; webkitSpeechRecognition?: new () => SR };
    const Ctor = w.SpeechRecognition || w.webkitSpeechRecognition;
    if (!Ctor) return;
    const r = new Ctor();
    r.lang = lang === "hi" ? "hi-IN" : "en-IN";
    r.continuous = true;
    r.interimResults = false;
    r.onresult = (e) => {
      let s = "";
      for (let i = e.resultIndex; i < e.results.length; i++) if (e.results[i].isFinal) s += e.results[i][0].transcript;
      if (s) onText(s.trim());
    };
    r.onend = () => setOn(false);
    r.onerror = () => setOn(false);
    rec.current = r;
    r.start();
    setOn(true);
  }

  if (!supported) return <p className="text-sm text-ink-3">{t("exp.voice_unsupported")}</p>;
  return (
    <Button type="button" variant={on ? "danger" : "secondary"} onClick={toggle} aria-pressed={on}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
      {on ? t("exp.voice_stop") : t("exp.voice")}
    </Button>
  );
}
