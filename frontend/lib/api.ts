import type { CodeReviewRequest, CodeReviewResponse } from "./types";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function reviewCode(
  baseUrl: string,
  payload: CodeReviewRequest,
  signal?: AbortSignal
): Promise<CodeReviewResponse> {
  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    signal,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response body wasn't JSON; keep statusText
    }
    throw new ApiError(detail, response.status);
  }

  return response.json();
}
