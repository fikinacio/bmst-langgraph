"""Evolution API wrapper for WhatsApp text + media messaging.

Used by REVISOR to send approval requests to the human approver, and used
by the approval webhook handler to parse incoming responses.

Retries: 3× on connection errors and 5xx responses with exponential backoff.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import settings
from src.protocols.io_schema import ReviewResult

logger = logging.getLogger(__name__)


class WhatsAppError(Exception):
    """Raised when the Evolution API returns an error or is unreachable."""


# ---------------------------------------------------------------------------
# Retry decorator shared by send_text and send_media
# ---------------------------------------------------------------------------

_retry_http = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, WhatsAppError)),
    reraise=True,
)


def _headers() -> dict[str, str]:
    return {
        "apikey": settings.evolution_api_key,
        "Content-Type": "application/json",
    }


def _instance_url(endpoint: str) -> str:
    """Build a full Evolution endpoint URL: {base}/message/{endpoint}/{instance}."""
    return f"{settings.evolution_api_url}/message/{endpoint}/{settings.evolution_instance}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@_retry_http
async def send_text(to: str, message: str) -> dict:
    """Send a plain-text WhatsApp message via the Evolution API.

    Args:
        to:      Recipient phone in international format (e.g. +41795748225).
        message: UTF-8 text. Accents preserved per project policy.

    Raises:
        WhatsAppError on non-2xx responses or network failures.
    """
    payload = {"number": to, "text": message}
    url = _instance_url("sendText")
    logger.debug("WhatsApp send_text", extra={"to": to, "len": len(message)})

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload, headers=_headers())
    except httpx.HTTPError as exc:
        logger.error("WhatsApp network error", extra={"to": to, "error": str(exc)})
        raise

    if response.status_code >= 500:
        logger.error(
            "WhatsApp server error",
            extra={"to": to, "status": response.status_code, "body": response.text[:300]},
        )
        raise WhatsAppError(f"Evolution API 5xx: {response.status_code}")

    if not response.is_success:
        logger.error(
            "WhatsApp client error",
            extra={"to": to, "status": response.status_code, "body": response.text[:300]},
        )
        raise WhatsAppError(f"Evolution API {response.status_code}: {response.text[:200]}")

    return response.json()


@_retry_http
async def send_media(to: str, media_url: str, caption: str) -> dict:
    """Send a media (image/video) message with an optional caption.

    media_url must be publicly reachable from the Evolution API container.
    """
    payload = {
        "number": to,
        "mediatype": "image",
        "media": media_url,
        "caption": caption,
    }
    url = _instance_url("sendMedia")
    logger.debug("WhatsApp send_media", extra={"to": to, "media_url": media_url})

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=_headers())
    except httpx.HTTPError as exc:
        logger.error("WhatsApp media network error", extra={"to": to, "error": str(exc)})
        raise

    if response.status_code >= 500:
        raise WhatsAppError(f"Evolution API 5xx: {response.status_code}")
    if not response.is_success:
        raise WhatsAppError(f"Evolution API {response.status_code}: {response.text[:200]}")

    return response.json()


# ---------------------------------------------------------------------------
# Webhook parsing
# ---------------------------------------------------------------------------


def parse_incoming_webhook(payload: dict) -> dict:
    """Normalise an Evolution API webhook payload into a stable shape.

    Returns:
        {"from": str, "message": str, "timestamp": datetime}

    Raises:
        WhatsAppError if required fields are missing.
    """
    try:
        data = payload["data"]
        sender = data["key"]["remoteJid"].split("@")[0]
        # The message body is one of several keys depending on type
        message_body = (
            data.get("message", {}).get("conversation")
            or data.get("message", {}).get("extendedTextMessage", {}).get("text")
            or ""
        )
        # messageTimestamp is unix seconds
        ts = datetime.fromtimestamp(int(data["messageTimestamp"]), tz=timezone.utc)
    except (KeyError, ValueError, AttributeError) as exc:
        logger.error("WhatsApp webhook parse failed", extra={"error": str(exc)})
        raise WhatsAppError(f"Malformed Evolution webhook: {exc}") from exc

    return {"from": sender, "message": message_body.strip(), "timestamp": ts}


# ---------------------------------------------------------------------------
# Approval message formatter
# ---------------------------------------------------------------------------


def format_approval_message(
    review: ReviewResult,
    content_preview: str,
) -> str:
    """Build the WhatsApp message REVISOR sends to the human approver.

    Format mirrors the project's two-block convention: a structured header
    followed by the content preview, separated by `---` lines.
    """
    quality_pct = int(round(review.quality_score * 100))
    detection_pct = int(round(review.ai_detection_score * 100))
    issues = ", ".join(review.issues) if review.issues else "nenhum"

    return (
        f"🔍 *Conteúdo para Aprovação*\n"
        f"📱 Plataforma: {review.platform.value.upper()}  |  🆔 {review.review_id}\n"
        f"📊 Qualidade: {quality_pct}%  |  Detecção IA: {detection_pct}%\n"
        f"⚠️ Problemas: {issues}\n"
        f"\n---\n"
        f"{content_preview}\n"
        f"---\n"
        f"\n"
        f"✅ Responda *APROVADO* para publicar\n"
        f"❌ Responda *REJEITADO* para descartar\n"
        f"✏️ Responda *REVISÃO: [nota]* para pedir alterações"
    )
