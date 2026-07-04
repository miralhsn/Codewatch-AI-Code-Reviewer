export type Severity = "critical" | "high" | "medium" | "low" | "info";
export type Category = "bug" | "security" | "performance" | "quality";
export type UsedModel = "openai" | "ollama" | "fallback";

export interface Finding {
  category: Category;
  severity: Severity;
  title: string;
  description: string;
  line: number | null;
}

export interface ReviewMetadata {
  request_id: string;
  latency_ms: number;
  cached: boolean;
  attempts: string[];
}

export interface CodeReviewResponse {
  used_model: UsedModel;
  findings: Finding[];
  refactored_code: string;
  diff: string;
  explanation: string;
  confidence: number;
  metadata: ReviewMetadata | null;
}

export interface CodeReviewRequest {
  code: string;
  language: string;
  prefer_provider?: "openai" | "ollama" | null;
}

export const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

export const LANGUAGES = [
  "python",
  "javascript",
  "typescript",
  "java",
  "c++",
  "go",
  "rust",
  "sql",
  "other",
] as const;
