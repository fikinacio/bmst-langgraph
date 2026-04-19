"""
BMST Agents — FastAPI entry point.

Exposes all agents as HTTP endpoints consumed by n8n, Evolution API webhooks,
and the Telegram bot callback handler.

Checkpointer strategy
---------------------
A single checkpointer instance is created during the FastAPI lifespan and reused
by every request.  This is critical for the Telegram callback flow:

  1. /hunter/batch         → starts a HUNTER run with the checkpointer
  2. preparar_aprovacao    → calls interrupt(), serialising state to the checkpointer
  3. Telegram bot          → founder taps a button, Telegram calls /telegram/callback
  4. /telegram/callback    → resumes the graph using the SAME checkpointer

In production (APP_ENV=production) the checkpointer is a RedisSaver — state
survives app restarts between steps 2 and 4.
In all other environments a MemorySaver is used (suitable for local testing only).
"""
from __future__ import annotations

import asyncio
import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import time
from contextlib import asynccontextmanager
from datetime import date
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from agents.hunter.graph import get_hunter_graph
from agents.closer.graph import get_closer_graph
from agents.delivery.graph import get_delivery_graph
from agents.ledger.graph import get_ledger_graph
from agents.prospector.graph import get_prospector_graph
from api.dependencies import verify_api_key
from api.models import (
    CloserDiagnoseRequest,
    CloserProposeRequest,
    DeliveryStartRequest,
    DeliveryUpdateRequest,
    DeliveryWebhookRequest,
    HealthResponse,
    HunterBatchRequest,
    HunterWebhookRequest,
    LedgerCheckPaymentsRequest,
    LedgerInvoiceRequest,
    MetricsResponse,
    ProspectorRunRequest,
    TelegramCallbackRequest,
    WebhookResponse,
)
from core.redis_client import (
    get_checkpointer,
    get_hunter_lock,
    hash_message,
    is_duplicate,
    mark_sent,
    release_hunter_lock,
)
from core.settings import settings

logger = logging.getLogger(__name__)

# ── Checkpointer singleton ────────────────────────────────────────────────────
# Initialised in lifespan() and referenced by endpoint handlers.
_checkpointer: Any = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _checkpointer
    if settings.APP_ENV == "production":
        _checkpointer = get_checkpointer()   # RedisSaver — state survives restarts
        logger.info("Checkpointer: RedisSaver (production)")
    else:
        _checkpointer = MemorySaver()        # In-memory — suitable for local dev only
        logger.info("Checkpointer: MemorySaver (development)")
    logger.info("bmst-agents starting up (env=%s)", settings.APP_ENV)
    yield
    logger.info("bmst-agents shutting down.")


# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(
    title="BMST Agents API",
    description="Multi-agent AI system for BMST Angola",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health / metrics ─────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health():
    """
    Check connectivity to all external services.

    Always returns HTTP 200 — callers should inspect the `status` field.
    Each service check has a 5-second timeout to avoid blocking the endpoint.
    """
    services: dict[str, str] = {}

    async def _check_redis() -> str:
        try:
            from core.redis_client import get_redis
            await asyncio.to_thread(get_redis().ping)
            return "ok"
        except Exception as exc:
            logger.warning("Health check Redis failed: %s", exc)
            return "error"

    async def _check_supabase() -> str:
        try:
            from core.memory import get_lead
            await asyncio.to_thread(get_lead, "+244000000000")
            return "ok"
        except Exception as exc:
            logger.warning("Health check Supabase failed: %s", exc)
            return "error"

    async def _check_evolution() -> str:
        try:
            import os
            import httpx
            base_url = os.environ.get("EVOLUTION_API_URL", "http://localhost:8080")
            api_key  = os.environ.get("EVOLUTION_API_KEY", "")
            instance = os.environ.get("EVOLUTION_INSTANCE", "bmst")
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0), follow_redirects=True) as client:
                resp = await client.get(
                    f"{base_url}/instance/connectionState/{instance}",
                    headers={"apikey": api_key},
                )
                resp.raise_for_status()
            return "ok"
        except Exception as exc:
            logger.warning("Health check Evolution failed: %s", exc)
            return "error"

    async def _check_sheets() -> str:
        try:
            import os
            from core.sheets_client import get_pending_leads
            sheet_id = os.environ.get("GOOGLE_SHEETS_ID", "")
            if not sheet_id:
                return "error"
            await get_pending_leads(sheet_id)
            return "ok"
        except Exception as exc:
            logger.warning("Health check Sheets failed: %s", exc)
            return "error"

    results = await asyncio.gather(
        asyncio.wait_for(_check_redis(),    timeout=5),
        asyncio.wait_for(_check_supabase(), timeout=5),
        asyncio.wait_for(_check_evolution(), timeout=5),
        asyncio.wait_for(_check_sheets(),   timeout=20),
        return_exceptions=True,
    )

    labels = ["redis", "supabase", "evolution", "sheets"]
    for label, result in zip(labels, results):
        services[label] = result if isinstance(result, str) else "error"

    overall = "ok" if all(v == "ok" for v in services.values()) else "degraded"
    return HealthResponse(status=overall, services=services)


