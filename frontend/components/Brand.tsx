import Link from "next/link";

/** Wordmark: a register "tick-box" glyph + name. Deliberately plain. */
export default function Brand({ href = "/", compact = false }: { href?: string; compact?: boolean }) {
  return (
    <Link href={href} className="flex items-center gap-2 font-semibold tracking-tight text-ink" aria-label="RPL-Sahayak AI home">
      <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden>
        <rect x="1" y="1" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" />
        <path d="M5.5 11.5l3.5 3.5 7.5-8" fill="none" stroke="var(--accent)" strokeWidth="2.4" strokeLinecap="square" />
      </svg>
      {!compact && <span className="text-[1.0625rem]">RPL-Sahayak <span className="text-ink-3 font-medium">AI</span></span>}
    </Link>
  );
}
