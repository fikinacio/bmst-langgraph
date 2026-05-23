"""FastAPI application entry point.

Run with:
    uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

Endpoints:
    GET  /health                — liveness probe
    POST /webhook/whatsapp      — REVISOR approval reply handler (see webhooks.py)
    POST /run/manual            — trigger pipeline manually   [API key required]
    GET  /runs/{session_id}     — poll pipeline run state     [API key required]
    GET  /publications          — recent publication_log rows [API key required]
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from src.api.webhooks import router as webhooks_router
from src.config.settings import settings
from src.memory.supabase_client import SupabaseMemory
from src.orchestrator.graph import compiled_graph, run_graph, setup_checkpointer

logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger(__name__)

# Shared Supabase client — connected once in lifespan, reused per request
_supabase = SupabaseMemory()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("FastAPI lifespan: setting up connections")
    await setup_checkpointer()
    await _supabase.connect()
    logger.info("FastAPI lifespan: ready")
    yield
    logger.info("FastAPI lifespan: shutting down")


app = FastAPI(
    title="BMST Social Agents",
    version="0.1.0",
    description="Multi-agent social media pipeline for BMST.",
    lifespan=lifespan,
)


# ── Middleware ────────────────────────────────────────────────────────────────


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000)
    logger.info(
        "HTTP request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception",
        extra={"method": request.method, "path": request.url.path},
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# ── API key dependency ────────────────────────────────────────────────────────


def verify_api_key(request: Request) -> None:
    """Validate X-API-Key header for protected endpoints."""
    api_key = request.headers.get("X-API-Key", "")
    if not api_key or api_key != settings.bmst_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


# ── Public endpoints ──────────────────────────────────────────────────────────


@app.get("/health")
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok", "env": settings.app_env}


# ── Protected endpoints ───────────────────────────────────────────────────────


@app.post("/run/manual", dependencies=[Depends(verify_api_key)], status_code=202)
async def run_manual() -> dict:
    """Trigger the social media pipeline manually.

    Returns immediately with the session_id. The pipeline runs in a background
    task; poll GET /runs/{session_id} to track progress.
    """
    session_id = str(uuid.uuid4())
    logger.info("Manual run triggered", extra={"session_id": session_id})
    asyncio.create_task(run_graph(session_id))
    return {"session_id": session_id, "status": "started"}


@app.get("/runs/{session_id}", dependencies=[Depends(verify_api_key)])
async def get_run(session_id: str) -> dict:
    """Return the current checkpoint state for a pipeline run."""
    config = {"configurable": {"thread_id": session_id}}
    snapshot = await compiled_graph.aget_state(config)

    if snapshot is None or not snapshot.values:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id!r} not found",
        )

    state = snapshot.values

    def _serialize(obj):
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return str(obj)

    return {
        "session_id": session_id,
        "status": state.get("status"),
        "current_agent": state.get("current_agent"),
        "pending_approval": state.get("pending_approval"),
        "approval_decision": state.get("approval_decision"),
        "revision_count": state.get("revision_count"),
        "publication_results": [
            _serialize(r) for r in state.get("publication_results", [])
        ],
        "errors": state.get("errors", []),
    }


@app.get("/publications", dependencies=[Depends(verify_api_key)])
async def get_publications(limit: int = 20) -> list[dict]:
    """Return recent publication_log rows from Supabase, newest first."""
    return await _supabase.list_publications(limit=limit)


app.include_router(webhooks_router)
