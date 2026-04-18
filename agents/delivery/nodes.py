# agents/delivery/nodes.py — DELIVERY agent node implementations
#
# Interrupt points:
#   - preparar_aprovacao_delivery  → founder reviews every outbound WA message (Telegram)
#   - solicitar_aprovacao_fase     → waits for client WhatsApp reply (phase approval)
#
# Graph entry is dispatched by proxima_acao:
#   "iniciar"             → iniciar_projecto
#   "actualizar"          → gerar_actualizacao
#   "solicitar_aprovacao" → solicitar_aprovacao_fase
#   "encerrar"            → encerrar_projecto

from __future__ import annotations

import asyncio
import json
import logging

import httpx
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from agents.delivery.state import DeliveryState
from agents.delivery.prompts import (
    ONBOARDING_PROMPT,
    ACTUALIZACAO_PROMPT,
    APROVACAO_FASE_PROMPT,
    ENCERRAMENTO_PROMPT,
    ActualizacaoSchema,
    FeedbackSchema,
)
from core.llm import create_json_message, create_message
from core.memory import save_message, update_lead_state, save_revisao
from core import evolution_client, telegram_client
from core.settings import settings

logger = logging.getLogger(__name__)
_AGENT = "delivery"


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _criar_pagina_notion(empresa: str, servico: str, projecto_id: str) -> str:
    """
    Create a project page in the Notion parent database.

    Returns the Notion page_id, or "" if Notion is not configured or the call fails.
    The page is pre-populated with the standard BMST project structure.
    """
    token = settings.NOTION_TOKEN
    db_id = settings.NOTION_DATABASE_ID

    if not token or not db_id:
        logger.warning("_criar_pagina_notion: Notion not configured — skipping")
        return ""

    page_body = {
        "parent": {"database_id": db_id},
        "icon": {"emoji": "📁"},
        "properties": {
            "Name": {
                "title": [{"text": {"content": f"{empresa} — {servico}"}}]
            },
        },
        "children": [
            _notion_heading(f"📋 Briefing — {empresa}"),
            _notion_callout("Fill in client briefing information here."),
            _notion_heading("📅 Timeline"),
            _notion_callout(f"Project ID: {projecto_id}"),
            _notion_heading("✅ Tasks"),
            _notion_heading("💬 Communications"),
            _notion_heading("📁 Files"),
            _notion_heading("💰 Financial"),
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.notion.com/v1/pages",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Notion-Version": "2022-06-28",
                    "Content-Type": "application/json",
                },
                json=page_body,
            )
            response.raise_for_status()
            page_id: str = response.json()["id"]
            logger.info("_criar_pagina_notion: created page %s for %s", page_id, empresa)
            return page_id
    except Exception as exc:
        logger.error("_criar_pagina_notion failed for %s: %s", empresa, exc)
        return ""


def _notion_heading(text: str) -> dict:
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def _notion_callout(text: str) -> dict:
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "icon": {"emoji": "ℹ️"},
        },
    }


def _format_update_message(responsavel: str, empresa: str, update: ActualizacaoSchema) -> str:
    """Format the progress update data into a natural WhatsApp message."""
    nome_curto = responsavel.split()[0] if responsavel else "bom dia"
    periodo = "tarde" if True else "manhã"   # could be time-based in production

    concluido_str = "\n".join(f"  ✅ {item}" for item in update.concluido_semana)
    em_curso_str  = "\n".join(f"  🔄 {item}" for item in update.em_curso)
    a_seguir_str  = "\n".join(f"  📅 {item}" for item in update.a_seguir)
    feedback_str  = f"\n💬 {update.pedido_feedback}" if update.pedido_feedback else ""

    return (
        f"Bom dia {nome_curto}!\n\n"
        f"Actualização do projecto *{empresa}*:\n\n"
        f"*Concluído esta semana:*\n{concluido_str}\n\n"
        f"*Em curso:*\n{em_curso_str}\n\n"
        f"*A seguir:*\n{a_seguir_str}"
        f"{feedback_str}\n\n"
        f"Fidel | BMST — Bisca+"
    )


# ── REVISOR bridge nodes ──────────────────────────────────────────────────────

