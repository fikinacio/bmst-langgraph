# core/sheets_client.py — Google Sheets API client via service account

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
from datetime import date
from typing import Any

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# Google Sheets API scope (read + write)
_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# Sheet structure constants
_TAB_NAME          = "leads_angola"
_HEADER_ROW        = 1          # row 1 is always the header
_MAX_LEADS         = 20         # anti-spam: HUNTER processes at most 20 leads/day
_COL_ESTADO_HUNTER = "U"        # column U  → estado_hunter
_COL_DATA_HUNTER   = "V"        # column V  → data_hunter
_COL_RESPOSTA      = "W"        # column W  → resposta
_COL_SEGMENTO      = "segmento" # header name used to identify segment A leads
_COL_ESTADO        = "estado_hunter"
_COL_WHATSAPP      = "whatsapp"
_COL_EMPRESA       = "empresa"


# ── Credentials ───────────────────────────────────────────────────────────────

def _load_credentials() -> Credentials:
    """
    Load service account credentials from GOOGLE_SERVICE_ACCOUNT_JSON.

    Accepts three formats:
      1. File path   → path to a .json file on disk
      2. Base64 str  → base64-encoded JSON (useful for Docker secrets/env vars)
      3. Raw JSON str→ the JSON object itself as a string
    """
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is not set in the environment.")

    # 1. File path
    if os.path.isfile(raw):
        return Credentials.from_service_account_file(raw, scopes=_SCOPES)

    # 2. Base64-encoded JSON
    try:
        decoded = base64.b64decode(raw).decode("utf-8")
        info = json.loads(decoded)
        return Credentials.from_service_account_info(info, scopes=_SCOPES)
    except Exception:
        pass

    # 3. Raw JSON string
    try:
        info = json.loads(raw)
        return Credentials.from_service_account_info(info, scopes=_SCOPES)
    except Exception as exc:
        raise RuntimeError(
            "GOOGLE_SERVICE_ACCOUNT_JSON is not a valid file path, "
            "base64 string, or JSON string."
        ) from exc


def _get_service():
    """Build and return the Google Sheets API service object (synchronous)."""
    creds = _load_credentials()
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


# ── Internal sync helpers (wrapped with asyncio.to_thread by public API) ──────

def _sync_get_all_rows(sheet_id: str) -> tuple[list[str], list[list[Any]]]:
    """
    Return (headers, data_rows) from the leads_angola tab.
    headers: list of column names from row 1.
    data_rows: list of rows (each row is a list of cell values).
    """
    service = _get_service()
    range_name = f"{_TAB_NAME}"
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=sheet_id, range=range_name)
        .execute()
    )
    values: list[list[Any]] = result.get("values", [])
    if not values:
        return [], []
    headers   = values[0]
    data_rows = values[1:]
    return headers, data_rows


def _row_to_dict(headers: list[str], row: list[Any]) -> dict:
    """Zip a row list with the header list, padding short rows with empty strings."""
    padded = row + [""] * (len(headers) - len(row))
    return dict(zip(headers, padded))


def _sync_update_cell(sheet_id: str, cell: str, value: str) -> None:
    """Write a single cell value (e.g. 'U5') to the sheet."""
    service = _get_service()
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{_TAB_NAME}!{cell}",
        valueInputOption="RAW",
        body={"values": [[value]]},
    ).execute()


# ── Public async API ──────────────────────────────────────────────────────────

async def get_pending_leads(sheet_id: str) -> list[dict]:
    """
    Read the 'leads_angola' tab and return leads where:
      - estado_hunter == "pendente"
      - segmento != "A"

    Each lead dict includes an extra key '_row_index' (1-based, including header row)
    so callers can use update_lead_status without re-fetching the sheet.

    Returns at most MAX_LEADS (20) leads.
    """
    try:
        headers, data_rows = await asyncio.to_thread(_sync_get_all_rows, sheet_id)
        if not headers:
            logger.warning("get_pending_leads: sheet is empty or unreadable")
            return []

        # Normalise header names (strip whitespace)
        headers = [h.strip() for h in headers]

        pending: list[dict] = []
        for i, row in enumerate(data_rows):
            lead = _row_to_dict(headers, row)
            if lead.get(_COL_ESTADO, "").strip().lower() != "pendente":
                continue
            if lead.get(_COL_SEGMENTO, "").strip().upper() == "A":
                continue
            lead["_row_index"] = i + 2  # +1 for header row, +1 for 1-based index
            pending.append(lead)
            if len(pending) >= _MAX_LEADS:
                break

        logger.info("get_pending_leads: found %d pending leads (sheet=%s)", len(pending), sheet_id)
        return pending

    except HttpError as exc:
        logger.error("get_pending_leads HTTP error (sheet=%s): %s", sheet_id, exc)
        return []
    except Exception as exc:
        logger.error("get_pending_leads failed (sheet=%s): %s", sheet_id, exc)
        return []


