"use client";

import clsx from "clsx";
import type { Finding, Severity } from "@/lib/types";
import { SEVERITY_ORDER } from "@/lib/types";

const SEVERITY_STYLE: Record<Severity, { dot: string; text: string; border: string }> = {
  critical: { dot: "bg-severity-critical", text: "text-severity-critical", border: "border-severity-critical/30" },
  high: { dot: "bg-severity-high", text: "text-severity-high", border: "border-severity-high/30" },
  medium: { dot: "bg-severity-medium", text: "text-severity-medium", border: "border-severity-medium/30" },
  low: { dot: "bg-severity-low", text: "text-severity-low", border: "border-severity-low/30" },
  info: { dot: "bg-severity-info", text: "text-severity-info", border: "border-severity-info/30" },
};

const CATEGORY_LABEL: Record<string, string> = {
  bug: "Bug",
  security: "Security",
  performance: "Performance",
  quality: "Quality",
};

export function SeveritySummary({ findings }: { findings: Finding[] }) {
  const counts = SEVERITY_ORDER.map((sev) => ({
    sev,
    count: findings.filter((f) => f.severity === sev).length,
  })).filter((c) => c.count > 0);

  if (counts.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {counts.map(({ sev, count }) => (
        <span
          key={sev}
          className={clsx(
            "flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
            SEVERITY_STYLE[sev].border,
            SEVERITY_STYLE[sev].text
          )}
        >
          <span className={clsx("h-1.5 w-1.5 rounded-full", SEVERITY_STYLE[sev].dot)} />
          {count} {sev}
        </span>
      ))}
    </div>
  );
}

export function FindingsList({
  findings,
  onJumpToLine,
}: {
  findings: Finding[];
  onJumpToLine?: (line: number) => void;
}) {
  if (findings.length === 0) {
    return (
      <div className="rounded-xl2 border border-dashed border-ink-border p-8 text-center text-sm text-text-muted">
        No findings to show yet — run a review to see results here.
      </div>
    );
  }

  const sorted = [...findings].sort(
    (a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)
  );

  return (
    <ul className="flex flex-col gap-2">
      {sorted.map((finding, idx) => {
        const style = SEVERITY_STYLE[finding.severity];
        return (
          <li
            key={idx}
            className={clsx(
              "animate-slide-up rounded-xl2 border bg-ink-800/40 p-4 transition-colors",
              style.border
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <span className={clsx("h-2 w-2 shrink-0 rounded-full", style.dot)} />
                <h4 className="text-sm font-semibold text-text-primary">{finding.title}</h4>
              </div>
              <div className="flex shrink-0 items-center gap-2 text-[11px] uppercase tracking-wide text-text-muted">
                <span>{CATEGORY_LABEL[finding.category] ?? finding.category}</span>
                {finding.line && (
                  <button
                    onClick={() => onJumpToLine?.(finding.line as number)}
                    className="rounded-md border border-ink-border bg-ink-700 px-1.5 py-0.5 font-mono text-signal-teal hover:bg-ink-600"
                  >
                    L{finding.line}
                  </button>
                )}
              </div>
            </div>
            <p className="mt-2 pl-4 text-sm leading-relaxed text-text-secondary">{finding.description}</p>
          </li>
        );
      })}
    </ul>
  );
}
