from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Severity(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    info = "info"


class Category(str, Enum):
    bug = "bug"
    security = "security"
    performance = "performance"
    quality = "quality"


class Finding(BaseModel):
    """A single, specific review comment.

    Structuring findings as objects (instead of four loose string lists like
    the original API) lets the frontend sort/filter by severity, jump to a
    line number, and render a category badge -- none of which is possible
    once everything is a flat string.
    """

    category: Category
    severity: Severity
    title: str = Field(..., min_length=1, max_length=120)
    description: str = Field(..., min_length=1)
    line: Optional[int] = Field(default=None, ge=1, description="1-indexed line number, if applicable")


class CodeReviewRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Source code to review")
    language: str = Field(..., min_length=1, description="Programming language name")
    prefer_provider: Optional[Literal["openai", "ollama"]] = Field(
        default=None,
        description="Optional hint to try this provider first; the router still falls back on failure.",
    )

    @field_validator("language")
    @classmethod
    def normalize_language(cls, value: str) -> str:
        return value.strip().lower()


class ReviewMetadata(BaseModel):
    request_id: str
    latency_ms: float
    cached: bool = False
    attempts: List[str] = Field(default_factory=list)


class CodeReviewResponse(BaseModel):
    used_model: Literal["openai", "ollama", "fallback"]
    findings: List[Finding] = Field(default_factory=list)
    refactored_code: str = ""
    diff: str = ""
    explanation: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: Optional[ReviewMetadata] = None

    @property
    def bugs(self) -> List[Finding]:
        return [f for f in self.findings if f.category == Category.bug]

    @property
    def security_risks(self) -> List[Finding]:
        return [f for f in self.findings if f.category == Category.security]

    @property
    def performance_improvements(self) -> List[Finding]:
        return [f for f in self.findings if f.category == Category.performance]

    @property
    def code_quality_issues(self) -> List[Finding]:
        return [f for f in self.findings if f.category == Category.quality]