@app.get("/metrics", response_model=MetricsResponse, tags=["system"],
         dependencies=[Depends(verify_api_key)])
async def metrics():
    """Return operational aggregates from Supabase."""
    from core.memory import get_lead  # noqa: F401 — import triggers client init check

    try:
        from core.settings import settings as s
        from supabase import create_client

        client = create_client(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)

        # Total leads
        total_result = await asyncio.to_thread(
            lambda: client.table("deals").select("id", count="exact").execute()
        )
        leads_total = total_result.count or 0

        # Leads updated today
        from datetime import date
        today = date.today().isoformat()
        hoje_result = await asyncio.to_thread(
            lambda: client.table("deals")
            .select("id", count="exact")
            .gte("updated_at", today)
            .execute()
        )
        leads_hoje = hoje_result.count or 0

        # Messages saved today
        msgs_result = await asyncio.to_thread(
            lambda: client.table("mensagens")
            .select("id", count="exact")
            .gte("timestamp", today)
            .execute()
        )
        mensagens_hoje = msgs_result.count or 0

        # Sent messages (direcao=assistant) today
        sent_result = await asyncio.to_thread(
            lambda: client.table("mensagens")
            .select("id", count="exact")
            .eq("direcao", "assistant")
            .gte("timestamp", today)
            .execute()
        )
        mensagens_enviadas_hoje = sent_result.count or 0

        return MetricsResponse(
            leads_total=leads_total,
            leads_hoje=leads_hoje,
            mensagens_hoje=mensagens_hoje,
            mensagens_enviadas_hoje=mensagens_enviadas_hoje,
        )

    except Exception as exc:
        logger.error("metrics() failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not retrieve metrics from Supabase.",
        )


# ── HUNTER ───────────────────────────────────────────────────────────────────

async def _run_hunter_batch(request: HunterBatchRequest, checkpointer: Any) -> None:
    """
    Background task: load leads from Google Sheets and run the HUNTER graph.

    The checkpointer is passed in from the lifespan singleton so that any
    interrupted graph can be resumed by the Telegram callback endpoint.
    """
    start = time.monotonic()
    try:
        from core.sheets_client import get_pending_leads

        sheet_id = request.sheet_id or settings.GOOGLE_SHEETS_ID
        leads = await get_pending_leads(sheet_id=sheet_id, max_leads=request.max_leads)
        if not leads:
            logger.info("HUNTER batch: no pending leads found.")
            return

        thread_id = f"hunter-batch-{int(time.time())}"
        initial_state = {
            "leads_pendentes":  leads,
            "leads_processados": 0,
            "mensagens_enviadas": 0,
            "erros": [],
        }

        graph = get_hunter_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        await graph.ainvoke(initial_state, config)

        elapsed = time.monotonic() - start
        logger.info(
            "HUNTER batch completed in %.1fs — thread_id=%s", elapsed, thread_id
        )
    except Exception as exc:
        logger.error("HUNTER batch failed: %s", exc)
    finally:
        release_hunter_lock()


