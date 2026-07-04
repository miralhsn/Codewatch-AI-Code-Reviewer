"use client";

import clsx from "clsx";
import type { CodeReviewResponse } from "@/lib/types";

const STAGES: { key: string; label: string }[] = [
  { key: "openai", label: "OpenAI" },
  { key: "ollama", label: "Ollama" },
  { key: "fallback", label: "Static rules" },
];

function stageStatus(stageKey: string, attempts: string[], usedModel: string) {
  const attempt = attempts.find((a) => a.startsWith(stageKey));
  if (stageKey === usedModel) return "used";
  if (!attempt) return "skipped";
  if (attempt.includes("circuit-open")) return "circuit-open";
  return "failed";
}

export function ProviderChain({ result }: { result: CodeReviewResponse }) {
  const attempts = result.metadata?.attempts ?? [result.used_model];
  const latency = result.metadata?.latency_ms;
  const cached = result.metadata?.cached ?? false;

  return (
    <div className="flex flex-wrap items-center gap-4 rounded-xl2 border border-ink-border bg-ink-800/60 px-5 py-3.5 shadow-panel">
      <div className="flex items-center gap-2">
        {STAGES.map((stage, idx) => {
          const status = stageStatus(stage.key, attempts, result.used_model);
          return (
            <div key={stage.key} className="flex items-center gap-2">
              <div className="flex items-center gap-1.5">
                <span
                  className={clsx("h-2 w-2 rounded-full", {
                    "bg-signal-teal": status === "used",
                    "bg-severity-critical": status === "failed",
                    "bg-text-muted/40": status === "skipped",
                    "bg-severity-high animate-pulse-dot": status === "circuit-open",
                  })}
                />
                <span
                  className={clsx("text-xs font-medium", {
                    "text-text-primary": status === "used",
                    "text-text-muted line-through decoration-severity-critical/60": status === "failed",
                    "text-text-muted/60": status === "skipped",
                    "text-severity-high": status === "circuit-open",
                  })}
                >
                  {stage.label}
                </span>
              </div>
              {idx < STAGES.length - 1 && <span className="text-text-muted/30">→</span>}
            </div>
          );
        })}
      </div>

      <div className="ml-auto flex items-center gap-4 text-xs text-text-secondary">
        {cached && (
          <span className="rounded-full border border-signal-violet/40 bg-signal-violet/10 px-2 py-0.5 font-medium text-signal-violet">
            cache hit
          </span>
        )}
        {typeof latency === "number" && <span className="font-mono">{latency.toFixed(0)}ms</span>}
        <ConfidenceMeter confidence={result.confidence} />
      </div>
    </div>
  );
}

function ConfidenceMeter({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color = pct >= 75 ? "bg-signal-teal" : pct >= 45 ? "bg-severity-high" : "bg-severity-critical";
  return (
    <div className="flex items-center gap-2">
      <span className="whitespace-nowrap">confidence {pct}%</span>
      <div className="h-1.5 w-16 overflow-hidden rounded-full bg-ink-600">
        <div className={clsx("h-full rounded-full", color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
