# core/telegram_client.py — Telegram Bot API client for founder notifications and approvals

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(15.0, connect=5.0)

# Urgency emoji map used in alerts
_URGENCY_EMOJI = {
    "alta":   "🔴",
    "média":  "🟡",
    "media":  "🟡",   # alias without accent
    "baixa":  "🟢",
}


# ── Configuration ─────────────────────────────────────────────────────────────

def _bot_url() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in the environment.")
    return f"https://api.telegram.org/bot{token}"

def _chat_id() -> str:
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID is not set in the environment.")
    return chat_id


# ── Internal HTTP helper ──────────────────────────────────────────────────────

async def _api_call(method: str, payload: dict[str, Any]) -> dict:
    """
    Call a Telegram Bot API method.

    Raises httpx.HTTPStatusError on API-level errors (non-200 HTTP responses).
    """
    url = f"{_bot_url()}/{method}"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(
                f"Telegram API error [{method}]: {data.get('description', 'unknown')}"
            )
        return data.get("result", {})


# ── Public API ────────────────────────────────────────────────────────────────

async def send_message(text: str, parse_mode: str = "HTML") -> dict:
    """
    Send a plain text message to the founder's Telegram chat.

    Args:
        text:       Message body. Use HTML tags (<b>, <i>, <code>) — not Markdown.
        parse_mode: Telegram parse mode. Defaults to "HTML" (more stable than Markdown).

    Returns:
        Telegram Message object dict.
    """
    try:
        result = await _api_call("sendMessage", {
            "chat_id":    _chat_id(),
            "text":       text,
            "parse_mode": parse_mode,
        })
        logger.info("send_message: sent %d chars to Telegram", len(text))
        return result
    except Exception as exc:
        logger.error("send_message failed: %s", exc)
        raise


async def answer_callback_query(callback_query_id: str, text: str = "") -> None:
    """
    Acknowledge a Telegram callback query (removes the loading spinner on the button).

    Must be called within 10 seconds of receiving the callback, otherwise
    Telegram shows an error to the user.
    """
    try:
        await _api_call("answerCallbackQuery", {
            "callback_query_id": callback_query_id,
            "text": text,
        })
    except Exception as exc:
        logger.warning("answer_callback_query failed (id=%s): %s", callback_query_id, exc)


async def send_approval_request(
    mensagem_cliente: str,
    contexto: dict,
    revisao_notas: str,
    thread_id: str = "",
) -> str:
    """
    Send a formatted approval request with an inline keyboard (✅ / ✏️ / ❌).

    This is called by the REVISOR after auto-correcting a message.
    The n8n Wait Node watches for the callback query response.

    Args:
        mensagem_cliente: Final text that will be sent to the prospect.
        contexto:         Dict with keys: empresa, segmento, canal, agente.
        revisao_notas:    Summary of changes made by the REVISOR ("none" if unchanged).

    Returns:
        The Telegram message_id as a string — stored in LangGraph state
        so the Wait Node can match the callback to the right thread.
    """
    empresa  = contexto.get("empresa",  "—")
    segmento = contexto.get("segmento", "—")
    canal    = contexto.get("canal",    "—")
    agente   = contexto.get("agente",   "—")

    body = (
        f"📝 <b>REVISOR — Approval Required</b>\n\n"
        f"<b>Company:</b> {empresa} — Seg {segmento}\n"
        f"<b>Channel:</b> {canal}\n"
        f"<b>Agent:</b> {agente}\n\n"
        f"<b>Message to send:</b>\n"
        f"<code>{'─' * 30}</code>\n"
        f"{mensagem_cliente}\n"
        f"<code>{'─' * 30}</code>\n\n"
        f"<b>Revisions made:</b> {revisao_notas or 'none'}"
    )

    # Inline keyboard: three buttons in one row.
    # callback_data format: "action:thread_id"
    # The thread_id lets /telegram/callback resume the exact LangGraph execution.
    # Fallback to empresa:agente if thread_id is not provided (dev mode).
    tid = thread_id or f"{agente}:{empresa}"
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Approve",  "callback_data": f"aprovar:{tid}"},
            {"text": "✏️ Edit",    "callback_data": f"editar:{tid}"},
            {"text": "❌ Reject",  "callback_data": f"rejeitar:{tid}"},
        ]]
    }

    try:
        result = await _api_call("sendMessage", {
            "chat_id":      _chat_id(),
            "text":         body,
            "parse_mode":   "HTML",
            "reply_markup": keyboard,
        })
        message_id = str(result.get("message_id", ""))
        logger.info(
            "send_approval_request: sent for empresa=%s message_id=%s",
            empresa, message_id,
        )
        return message_id
    except Exception as exc:
        logger.error("send_approval_request failed (empresa=%s): %s", empresa, exc)
        raise