async def preparar_para_revisor_delivery(
    state: DeliveryState,
    config: RunnableConfig,
) -> dict:
    """Bridge: populate REVISOR fields before the REVISOR pipeline runs."""
    thread_id = config["configurable"].get("thread_id", "")
    return {
        "status":                "pendente",
        "texto_corrigido":       None,
        "problemas_encontrados": [],
        "auto_correcoes":        [],
        "qualidade_estimada":    "alta",
        "aprovacao_fundador":    None,
        "motivo_escalonamento":  None,
        "_revisor_contexto": {
            "empresa":   state.get("empresa", ""),
            "segmento":  state.get("segmento", "B"),
            "canal":     "WhatsApp",
            "agente":    "DELIVERY",
            "thread_id": thread_id,
        },
        "lead_id": state.get("projecto_id", ""),
    }


async def preparar_aprovacao_delivery(
    state: DeliveryState,
    config: RunnableConfig,
) -> dict:
    """
    DELIVERY-specific founder approval node — mirrors CLOSER's pattern.

    Sends the REVISOR-approved (or corrected) text to the founder via Telegram,
    then interrupts until the founder taps Approve / Edit / Reject.
    """
    thread_id      = config["configurable"].get("thread_id", "")
    texto_proposto = state.get("texto_corrigido") or state.get("texto_original", "")
    is_escalado    = state.get("status") == "escalado"

    from agents.revisor.nodes import _format_revisao_notes
    revisao_notas = _format_revisao_notes(state, is_escalado)

    try:
        await save_revisao(
            lead_id=state.get("lead_id", state.get("projecto_id", "")),
            texto_original=state.get("texto_original", ""),
            texto_final=texto_proposto,
            status=state.get("status", "pendente"),
            notas=revisao_notas,
        )
    except Exception as exc:
        logger.warning("preparar_aprovacao_delivery: save_revisao failed: %s", exc)

    contexto = dict(state.get("_revisor_contexto") or {})
    message_id = await telegram_client.send_approval_request(
        mensagem_cliente=texto_proposto,
        contexto=contexto,
        revisao_notas=revisao_notas,
        thread_id=thread_id,
    )

    logger.info(
        "delivery.preparar_aprovacao: Telegram sent (id=%s), entering interrupt",
        message_id,
    )

    # ── INTERRUPT: founder reviews the outbound client message ─────────────────
    decisao: dict = interrupt({
        "fase":                "aguarda_aprovacao_mensagem",
        "telegram_message_id": message_id,
        "texto_proposto":      texto_proposto,
    })
    # ── RESUME POINT ─────────────────────────────────────────────────────────

    aprovado      = decisao.get("aprovado", False)
    texto_editado = decisao.get("texto_editado")

    return {
        "aprovacao_fundador": aprovado,
        "texto_corrigido":    texto_editado or texto_proposto,
        "status":             "aprovado" if aprovado else "rejeitado",
    }


async def processar_resultado_revisor_delivery(state: DeliveryState) -> dict:
    """Bridge: extract the final approved text for use by enviar_mensagem_delivery."""
    return {
        "mensagem_actualizacao": (
            state.get("texto_corrigido") or state.get("texto_original", "")
        ),
    }


# ── Node: enviar_mensagem_delivery ────────────────────────────────────────────

async def enviar_mensagem_delivery(state: DeliveryState) -> dict:
    """
    Send the founder-approved message to the client via WhatsApp.

    After sending, updates the lead state in Supabase.
    """
    if not state.get("aprovacao_fundador"):
        logger.info("delivery.enviar_mensagem_delivery: rejected by founder — not sending")
        return {"proxima_acao": "rejeitado"}

    phone  = state["phone"]
    texto  = state.get("mensagem_actualizacao") or state.get("texto_corrigido") or ""

    await evolution_client.send_text_message(phone, texto)
    await save_message(phone, "assistant", texto, _AGENT)
    await update_lead_state(phone, f"delivery_{state.get('fase_atual', 'em_curso')}", _AGENT)

    logger.info(
        "delivery.enviar_mensagem_delivery: sent to %s (fase=%s)",
        phone, state.get("fase_atual"),
    )
    return {}


# ── Node: iniciar_projecto ────────────────────────────────────────────────────

