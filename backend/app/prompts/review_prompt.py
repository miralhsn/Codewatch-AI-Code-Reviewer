"""Prompt construction for LLM-backed review providers.

Key change from the original prompt: findings are now requested as
structured objects (category/severity/title/description/line) instead of
four separate free-text arrays. This does most of the "quality" work up
front, because the model has to commit to a severity and (where possible)
a line number rather than writing a vague paragraph.
"""
from textwrap import dedent

RESPONSE_SCHEMA = """
{
  "findings": [
    {
      "category": "bug | security | performance | quality",
      "severity": "critical | high | medium | low | info",
      "title": "short specific title, <= 12 words",
      "description": "1-3 sentences citing the exact code behavior",
      "line": 12
    }
  ],
  "refactored_code": "string",
  "diff": "string",
  "explanation": "string",
  "confidence": 0.0
}
""".strip()


def build_review_prompt(code: str, language: str, strict_retry: bool = False) -> str:
    retry_rule = (
        "- PREVIOUS RESPONSE WAS INVALID JSON OR FAILED SCHEMA VALIDATION.\n"
        "- Return ONLY a single valid JSON object. No prose, no markdown fences.\n"
        if strict_retry
        else ""
    )
    numbered_code = "\n".join(f"{i + 1:>4} | {line}" for i, line in enumerate(code.splitlines()))
    return dedent(
        f"""
        You are a principal software engineer reviewing a production pull request in {language}.
        Line numbers are shown as a prefix ("N | code") purely so you can cite exact lines in
        "line" fields -- do not include the prefix in "refactored_code".

        Return ONLY valid JSON matching this schema:
        {RESPONSE_SCHEMA}

        Process (perform internally, do not narrate it):
        1. Read the code and infer its intent.
        2. Identify concrete bugs, security risks, performance issues, and quality issues.
           Only report issues that are actually present -- never invent findings.
        3. Rewrite an improved, complete, runnable version of the code.
        4. Write a concise unified-diff-style summary of what changed and why.
        5. Write a short, factual explanation of the original code's behavior.

        STRICT RULES:
        - If there are truly no issues in a category, omit findings for that category.
        - Every finding must reference specific, real code behavior -- no generic filler
          like "improve readability" without saying what and where.
        - Include a "line" number whenever the finding maps to a specific line.
        - "refactored_code" must be complete and runnable, not a diff or snippet.
        - Preserve original functionality unless fixing a concrete, cited defect.
        - Never return refactored_code identical to the input unless it is already optimal;
          if so, still return it and explain why in "explanation".
        - "confidence" is your own calibrated confidence in this review, 0.0-1.0.
        - Output must start with '{{' and end with '}}'. No commentary outside the JSON.
        {retry_rule}
        Language: {language}
        Code (line-numbered for reference only):
        ```
        {numbered_code}
        ```
        """
    ).strip()


def build_provider_messages(code: str, language: str, strict_retry: bool = False) -> list[dict[str, str]]:
    prompt = build_review_prompt(code=code, language=language, strict_retry=strict_retry)
    return [
        {
            "role": "system",
            "content": (
                "You are a principal-level code reviewer for production systems. "
                "You output strict JSON only, with no surrounding text."
            ),
        },
        {"role": "user", "content": prompt},
    ]


def build_self_check_prompt(code: str, language: str, draft_json: str) -> str:
    return dedent(
        f"""
        Audit the following draft review for hallucinated findings.
        For each finding, verify it against the original code; drop any finding that
        does not correspond to real code behavior. Keep valid findings unchanged.
        Ensure "refactored_code" is complete, runnable, and actually improved.
        Return ONLY valid JSON using the exact same schema as the draft.

        Language: {language}
        Original code:
        ```{language}
        {code}
        ```

        Draft JSON to audit:
        {draft_json}
        """
    ).strip()
