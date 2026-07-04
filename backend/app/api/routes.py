from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from ..core.exceptions import CodeTooLargeError
from ..core.logging import request_id_ctx
from ..schemas.review import CodeReviewRequest, CodeReviewResponse

router = APIRouter()


@router.get("/health", tags=["meta"])
def health_check(request: Request) -> dict:
    orchestrator = request.app.state.orchestrator
    return {
        "status": "ok",
        "cache": orchestrator.cache_stats(),
        "circuit_breakers": orchestrator.breaker_snapshot(),
    }


@router.post("/review", response_model=CodeReviewResponse, tags=["review"])
def review(payload: CodeReviewRequest, request: Request) -> CodeReviewResponse:
    code = payload.code.strip()
    language = payload.language.strip()

    if not code:
        raise HTTPException(status_code=400, detail="`code` cannot be empty.")
    if not language:
        raise HTTPException(status_code=400, detail="`language` cannot be empty.")

    orchestrator = request.app.state.orchestrator
    try:
        return orchestrator.review(
            code=code,
            language=language,
            prefer_provider=payload.prefer_provider,
            request_id=request_id_ctx.get(),
        )
    except CodeTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive last resort
        raise HTTPException(status_code=500, detail=f"Failed to review code: {exc}") from exc
