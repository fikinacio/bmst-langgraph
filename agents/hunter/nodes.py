# agents/hunter/nodes.py — HUNTER agent node implementations

from __future__ import annotations

import asyncio
import logging
import os
import time

from agents.hunter.state import HunterState
from agents.hunter.prompts import (
    TRIAGEM_PROMPT,
    SELECAO_TEMPLATE_PROMPT,
    GERACAO_MENSAGEM_PROMPT,
    TriagemSchema,
    SelecaoTemplateSchema,
)
from core.llm import create_json_message, create_message
from core.memory import update_lead_state, save_message, get_lead
from core.redis_client import is_duplicate, mark_sent, hash_message
from core import sheets_client, evolution_client, telegram_client

logger = logging.getLogger(__name__)

_SHEET_ID = os.environ.get("GOOGLE_SHEETS_ID", "")
_AGENT    = "hunter"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _lead_atual(state: HunterState) -> dict:
    """Return the lead dict currently being processed from the batch list."""
    leads = state.get("leads_pendentes") or []
    idx   = state.get("leads_processados") or 0
    return leads[idx] if idx < len(leads) else {}


def _extrair_campos_lead(lead: dict) -> dict:
    """Map Google Sheet column names to HunterState field names."""
    def _int(val) -> int | None:
        try:
            return int(str(val).replace(",", "").replace(".", "").strip())
        except (ValueError, TypeError):
            return None

    return {
        "lead_id":         str(lead.get("id", "")),
        "sheet_row_index": lead.get("_row_index"),
        "empresa":         lead.get("empresa", ""),
        "sector":          lead.get("sector", ""),
        "segmento":        lead.get("segmento", ""),
        "responsavel":     lead.get("responsavel", ""),
        "whatsapp":        lead.get("whatsapp", ""),
        "notas_abordagem": lead.get("notas_abordagem", ""),
        "oportunidade":    lead.get("oportunidade", ""),
        "servico_bmst":    lead.get("servico_bmst", ""),
        "valor_est_aoa":   _int(lead.get("valor_est_aoa")),
    }


def _parse_message_blocks(raw: str) -> tuple[str, str]:
    """
    Split LLM output into (mensagem_cliente, nota_interna).

    Expected format:
        ### MENSAGEM_CLIENTE
        [text]
        ---
        ### NOTA_INTERNA
        [text]
    """
    parts = raw.split("---")
    if len(parts) < 2:
        # Fallback: treat the whole output as the message
        return raw.strip(), ""

    mensagem_block = parts[0]
    nota_block     = parts[1]

    # Strip the ### header from each block
    mensagem = mensagem_block.replace("### MENSAGEM_CLIENTE", "").strip()
    nota     = nota_block.replace("### NOTA_INTERNA", "").strip()
    return mensagem, nota


def _validar_mensagem(mensagem: str) -> str | None:
    """
    Quick structural validation before sending to REVISOR.

    Returns None if valid, or a description of the first problem found.
    """
    lines = [l for l in mensagem.strip().splitlines() if l.strip()]
    if len(lines) > 6:
        return f"Message too long: {len(lines)} lines (max 5)"

    forbidden = [
        "inteligência artificial", "algoritmo", "chatbot", "machine learning",
        "n8n", "dify", " bot ", "automatizado",
    ]
    lower = mensagem.lower()
    for term in forbidden:
        if term in lower:
            return f"Contains forbidden term: '{term}'"

    if "fidel" not in lower:
        return "Missing signature (Fidel Kussunga / Bisca+)"

    return None   # valid


# ── Node: carregar_leads_sheet ────────────────────────────────────────────────

async def carregar_leads_sheet(state: HunterState) -> dict:
    """Load pending leads from Google Sheets. Entry point for the daily batch run."""
    logger.info("hunter.carregar_leads_sheet: fetching pending leads")

    leads = await sheets_client.get_pending_leads(_SHEET_ID)

    if not leads:
        logger.info("hunter.carregar_leads_sheet: no pending leads today")
        return {
            "leads_pendentes":   [],
            "leads_processados": 0,
            "mensagens_enviadas": 0,
            "proxima_acao":      "sem_leads_hoje",
        }

    logger.info("hunter.carregar_leads_sheet: loaded %d leads", len(leads))
    return {
        "leads_pendentes":   leads,
        "leads_processados": 0,
        "mensagens_enviadas": 0,
        "proxima_acao":      "tem_leads",
    }


