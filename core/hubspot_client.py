# core/hubspot_client.py — HubSpot CRM client (leads stored as Company + associated Contact)
#
# Replaces the former Google Sheets lead store. Each prospected lead becomes:
#   • one Company  — carries all firmographic + BMST workflow fields (estado_hunter, etc.)
#   • one Contact  — the decision-maker (responsavel + whatsapp), associated to the Company
#
# The Company is the primary lead record: status updates, response logging and the
# HUNTER "pending" queue all key off Company custom properties. The opaque record id
# returned to callers (under the legacy key "_row_index") is the HubSpot Company id.
#
# Custom properties are created automatically on first use via ensure_schema().

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import date
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────

_BASE_URL    = "https://api.hubapi.com"
_TIMEOUT     = httpx.Timeout(30.0, connect=10.0)
_MAX_RETRIES = 2          # total attempts = 1 + MAX_RETRIES
_MAX_LEADS   = 20         # anti-spam: HUNTER processes at most 20 leads/day
_PROP_GROUP  = "companyinformation"   # built-in group new company props are filed under


def _token() -> str:
    return os.environ.get("HUBSPOT_ACCESS_TOKEN", "")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_token()}",
        "Content-Type":  "application/json",
    }


# ── Property mapping ──────────────────────────────────────────────────────────
#
# lead-dict key (the original Google Sheets column name) → HubSpot Company property.
# Standard HubSpot properties (name, website) are reused; everything else is a
# custom "bmst_" property created by ensure_schema().

_PROP_MAP: dict[str, str] = {
    "empresa":         "name",
    "website":         "website",
    "id":              "bmst_lead_id",
    "data_registo":    "bmst_data_registo",
    "sector":          "bmst_sector",
    "responsavel":     "bmst_responsavel",
    "whatsapp":        "bmst_whatsapp",
    "instagram":       "bmst_instagram",
    "localizacao":     "bmst_localizacao",
    "nr_funcionarios": "bmst_nr_funcionarios",
    "segmento":        "bmst_segmento",
    "servico_bmst":    "bmst_servico",
    "oportunidade":    "bmst_oportunidade",
    "notas_abordagem": "bmst_notas_abordagem",
    "valor_est_aoa":   "bmst_valor_est_aoa",
    "fonte":           "bmst_fonte",
    "estado_hunter":   "bmst_estado_hunter",
    "data_hunter":     "bmst_data_hunter",
    "resposta":        "bmst_resposta",
}
_REVERSE_MAP: dict[str, str] = {hs: lead for lead, hs in _PROP_MAP.items()}

# Custom (bmst_*) company properties only — these are the ones we must create.
# Stored as plain text to avoid HubSpot date/number coercion surprises (the source
# values are free-form strings such as Angolan kwanza amounts or employee ranges).
_CUSTOM_PROPS: list[dict[str, str]] = [
    {"name": hs, "label": lead.replace("_", " ").title()}
    for lead, hs in _PROP_MAP.items()
    if hs.startswith("bmst_")
]

# HubSpot search lags the object index by a few seconds; ensure_schema runs once.
_schema_ensured = False


# ── HTTP helpers with retry ───────────────────────────────────────────────────

async def _request(method: str, endpoint: str, payload: dict | None = None) -> dict:
    """
    Call the HubSpot API with retries on transient errors.

    Raises httpx.HTTPStatusError on non-transient HTTP errors (4xx).
    """
    url = f"{_BASE_URL}{endpoint}"
    last_exc: Exception | None = None

    async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
        for attempt in range(1, _MAX_RETRIES + 2):   # attempts: 1, 2, 3
            try:
                response = await client.request(
                    method, url, json=payload, headers=_headers()
                )
                response.raise_for_status()
                return response.json() if response.content else {}
            except (httpx.TimeoutException, httpx.ConnectError) as exc:
                last_exc = exc
                if attempt <= _MAX_RETRIES:
                    wait = 2 ** (attempt - 1)   # 1s, 2s
                    logger.warning(
                        "hubspot %s retry %d/%d (url=%s delay=%ds): %s",
                        method, attempt, _MAX_RETRIES, url, wait, exc,
                    )
                    await asyncio.sleep(wait)
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "hubspot %s HTTP %d (url=%s): %s",
                    method, exc.response.status_code, url, exc.response.text[:300],
                )
                raise

    raise RuntimeError(
        f"HubSpot {method} {endpoint} failed after {_MAX_RETRIES + 1} attempts: {last_exc}"
    ) from last_exc


def _normalise_phone(phone: str) -> str:
    """Strip spaces for consistent equality matching (mirrors the old sheet logic)."""
    return re.sub(r"\s+", "", phone or "").strip()


