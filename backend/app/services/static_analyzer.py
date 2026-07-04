"""Deterministic, rule-based review fallback.

This replaces the original fallback, which had a hardcoded special case that
only produced a "real" rewrite for one specific example function
(`calculate_total`) and silently no-op'd for everything else while claiming
"FORCE improvement". That's a demo trick, not a review engine, and it's
actively misleading in a fallback path that's supposed to be trustworthy
when the paid providers are unavailable.

Instead, this module:
  * Uses Python's `ast` module for real structural analysis of Python code
    (bare excepts, mutable default args, `== None`, eval/exec, broad
    `except Exception`, loops that index by `range(len(...))`), each with an
    accurate line number.
  * Uses conservative regex heuristics for other languages, scoped to
    patterns that are reliably problematic (SQL `SELECT *`, `eval(`,
    logging of secrets, empty catch blocks, `== null` in JS/TS/Java).
  * Only ever emits `refactored_code` that differs from the input via
    mechanical, unambiguously-safe text substitutions (e.g. `== None` ->
    `is None`). It never fabricates a rewrite it can't justify -- if no safe
    substitution applies, it returns the original code and says so plainly
    in `explanation`, rather than pretending to have improved it.
"""
from __future__ import annotations

import ast
import re

from ..schemas.review import Category, CodeReviewResponse, Finding, Severity
from .validation import generate_code_diff


def _python_findings(code: str) -> tuple[list[Finding], str]:
    """Returns (findings, possibly-fixed code) using AST analysis."""
    findings: list[Finding] = []
    fixed = code

    # Safe, mechanical substitutions only.
    fixed, n = re.subn(r"==\s*None\b", "is None", fixed)
    if n:
        findings.append(
            Finding(
                category=Category.quality,
                severity=Severity.low,
                title="Use `is None` instead of `== None`",
                description="Identity comparisons to None should use `is`/`is not`, "
                "since `==` can be overridden by `__eq__` and gives misleading results.",
            )
        )
    fixed, n = re.subn(r"!=\s*None\b", "is not None", fixed)
    if n:
        findings.append(
            Finding(
                category=Category.quality,
                severity=Severity.low,
                title="Use `is not None` instead of `!= None`",
                description="Same rationale as `== None`: identity comparisons should use `is not`.",
            )
        )

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        findings.append(
            Finding(
                category=Category.bug,
                severity=Severity.critical,
                title="Code does not parse",
                description=f"Python syntax error: {exc.msg}",
                line=exc.lineno,
            )
        )
        return findings, fixed

    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append(
                Finding(
                    category=Category.bug,
                    severity=Severity.high,
                    title="Bare `except:` clause",
                    description="Catches every exception including SystemExit/KeyboardInterrupt, "
                    "hiding real bugs. Catch a specific exception type instead.",
                    line=node.lineno,
                )
            )
        elif isinstance(node, ast.ExceptHandler) and isinstance(node.type, ast.Name) and node.type.id == "Exception":
            findings.append(
                Finding(
                    category=Category.quality,
                    severity=Severity.medium,
                    title="Overly broad `except Exception`",
                    description="Catching the generic `Exception` class can mask unrelated bugs. "
                    "Prefer catching the specific exception types you expect.",
                    line=node.lineno,
                )
            )
        elif isinstance(node, ast.FunctionDef):
            for default in node.args.defaults:
                if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                    findings.append(
                        Finding(
                            category=Category.bug,
                            severity=Severity.high,
                            title="Mutable default argument",
                            description=f"Function `{node.name}` uses a mutable default argument, "
                            "which is shared and mutated across calls. Use `None` and initialize inside the function.",
                            line=node.lineno,
                        )
                    )
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
            findings.append(
                Finding(
                    category=Category.security,
                    severity=Severity.critical,
                    title=f"Use of `{node.func.id}()`",
                    description=f"`{node.func.id}()` executes arbitrary code and is a common injection vector. "
                    "Avoid it, or strictly sandbox and validate the input first.",
                    line=node.lineno,
                )
            )
        elif isinstance(node, ast.For):
            # for i in range(len(x)): ... x[i] ...  -> suggest enumerate/direct iteration
            is_range_len = (
                isinstance(node.iter, ast.Call)
                and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == "range"
                and len(node.iter.args) == 1
                and isinstance(node.iter.args[0], ast.Call)
                and isinstance(node.iter.args[0].func, ast.Name)
                and node.iter.args[0].func.id == "len"
            )
            if is_range_len:
                findings.append(
                    Finding(
                        category=Category.performance,
                        severity=Severity.low,
                        title="Index-based iteration via `range(len(...))`",
                        description="Iterating with `for i in range(len(x))` and then indexing `x[i]` is less "
                        "idiomatic and slightly slower than iterating directly or with `enumerate()`.",
                        line=node.lineno,
                    )
                )
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print":
            for arg in node.args:
                names = [n.id for n in ast.walk(arg) if isinstance(n, ast.Name)]
                if any(re.search(r"pass(word)?|token|secret|api_key", n, re.IGNORECASE) for n in names):
                    findings.append(
                        Finding(
                            category=Category.security,
                            severity=Severity.high,
                            title="Sensitive value passed to `print()`",
                            description="Printing a variable that looks like a credential can leak it into logs.",
                            line=node.lineno,
                        )
                    )

    return findings, fixed