# ── Node: preparar_lead_atual ─────────────────────────────────────────────────

async def preparar_lead_atual(state: HunterState) -> dict:
    """
    Copy the current lead's fields into the top-level state.

    This node is the loop entry point — every iteration starts here.
    It resets all processing fields so stale data from the previous
    lead cannot bleed into the current iteration.
    """
    lead = _lead_atual(state)
    if not lead:
        logger.error("hunter.preparar_lead_atual: no lead at index %d", state.get("leads_processados", 0))
        return {"proxima_acao": "sem_leads_hoje"}

    logger.info(
        "hunter.preparar_lead_atual: [%d/%d] empresa=%s segmento=%s",
        (state.get("leads_processados") or 0) + 1,
        len(state.get("leads_pendentes") or []),
        lead.get("empresa"),
        lead.get("segmento"),
    )

    return {
        **_extrair_campos_lead(lead),
        # Reset all processing fields for this iteration
        "qualificado":          None,
        "motivo_rejeicao":      None,
        "template_usado":       None,
        "mensagem_gerada":      None,
        "nota_interna":         None,
        "texto_original":       None,
        "texto_corrigido":      None,
        "status":               "pendente",
        "problemas_encontrados": [],
        "auto_correcoes":       [],
        "qualidade_estimada":   None,
        "motivo_escalonamento": None,
        "aprovacao_fundador":   None,
        "revisao_status":       None,
        "revisao_texto_final":  None,
        "revisao_notas":        None,
        "mensagem_enviada":     False,
        "whatsapp_message_id":  None,
        "proxima_acao":         None,
        "erro":                 None,
    }


# ── Node: confirmar_segmento ──────────────────────────────────────────────────

async def confirmar_segmento(state: HunterState) -> dict:
    """
    Use the LLM to confirm (or override) the PROSPECTOR's segment classification.

    Seg A → archive immediately, no contact.
    Seg C with 'escalar_fundador' flag → notify founder first.
    Seg B (or C without flag) → proceed to message generation.
    """
    triagem = await create_json_message(
        system=TRIAGEM_PROMPT,
        user=(
            f"Lead to triage:\n"
            f"- Company: {state.get('empresa')}\n"
            f"- Sector: {state.get('sector')}\n"
            f"- Segment (PROSPECTOR): {state.get('segmento')}\n"
            f"- Estimated value (AOA): {state.get('valor_est_aoa')}\n"
            f"- Notes: {state.get('notas_abordagem', '')[:500]}"
        ),
        schema=TriagemSchema,
        model="haiku",
        agent_name=_AGENT,
        node_name="confirmar_segmento",
    )

    logger.info(
        "hunter.confirmar_segmento: empresa=%s seg=%s qualificado=%s motivo=%s",
        state.get("empresa"), triagem.segmento_confirmado,
        triagem.qualificado, triagem.motivo,
    )

    if not triagem.qualificado or triagem.segmento_confirmado == "A":
        return {
            "segmento":       "A",
            "qualificado":    False,
            "motivo_rejeicao": triagem.motivo,
            "proxima_acao":   "arquivar",
        }

    # Segment C: check for the founder escalation flag
    if triagem.segmento_confirmado == "C":
        notas = (state.get("notas_abordagem") or "").lower()
        if "escalar_fundador: sim" in notas:
            return {
                "segmento":     "C",
                "qualificado":  True,
                "proxima_acao": "aguardar_aprovacao_seg_c",
            }

    return {
        "segmento":     triagem.segmento_confirmado,
        "qualificado":  True,
        "proxima_acao": "gerar_mensagem",
    }


# ── Node: gerar_mensagem_hunter ───────────────────────────────────────────────