# ── Schema bootstrap ──────────────────────────────────────────────────────────

async def ensure_schema() -> None:
    """
    Create any missing bmst_* custom Company properties. Idempotent — a property
    that already exists (409 Conflict) is treated as success. Runs at most once
    per process.
    """
    global _schema_ensured
    if _schema_ensured:
        return
    if not _token():
        logger.warning("hubspot.ensure_schema: HUBSPOT_ACCESS_TOKEN not set, skipping")
        return

    for prop in _CUSTOM_PROPS:
        body = {
            "name":      prop["name"],
            "label":     prop["label"],
            "type":      "string",
            "fieldType": "text",
            "groupName": _PROP_GROUP,
        }
        try:
            await _request("POST", "/crm/v3/properties/companies", body)
            logger.info("hubspot.ensure_schema: created property %s", prop["name"])
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 409:
                continue   # already exists — fine
            logger.error(
                "hubspot.ensure_schema: failed to create %s: %s",
                prop["name"], exc.response.text[:200],
            )
        except Exception as exc:
            logger.error("hubspot.ensure_schema: error creating %s: %s", prop["name"], exc)

    _schema_ensured = True


# ── Conversion helpers ────────────────────────────────────────────────────────

def _lead_to_company_props(lead: dict) -> dict[str, str]:
    """Map a lead dict (sheet-column keys) to HubSpot company properties."""
    props: dict[str, str] = {}
    for lead_key, hs_key in _PROP_MAP.items():
        value = lead.get(lead_key)
        if value not in (None, ""):
            props[hs_key] = str(value)
    return props


def _company_to_lead(record: dict) -> dict:
    """Map a HubSpot company record back to a lead dict with the original keys."""
    props = record.get("properties", {}) or {}
    lead: dict = {}
    for hs_key, value in props.items():
        lead_key = _REVERSE_MAP.get(hs_key)
        if lead_key is not None:
            lead[lead_key] = value if value is not None else ""
    lead["_row_index"] = record.get("id")
    return lead


# Every bmst_* property plus the standard ones we read back.
_READ_PROPERTIES = list(_PROP_MAP.values())


# ── Public async API ──────────────────────────────────────────────────────────

async def get_pending_leads() -> list[dict]:
    """
    Return Company leads where estado_hunter == "pendente" and segmento != "A".

    Segment filtering is done client-side (as in the old sheet logic) so that
    leads with an empty segmento are still included. Returns at most MAX_LEADS.
    Each lead dict carries "_row_index" = HubSpot Company id.
    """
    try:
        await ensure_schema()
        body = {
            "filterGroups": [
                {"filters": [
                    {"propertyName": "bmst_estado_hunter", "operator": "EQ", "value": "pendente"},
                ]},
            ],
            "properties": _READ_PROPERTIES,
            "limit": 100,
        }
        result = await _request("POST", "/crm/v3/objects/companies/search", body)

        pending: list[dict] = []
        for record in result.get("results", []):
            lead = _company_to_lead(record)
            if (lead.get("segmento") or "").strip().upper() == "A":
                continue
            pending.append(lead)
            if len(pending) >= _MAX_LEADS:
                break

        logger.info("get_pending_leads: found %d pending leads", len(pending))
        return pending

    except Exception as exc:
        logger.error("get_pending_leads failed: %s", exc)
        return []


async def update_lead_status(
    record_id: str,
    status: str,
    date_str: str | None = None,
) -> bool:
    """
    Update estado_hunter and data_hunter on a Company lead.

    Args:
        record_id: HubSpot Company id (the "_row_index" returned by get_pending_leads).
        status:    New estado_hunter value (e.g. "enviado", "arquivado").
        date_str:  ISO date string. Defaults to today.
    """
    try:
        today = date_str or date.today().isoformat()
        await _request(
            "PATCH",
            f"/crm/v3/objects/companies/{record_id}",
            {"properties": {"bmst_estado_hunter": status, "bmst_data_hunter": today}},
        )
        logger.debug("update_lead_status: id=%s status=%s date=%s", record_id, status, today)
        return True
    except Exception as exc:
        logger.error("update_lead_status failed (id=%s): %s", record_id, exc)
        return False


async def mark_lead_response(record_id: str, response: str) -> bool:
    """Write the prospect's reply text to the Company's bmst_resposta property."""
    try:
        await _request(
            "PATCH",
            f"/crm/v3/objects/companies/{record_id}",
            {"properties": {"bmst_resposta": response}},
        )
        logger.debug("mark_lead_response: id=%s response_length=%d", record_id, len(response))
        return True
    except Exception as exc:
        logger.error("mark_lead_response failed (id=%s): %s", record_id, exc)
        return False