async def update_lead_status(
    sheet_id: str,
    row_index: int,
    status: str,
    date_str: str | None = None,
) -> bool:
    """
    Update columns U (estado_hunter) and V (data_hunter) for a given row.

    Args:
        sheet_id:  Google Sheets document ID.
        row_index: 1-based row number (row 1 = header).
        status:    New value for estado_hunter (e.g. "enviado", "arquivado").
        date_str:  ISO date string. Defaults to today if not provided.
    """
    try:
        today = date_str or date.today().isoformat()
        await asyncio.to_thread(
            _sync_update_cell, sheet_id, f"{_COL_ESTADO_HUNTER}{row_index}", status
        )
        await asyncio.to_thread(
            _sync_update_cell, sheet_id, f"{_COL_DATA_HUNTER}{row_index}", today
        )
        logger.debug(
            "update_lead_status: row=%d status=%s date=%s", row_index, status, today
        )
        return True
    except HttpError as exc:
        logger.error("update_lead_status HTTP error (row=%d): %s", row_index, exc)
        return False
    except Exception as exc:
        logger.error("update_lead_status failed (row=%d): %s", row_index, exc)
        return False


async def mark_lead_response(sheet_id: str, row_index: int, response: str) -> bool:
    """
    Write the prospect's response text to column W (resposta).

    Args:
        sheet_id:   Google Sheets document ID.
        row_index:  1-based row number.
        response:   Response text received via WhatsApp webhook.
    """
    try:
        await asyncio.to_thread(
            _sync_update_cell, sheet_id, f"{_COL_RESPOSTA}{row_index}", response
        )
        logger.debug("mark_lead_response: row=%d response_length=%d", row_index, len(response))
        return True
    except HttpError as exc:
        logger.error("mark_lead_response HTTP error (row=%d): %s", row_index, exc)
        return False
    except Exception as exc:
        logger.error("mark_lead_response failed (row=%d): %s", row_index, exc)
        return False


async def get_lead_by_whatsapp(sheet_id: str, phone: str) -> dict | None:
    """
    Search for a lead by WhatsApp number. Used when a prospect reply arrives.

    Returns the lead dict (with '_row_index') or None if not found.
    """
    try:
        headers, data_rows = await asyncio.to_thread(_sync_get_all_rows, sheet_id)
        if not headers:
            return None
        headers = [h.strip() for h in headers]

        # Normalise the search phone (remove spaces)
        needle = phone.replace(" ", "").strip()

        for i, row in enumerate(data_rows):
            lead = _row_to_dict(headers, row)
            cell_phone = lead.get(_COL_WHATSAPP, "").replace(" ", "").strip()
            if cell_phone == needle:
                lead["_row_index"] = i + 2
                logger.debug("get_lead_by_whatsapp: found phone=%s row=%d", phone, i + 2)
                return lead

        logger.debug("get_lead_by_whatsapp: not found phone=%s", phone)
        return None

    except Exception as exc:
        logger.error("get_lead_by_whatsapp failed (phone=%s): %s", phone, exc)
        return None


async def check_duplicate(sheet_id: str, empresa: str, phone: str) -> bool:
    """
    Check whether a company name or phone number already exists in the sheet.

    Returns True if a duplicate is found (caller should skip this lead).
    """
    try:
        headers, data_rows = await asyncio.to_thread(_sync_get_all_rows, sheet_id)
        if not headers:
            return False
        headers = [h.strip() for h in headers]

        needle_phone   = phone.replace(" ", "").strip().lower()
        needle_empresa = empresa.strip().lower()

        for row in data_rows:
            lead = _row_to_dict(headers, row)
            existing_phone   = lead.get(_COL_WHATSAPP, "").replace(" ", "").strip().lower()
            existing_empresa = lead.get(_COL_EMPRESA, "").strip().lower()
            if existing_phone == needle_phone or existing_empresa == needle_empresa:
                logger.debug(
                    "check_duplicate: duplicate found empresa=%s phone=%s", empresa, phone
                )
                return True

        return False

    except Exception as exc:
        logger.error("check_duplicate failed (empresa=%s phone=%s): %s", empresa, phone, exc)
        return False  # safe default: do not block lead on error