async def gerar_mensagem_hunter(state: HunterState) -> dict:
    """
    Generate a personalised WhatsApp message using the sector template and lead notes.

    Steps:
      1. Validate that notas_abordagem is present (mandatory hook).
      2. Select the best template with Haiku (fast classification).
      3. Generate the final message with Sonnet (writing quality matters).
      4. Split output into MENSAGEM_CLIENTE and NOTA_INTERNA blocks.
      5. Run a quick structural validation before handing off to REVISOR.
    """
    notas = (state.get("notas_abordagem") or "").strip()
    if not notas:
        logger.warning("hunter.gerar_mensagem_hunter: notas_abordagem is empty for empresa=%s", state.get("empresa"))
        return {
            "qualificado":    False,
            "motivo_rejeicao": "notas_abordagem is empty — cannot personalise message",
            "proxima_acao":   "arquivar",
            "erro":           "notas_abordagem_vazio",
        }

    # Step 1: select template
    selecao = await create_json_message(
        system=SELECAO_TEMPLATE_PROMPT,
        user=(
            f"Lead details:\n"
            f"- Company: {state.get('empresa')}\n"
            f"- Sector: {state.get('sector')}\n"
            f"- Notes: {notas[:400]}"
        ),
        schema=SelecaoTemplateSchema,
        model="haiku",
        agent_name=_AGENT,
        node_name="selecionar_template",
    )
    logger.info(
        "hunter.gerar_mensagem_hunter: template=%s justificacao=%s",
        selecao.template, selecao.justificacao,
    )

    # Step 2: generate the full message (Sonnet — writing quality is critical)
    raw = await create_message(
        system=GERACAO_MENSAGEM_PROMPT,
        user=(
            f"Write a WhatsApp message for this lead:\n\n"
            f"Template to use: {selecao.template}\n"
            f"Company: {state.get('empresa')}\n"
            f"Sector: {state.get('sector')}\n"
            f"Segment: {state.get('segmento')}\n"
            f"Decision-maker: {state.get('responsavel') or 'unknown'}\n"
            f"notas_abordagem (MANDATORY hook): {notas}\n"
            f"Opportunity identified: {state.get('oportunidade') or 'not specified'}\n"
            f"Recommended BMST service: {state.get('servico_bmst') or 'not specified'}"
        ),
        model="sonnet",
        agent_name=_AGENT,
        node_name="gerar_mensagem",
    )

    # Step 3: parse the two output blocks
    mensagem, nota = _parse_message_blocks(raw)

    # Step 4: structural validation
    problema = _validar_mensagem(mensagem)
    if problema:
        logger.warning("hunter.gerar_mensagem_hunter: validation failed: %s", problema)
        return {
            "mensagem_gerada": mensagem,
            "nota_interna":    nota,
            "template_usado":  selecao.template,
            "erro":            f"mensagem_invalida: {problema}",
            "proxima_acao":    "arquivar",
        }

    return {
        "mensagem_gerada": mensagem,
        "nota_interna":    nota,
        "template_usado":  selecao.template,
        "erro":            None,
    }


# ── Node: preparar_para_revisor (bridge) ──────────────────────────────────────

async def preparar_para_revisor(state: HunterState) -> dict:
    """
    Bridge node: copy HunterState fields to REVISOR field names.

    The REVISOR nodes (avaliar_texto, auto_corrigir, etc.) read from
    state["texto_original"], state["status"] etc. This node ensures
    those keys are populated before the REVISOR nodes run.
    """
    return {
        "texto_original":           state["mensagem_gerada"],
        "status":                   "pendente",
        "texto_corrigido":          None,
        "problemas_encontrados":    [],
        "auto_correcoes":           [],
        "qualidade_estimada":       "alta",
        "aprovacao_fundador":       None,
        "motivo_escalonamento":     None,
        # Context dict read by send_approval_request in preparar_aprovacao
        "_revisor_contexto": {
            "empresa":  state.get("empresa", ""),
            "segmento": state.get("segmento", ""),
            "canal":    "WhatsApp",
            "agente":   "HUNTER",
        },
        # lead_id is read by save_revisao inside preparar_aprovacao
        "lead_id": state.get("lead_id", "unknown"),
    }


# ── Node: processar_resultado_revisor (bridge) ────────────────────────────────

