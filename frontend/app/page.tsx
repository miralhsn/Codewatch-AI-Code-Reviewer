"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { CodeEditor } from "@/components/CodeEditor";
import { LanguageSelect } from "@/components/LanguageSelect";
import { ProviderChain } from "@/components/ProviderChain";
import { SeveritySummary, FindingsList } from "@/components/FindingsList";
import { DiffView } from "@/components/DiffView";
import { reviewCode, ApiError } from "@/lib/api";
import type { CodeReviewResponse } from "@/lib/types";

const EXAMPLE_CODE = `def calculate_total(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]["price"]
    print("total", total)
    return total
`;

type Tab = "findings" | "refactored" | "diff";

export default function Home() {
  const [code, setCode] = useState(EXAMPLE_CODE);
  const [language, setLanguage] = useState("python");
  const [apiBaseUrl, setApiBaseUrl] = useState(
    process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"
  );
  const [showSettings, setShowSettings] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<CodeReviewResponse | null>(null);
  const [tab, setTab] = useState<Tab>("findings");
  const [highlightLine, setHighlightLine] = useState<number | null>(null);

  async function handleReview() {
    if (!code.trim()) {
      setError("Paste some code before requesting a review.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await reviewCode(apiBaseUrl, { code, language });
      setResult(data);
      setTab("findings");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`${err.status}: ${err.message}`);
      } else {
        setError("Could not reach the review API. Is the backend running?");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-ink-900 bg-grid">
      <header className="border-b border-ink-border/60 bg-ink-900/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-signal-teal/10 font-display text-signal-teal">
              ⌁
            </div>
            <div>
              <h1 className="font-display text-lg font-semibold tracking-tight text-text-primary">
                Codewatch
              </h1>
              <p className="text-xs text-text-muted">Provider-resilient AI code review</p>
            </div>
          </div>
          <button
            onClick={() => setShowSettings((s) => !s)}
            className="rounded-lg border border-ink-border px-3 py-1.5 text-xs font-medium text-text-secondary hover:border-signal-teal/40 hover:text-signal-teal"
          >
            {showSettings ? "Hide settings" : "Settings"}
          </button>
        </div>
        <AnimatePresence>
          {showSettings && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden border-t border-ink-border/60"
            >
              <div className="mx-auto flex max-w-7xl items-center gap-3 px-6 py-3 text-sm">
                <label className="text-text-muted">Backend URL</label>
                <input
                  value={apiBaseUrl}
                  onChange={(e) => setApiBaseUrl(e.target.value)}
                  className="w-72 rounded-lg border border-ink-border bg-ink-800 px-3 py-1.5 font-mono text-xs text-text-primary focus:border-signal-teal focus:outline-none"
                />
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </header>

      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-6 px-6 py-8 lg:grid-cols-2">
        {/* Left: input */}
        <section className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <LanguageSelect value={language} onChange={setLanguage} />
            <button
              onClick={handleReview}
              disabled={loading}
              className="rounded-lg bg-signal-teal px-5 py-2 text-sm font-semibold text-ink-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Reviewing…" : "Review code"}
            </button>
          </div>
          <CodeEditor value={code} onChange={setCode} language={language} height="560px" />
          {error && (
            <div className="rounded-xl2 border border-severity-critical/30 bg-severity-critical/5 px-4 py-3 text-sm text-severity-critical">
              {error}
            </div>
          )}
        </section>

        {/* Right: results */}
        <section className="flex flex-col gap-4">
          {result ? (
            <>
              <ProviderChain result={result} />
              <SeveritySummary findings={result.findings} />

              <div className="flex gap-1 rounded-lg border border-ink-border bg-ink-800/60 p-1 text-sm">
                {(["findings", "refactored", "diff"] as Tab[]).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`flex-1 rounded-md px-3 py-1.5 font-medium capitalize transition ${
                      tab === t
                        ? "bg-ink-700 text-text-primary"
                        : "text-text-muted hover:text-text-secondary"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>

              <div className="min-h-0 flex-1">
                {tab === "findings" && (
                  <FindingsList findings={result.findings} onJumpToLine={setHighlightLine} />
                )}
                {tab === "refactored" && (
                  <CodeEditor
                    value={result.refactored_code}
                    language={language}
                    readOnly
                    height="480px"
                    highlightLine={highlightLine}
                  />
                )}
                {tab === "diff" && <DiffView diff={result.diff} />}
              </div>

              {result.explanation && (
                <div className="rounded-xl2 border border-ink-border bg-ink-800/40 p-4 text-sm leading-relaxed text-text-secondary">
                  <span className="mb-1 block text-xs font-semibold uppercase tracking-wide text-text-muted">
                    Explanation
                  </span>
                  {result.explanation}
                </div>
              )}
            </>
          ) : (
            <div className="flex h-full min-h-[400px] flex-col items-center justify-center gap-2 rounded-xl2 border border-dashed border-ink-border text-center text-text-muted">
              <p className="font-display text-base text-text-secondary">Nothing reviewed yet</p>
              <p className="max-w-xs text-sm">
                Paste code on the left and hit <span className="text-signal-teal">Review code</span> to see
                structured findings, a refactor, and a diff.
              </p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
