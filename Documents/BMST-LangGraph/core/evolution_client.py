# core/evolution_client.py — Evolution API client for WhatsApp messaging

from __future__ import annotations

import asyncio
import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

def _base_url() -> str:
    return os.environ.get("EVOLUTION_API_URL", "http://localhost:8080")

def _api_key() -> str:
    return os.environ.get("EVOLUTION_API_KEY", "")

def _instance() -> str:
    return os.environ.get("EVOLUTION_INSTANCE", "bmst")

_TIMEOUT      = httpx.Timeout(30.0, connect=10.0)
_MAX_RETRIES  = 2   # total attempts = 1 + MAX_RETRIES


# ── Phone normalisation ───────────────────────────────────────────────────────

def _normalise_phone(phone: str) -> str:
    """
    Normalise a phone number to +244XXXXXXXXX (Angolan format).

    Handles:
      "923 456 789"    → "+244923456789"
      "244923456789"   → "+244923456789"
      "+244923456789"  → "+244923456789"  (already correct)
      "923456789"      → "+244923456789"  (local 9-digit Angola number)
    """
    # Strip everything except digits and leading +
    digits = re.sub(r"[^\d+]", "", phone.strip())

    if digits.startswith("+244"):
        return digits
    if digits.startswith("244"):
        return "+" + digits
    if digits.startswith("9") and len(digits) == 9:
        # Local Angola mobile: 9XXXXXXXX
        return "+244" + digits
    if digits.startswith("9") and len(digits) == 12 and digits[:3] == "244":
        return "+" + digits

    # Unknown format — return as-is with a warning
    logger.warning("normalise_phone: unrecognised format '%s', using as-is", phone)
    return phone


# ── HTTP helper with retry ────────────────────────────────────────────────────

async def _post(endpoint: str, payload: dict) -> dict:
    """
    POST to the Evolution API with up to MAX_RETRIES retries on transient errors.

    Raises httpx.HTTPStatusError on final failure.
    """
    url     = f"{_base_url()}{endpoint}"
    headers = {
        "apikey":       _api_key(),
        "Content-Type": "application/json",
    }
    last_exc: Exception | None = None

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for attempt in range(1, _MAX_RETRIES + 2):  # attempts: 1, 2, 3
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                if attempt <= _MAX_RETRIES:
                    wait = 2 ** (attempt - 1)   # 1s, 2s
                    logger.warning(
                        "evolution POST retry %d/%d (url=%s delay=%ds): %s",
                        attempt, _MAX_RETRIES, url, wait, exc,
                    )
                    await asyncio.sleep(wait)
            except httpx.HTTPStatusError as exc:
                # 4xx errors: do not retry (bad payload, auth error, etc.)
                logger.error(
                    "evolution POST HTTP %d (url=%s): %s",
                    exc.response.status_code, url, exc.response.text[:300],
                )
                raise

    raise RuntimeError(
        f"Evolution API POST failed after {_MAX_RETRIES + 1} attempts: {last_exc}"
    ) from last_exc


async def _get(endpoint: str) -> dict:
    """GET from the Evolution API (no retry — used only for status checks)."""
    url     = f"{_base_url()}{endpoint}"
    headers = {"apikey": _api_key()}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "evolution GET HTTP %d (url=%s): %s",
                exc.response.status_code, url, exc.response.text[:300],
            )
            raise


# ── Public API ────────────────────────────────────────────────────────────────

async def send_text_message(phone: str, text: str) -> dict:
    """
    Send a plain-text WhatsApp message via Evolution API.

    Args:
        phone: Recipient number (any Angolan format — normalised internally).
        text:  Message body.

    Returns:
        Evolution API response dict on success.

    Raises:
        RuntimeError: If all retry attempts fail.
    """
    normalised = _normalise_phone(phone)
    payload = {
        "number":      normalised,
        "options":     {"delay": 1200, "presence": "composing"},
        "textMessage": {"text": text},
    }
    try:
        result = await _post(f"/message/sendText/{_instance()}", payload)
        logger.info(
            "send_text_message: sent to %s (chars=%d)", normalised, len(text)
        )
        return result
    except Exception as exc:
        logger.error("send_text_message failed (phone=%s): %s", normalised, exc)
        raise


async def send_document(
    phone: str,
    document_url: str,
    filename: str,
    caption: str = "",
) -> dict:
    """
    Send a document (PDF) via WhatsApp — used for proposals and invoices.

    Args:
        phone:        Recipient number.
        document_url: Public URL of the PDF (e.g. from Gotenberg/storage).
        filename:     Display name shown in WhatsApp (e.g. "Proposta_BMST.pdf").
        caption:      Optional caption text displayed below the document.

    Returns:
        Evolution API response dict on success.
    """
    normalised = _normalise_phone(phone)
    payload = {
        "number":  normalised,
        "options": {"delay": 1200},
        "mediaMessage": {
            "mediatype": "document",
            "media":     document_url,
            "fileName":  filename,
            "caption":   caption,
        },
    }
    try:
        result = await _post(f"/message/sendMedia/{_instance()}", payload)
        logger.info(
            "send_document: sent '%s' to %s", filename, normalised
        )
        return result
    except Exception as exc:
        logger.error(
            "send_document failed (phone=%s file=%s): %s", normalised, filename, exc
        )
        raise


async def get_message_status(message_id: str) -> str:
    """
    Check the delivery status of a previously sent message.

    Returns:
        "sent"      — delivered to Evolution API but not yet to device
        "delivered" — delivered to device
        "read"      — read by recipient
        "failed"    — delivery failed
        "unknown"   — status could not be determined
    """
    try:
        data   = await _get(f"/message/status/{_instance()}/{message_id}")
        status = data.get("status", "unknown").lower()

        # Normalise Evolution API status names to our internal vocab
        _status_map = {
            "server_ack": "sent",
            "delivery_ack": "delivered",
            "read": "read",
            "played": "read",
            "error": "failed",
        }
        normalised_status = _status_map.get(status, status)
        logger.debug("get_message_status: id=%s status=%s", message_id, normalised_status)
        return normalised_status

    except Exception as exc:
        logger.error("get_message_status failed (id=%s): %s", message_id, exc)
        return "unknown"