async def processar_resultado_revisor(state: HunterState) -> dict:
    """
    Bridge node: copy REVISOR results back to HunterState summary fields.

    Runs after preparar_aprovacao (i.e. after the interrupt resumes).
    """
    from agents.revisor.nodes import _format_revisao_notes  # avoid circular import

    notas = _format_revisao_notes(state, state.get("status") == "escalado")

    return {
        "revisao_status":      state.get("status"),
        "revisao_texto_final": state.get("texto_corrigido") or state.get("texto_original"),
        "revisao_notas":       notas,
    }


# ── Node: arquivar_lead ───────────────────────────────────────────────────────

async def arquivar_lead(state: HunterState) -> dict:
    """Archive the current lead in the Google Sheet and Supabase."""
    phone = state.get("whatsapp", "")
    row   = state.get("sheet_row_index")

    if row:
        await sheets_client.update_lead_status(_SHEET_ID, row, "arquivado")
    if phone:
        await update_lead_state(phone, "arquivado", _AGENT)

    logger.info(
        "hunter.arquivar_lead: empresa=%s motivo=%s",
        state.get("empresa"), state.get("motivo_rejeicao") or "founder rejected",
    )
    return {"proxima_acao": "proximo_lead"}


# ── Node: notificar_seg_c ─────────────────────────────────────────────────────

async def notificar_seg_c(state: HunterState) -> dict:
    """Notify the founder about a Segment C lead requiring pre-approval."""
    msg = (
        f"⚠️ <b>HUNTER — Seg C Pre-Approval Required</b>\n\n"
        f"<b>Company:</b> {state.get('empresa')}\n"
        f"<b>Sector:</b> {state.get('sector')}\n"
        f"<b>Est. value:</b> {state.get('valor_est_aoa', 0):,} AOA\n\n"
        f"<b>Hook identified:</b>\n{state.get('notas_abordagem', '')[:400]}\n\n"
        f"Reply to this message to approve outreach for this lead."
    )
    try:
        await telegram_client.send_message(msg)
    except Exception as exc:
        logger.error("hunter.notificar_seg_c: telegram failed: %s", exc)

    return {"proxima_acao": "proximo_lead"}


# ── Node: enviar_whatsapp ─────────────────────────────────────────────────────

async def enviar_whatsapp(state: HunterState) -> dict:
    """
    Send the approved message via Evolution API.

    Guards:
      - aprovacao_fundador must be True
      - Deduplication check via Redis (prevents resend of same message)
      - 90-second delay after sending (anti-spam, run in background thread)
    """
    if not state.get("aprovacao_fundador"):
        logger.warning("hunter.enviar_whatsapp: no founder approval — skipping send")
        return {"proxima_acao": "proximo_lead"}

    phone   = state.get("whatsapp", "")
    texto   = state.get("revisao_texto_final") or state.get("texto_corrigido") or state.get("mensagem_gerada", "")
    msg_hash = hash_message(texto)

    # Deduplication check
    if is_duplicate(phone, msg_hash):
        logger.warning("hunter.enviar_whatsapp: duplicate detected for phone=%s — skipping", phone)
        return {"proxima_acao": "proximo_lead", "erro": "duplicate_message"}

    try:
        result = await evolution_client.send_text_message(phone, texto)
        message_id = result.get("key", {}).get("id") or result.get("messageId", "")
    except Exception as exc:
        logger.error("hunter.enviar_whatsapp: send failed (phone=%s): %s", phone, exc)
        return {"erro": f"whatsapp_send_failed: {exc}", "proxima_acao": "proximo_lead"}

    # Mark as sent in Redis (24h dedup window)
    mark_sent(phone, msg_hash)

    # Update Google Sheet status
    row = state.get("sheet_row_index")
    if row:
        await sheets_client.update_lead_status(_SHEET_ID, row, "enviado")

    # Persist to Supabase
    await save_message(phone, "assistant", texto, _AGENT)

    # Update lead state in Supabase
    await update_lead_state(phone, "enviado", _AGENT)

    logger.info("hunter.enviar_whatsapp: sent to %s (message_id=%s)", phone, message_id)

    # Anti-spam delay: 90 seconds between messages, non-blocking
    await asyncio.to_thread(time.sleep, 90)

    return {
        "mensagem_enviada":    True,
        "whatsapp_message_id": message_id,
        "proxima_acao":        "proximo_lead",
    }