@app.post(
    "/hunter/batch",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["hunter"],
    dependencies=[Depends(verify_api_key)],
)
async def hunter_batch(request: HunterBatchRequest, background_tasks: BackgroundTasks):
    """
    Trigger a HUNTER batch run against Google Sheets.

    Returns 202 immediately.  The batch runs in the background.
    Returns 409 if a batch is already running.
    """
    if not get_hunter_lock():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A HUNTER batch is already running. Try again later.",
        )
    background_tasks.add_task(_run_hunter_batch, request, _checkpointer)
    return {"message": f"HUNTER batch started (max_leads={request.max_leads})."}


@app.post("/hunter/webhook", response_model=WebhookResponse, tags=["hunter"])
async def hunter_webhook(request: HunterWebhookRequest):
    """
    Receive an inbound WhatsApp message forwarded by Evolution API.

    Performs deduplication via Redis before persisting to Supabase.
    Returns 200 even for duplicates (idempotent).
    """
    from core.memory import save_message, upsert_lead

    msg_hash = hash_message(request.message)

    if is_duplicate(request.phone, msg_hash):
        logger.info("Duplicate message ignored: phone=%s hash=%s", request.phone, msg_hash)
        return WebhookResponse(success=True, action="ignored_duplicate")

    mark_sent(request.phone, msg_hash)

    # Persist lead (upsert) and the inbound message
    await asyncio.to_thread(upsert_lead, {"phone": request.phone})
    await asyncio.to_thread(
        save_message,
        request.phone,
        "user",
        request.message,
        "hunter",
    )

    return WebhookResponse(success=True, action="queued")


# ── TELEGRAM CALLBACK ─────────────────────────────────────────────────────────

