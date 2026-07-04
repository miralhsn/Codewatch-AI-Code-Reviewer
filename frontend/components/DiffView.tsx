"use client";

import clsx from "clsx";

export function DiffView({ diff }: { diff: string }) {
  if (!diff || diff.trim() === "No meaningful code changes detected.") {
    return (
      <div className="rounded-xl2 border border-dashed border-ink-border p-8 text-center text-sm text-text-muted">
        No meaningful code changes detected.
      </div>
    );
  }

  const lines = diff.split("\n");

  return (
    <div className="overflow-x-auto rounded-xl2 border border-ink-border bg-ink-900 font-mono text-[13px] leading-6">
      {lines.map((line, idx) => {
        const isAdd = line.startsWith("+") && !line.startsWith("+++");
        const isRemove = line.startsWith("-") && !line.startsWith("---");
        const isHeader = line.startsWith("@@") || line.startsWith("---") || line.startsWith("+++");
        return (
          <div
            key={idx}
            className={clsx("whitespace-pre px-4", {
              "bg-diff-addBg text-diff-add": isAdd,
              "bg-diff-removeBg text-diff-remove": isRemove,
              "text-text-muted": isHeader,
              "text-text-secondary": !isAdd && !isRemove && !isHeader,
            })}
          >
            {line || " "}
          </div>
        );
      })}
    </div>
  );
}
