"""HTTP webhook handlers — currently just the WhatsApp approval webhook.

POST /webhook/whatsapp receives Evolution-API push events. When the
approver replies APPROVE/REJECT/REVISE to a REVISOR approval message,
this handler:

    1. Verifies the sender phone matches settings.revisor_approver_phone.
       Other senders get 200 OK ignored (Evolution retries on 4xx/5xx).
    2. Parses the decision keyword (EN or PT, case-insensitive) and any
       attached note.
    3. Looks up the session_id of the latest review_log row still pending
       human_decision for this approver.
    4. Persists the human decision to all matching review_log rows via
       supabase.update_approval_by_session().
    5. Resumes the paused LangGraph using:
         compiled_graph.aupdate_state(... as_node="revisor")
         compiled_graph.ainvoke(None, config)
       The router then sends the graph to PUBLISHER, WRITER, or END.

The session_id lookup approach is the spec's Option B (query review_log).
This avoids requiring the human to quote any session ID in their reply.
"""

import logging
import re
from typing import Optional

from fastapi import APIRouter, Request

from src.config.settings import settings
from src.memory.supabase_client import SupabaseMemory
from src.orchestrator.graph import compiled_graph, setup_checkpointer
from src.tools import whatsapp

logger = logging.getLogger(__name__)

router = APIRouter()


# Approver display name must match what REVISOR writes to review_log.approver.
_APPROVER_NAME: str = "Fidel Inácio Kussunga"


# ---------------------------------------------------------------------------
# Decision parser
# ---------------------------------------------------------------------------


# Variants accepted for each decision. Order matters within a group only when
# variants are prefixes of each other (none are here).
_APPROVE_KEYWORDS: tuple[str, ...] = ("APROVADO", "APPROVED", "APPROVE")
_REJECT_KEYWORDS: tuple[str, ...] = ("REJEITADO", "REJECTED", "REJECT")
_REVISE_KEYWORDS: tuple[str, ...] = ("REVISÃO", "REVISAO", "REVISION", "REVISE")


def _parse_decision(message: str) -> tuple[Optional[str], Optional[str]]:
    """Extract (decision, note) from the human's WhatsApp reply.

    Recognised forms (case-insensitive):
        APROVADO / APPROVED / APPROVE
        REJEITADO[: reason] / REJECTED[: reason] / REJECT[: reason]
        REVISÃO: note / REVISION: note / REVISE: note  (note required)

    Returns (None, None) if no keyword matches.
    """
    text = message.strip()
    if not text:
        return None, None

    upper = text.upper()

    # APPROVE — bare keyword, or followed by punctuation only
    for kw in _APPROVE_KEYWORDS:
        if upper == kw or re.match(rf"^{re.escape(kw)}[\s\.\!\?,]*$", upper):
            return "approved", None

    # REJECT — bare keyword OR keyword + ":" + reason OR keyword + " " + reason
    for kw in _REJECT_KEYWORDS:
        if upper == kw:
            return "rejected", None
        match = re.match(rf"^{re.escape(kw)}\s*[:\-]\s*(.+)$", text, flags=re.IGNORECASE)
        if match:
            return "rejected", match.group(1).strip() or None

    # REVISE — keyword + ":" + note (note required, treat empty as placeholder)
    for kw in _REVISE_KEYWORDS:
        match = re.match(rf"^{re.escape(kw)}\s*[:\-]\s*(.+)$", text, flags=re.IGNORECASE)
        if match:
            note = match.group(1).strip()
            return "revision_requested", note or "no note provided"

    return None, None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize_phone(phone: str) -> str:
    """Strip whitespace and ensure a leading '+' for comparison."""
    phone = phone.strip()
    if not phone.startswith("+"):
        phone = "+" + phone
    return phone


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request) -> dict:
    """Receive an Evolution API webhook and resume the paused REVISOR graph."""
    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("WhatsApp webhook: malformed JSON", extra={"error": str(exc)})
        return {"status": "malformed_json"}

    try:
        parsed = whatsapp.parse_incoming_webhook(payload)
    except whatsapp.WhatsAppError as exc:
        logger.warning("WhatsApp webhook: parse failed", extra={"error": str(exc)})
        return {"status": "parse_failed"}

    # ── Sender verification ─────────────────────────────────────────────────
    sender = _normalize_phone(parsed["from"])
    expected = _normalize_phone(settings.revisor_approver_phone)
    if sender != expected:
        logger.info(
            "WhatsApp webhook: sender not authorised",
            extra={"sender": sender, "expected": expected},
        )
        return {"status": "ignored", "reason": "sender_not_authorised"}

    # ── Decision parsing ────────────────────────────────────────────────────
    decision, note = _parse_decision(parsed["message"])
    if decision is None:
        logger.info(
            "WhatsApp webhook: message did not match a known decision keyword",
            extra={"message_preview": parsed["message"][:80]},
        )
        return {"status": "unrecognized", "message_preview": parsed["message"][:80]}

    logger.info(
        "WhatsApp webhook: decision parsed",
        extra={"decision": decision, "note_preview": (note or "")[:80]},
    )

    # ── Session lookup ──────────────────────────────────────────────────────
    supa = SupabaseMemory()
    await supa.connect()
    session_id = await supa.get_latest_pending_session(approver=_APPROVER_NAME)
    if session_id is None:
        logger.info("WhatsApp webhook: no pending session in review_log")
        return {"status": "no_pending"}

    # ── Persist decision to all review_log rows for this session ────────────
    await supa.update_approval_by_session(session_id, decision, note)

    # ── Resume the paused graph ─────────────────────────────────────────────
    await setup_checkpointer()
    config = {"configurable": {"thread_id": session_id}}

    await compiled_graph.aupdate_state(
        config,
        {
            "approval_decision": decision,
            "revision_note": note,
            "pending_approval": False,
        },
        as_node="revisor",
    )
    await compiled_graph.ainvoke(None, config=config)

    logger.info(
        "WhatsApp webhook: graph resumed",
        extra={"session_id": session_id, "decision": decision},
    )

    return {"status": "resumed", "session_id": session_id, "decision": decision}