@app.post("/telegram/callback", response_model=WebhookResponse, tags=["telegram"])
async def telegram_callback(request: TelegramCallbackRequest):
    """
    Resume an interrupted HUNTER graph after the founder responds on Telegram.

    Flow:
      1. Telegram calls this endpoint when the founder taps Aprovar / Editar / Rejeitar.
      2. We answer the callback query immediately (Telegram requires < 10 seconds).
      3. We build the resume payload based on the action.
      4. We resume the LangGraph thread via Command(resume=...).

    The thread_id embedded in the callback_data identifies which HUNTER run to resume.
    """
    from core.telegram_client import answer_callback_query

    # Step 1 — acknowledge the callback to Telegram immediately
    try:
        await answer_callback_query(
            callback_query_id=request.callback_query_id,
            text="A processar...",
        )
    except Exception as exc:
        # Non-fatal — Telegram will show a loading indicator but the resume still works
        logger.warning("answer_callback_query failed: %s", exc)

    # Step 2 — build the resume payload
    if request.data == "aprovar":
        resume_payload = {"aprovado": True, "texto_editado": None}
    elif request.data == "editar":
        resume_payload = {"aprovado": True, "texto_editado": request.edited_text}
    else:  # rejeitar
        resume_payload = {"aprovado": False, "texto_editado": None}

    # Step 3 — resume the interrupted graph
    # The thread_id prefix identifies which agent graph owns this thread:
    #   "hunter-*"  → HUNTER graph
    #   "closer-*"  → CLOSER graph
    try:
        checkpointer = get_checkpointer()
        tid = request.thread_id
        if tid.startswith("closer-"):
            graph = get_closer_graph(checkpointer=checkpointer)
        elif tid.startswith("delivery-"):
            graph = get_delivery_graph(checkpointer=checkpointer)
        elif tid.startswith("ledger-"):
            graph = get_ledger_graph(checkpointer=checkpointer)
        else:
            graph = get_hunter_graph(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": tid}}
        await graph.ainvoke(Command(resume=resume_payload), config)
    except Exception as exc:
        logger.error(
            "telegram_callback: failed to resume thread_id=%s — %s",
            request.thread_id, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume graph thread: {exc}",
        )

    return WebhookResponse(
        success=True,
        action=request.data,
        thread_id=request.thread_id,
    )


# ── CLOSER ────────────────────────────────────────────────────────────────────

async def _start_closer_run(request: CloserDiagnoseRequest, checkpointer: Any) -> None:
    """
    Background task: start the CLOSER graph for a qualified lead.

    The CLOSER is a conversational agent — it sends a first diagnostic question,
    then pauses (interrupt) waiting for the prospect's WhatsApp reply.
    Replies arrive at /closer/webhook and resume the graph.
    """
    phone     = request.phone
    thread_id = f"closer-{phone}"

    initial_state = {
        "phone":             phone,
        "empresa":           request.empresa,
        "sector":            request.sector,
        "segmento":          request.segmento,
        "responsavel":       request.responsavel,
        "historico_conversa": request.historico,
        "perguntas_feitas":  [],
        "respostas_cliente": [],
        "diagnostico_completo": False,
        "problema_identificado": None,
        "servico_recomendado": None,
        "rascunho_proposta": None,
        "proposta_aprovada": None,
        "edicoes_fundador":  None,
        "pdf_url":           None,
        "proposta_enviada":  False,
        "followup_dia":      0,
        "proxima_acao":      None,
        "erro":              None,
        # REVISOR shared fields (initialised to safe defaults)
        "texto_original":       None,
        "texto_corrigido":      None,
        "status":               "pendente",
        "problemas_encontrados": [],
        "auto_correcoes":       [],
        "qualidade_estimada":   None,
        "aprovacao_fundador":   None,
        "motivo_escalonamento": None,
        "_revisor_contexto":    {},
        "lead_id":              phone,
        # Internal cache fields
        "_solucao_cache":                  None,
        "_texto_apresentacao_final":       None,
        "_revisao_notas_apresentacao":     None,
        "_objecao_detectada":              None,
        "_classificacao_proposta":         None,
    }

    try:
        graph  = get_closer_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        await graph.ainvoke(initial_state, config)
    except Exception as exc:
        logger.error("CLOSER start failed (phone=%s): %s", phone, exc)


@app.post(
    "/closer/diagnose",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["closer"],
    dependencies=[Depends(verify_api_key)],
)
async def closer_diagnose(request: CloserDiagnoseRequest, background_tasks: BackgroundTasks):
    """
    Start a CLOSER conversational run for a lead passed from HUNTER.

    Launches the full CLOSER pipeline in the background (diagnostic → solution →
    presentation → proposal → follow-up).  Returns 202 immediately.

    The CLOSER pauses after each WhatsApp message, waiting for the prospect's
    reply via /closer/webhook.  Founder approvals arrive via /telegram/callback.
    """
    background_tasks.add_task(_start_closer_run, request, _checkpointer)
    return {"message": f"CLOSER started for {request.phone} ({request.empresa})."}


@app.post("/closer/webhook", response_model=WebhookResponse, tags=["closer"])
async def closer_webhook(request: HunterWebhookRequest):
    """
    Receive a WhatsApp reply from a prospect and resume the CLOSER graph.

    Evolution API calls this endpoint when the prospect sends a message during
    an active CLOSER conversation.  The thread_id is derived from the phone number.
    """
    from core.memory import save_message as _save

    phone     = request.phone
    thread_id = f"closer-{phone}"

    # Deduplication check
    msg_hash = hash_message(request.message)
    if is_duplicate(phone, msg_hash):
        logger.info("CLOSER webhook: duplicate message ignored for phone=%s", phone)
        return WebhookResponse(success=True, action="ignored_duplicate")

    mark_sent(phone, msg_hash)
    await asyncio.to_thread(_save, phone, "user", request.message, "prospect")

    # Resume the interrupted CLOSER graph with the prospect's reply
    try:
        graph  = get_closer_graph(checkpointer=get_checkpointer())
        config = {"configurable": {"thread_id": thread_id}}
        await graph.ainvoke(
            Command(resume={"texto_prospect": request.message}),
            config,
        )
    except Exception as exc:
        logger.error("CLOSER webhook: resume failed (phone=%s): %s", phone, exc)
        # Return success anyway — the message is saved, retry is possible
        return WebhookResponse(success=False, action="resume_failed", thread_id=thread_id)

    return WebhookResponse(success=True, action="resumed", thread_id=thread_id)


@app.post("/closer/propose", tags=["closer"], dependencies=[Depends(verify_api_key)])
async def closer_propose(request: CloserProposeRequest):
    """
    Placeholder for direct proposal generation without the full diagnostic phase.
    Not yet implemented — use /closer/diagnose to start the full CLOSER pipeline.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Direct proposal generation not yet implemented. Use /closer/diagnose.",
    )


# ── DELIVERY ──────────────────────────────────────────────────────────────────

async def _run_delivery(
    request: DeliveryStartRequest | DeliveryUpdateRequest,
    checkpointer: Any,
) -> None:
    """
    Background task: run the DELIVERY graph for a project action.

    The thread_id is scoped to the project so Telegram callbacks and client
    WhatsApp replies can resume the correct graph run.
    """
    projecto_id = request.projecto_id
    thread_id   = f"delivery-{projecto_id}"

    if isinstance(request, DeliveryStartRequest):
        initial_state: dict = {
            "projecto_id":              projecto_id,
            "empresa":                  request.empresa,
            "servico":                  request.servico,
            "phone":                    request.phone,
            "responsavel":              request.responsavel,
            "segmento":                 request.segmento,
            "fase_atual":               "onboarding",
            "data_inicio":              date.today().isoformat(),
            "data_entrega_prevista":    request.data_entrega_prevista,
            "itens_concluidos":         [],
            "itens_pendentes":          [],
            "aguarda_aprovacao_fase":   False,
            "mensagem_actualizacao":    None,
            "feedback_cliente":         None,
            "notion_page_id":           None,
            "pagamento_final_confirmado": False,
            "proxima_acao":             "iniciar",
            "erro":                     None,
            # REVISOR shared fields
            "texto_original":           None,
            "texto_corrigido":          None,
            "status":                   "pendente",
            "problemas_encontrados":    [],
            "auto_correcoes":           [],
            "qualidade_estimada":       None,
            "aprovacao_fundador":       None,
            "motivo_escalonamento":     None,
            "_revisor_contexto":        {},
            "lead_id":                  projecto_id,
        }
    else:
        # DeliveryUpdateRequest — only provide the fields being updated
        initial_state = {
            "projecto_id":           projecto_id,
            "proxima_acao":          request.proxima_acao,
            "itens_concluidos":      request.itens_concluidos,
            "itens_pendentes":       request.itens_pendentes,
            # Reset REVISOR fields for this run
            "texto_original":        None,
            "texto_corrigido":       None,
            "status":                "pendente",
            "problemas_encontrados": [],
            "auto_correcoes":        [],
            "qualidade_estimada":    None,
            "aprovacao_fundador":    None,
            "motivo_escalonamento":  None,
            "_revisor_contexto":     {},
            "lead_id":               projecto_id,
        }

    try:
        graph  = get_delivery_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        await graph.ainvoke(initial_state, config)
        logger.info(
            "DELIVERY run completed — projecto_id=%s proxima_acao=%s",
            projecto_id, initial_state.get("proxima_acao"),
        )
    except Exception as exc:
        logger.error("DELIVERY run failed (projecto_id=%s): %s", projecto_id, exc)


@app.post(
    "/delivery/start",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["delivery"],
    dependencies=[Depends(verify_api_key)],
)
async def delivery_start(request: DeliveryStartRequest, background_tasks: BackgroundTasks):
    """
    Start the DELIVERY pipeline for a new project.

    Creates the Notion workspace, generates the onboarding message, sends it
    for founder review on Telegram, then delivers to the client via WhatsApp.
    Returns 202 immediately — the pipeline runs in the background.
    """
    background_tasks.add_task(_run_delivery, request, _checkpointer)
    return {"message": f"DELIVERY started for project {request.projecto_id}."}


@app.post(
    "/delivery/update",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["delivery"],
    dependencies=[Depends(verify_api_key)],
)
async def delivery_update(request: DeliveryUpdateRequest, background_tasks: BackgroundTasks):
    """
    Trigger a DELIVERY action on an active project.

    Actions: 'actualizar' (progress update), 'solicitar_aprovacao' (phase change),
    'encerrar' (final delivery).  Returns 202 immediately.
    """
    background_tasks.add_task(_run_delivery, request, _checkpointer)
    return {
        "message": (
            f"DELIVERY action '{request.proxima_acao}' queued "
            f"for project {request.projecto_id}."
        )
    }


@app.post("/delivery/webhook", response_model=WebhookResponse, tags=["delivery"])
async def delivery_webhook(request: DeliveryWebhookRequest):
    """
    Resume a DELIVERY graph paused waiting for a client phase-approval reply.

    Evolution API calls this endpoint when the client responds to a Template 12
    phase-approval message ('SIM' / 'NÃO').
    The thread_id identifies the correct paused DELIVERY run.
    """
    try:
        graph  = get_delivery_graph(checkpointer=get_checkpointer())
        config = {"configurable": {"thread_id": request.thread_id}}
        await graph.ainvoke(
            Command(resume={"aprovado": request.aprovado}),
            config,
        )
    except Exception as exc:
        logger.error(
            "delivery_webhook: failed to resume thread_id=%s — %s",
            request.thread_id, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resume delivery graph: {exc}",
        )

    return WebhookResponse(
        success=True, action="resumed", thread_id=request.thread_id
    )


# ── LEDGER ────────────────────────────────────────────────────────────────────

async def _run_ledger(request: LedgerInvoiceRequest, checkpointer: Any) -> None:
    """
    Background task: start the LEDGER billing pipeline for a new invoice.

    The proxima_acao is derived from tipo_factura so the graph dispatches
    to the correct invoice node (emitir_adiantamento vs emitir_saldo).
    """
    projecto_id  = request.projecto_id
    proxima_acao = (
        "emitir_adiantamento" if request.tipo_factura == "adiantamento" else "emitir_saldo"
    )
    thread_id = f"ledger-{projecto_id}-{request.tipo_factura}"

    initial_state: dict = {
        "projecto_id":              projecto_id,
        "empresa":                  request.empresa,
        "phone":                    request.phone,
        "responsavel":              request.responsavel,
        "servico":                  request.servico,
        "tipo_factura":             request.tipo_factura,
        "valor_aoa":                request.valor_aoa,
        "data_emissao":             None,
        "data_vencimento":          None,
        "estado_pagamento":         "pendente",
        "dias_atraso":              0,
        "invoice_ninja_id":         None,
        "mensagem_lembrete":        None,
        "lembrete_d3_enviado":      False,
        "lembrete_d7_enviado":      False,
        "lembrete_d14_enviado":     False,
        "fundador_alertado":        False,
        "pagamento_final_confirmado": False,
        "relatorio_mensal":         None,
        "proxima_acao":             proxima_acao,
        "erro":                     None,
        # REVISOR shared fields
        "texto_original":           None,
        "texto_corrigido":          None,
        "status":                   "pendente",
        "problemas_encontrados":    [],
        "auto_correcoes":           [],
        "qualidade_estimada":       None,
        "aprovacao_fundador":       None,
        "motivo_escalonamento":     None,
        "_revisor_contexto":        {},
        "lead_id":                  projecto_id,
    }

    try:
        graph  = get_ledger_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        await graph.ainvoke(initial_state, config)
        logger.info(
            "LEDGER invoice run completed — projecto_id=%s tipo=%s",
            projecto_id, request.tipo_factura,
        )
    except Exception as exc:
        logger.error("LEDGER invoice run failed (projecto_id=%s): %s", projecto_id, exc)


async def _run_ledger_verificar(
    request: LedgerCheckPaymentsRequest,
    checkpointer: Any,
) -> None:
    """Background task: run payment verification for a pending invoice."""
    projecto_id = request.projecto_id
    thread_id   = f"ledger-{projecto_id}-verificar"

    initial_state: dict = {
        "projecto_id":              projecto_id,
        "empresa":                  "",
        "phone":                    "",
        "responsavel":              "",
        "servico":                  "",
        "tipo_factura":             "adiantamento",
        "valor_aoa":                0,
        "data_emissao":             None,
        "data_vencimento":          None,
        "estado_pagamento":         "pendente",
        "dias_atraso":              0,
        "invoice_ninja_id":         request.invoice_ninja_id or None,
        "mensagem_lembrete":        None,
        "lembrete_d3_enviado":      False,
        "lembrete_d7_enviado":      False,
        "lembrete_d14_enviado":     False,
        "fundador_alertado":        False,
        "pagamento_final_confirmado": False,
        "relatorio_mensal":         None,
        "proxima_acao":             "verificar",
        "erro":                     None,
        # REVISOR shared fields
        "texto_original":           None,
        "texto_corrigido":          None,
        "status":                   "pendente",
        "problemas_encontrados":    [],
        "auto_correcoes":           [],
        "qualidade_estimada":       None,
        "aprovacao_fundador":       None,
        "motivo_escalonamento":     None,
        "_revisor_contexto":        {},
        "lead_id":                  projecto_id,
    }

    try:
        graph  = get_ledger_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        await graph.ainvoke(initial_state, config)
        logger.info("LEDGER verificar completed — projecto_id=%s", projecto_id)
    except Exception as exc:
        logger.error("LEDGER verificar failed (projecto_id=%s): %s", projecto_id, exc)


@app.post(
    "/ledger/invoice",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["ledger"],
    dependencies=[Depends(verify_api_key)],
)
async def ledger_invoice(request: LedgerInvoiceRequest, background_tasks: BackgroundTasks):
    """
    Issue an invoice (advance or final balance) and notify the client via WhatsApp.

    Creates the invoice in InvoiceNinja, generates a notification message,
    sends it for founder approval on Telegram, then delivers to the client.
    Returns 202 immediately — the pipeline runs in the background.
    """
    background_tasks.add_task(_run_ledger, request, _checkpointer)
    return {
        "message": (
            f"LEDGER invoice queued for project {request.projecto_id} "
            f"({request.tipo_factura})."
        )
    }


@app.post(
    "/ledger/check-payments",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["ledger"],
    dependencies=[Depends(verify_api_key)],
)
async def ledger_check_payments(
    request: LedgerCheckPaymentsRequest,
    background_tasks: BackgroundTasks,
):
    """
    Check payment status for an invoice and trigger reminders if overdue.

    Called daily at 09:30 by the n8n scheduler for all pending invoices.
    Returns 202 immediately — the check runs in the background.
    """
    background_tasks.add_task(_run_ledger_verificar, request, _checkpointer)
    return {
        "message": f"LEDGER payment check queued for project {request.projecto_id}."
    }


# ── PROSPECTOR ────────────────────────────────────────────────────────────────

async def _run_prospector(request: ProspectorRunRequest, checkpointer: Any) -> None:
    """
    Background task: run a PROSPECTOR session.

    The PROSPECTOR runs autonomously — no interrupts — and writes qualified leads
    directly to the Google Sheet, then sends a Telegram report.
    """
    thread_id = f"prospector-{int(time.time())}"
    initial_state = {
        "sector":        request.sector,
        "city":          request.city,
        "max_companies": request.max_companies,
        # All other fields are initialised by initialize_session
        "run_date":          "",
        "raw_companies":     [],
        "current_company":   None,
        "current_index":     0,
        "whatsapp_found":    None,
        "instagram_url":     None,
        "facebook_url":      None,
        "website_url":       None,
        "scraped_content":   None,
        "approach_notes":    None,
        "opportunity":       None,
        "recommended_service": None,
        "segment":             None,
        "estimated_value_aoa": None,
        "qualified":           None,
        "leads_written":       0,
        "leads_skipped":       0,
        "errors":              [],
        "next_action":         None,
        "error":               None,
    }

    start = time.monotonic()
    try:
        graph  = get_prospector_graph(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        await graph.ainvoke(initial_state, config)
        elapsed = time.monotonic() - start
        logger.info("PROSPECTOR session completed in %.1fs — thread_id=%s", elapsed, thread_id)
    except Exception as exc:
        logger.error("PROSPECTOR session failed: %s", exc)


@app.post(
    "/prospector/run",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["prospector"],
    dependencies=[Depends(verify_api_key)],
)
async def prospector_run(request: ProspectorRunRequest, background_tasks: BackgroundTasks):
    """
    Trigger a PROSPECTOR session to discover and enrich leads from Google Places.

    Normally called by the n8n cron at 07:00 UTC (08:00 Luanda) — one hour before
    the HUNTER processes the leads.  The sector is determined from the day-of-week
    calendar unless overridden in the request body.

    Returns 202 immediately — the session runs in the background.
    """
    background_tasks.add_task(_run_prospector, request, _checkpointer)
    return {
        "message": (
            f"PROSPECTOR session started "
            f"(sector={request.sector or 'auto'}, city={request.city}, "
            f"max={request.max_companies})."
        )
    }