# ── Node: avancar_lead ────────────────────────────────────────────────────────

async def avancar_lead(state: HunterState) -> dict:
    """
    Increment the lead counter and update batch statistics.

    This node is the loop junction: after processing, it decides whether
    to loop back (more leads) or exit to the daily report.
    """
    processados = (state.get("leads_processados") or 0) + 1
    enviadas    = (state.get("mensagens_enviadas") or 0) + (1 if state.get("mensagem_enviada") else 0)

    total = len(state.get("leads_pendentes") or [])
    proxima = "continuar" if processados < total else "finalizar"

    logger.info(
        "hunter.avancar_lead: %d/%d processados=%d enviadas=%d → %s",
        processados, total, processados, enviadas, proxima,
    )
    return {
        "leads_processados": processados,
        "mensagens_enviadas": enviadas,
        "proxima_acao":       proxima,
    }


# ── Node: processar_resposta ──────────────────────────────────────────────────

async def processar_resposta(state: HunterState) -> dict:
    """
    Classify a prospect's WhatsApp reply and route accordingly.

    Called when a webhook arrives from Evolution API (not part of the batch loop).
    """
    resposta = state.get("nota_interna") or ""   # reused field for incoming text in webhook mode
    phone    = state.get("whatsapp", "")

    classificacao_raw = await create_message(
        system=(
            "Classify this WhatsApp reply from a business prospect into exactly one category:\n"
            "INTERESSADO   — shows genuine interest, asks questions, suggests a meeting\n"
            "NEUTRO        — polite but non-committal ('ok', 'obrigado', 'já vi')\n"
            "NAO_INTERESSADO — explicitly declines or says not the right time\n"
            "SEM_RESPOSTA  — empty or accidental message\n\n"
            "Respond with ONLY the category name. Nothing else."
        ),
        user=f"Reply received: {resposta}",
        model="haiku",
        agent_name=_AGENT,
        node_name="processar_resposta",
    )

    classificacao = classificacao_raw.strip().upper()
    if classificacao not in ("INTERESSADO", "NEUTRO", "NAO_INTERESSADO", "SEM_RESPOSTA"):
        classificacao = "NEUTRO"

    logger.info("hunter.processar_resposta: phone=%s classificacao=%s", phone, classificacao)

    # Update sheet and Supabase
    row = state.get("sheet_row_index")
    if row and resposta:
        await sheets_client.mark_lead_response(_SHEET_ID, row, resposta)
    if phone:
        await update_lead_state(phone, f"respondeu_{classificacao.lower()}", _AGENT)
        await save_message(phone, "user", resposta, "prospect")

    proxima = "passar_ao_closer" if classificacao == "INTERESSADO" else "proximo_lead"

    return {
        "proxima_acao": proxima,
        "nota_interna": classificacao,   # reuse field to signal classification result
    }


# ── Node: gerar_relatorio_diario ──────────────────────────────────────────────

async def gerar_relatorio_diario(state: HunterState) -> dict:
    """Format and send the daily HUNTER report to the founder via Telegram."""
    from datetime import date

    leads    = state.get("leads_pendentes") or []
    enviadas = state.get("mensagens_enviadas") or 0

    report = {
        "data":               date.today().isoformat(),
        "processados":        state.get("leads_processados") or 0,
        "enviadas":           enviadas,
        "aguardam":           0,    # populated when real-time tracking is added
        "arquivados":         sum(1 for l in leads if l.get("segmento") == "A"),
        "seg_c_pendentes":    sum(1 for l in leads if l.get("segmento") == "C"),
        "respostas":          0,
        "interessados":       0,
        "nomes_interessados": "",
        "neutros":            0,
        "nao_interessados":   0,
        "followups":          0,
    }

    try:
        await telegram_client.send_daily_report(report)
        logger.info("hunter.gerar_relatorio_diario: report sent for %s", report["data"])
    except Exception as exc:
        logger.error("hunter.gerar_relatorio_diario: telegram failed: %s", exc)

    return {}
