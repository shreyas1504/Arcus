# ── backend/main.py ────────────────────────────────────────────────────────
# FastAPI entry point for the Arcus backend.
#
#   uvicorn backend.main:app --reload --port 8000

import logging
logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI  # type: ignore
from fastapi.concurrency import run_in_threadpool  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore

from backend.routers import portfolio, chat, news, adapter, research  # type: ignore

app = FastAPI(
    title="Arcus API",
    description="Institutional-grade portfolio risk analytics — REST API",
    version="2.0.0",
)

# CORS — allow dev servers + production deployments.
# Every origin the app is actually served from must be listed here, or the
# browser blocks the API call even when the backend is healthy.
ALLOWED_ORIGINS = [
    "http://localhost:8080",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://shreyas1504.github.io",   # GitHub Pages
    "https://arcus-insights.com",      # custom domain (Vercel)
    "https://www.arcus-insights.com",
]

# Vercel preview deployments get a generated *.vercel.app hostname.
ALLOWED_ORIGIN_REGEX = r"https://.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router)
app.include_router(chat.router)
app.include_router(news.router)
app.include_router(adapter.router)
app.include_router(research.router)


@app.on_event("startup")
async def warm_research_index():
    """Load BGE and the Chroma collection before the first enabled request."""
    if research.research_enabled():
        ready = await run_in_threadpool(research.get_qa_service().ready)
        if not ready:
            logging.getLogger(__name__).warning(
                "Arcus Research is enabled but its Chroma index is unavailable"
            )


@app.get("/")
async def root():
    return {"name": "Arcus API", "version": "2.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
