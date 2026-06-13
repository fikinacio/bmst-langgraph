# agents/prospector/nodes.py — PROSPECTOR agent node implementations

from __future__ import annotations

import logging

from agents.prospector.state import ProspectorState
from agents.prospector.prompts import (
    QUALIFICACAO_PROMPT,
    HOOK_GENERATION_PROMPT,
    QualificacaoSchema,
)
from core.llm import create_json_message, create_message
from core import hubspot_client

logger = logging.getLogger(__name__)

_AGENT    = "prospector"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _lead_atual(state: ProspectorState) -> dict:
    leads = state.get("leads_raw") or []
    idx   = state.get("leads_processados") or 0
    return leads[idx] if idx < len(leads) else {}


def _build_company_context(state: ProspectorState) -> str:
    """Build the user prompt for the LLM from available company fields."""
    parts = [
        f"Company: {state.get('empresa') or 'unknown'}",
        f"Sector: {state.get('sector') or 'unknown'}",
    ]
    if state.get("responsavel"):
        parts.append(f"Decision-maker: {state['responsavel']}")
    if state.get("localizacao"):
        parts.append(f"Location: {state['localizacao']}")
    if state.get("nr_funcionarios"):
        parts.append(f"Employees: {state['nr_funcionarios']}")
    if state.get("website"):
        parts.append(f"Website: {state['website']}")
    if state.get("instagram"):
        parts.append(f"Instagram: {state['instagram']}")
    if state.get("notas_manuais"):
        parts.append(f"Notes: {state['notas_manuais']}")
    return "\n".join(parts)


# ── Node: preparar_lead_raw ───────────────────────────────────────────────────

async def preparar_lead_raw(state: ProspectorState) -> dict:
    """
    Copy the current raw lead into the top-level state fields.

    This is the loop entry point. Every iteration resets all processing fields
    so stale data from the previous lead cannot bleed into the next one.
    """
    lead = _lead_atual(state)
    if not lead:
        logger.error(
            "prospector.preparar_lead_raw: no lead at index %d",
            state.get("leads_processados", 0),
        )
        return {"proxima_acao": "finalizar"}

    idx   = (state.get("leads_processados") or 0) + 1
    total = len(state.get("leads_raw") or [])
    logger.info(
        "prospector.preparar_lead_raw: [%d/%d] empresa=%s sector=%s",
        idx, total, lead.get("empresa"), lead.get("sector"),
    )

    return {
        "empresa":         lead.get("empresa", ""),
        "sector":          lead.get("sector", ""),
        "responsavel":     lead.get("responsavel") or None,
        "whatsapp":        lead.get("whatsapp") or None,
        "website":         lead.get("website") or None,
        "instagram":       lead.get("instagram") or None,
        "localizacao":     lead.get("localizacao") or None,
        "nr_funcionarios": lead.get("nr_funcionarios") or None,
        "fonte":           lead.get("fonte") or "manual",
        "notas_manuais":   lead.get("notas_manuais") or None,
        # Reset processing fields
        "pain_points":      [],
        "presenca_resumo":  None,
        "segmento":         None,
        "valor_est_aoa":    None,
        "oportunidade":     None,
        "servico_bmst":     None,
        "notas_abordagem":  None,
        "qualificado":      None,
        "motivo_rejeicao":  None,
        "lead_gravado":     False,
        "proxima_acao":     None,
        "erro":             None,
    }


# ── Node: verificar_duplicado ─────────────────────────────────────────────────

async def verificar_duplicado(state: ProspectorState) -> dict:
    """
    Check whether this empresa/phone already exists in HubSpot.

    Duplicates are skipped — we set proxima_acao="duplicado" so the graph
    routes straight to avancar_lead without calling the LLM or writing to HubSpot.
    """
    empresa = state.get("empresa", "")
    phone   = state.get("whatsapp", "")

    if not empresa and not phone:
        return {"proxima_acao": "qualificar"}

    is_dup = await hubspot_client.check_duplicate(empresa, phone)
    if is_dup:
        logger.info(
            "prospector.verificar_duplicado: DUPLICATE empresa=%s phone=%s — skipping",
            empresa, phone,
        )
        return {
            "qualificado":    False,
            "motivo_rejeicao": "duplicate — already in HubSpot",
            "proxima_acao":   "duplicado",
        }

    return {"proxima_acao": "qualificar"}


# ── Node: analisar_e_qualificar ───────────────────────────────────────────────

async def analisar_e_qualificar(state: ProspectorState) -> dict:
    """
    Use the LLM to classify the lead (A/B/C), identify pain points, recommend
    a BMST service, and estimate deal value.

    A Segment A result sets qualificado=False and routes to registar_lead
    (archived) without generating a hook.
    """
    context = _build_company_context(state)
    logger.info(
        "prospector.analisar_e_qualificar: empresa=%s", state.get("empresa")
    )

    qualificacao = await create_json_message(
        system=QUALIFICACAO_PROMPT,
        user=f"Analyse this lead:\n\n{context}",
        schema=QualificacaoSchema,
        model="haiku",
        agent_name=_AGENT,
        node_name="analisar_e_qualificar",
    )

    logger.info(
        "prospector.analisar_e_qualificar: empresa=%s seg=%s qualificado=%s valor=%d",
        state.get("empresa"),
        qualificacao.segmento,
        qualificacao.qualificado,
        qualificacao.valor_est_aoa,
    )

    result = {
        "segmento":        qualificacao.segmento,
        "qualificado":     qualificacao.qualificado,
        "motivo_rejeicao": qualificacao.motivo_rejeicao,
        "pain_points":     qualificacao.pain_points,
        "oportunidade":    qualificacao.oportunidade,
        "servico_bmst":    qualificacao.servico_bmst,
        "valor_est_aoa":   qualificacao.valor_est_aoa,
        "presenca_resumo": qualificacao.presenca_resumo,
    }

    if not qualificacao.qualificado or qualificacao.segmento == "A":
        result["proxima_acao"] = "arquivar"
    else:
        result["proxima_acao"] = "gerar_hook"

    return result