async def get_lead_by_whatsapp(phone: str) -> dict | None:
    """
    Find a Company lead by WhatsApp number. Used when a prospect reply arrives.

    Returns the lead dict (with "_row_index") or None if not found.
    """
    try:
        await ensure_schema()
        needle = _normalise_phone(phone)
        filters = [{"propertyName": "bmst_whatsapp", "operator": "EQ", "value": needle}]
        if needle != phone:
            # Also try the raw value in case it was stored unnormalised.
            filters_alt = [{"propertyName": "bmst_whatsapp", "operator": "EQ", "value": phone}]
            filter_groups = [{"filters": filters}, {"filters": filters_alt}]
        else:
            filter_groups = [{"filters": filters}]

        body = {
            "filterGroups": filter_groups,
            "properties": _READ_PROPERTIES,
            "limit": 1,
        }
        result = await _request("POST", "/crm/v3/objects/companies/search", body)
        records = result.get("results", [])
        if not records:
            logger.debug("get_lead_by_whatsapp: not found phone=%s", phone)
            return None

        lead = _company_to_lead(records[0])
        logger.debug("get_lead_by_whatsapp: found phone=%s id=%s", phone, lead["_row_index"])
        return lead

    except Exception as exc:
        logger.error("get_lead_by_whatsapp failed (phone=%s): %s", phone, exc)
        return None


async def append_lead_row(lead: dict) -> str | None:
    """
    Create a Company lead and an associated decision-maker Contact.

    Returns the new Company id (string), or None on failure. The Company id is
    used by callers exactly as the old sheet row index was.
    """
    try:
        await ensure_schema()

        # 1. Company — carries all firmographic + workflow fields.
        company_props = _lead_to_company_props(lead)
        company = await _request(
            "POST", "/crm/v3/objects/companies", {"properties": company_props}
        )
        company_id = company.get("id")
        if not company_id:
            logger.error("append_lead_row: no company id returned for empresa=%s",
                         lead.get("empresa", "?"))
            return None

        # 2. Contact — the decision-maker. Skipped if we have neither name nor phone.
        responsavel = (lead.get("responsavel") or "").strip()
        whatsapp    = (lead.get("whatsapp") or "").strip()
        if responsavel or whatsapp:
            first, _, last = responsavel.partition(" ")
            contact_props = {
                "firstname": first or responsavel,
                "lastname":  last,
                "phone":     whatsapp,
                "company":   lead.get("empresa", ""),
            }
            contact_props = {k: v for k, v in contact_props.items() if v}
            try:
                contact = await _request(
                    "POST", "/crm/v3/objects/contacts", {"properties": contact_props}
                )
                contact_id = contact.get("id")
                if contact_id:
                    # 3. Associate Contact ↔ Company (default association type).
                    await _request(
                        "PUT",
                        f"/crm/v4/objects/companies/{company_id}"
                        f"/associations/default/contacts/{contact_id}",
                        None,
                    )
            except Exception as exc:
                # Contact creation/association is non-fatal: the Company lead is the
                # source of truth and was already created.
                logger.warning(
                    "append_lead_row: contact create/associate failed (empresa=%s): %s",
                    lead.get("empresa", "?"), exc,
                )

        logger.info(
            "append_lead_row: created empresa=%s company_id=%s",
            lead.get("empresa", "?"), company_id,
        )
        return company_id

    except Exception as exc:
        logger.error("append_lead_row failed (empresa=%s): %s", lead.get("empresa", "?"), exc)
        return None


async def check_duplicate(empresa: str, phone: str) -> bool:
    """
    Return True if a Company with the same name OR WhatsApp number already exists.

    Safe default on error is False (do not block the lead), matching the old logic.
    """
    try:
        await ensure_schema()
        filter_groups = []
        if empresa and empresa.strip():
            filter_groups.append(
                {"filters": [{"propertyName": "name", "operator": "EQ", "value": empresa.strip()}]}
            )
        needle_phone = _normalise_phone(phone)
        if needle_phone:
            filter_groups.append(
                {"filters": [{"propertyName": "bmst_whatsapp", "operator": "EQ", "value": needle_phone}]}
            )
        if not filter_groups:
            return False

        body = {"filterGroups": filter_groups, "properties": ["name"], "limit": 1}
        result = await _request("POST", "/crm/v3/objects/companies/search", body)
        is_dup = bool(result.get("results"))
        if is_dup:
            logger.debug("check_duplicate: duplicate found empresa=%s phone=%s", empresa, phone)
        return is_dup

    except Exception as exc:
        logger.error("check_duplicate failed (empresa=%s phone=%s): %s", empresa, phone, exc)
        return False   # safe default: do not block lead on error
