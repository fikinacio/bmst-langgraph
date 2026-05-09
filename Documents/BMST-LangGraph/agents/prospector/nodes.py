# agents/prospector/nodes.py — PROSPECTOR agent node implementations

from __future__ import annotations

import asyncio
import logging
import re
from datetime import date

import httpx

from agents.prospector.state import ProspectorState
from agents.prospector.prompts import (
    SECTOR_POR_DIA,
    QUERIES_POR_SECTOR,
    CLASSIFICACAO_EMPRESA_PROMPT,
    ClassificacaoEmpresaSchema,
)
from core.llm import create_json_message
from core import sheets_client, telegram_client

logger = logging.getLogger(__name__)

_AGENT = "prospector"
_PLACES_BASE = "https://maps.googleapis.com/maps/api/place"
_LUANDA_LATLNG = "-8.8390,13.2894"   # Luanda city centre
_PLACES_RADIUS = 50000                # 50 km radius


# ── Internal helpers ──────────────────────────────────────────────────────────

def _format_whatsapp_angola(phone: str) -> str | None:
    """
    Normalise a phone number to E.164 format for Angola (+244XXXXXXXXX).

    Returns None if the number cannot be formatted as a valid Angolan number.
    """
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("244") and len(digits) == 12:
        return f"+{digits}"
    if len(digits) == 9 and digits[0] in "29":
        return f"+244{digits}"
    return None


