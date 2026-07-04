"use client";

import { LANGUAGES } from "@/lib/types";

export function LanguageSelect({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="rounded-lg border border-ink-border bg-ink-800 px-3 py-1.5 text-sm text-text-primary focus:border-signal-teal focus:outline-none"
    >
      {LANGUAGES.map((lang) => (
        <option key={lang} value={lang}>
          {lang}
        </option>
      ))}
    </select>
  );
}