# ── Node: gerar_hook ──────────────────────────────────────────────────────────

async def gerar_hook(state: ProspectorState) -> dict:
    """
    Generate the notas_abordagem hook that the HUNTER will use as its opening line.

    Uses Sonnet (not Haiku) because the quality of this text directly determines
    whether the REVISOR escalates the message to the founder.
    """
    context = _build_company_context(state)
    pain_str = "\n".join(f"- {p}" for p in (state.get("pain_points") or []))
    presenca = state.get("presenca_resumo") or "No detailed digital presence data available."

    logger.info("prospector.gerar_hook: empresa=%s", state.get("empresa"))

    hook = await create_message(
        system=HOOK_GENERATION_PROMPT,
        user=(
            f"Company data:\n{context}\n\n"
            f"Digital presence summary: {presenca}\n\n"
            f"Identified pain points:\n{pain_str}\n\n"
            f"Opportunity: {state.get('oportunidade', '')}"
        ),
        model="sonnet",
        agent_name=_AGENT,
        node_name="gerar_hook",
    )

    logger.info(
        "prospector.gerar_hook: empresa=%s hook_length=%d",
        state.get("empresa"), len(hook),
    )

    return {"notas_abordagem": hook.strip()}


# ── Node: registar_lead ───────────────────────────────────────────────────────

async def registar_lead(state: ProspectorState) -> dict:
    """
    Write the enriched lead data to HubSpot (Company + associated Contact).

    Segment A leads are written with estado_hunter="arquivado" (for record keeping).
    Segment B/C leads are written with estado_hunter="pendente" so the HUNTER picks them up.
    """
    from datetime import date

    estado = "pendente" if state.get("qualificado") else "arquivado"

    import uuid
    lead_row = {
        "id":               str(uuid.uuid4())[:8],
        "data_registo":     date.today().isoformat(),
        "empresa":          state.get("empresa", ""),
        "sector":           state.get("sector", ""),
        "responsavel":      state.get("responsavel", ""),
        "whatsapp":         state.get("whatsapp", ""),
        "website":          state.get("website", ""),
        "instagram":        state.get("instagram", ""),
        "localizacao":      state.get("localizacao", ""),
        "nr_funcionarios":  state.get("nr_funcionarios", ""),
        "segmento":         state.get("segmento", ""),
        "servico_bmst":     state.get("servico_bmst", ""),
        "oportunidade":     state.get("oportunidade", ""),
        "notas_abordagem":  state.get("notas_abordagem", ""),
        "valor_est_aoa":    state.get("valor_est_aoa", ""),
        "fonte":            state.get("fonte", "manual"),
        "estado_hunter":    estado,
        "data_hunter":      date.today().isoformat() if estado == "arquivado" else "",
        "resposta":         "",
    }

    logger.info(
        "prospector.registar_lead: empresa=%s estado=%s",
        state.get("empresa"), estado,
    )

    row_index = await hubspot_client.append_lead_row(lead_row)

    if row_index:
        return {"lead_gravado": True, "proxima_acao": "proximo_lead"}

    logger.error(
        "prospector.registar_lead: append failed for empresa=%s", state.get("empresa")
    )
    return {
        "lead_gravado": False,
        "erro":         "hubspot_append_failed",
        "proxima_acao": "proximo_lead",
    }


# ── Node: avancar_lead ────────────────────────────────────────────────────────

async def avancar_lead(state: ProspectorState) -> dict:
    """
    Increment the lead counter and decide whether to loop or finish.
    """
    processados = (state.get("leads_processados") or 0) + 1
    gravados    = (state.get("leads_gravados") or 0) + (1 if state.get("lead_gravado") else 0)
    total       = len(state.get("leads_raw") or [])
    proxima     = "continuar" if processados < total else "finalizar"

    logger.info(
        "prospector.avancar_lead: %d/%d gravados=%d → %s",
        processados, total, gravados, proxima,
    )

    return {
        "leads_processados": processados,
        "leads_gravados":    gravados,
        "proxima_acao":      proxima,
    }


# ── Node: gerar_relatorio ─────────────────────────────────────────────────────

async def gerar_relatorio(state: ProspectorState) -> dict:
    """Send a brief PROSPECTOR completion summary to the founder via Telegram."""
    from core import telegram_client

    total     = len(state.get("leads_raw") or [])
    gravados  = state.get("leads_gravados") or 0
    pendentes = gravados  # all gravados with estado=pendente are ready for HUNTER

    msg = (
        f"✅ <b>PROSPECTOR — Batch concluído</b>\n\n"
        f"Leads recebidos: {total}\n"
        f"Gravados na sheet: {gravados}\n"
        f"Prontos para o HUNTER: {pendentes}\n\n"
        f"O HUNTER irá processar os leads quando o batch diário for activado."
    )

    try:
        await telegram_client.send_message(msg)
        logger.info("prospector.gerar_relatorio: report sent (%d/%d)", gravados, total)
    except Exception as exc:
        logger.error("prospector.gerar_relatorio: telegram failed: %s", exc)

    return {}