async def _search_places(query: str, api_key: str) -> list[dict]:
    """Call the Google Places Text Search API and return raw place results."""
    params = {
        "query": query,
        "location": _LUANDA_LATLNG,
        "radius": _PLACES_RADIUS,
        "key": api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{_PLACES_BASE}/textsearch/json", params=params)
            r.raise_for_status()
            data = r.json()
        results = data.get("results", [])
        logger.info("_search_places: query=%r → %d results", query, len(results))
        return results
    except Exception as exc:
        logger.error("_search_places failed (query=%r): %s", query, exc)
        return []


async def _get_place_details(place_id: str, api_key: str) -> dict:
    """Fetch phone number and website for a place via the Place Details API."""
    params = {
        "place_id": place_id,
        "fields": "name,formatted_phone_number,website,formatted_address,rating,user_ratings_total,types",
        "key": api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{_PLACES_BASE}/details/json", params=params)
            r.raise_for_status()
            return r.json().get("result", {})
    except Exception as exc:
        logger.error("_get_place_details failed (place_id=%s): %s", place_id, exc)
        return {}


# ── Node 1: determinar_sector ─────────────────────────────────────────────────

async def determinar_sector(state: ProspectorState) -> dict:
    """Determine the sector of the day from the weekly calendar."""
    sector = (state.get("sector") or "").strip()
    if not sector:
        weekday = date.today().weekday()   # 0=Monday … 4=Friday
        if weekday >= 5:
            logger.info("prospector.determinar_sector: weekend — skipping")
            return {"sector_do_dia": "", "erro": "weekend"}
        sector = SECTOR_POR_DIA.get(weekday, "Retalho e Distribuição")

    logger.info("prospector.determinar_sector: sector=%s", sector)
    return {"sector_do_dia": sector, "erro": None}


# ── Node 2: buscar_empresas ───────────────────────────────────────────────────

async def buscar_empresas(state: ProspectorState) -> dict:
    """Search Google Places for companies in the sector of the day."""
    from core.settings import settings

    api_key = settings.GOOGLE_PLACES_API_KEY
    if not api_key:
        logger.error("prospector.buscar_empresas: GOOGLE_PLACES_API_KEY not set")
        return {"companies_raw": [], "erro": "GOOGLE_PLACES_API_KEY not configured"}

    sector = state.get("sector_do_dia", "")
    city   = state.get("city") or "Luanda"
    queries = QUERIES_POR_SECTOR.get(sector, [f"empresas {city}"])

    # Run all queries concurrently, deduplicate by place_id
    all_results = await asyncio.gather(*[
        _search_places(f"{q} {city}" if city.lower() not in q.lower() else q, api_key)
        for q in queries
    ])

    seen_ids: set[str] = set()
    companies: list[dict] = []
    for batch in all_results:
        for place in batch:
            pid = place.get("place_id", "")
            if pid and pid not in seen_ids:
                seen_ids.add(pid)
                companies.append(place)

    logger.info(
        "prospector.buscar_empresas: sector=%s → %d unique companies found",
        sector, len(companies),
    )
    return {"companies_raw": companies}


# ── Node 3: classificar_e_filtrar ────────────────────────────────────────────

async def classificar_e_filtrar(state: ProspectorState) -> dict:
    """
    For each company from Google Places:
    1. Fetch phone/website details
    2. Skip if no Angolan phone number found
    3. Use LLM to classify segment and generate approach notes
    4. Skip Seg A companies
    5. Check for duplicates in the Sheet
    """
    from core.settings import settings

    api_key  = settings.GOOGLE_PLACES_API_KEY
    sheet_id = settings.GOOGLE_SHEETS_ID
    sector   = state.get("sector_do_dia", "")
    max_co   = state.get("max_companies") or 20
    raw      = state.get("companies_raw") or []

    leads_qualificados: list[dict] = []
    ignorados = 0

    for place in raw:
        if len(leads_qualificados) >= max_co:
            break

        place_id = place.get("place_id", "")
        nome     = place.get("name", "")

        # Fetch detailed info (phone, website)
        details = await _get_place_details(place_id, api_key) if place_id else {}
        phone_raw = details.get("formatted_phone_number", "") or place.get("formatted_phone_number", "")
        whatsapp  = _format_whatsapp_angola(phone_raw)

        if not whatsapp:
            logger.debug("prospector: skipping %s — no Angolan phone number", nome)
            ignorados += 1
            continue

        # Check for duplicates in the sheet
        is_dup = await sheets_client.check_duplicate(sheet_id, nome, whatsapp)
        if is_dup:
            logger.info("prospector: skipping %s — duplicate in sheet", nome)
            ignorados += 1
            continue

        # Build context for LLM classification
        website  = details.get("website", "") or ""
        address  = details.get("formatted_address", "") or place.get("formatted_address", "")
        rating   = details.get("rating", "")
        n_reviews = details.get("user_ratings_total", "")

        user_prompt = (
            f"Empresa: {nome}\n"
            f"Sector: {sector}\n"
            f"Localização: {address}\n"
            f"Website: {website or 'não encontrado'}\n"
            f"Telefone: {phone_raw}\n"
            f"Avaliação Google: {rating}/5 ({n_reviews} avaliações)\n"
        )

        try:
            classificacao = await create_json_message(
                system=CLASSIFICACAO_EMPRESA_PROMPT,
                user=user_prompt,
                schema=ClassificacaoEmpresaSchema,
                model="haiku",
                agent_name=_AGENT,
                node_name="classificar_empresa",
            )
        except Exception as exc:
            logger.error("prospector: LLM classification failed for %s: %s", nome, exc)
            ignorados += 1
            continue

        if not classificacao.qualificado or classificacao.segmento == "A":
            logger.info("prospector: %s → Seg A / not qualified — skipping", nome)
            ignorados += 1
            continue

        lead = {
            "empresa":         nome,
            "sector":          sector,
            "segmento":        classificacao.segmento,
            "responsavel":     "A confirmar",
            "cargo":           "",
            "whatsapp":        whatsapp,
            "email":           "",
            "website":         website,
            "instagram":       "",
            "localizacao":     address,
            "nr_funcionarios": "",
            "servico_bmst":    classificacao.servico_bmst,
            "pain_point":      classificacao.pain_point,
            "valor_est_aoa":   classificacao.valor_est_aoa,
            "notas_abordagem": classificacao.notas_abordagem,
            "notas":           classificacao.notas_seg_c or "",
            "oportunidade":    classificacao.oportunidade,
            "fonte":           "Google Places",
        }
        leads_qualificados.append(lead)
        logger.info(
            "prospector: %s → Seg %s ✓ (whatsapp=%s)",
            nome, classificacao.segmento, whatsapp,
        )

    logger.info(
        "prospector.classificar_e_filtrar: qualified=%d ignored=%d",
        len(leads_qualificados), ignorados,
    )
    return {
        "leads_qualificados": leads_qualificados,
        "leads_ignorados":    ignorados,
    }


# ── Node 4: escrever_no_sheet ─────────────────────────────────────────────────

async def escrever_no_sheet(state: ProspectorState) -> dict:
    """Write qualified leads to the Google Sheet."""
    from core.settings import settings

    leads = state.get("leads_qualificados") or []
    if not leads:
        logger.info("prospector.escrever_no_sheet: no leads to write")
        return {"leads_escritos": 0}

    sheet_id = settings.GOOGLE_SHEETS_ID
    escritos = await sheets_client.append_leads(sheet_id, leads)
    logger.info("prospector.escrever_no_sheet: %d leads written", escritos)
    return {"leads_escritos": escritos}


# ── Node 5: enviar_relatorio ──────────────────────────────────────────────────

async def enviar_relatorio(state: ProspectorState) -> dict:
    """Send the daily PROSPECTOR report to the founder via Telegram."""
    sector   = state.get("sector_do_dia", "—")
    today    = date.today()
    dia_ptbr = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][today.weekday()]

    leads    = state.get("leads_qualificados") or []
    escritos = state.get("leads_escritos", 0)
    ignorados = state.get("leads_ignorados", 0)
    total_encontrados = len(state.get("companies_raw") or [])
    erro     = state.get("erro")

    if erro == "weekend":
        msg = (
            f"📅 <b>PROSPECTOR — {dia_ptbr} {today.isoformat()}</b>\n\n"
            f"🚫 Fim de semana — sem prospecção hoje."
        )
        try:
            await telegram_client.send_message(msg)
        except Exception as exc:
            logger.error("enviar_relatorio: telegram failed: %s", exc)
        return {}

    if erro and erro != "weekend":
        msg = (
            f"🔴 <b>PROSPECTOR — Erro</b>\n\n"
            f"<b>Sector:</b> {sector}\n"
            f"<b>Erro:</b> {erro}\n"
            f"<b>Data:</b> {today.isoformat()}"
        )
        try:
            await telegram_client.send_message(msg)
        except Exception as exc:
            logger.error("enviar_relatorio: telegram failed: %s", exc)
        return {}

    # Build leads detail list (max 10 lines to keep Telegram message manageable)
    seg_b = [l for l in leads if l.get("segmento") == "B"]
    seg_c = [l for l in leads if l.get("segmento") == "C"]

    leads_linhas = ""
    for lead in leads[:10]:
        seg_flag = " ⚠️" if lead.get("segmento") == "C" else ""
        leads_linhas += (
            f"• <b>{lead['empresa']}</b> — Seg {lead['segmento']}{seg_flag}\n"
            f"  {lead.get('pain_point', '')[:80]}\n"
        )

    seg_c_linhas = ""
    for lead in seg_c:
        seg_c_linhas += (
            f"• {lead['empresa']} — {lead.get('whatsapp', '')} — {lead.get('pain_point', '')[:60]}\n"
        )

    msg = (
        f"🔍 <b>PROSPECTOR — {dia_ptbr} {today.isoformat()}</b>\n"
        f"Sector: <b>{sector}</b>\n\n"
        f"📊 <b>RESULTADOS:</b>\n"
        f"📍 Google Places: {total_encontrados} empresas encontradas\n"
        f"✅ Inseridas: <b>{escritos}</b> leads"
        + (f" (Seg B: {len(seg_b)} | Seg C: {len(seg_c)})" if leads else "") + "\n"
        f"❌ Descartadas: <b>{ignorados}</b> (Seg A / Sem WhatsApp / Duplicadas)\n"
    )

    if leads_linhas:
        msg += f"\n📋 <b>LEADS HOJE:</b>\n{leads_linhas}"

    if seg_c_linhas:
        msg += f"\n⚠️ <b>ESCALAR (Seg C — aguarda aprovação):</b>\n{seg_c_linhas}"

    msg += f"\n✅ Sheet actualizado. HUNTER processa às 09h00."

    try:
        await telegram_client.send_message(msg)
        logger.info("prospector.enviar_relatorio: report sent for %s", today.isoformat())
    except Exception as exc:
        logger.error("prospector.enviar_relatorio: telegram failed: %s", exc)

    return {}
