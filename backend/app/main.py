from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .core.config import get_settings
from .core.logging import setup_logging
from .core.middleware import RequestContextMiddleware
from .core.rate_limit import RateLimitMiddleware, SlidingWindowRateLimiter
from .services.reviewer import ReviewOrchestrator

setup_logging()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.orchestrator = ReviewOrchestrator(settings)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Production-style AI code review API with OpenAI/Ollama routing, "
    "a deterministic static-analysis fallback, caching, and a per-provider circuit breaker.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(
    RateLimitMiddleware,
    limiter=SlidingWindowRateLimiter(
        max_requests=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
    ),
)
app.add_middleware(RequestContextMiddleware)

app.include_router(router)
