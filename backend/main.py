# ── backend/main.py ────────────────────────────────────────────────────────
# FastAPI entry point for the Arcus backend.
#
#   uvicorn backend.main:app --reload --port 8000

import logging
logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore

from backend.routers import portfolio, chat, news, adapter  # type: ignore

app = FastAPI(
    title="Arcus API",
    description="Institutional-grade portfolio risk analytics — REST API",
    version="2.0.0",
)

# CORS — allow dev servers + production GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:3000",
        "https://shreyas1504.github.io",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(portfolio.router)
app.include_router(chat.router)
app.include_router(news.router)
app.include_router(adapter.router)


@app.get("/")
async def root():
    return {"name": "Arcus API", "version": "2.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
