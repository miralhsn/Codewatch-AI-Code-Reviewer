"use client";

import Editor, { OnMount } from "@monaco-editor/react";

const MONACO_LANGUAGE_MAP: Record<string, string> = {
  "c++": "cpp",
  other: "plaintext",
};

export function CodeEditor({
  value,
  onChange,
  language,
  readOnly = false,
  highlightLine,
  height = "420px",
}: {
  value: string;
  onChange?: (value: string) => void;
  language: string;
  readOnly?: boolean;
  highlightLine?: number | null;
  height?: string;
}) {
  const monacoLanguage = MONACO_LANGUAGE_MAP[language] ?? language;

  const handleMount: OnMount = (editor, monaco) => {
    monaco.editor.defineTheme("codewatch-dark", {
      base: "vs-dark",
      inherit: true,
      rules: [],
      colors: {
        "editor.background": "#0B0E14",
        "editor.lineHighlightBackground": "#12161F",
        "editorLineNumber.foreground": "#3A4256",
        "editorLineNumber.activeForeground": "#9AA3B8",
        "editorGutter.background": "#0B0E14",
        "editor.selectionBackground": "#2DD4BF33",
      },
    });
    monaco.editor.setTheme("codewatch-dark");

    if (highlightLine) {
      editor.revealLineInCenter(highlightLine);
      editor.deltaDecorations(
        [],
        [
          {
            range: new monaco.Range(highlightLine, 1, highlightLine, 1),
            options: {
              isWholeLine: true,
              className: "highlighted-finding-line",
              linesDecorationsClassName: "highlighted-finding-gutter",
            },
          },
        ]
      );
    }
  };

  return (
    <div className="overflow-hidden rounded-xl2 border border-ink-border">
      <Editor
        height={height}
        language={monacoLanguage}
        value={value}
        onChange={(v) => onChange?.(v ?? "")}
        onMount={handleMount}
        theme="codewatch-dark"
        options={{
          readOnly,
          minimap: { enabled: false },
          fontFamily: "var(--font-jetbrains-mono)",
          fontSize: 13.5,
          lineHeight: 22,
          padding: { top: 16, bottom: 16 },
          scrollBeyondLastLine: false,
          renderLineHighlight: "all",
          smoothScrolling: true,
        }}
      />
    </div>
  );
}
