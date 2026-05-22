"""FastAPI application entry point.

Run with:
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

Endpoints:
    GET  /health             — liveness probe
    POST /webhook/whatsapp   — REVISOR approval reply handler (see webhooks.py)
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.webhooks import router as webhooks_router
from src.config.settings import settings
from src.orchestrator.graph import setup_checkpointer

logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the Redis checkpointer indices at boot.

    setup_checkpointer is idempotent. Doing it here surfaces Redis
    connectivity issues at process startup rather than on the first
    pipeline run or webhook.
    """
    logger.info("FastAPI lifespan: setting up Redis checkpointer indices")
    await setup_checkpointer()
    logger.info("FastAPI lifespan: ready")
    yield
    logger.info("FastAPI lifespan: shutting down")


app = FastAPI(
    title="BMST Social Agents",
    version="0.1.0",
    description="Multi-agent social media pipeline for BMST.",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "env": settings.app_env}


app.include_router(webhooks_router)