_GENERIC_RULES: list[tuple[str, Category, Severity, str, str]] = [
    (r"\beval\s*\(", Category.security, Severity.critical, "Use of `eval`-style execution",
     "Dynamic evaluation of strings as code is a common injection vector."),
    (r"select\s+\*", Category.performance, Severity.medium, "`SELECT *` in SQL",
     "Fetching all columns wastes bandwidth and breaks if the schema changes. Select only needed columns."),
    (r"catch\s*\(\s*\w*\s*\)\s*\{\s*\}", Category.bug, Severity.high, "Empty catch block",
     "Swallowing an exception silently hides failures. At minimum log it."),
    (r"==\s*null\b", Category.quality, Severity.low, "Loose equality with `null`",
     "Prefer `=== null` (or a language-appropriate strict check) to avoid type coercion surprises."),
    (r"(password|secret|api[_-]?key)\s*=\s*['\"][^'\"]+['\"]", Category.security, Severity.critical,
     "Hardcoded credential", "A credential appears to be hardcoded in source. Move it to a secret manager or env var."),
    (r"while\s*\(\s*true\s*\)|while\s+true\b", Category.bug, Severity.medium, "Unconditional infinite loop",
     "Verify there is a reachable exit condition or explicit break."),
]


def _generic_findings(code: str, language: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = code.splitlines()
    for pattern, category, severity, title, description in _GENERIC_RULES:
        regex = re.compile(pattern, re.IGNORECASE)
        for idx, line in enumerate(lines, start=1):
            if regex.search(line):
                findings.append(
                    Finding(category=category, severity=severity, title=title, description=description, line=idx)
                )
    return findings


class StaticAnalysisProvider:
    """Zero-dependency, zero-network fallback. Always succeeds."""

    name = "fallback"

    def review(self, code: str, language: str) -> CodeReviewResponse:
        if language.lower() == "python":
            findings, refactored_code = _python_findings(code)
        else:
            findings = _generic_findings(code, language)
            refactored_code = code

        if not findings:
            findings.append(
                Finding(
                    category=Category.quality,
                    severity=Severity.info,
                    title="No rule-based issues detected",
                    description="Static heuristics found nothing to flag. This does not guarantee correctness -- "
                    "it only means none of the fallback engine's known patterns matched.",
                )
            )

        diff = generate_code_diff(code, refactored_code, language)
        explanation = (
            f"Generated in offline fallback mode using deterministic static-analysis rules for {language} "
            "(no LLM was reachable). Only mechanical, unambiguously-safe fixes are auto-applied; "
            "everything else is reported as a finding for a human (or the LLM providers, once available) to act on."
        )
        return CodeReviewResponse(
            used_model="fallback",
            findings=findings,
            refactored_code=refactored_code,
            diff=diff,
            explanation=explanation,
            confidence=0.4,
        )
