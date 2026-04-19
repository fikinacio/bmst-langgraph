# agents/revisor/nodes.py — REVISOR node implementations (shared by HUNTER and CLOSER)

from __future__ import annotations

import json
import logging

from langgraph.types import interrupt

from agents.revisor.state import RevisorState
from agents.revisor.prompts import (
    CHECKLIST_AVALIACAO_PROMPT,
    AUTO_CORRECAO_PROMPT,
    VERIFICAR_PERSONALIZACAO_PROMPT,
    RevisorAvaliacaoSchema,
)
from core.llm import create_json_message, create_message
from core.telegram_client import send_approval_request
from core.memory import save_revisao

logger = logging.getLogger(__name__)

# Agent and node names passed to create_message for Langfuse tracing
_AGENT = "revisor"


# ── Node 1: avaliar_texto ─────────────────────────────────────────────────────

async def avaliar_texto(state: RevisorState) -> dict:
    """
    Evaluate the original text against the REVISOR checklist.

    Calls the LLM with CHECKLIST_AVALIACAO_PROMPT and parses the result into
    RevisorAvaliacaoSchema. Populates problemas_encontrados, qualidade_estimada,
    and sets an initial status.
    """
    texto = state.get("texto_original") or ""
    logger.info("revisor.avaliar_texto: evaluating text (%d chars)", len(texto))

    avaliacao = await create_json_message(
        system=CHECKLIST_AVALIACAO_PROMPT,
        user=(
            f"Evaluate this WhatsApp message:\n\n"
            f"---\n{state['texto_original']}\n---"
        ),
        schema=RevisorAvaliacaoSchema,
        model="haiku",           # fast — evaluation is classification, not generation
        agent_name=_AGENT,
        node_name="avaliar_texto",
    )

    logger.info(
        "revisor.avaliar_texto: status=%s quality=%s problems=%d",
        avaliacao.status,
        avaliacao.qualidade_estimada,
        len(avaliacao.problemas_encontrados),
    )

    return {
        "status":                avaliacao.status,
        "problemas_encontrados": avaliacao.problemas_encontrados,
        "qualidade_estimada":    avaliacao.qualidade_estimada,
        "motivo_escalonamento":  avaliacao.motivo_escalonamento,
        # Keep texto_corrigido as None — auto_corrigir will fill it if needed
        "texto_corrigido":       None,
        "auto_correcoes":        [],
    }


# ── Node 2: auto_corrigir ─────────────────────────────────────────────────────

async def auto_corrigir(state: RevisorState) -> dict:
    """
    Automatically fix minor violations (forbidden terms, banned phrases).

    If the LLM responds with "ESCALATE", the text has structural problems
    that cannot be fixed by substitution — status is set to "escalado".
    """
    problemas_str = "\n".join(f"- {p}" for p in state["problemas_encontrados"])
    logger.info(
        "revisor.auto_corrigir: attempting to fix %d problem(s)",
        len(state["problemas_encontrados"]),
    )

    raw = await create_message(
        system=AUTO_CORRECAO_PROMPT,
        user=(
            f"Original message:\n---\n{state['texto_original']}\n---\n\n"
            f"Problems to fix:\n{problemas_str}"
        ),
        model="sonnet",          # sonnet for rewriting — needs natural quality
        agent_name=_AGENT,
        node_name="auto_corrigir",
    )

    # The LLM signals it cannot fix the message without restructuring
    if raw.strip().upper() == "ESCALATE":
        logger.warning("revisor.auto_corrigir: LLM requested escalation")
        return {
            "status":               "escalado",
            "motivo_escalonamento": (
                "Auto-correction engine could not fix the issues without "
                "rewriting the message structure. Founder review required."
            ),
            "texto_corrigido": None,
            "auto_correcoes":  [],
        }

    # Build a human-readable summary of what was changed
    correcoes_feitas = [
        f"Fixed: {p}" for p in state["problemas_encontrados"]
    ]

    logger.info(
        "revisor.auto_corrigir: corrected (%d chars → %d chars)",
        len(state["texto_original"]),
        len(raw),
    )

    return {
        "status":          "corrigido",
        "texto_corrigido": raw.strip(),
        "auto_correcoes":  correcoes_feitas,
    }


# ── Node 3: verificar_personalizacao ─────────────────────────────────────────