async def iniciar_projecto(state: DeliveryState) -> dict:
    """
    Project kickoff: create the Notion workspace and generate the onboarding message.

    The onboarding text is stored in texto_original and then routed through the
    REVISOR pipeline (preparar_para_revisor_delivery → avaliar → … → send).
    """
    empresa    = state["empresa"]
    servico    = state["servico"]
    projecto_id = state["projecto_id"]
    responsavel = state.get("responsavel", "")

    # Create Notion page (async, best-effort)
    notion_page_id = await _criar_pagina_notion(empresa, servico, projecto_id)

    # Generate natural onboarding message with Sonnet
    texto = await create_message(
        system=ONBOARDING_PROMPT,
        user=(
            f"Write the onboarding message for:\n"
            f"Company: {empresa}\n"
            f"Service: {servico}\n"
            f"Contact name: {responsavel or 'the client'}\n"
            f"Project start date: {state.get('data_inicio', 'today')}"
        ),
        model="sonnet",
        agent_name=_AGENT,
        node_name="iniciar_projecto",
    )

    logger.info("delivery.iniciar_projecto: onboarding text generated for %s", empresa)

    return {
        "notion_page_id": notion_page_id,
        "texto_original": texto.strip(),
        "fase_atual":     "onboarding",
    }


# ── Node: gerar_actualizacao ──────────────────────────────────────────────────

async def gerar_actualizacao(state: DeliveryState) -> dict:
    """
    Generate a structured project progress update (Template 11).

    Called 2x per week (Monday and Thursday at 10:00) by the n8n scheduler.
    The update is based on the current itens_concluidos and itens_pendentes.
    After generating text, routes through REVISOR before sending.
    """
    empresa         = state["empresa"]
    concluidos      = state.get("itens_concluidos") or []
    pendentes       = state.get("itens_pendentes") or []

    # Use LLM to generate a structured update (JSON)
    update = await create_json_message(
        system=ACTUALIZACAO_PROMPT,
        user=(
            f"Generate a project update for:\n"
            f"Company: {empresa}\n"
            f"Service: {state.get('servico', '')}\n"
            f"Current phase: {state.get('fase_atual', '—')}\n"
            f"Items completed: {json.dumps(concluidos, ensure_ascii=False)}\n"
            f"Items pending: {json.dumps(pendentes, ensure_ascii=False)}\n"
            f"Target delivery: {state.get('data_entrega_prevista', '—')}"
        ),
        schema=ActualizacaoSchema,
        model="haiku",   # structured extraction, not creative writing
        agent_name=_AGENT,
        node_name="gerar_actualizacao",
    )

    # Format into natural WhatsApp prose
    texto = _format_update_message(state.get("responsavel", ""), empresa, update)

    logger.info("delivery.gerar_actualizacao: update generated for %s", empresa)

    return {"texto_original": texto}


# ── Node: solicitar_aprovacao_fase ────────────────────────────────────────────

async def solicitar_aprovacao_fase(state: DeliveryState) -> dict:
    """
    Send a phase approval request to the client, then pause until they reply.

    The phase approval message (Template 12) is sent directly — no REVISOR
    needed as it is a fixed-format template request.

    Interrupt resumes via /delivery/webhook with Command(resume={"aprovado": bool}).
    """
    phone      = state["phone"]
    responsavel = state.get("responsavel", "cliente")
    nome_curto = responsavel.split()[0] if responsavel else "cliente"
    fase_atual = state.get("fase_atual", "a fase actual")

    # Map current phase to next phase label
    PROXIMA_FASE_MAP = {
        "onboarding":     "desenvolvimento",
        "desenvolvimento": "revisão",
        "revisao":        "entrega final",
        "entrega_final":  "conclusão",
    }
    proxima_fase = PROXIMA_FASE_MAP.get(fase_atual, "a próxima fase")

    # Generate the approval request (template-based, using Sonnet for naturalness)
    texto = await create_message(
        system=APROVACAO_FASE_PROMPT,
        user=(
            f"Write the phase approval request for:\n"
            f"Contact: {nome_curto}\n"
            f"Completed phase: {fase_atual}\n"
            f"Next phase: {proxima_fase}\n"
            f"Company: {state.get('empresa', '')}"
        ),
        model="haiku",
        agent_name=_AGENT,
        node_name="solicitar_aprovacao_fase",
    )

    await evolution_client.send_text_message(phone, texto.strip())
    await save_message(phone, "assistant", texto.strip(), _AGENT)

    logger.info(
        "delivery.solicitar_aprovacao_fase: request sent to %s (fase=%s)",
        phone, fase_atual,
    )

    # ── INTERRUPT: wait for client WhatsApp approval ──────────────────────────
    resposta = interrupt({"fase": "aguarda_aprovacao_fase", "fase_atual": fase_atual})
    # ── RESUME POINT ─────────────────────────────────────────────────────────

    texto_cliente = resposta.get("aprovado_texto") or resposta.get("texto_prospect", "")
    aprovado      = resposta.get("aprovado", False)

    await save_message(phone, "user", texto_cliente, "cliente")

    logger.info(
        "delivery.solicitar_aprovacao_fase: client response — aprovado=%s", aprovado
    )

    return {
        "aguarda_aprovacao_fase": False,
        "feedback_cliente":       texto_cliente,
        "proxima_acao":           "avancado" if aprovado else "rejeitado_cliente",
    }