async def send_proposal_approval_request(
    proposta: dict,
    thread_id: str = "",
) -> str:
    """
    Send a CLOSER proposal approval request to the founder with inline keyboard.

    Used by the CLOSER agent after generating a proposal draft.  The founder
    reviews the proposal and taps Approve / Edit / Reject.

    Args:
        proposta:   Proposal dict with keys: cliente, decisor, solucao_proposta,
                    entregaveis, prazo_semanas, valor_aoa, notas_fundador.
        thread_id:  LangGraph thread_id to embed in callback_data so the
                    /telegram/callback endpoint can resume the correct graph.

    Returns:
        Telegram message_id as a string.
    """
    cliente    = proposta.get("cliente", "—")
    decisor    = proposta.get("decisor", "—")
    servico    = proposta.get("solucao_proposta", "—")
    valor      = proposta.get("valor_aoa", 0)
    prazo      = proposta.get("prazo_semanas", "—")
    condicoes  = proposta.get("condicoes_pagamento", "50% assinatura + 50% antes entrega")
    validade   = proposta.get("validade_proposta_dias", 15)
    notas      = proposta.get("notas_fundador", "")
    entregaveis = proposta.get("entregaveis", [])

    entregaveis_str = "\n".join(f"  • {e}" for e in entregaveis) or "  —"

    body = (
        f"🟡 <b>CLOSER — Proposal Approval Required</b>\n\n"
        f"<b>Client:</b> {cliente}\n"
        f"<b>Decision-maker:</b> {decisor}\n"
        f"<b>Service:</b> {servico}\n"
        f"<b>Value:</b> {valor:,} AOA\n"
        f"<b>Timeline:</b> {prazo} weeks\n"
        f"<b>Payment:</b> {condicoes}\n"
        f"<b>Valid for:</b> {validade} days\n\n"
        f"<b>Deliverables:</b>\n{entregaveis_str}\n\n"
        + (f"<b>Founder notes:</b> {notas}" if notas else "")
    )

    tid = thread_id or f"closer:{cliente}"
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Approve", "callback_data": f"aprovar:{tid}"},
            {"text": "✏️ Edit",   "callback_data": f"editar:{tid}"},
            {"text": "❌ Reject", "callback_data": f"rejeitar:{tid}"},
        ]]
    }

    try:
        result = await _api_call("sendMessage", {
            "chat_id":      _chat_id(),
            "text":         body,
            "parse_mode":   "HTML",
            "reply_markup": keyboard,
        })
        message_id = str(result.get("message_id", ""))
        logger.info(
            "send_proposal_approval_request: sent for cliente=%s message_id=%s",
            cliente, message_id,
        )
        return message_id
    except Exception as exc:
        logger.error("send_proposal_approval_request failed (cliente=%s): %s", cliente, exc)
        raise


async def send_alert(title: str, body: str, urgency: str = "média") -> dict:
    """
    Send an operational alert to the founder.

    Args:
        title:   Short title (e.g. "Payment overdue", "System error").
        body:    Detailed description.
        urgency: "alta" | "média" | "baixa"

    Returns:
        Telegram Message object dict.
    """
    emoji = _URGENCY_EMOJI.get(urgency.lower(), "⚠️")
    text  = (
        f"{emoji} <b>BMST ALERT — {title}</b>\n\n"
        f"{body}"
    )
    try:
        result = await send_message(text)
        logger.info("send_alert: sent title='%s' urgency=%s", title, urgency)
        return result
    except Exception as exc:
        logger.error("send_alert failed (title=%s): %s", title, exc)
        raise


async def send_daily_report(report: dict) -> dict:
    """
    Format and send the HUNTER daily report to the founder.

    Expected report dict keys:
        data             (str)   — ISO date e.g. "2026-04-17"
        processados      (int)   — total leads processed
        enviadas         (int)   — messages sent
        aguardam         (int)   — waiting for approval
        arquivados       (int)   — auto-archived (Seg A)
        seg_c_pendentes  (int)   — Seg C awaiting founder approval
        respostas        (int)   — replies received today
        interessados     (int)
        nomes_interessados (str) — comma-separated names
        neutros          (int)
        nao_interessados (int)
        followups        (int)   — follow-ups scheduled for tomorrow
    """
    # Safely extract each field with a fallback to avoid KeyError
    g = report.get

    text = (
        f"📊 <b>HUNTER — {g('data', '—')}</b>\n\n"
        f"📤 Processed today: <b>{g('processados', 0)}</b> leads\n"
        f"✅ Messages sent: <b>{g('enviadas', 0)}</b>\n"
        f"⏳ Awaiting approval: <b>{g('aguardam', 0)}</b>\n"
        f"🔴 Auto-archived (Seg A): <b>{g('arquivados', 0)}</b>\n"
        f"⚠️ Seg C pending founder approval: <b>{g('seg_c_pendentes', 0)}</b>\n\n"
        f"💬 Replies received today: <b>{g('respostas', 0)}</b>\n"
        f"🟢 Interested: <b>{g('interessados', 0)}</b>"
        + (f" → {g('nomes_interessados', '')}" if g('nomes_interessados') else "") + "\n"
        f"🟡 Neutral: <b>{g('neutros', 0)}</b>\n"
        f"🔴 Not interested: <b>{g('nao_interessados', 0)}</b>\n\n"
        f"📅 <b>Tomorrow:</b>\n"
        f"• Follow-ups scheduled: <b>{g('followups', 0)}</b>\n"
        f"• New leads from PROSPECTOR: (at 08h00)"
    )

    try:
        result = await send_message(text)
        logger.info("send_daily_report: sent for date=%s", g('data', '?'))
        return result
    except Exception as exc:
        logger.error("send_daily_report failed: %s", exc)
        raise