async def verificar_personalizacao(state: RevisorState) -> dict:
    """
    Verify that the (possibly corrected) text contains genuine company-specific
    personalisation. A generic message is always escalated regardless of other scores.
    """
    # Use the corrected text if available, otherwise the original
    texto = state.get("texto_corrigido") or state["texto_original"]

    logger.info("revisor.verificar_personalizacao: checking personalisation")

    raw = await create_message(
        system=VERIFICAR_PERSONALIZACAO_PROMPT,
        user=f"Check this message:\n\n---\n{texto}\n---",
        model="haiku",
        agent_name=_AGENT,
        node_name="verificar_personalizacao",
    )

    try:
        result = json.loads(raw)
        is_personalised: bool = result.get("is_personalised", False)
        reason: str           = result.get("reason", "No reason provided")
    except (json.JSONDecodeError, AttributeError):
        logger.warning("revisor.verificar_personalizacao: JSON parse failed, assuming not personalised")
        is_personalised = False
        reason = "Could not parse personalisation check result."

    if not is_personalised:
        logger.warning("revisor.verificar_personalizacao: ESCALATED — %s", reason)
        problemas = list(state.get("problemas_encontrados") or [])
        problemas.append(f"Not personalised: {reason}")
        return {
            "status":                "escalado",
            "motivo_escalonamento":  f"Message is not personalised. {reason}",
            "problemas_encontrados": problemas,
        }

    logger.info("revisor.verificar_personalizacao: OK — %s", reason)
    return {}   # no state change needed — routing continues normally


# ── Node 4: preparar_aprovacao ────────────────────────────────────────────────

async def preparar_aprovacao(state: RevisorState) -> dict:
    """
    Send an approval request to the founder via Telegram, then PAUSE execution.

    The interrupt() call serialises the full graph state to Redis and returns
    control to FastAPI. Execution resumes only when the founder responds via
    the Telegram inline keyboard (n8n routes the callback back to FastAPI
    which calls graph.ainvoke with Command(resume={...})).

    The value returned by interrupt() is the dict provided by the n8n resume call:
        {"aprovado": bool, "texto_editado": str | None}
    """
    texto_para_enviar = state.get("texto_corrigido") or state["texto_original"]
    is_escalado       = state["status"] == "escalado"

    # Build context for the Telegram message
    revisao_notas = _format_revisao_notes(state, is_escalado)

    # Attempt to save the review record to Supabase (best-effort — do not block)
    try:
        await save_revisao(
            lead_id=state.get("lead_id", "unknown"),   # type: ignore[arg-type]
            texto_original=state["texto_original"],
            texto_final=texto_para_enviar,
            status=state["status"],
            notas=revisao_notas,
        )
    except Exception as exc:
        logger.warning("preparar_aprovacao: save_revisao failed (non-blocking): %s", exc)

    # Send the Telegram approval request with inline keyboard
    contexto = state.get("_revisor_contexto", {})   # injected by parent graph
    message_id = await send_approval_request(
        mensagem_cliente=texto_para_enviar,
        contexto=contexto,
        revisao_notas=revisao_notas,
    )
    logger.info(
        "preparar_aprovacao: Telegram message sent (id=%s), entering interrupt",
        message_id,
    )

    # ── INTERRUPT ─────────────────────────────────────────────────────────────
    # Pauses here. LangGraph serialises state to Redis. FastAPI returns to n8n.
    # Resumes when n8n calls POST /resume with:
    #   {"aprovado": bool, "texto_editado": str | None}
    decisao: dict = interrupt({
        "telegram_message_id": message_id,
        "status_revisor":      state["status"],
        "texto_proposto":      texto_para_enviar,
    })
    # ── RESUME POINT ──────────────────────────────────────────────────────────

    aprovado      = decisao.get("aprovado", False)
    texto_editado = decisao.get("texto_editado")   # set if founder chose ✏️ Edit

    final_text = texto_editado or texto_para_enviar
    final_status = "aprovado" if aprovado else "rejeitado"

    logger.info(
        "preparar_aprovacao: founder decision — aprovado=%s edited=%s",
        aprovado,
        bool(texto_editado),
    )

    return {
        "aprovacao_fundador": aprovado,
        "texto_corrigido":    final_text,
        "status":             final_status,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_revisao_notes(state: RevisorState, is_escalado: bool) -> str:
    """Build a concise human-readable summary of what the REVISOR found and changed."""
    parts: list[str] = []

    if state.get("auto_correcoes"):
        parts.append("Auto-corrections: " + "; ".join(state["auto_correcoes"]))

    if state.get("problemas_encontrados"):
        parts.append("Problems found: " + "; ".join(state["problemas_encontrados"]))

    if is_escalado and state.get("motivo_escalonamento"):
        parts.append(f"⚠️ Escalated: {state['motivo_escalonamento']}")

    if not parts:
        parts.append("none — text approved as-is")

    return " | ".join(parts)