# ── Node: registar_feedback ───────────────────────────────────────────────────

async def registar_feedback(state: DeliveryState) -> dict:
    """
    Parse and save client feedback (phase approval or satisfaction survey).

    Uses Haiku to extract structured data from the client's free-text response.
    """
    feedback_raw = state.get("feedback_cliente") or ""
    if not feedback_raw:
        return {}

    parsed = await create_json_message(
        system=(
            "Parse the client's WhatsApp response into structured feedback.\n"
            "Set aprovado=True if the message is a clear 'yes', 'sim', 'aprovado', "
            "or any positive affirmation.\n"
            "Respond with valid JSON only."
        ),
        user=f"Client response: {feedback_raw}",
        schema=FeedbackSchema,
        model="haiku",
        agent_name=_AGENT,
        node_name="registar_feedback",
    )

    # Persist to Supabase via save_revisao (reused as general notes store)
    try:
        await save_revisao(
            lead_id=state.get("projecto_id", state.get("phone", "")),
            texto_original=feedback_raw,
            texto_final=feedback_raw,
            status="aprovado" if parsed.aprovado else "rejeitado",
            notas=(
                f"nota={parsed.nota_satisfacao} | "
                f"comentario={parsed.comentario} | "
                f"recomenda={parsed.recomendaria}"
            ),
        )
    except Exception as exc:
        logger.warning("registar_feedback: save_revisao failed: %s", exc)

    logger.info(
        "delivery.registar_feedback: aprovado=%s nota=%s",
        parsed.aprovado, parsed.nota_satisfacao,
    )

    return {
        "feedback_cliente": feedback_raw,
        "aguarda_aprovacao_fase": False,
    }


# ── Node: encerrar_projecto ───────────────────────────────────────────────────

async def encerrar_projecto(state: DeliveryState) -> dict:
    """
    Generate the final delivery message, check payment status, and close the project.

    If final payment is not confirmed, alerts the founder and does NOT send
    access credentials (per the DELIVERY absolute rules).

    After sending, sets a Supabase flag so LEDGER knows to emit the final invoice.
    """
    phone    = state["phone"]
    empresa  = state["empresa"]

    # Guard: do not deliver if final payment not confirmed
    if not state.get("pagamento_final_confirmado"):
        msg = (
            f"⚠️ <b>DELIVERY — PAYMENT BLOCK</b>\n\n"
            f"Project: <b>{empresa} — {state.get('servico', '')}</b>\n"
            f"Problem: Project ready for delivery but final payment not confirmed.\n"
            f"Action: Confirm payment with LEDGER before releasing access."
        )
        try:
            await telegram_client.send_message(msg)
        except Exception as exc:
            logger.error("encerrar_projecto: Telegram alert failed: %s", exc)
        return {"proxima_acao": "bloqueado_pagamento"}

    # Generate the final delivery message with Sonnet
    entregaveis_str = "\n".join(
        f"• {item}" for item in (state.get("itens_concluidos") or ["[to be listed]"])
    )

    texto = await create_message(
        system=ENCERRAMENTO_PROMPT,
        user=(
            f"Write the final delivery message for:\n"
            f"Company: {empresa}\n"
            f"Service: {state.get('servico', '')}\n"
            f"Contact: {state.get('responsavel', 'the client')}\n"
            f"Deliverables:\n{entregaveis_str}"
        ),
        model="sonnet",
        agent_name=_AGENT,
        node_name="encerrar_projecto",
    )

    logger.info("delivery.encerrar_projecto: final message generated for %s", empresa)

    # Update project status in Supabase (signals LEDGER to process final payment)
    await update_lead_state(phone, "entrega_concluida", _AGENT)

    return {
        "fase_atual":     "concluido",
        "texto_original": texto.strip(),
    }
