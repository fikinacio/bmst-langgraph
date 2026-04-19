# agents/closer/nodes.py — CLOSER agent node implementations
#
# Two interrupt() points:
#   1. preparar_aprovacao_apresentacao  → founder approves the verbal pitch angle
#   2. gerar_rascunho_proposta          → founder approves the full proposal JSON
#
# WhatsApp-reply interrupts (resuming via /closer/webhook):
#   - iniciar_diagnostico               → waits for P1 answer
#   - processar_resposta_diagnostico    → waits for P2, P3 answers (loops)
#   - processar_resposta_proposta       → waits for prospect reply after sending proposal

from __future__ import annotations

import asyncio
import json
import logging
import time

import httpx
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from agents.closer.state import CloserState
from agents.closer.prompts import (
    PERGUNTAS_DIAGNOSTICO,
    DIAGNOSTICO_EXTRACT_PROMPT,
    SELECAO_SOLUCAO_PROMPT,
    APRESENTACAO_VERBAL_PROMPT,
    GERACAO_PROPOSTA_PROMPT,
    CLASSIFICAR_RESPOSTA_PROMPT,
    GERIR_OBJECAO_PROMPT,
    DiagnosisExtractSchema,
    SolucaoSchema,
    PropostaDraftSchema,
    RespostaPropostaSchema,
    ObjecaoResponseSchema,
)
from core.llm import create_json_message, create_message
from core.memory import save_message, update_lead_state, save_revisao
from core import evolution_client, telegram_client
from core.settings import settings

logger = logging.getLogger(__name__)
_AGENT = "closer"


# ── Internal helpers ──────────────────────────────────────────────────────────

def _build_diagnostico_context(state: CloserState) -> str:
    """Format the Q&A pairs collected so far for LLM context."""
    pairs = zip(
        state.get("perguntas_feitas") or [],
        state.get("respostas_cliente") or [],
    )
    return "\n".join(
        f"Q{i+1}: {q}\nA{i+1}: {a}"
        for i, (q, a) in enumerate(pairs)
    )


async def _render_proposta_html(proposta: dict) -> str:
    """Generate a self-contained HTML document for the proposal PDF."""
    from datetime import date

    entregaveis = proposta.get("entregaveis", [])
    entregaveis_html = "".join(f"<li>{e}</li>" for e in entregaveis)

    return f"""<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; color: #333; }}
  h1 {{ color: #1a1a2e; border-bottom: 2px solid #e94560; padding-bottom: 8px; }}
  h2 {{ color: #16213e; font-size: 14px; margin-top: 24px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
  td {{ padding: 8px 12px; border: 1px solid #ddd; }}
  td:first-child {{ font-weight: bold; background: #f8f9fa; width: 35%; }}
  ul {{ padding-left: 20px; }}
  .footer {{ margin-top: 40px; font-size: 11px; color: #999; }}
</style>
</head>
<body>
<h1>Proposta Comercial — BMST Angola</h1>
<table>
  <tr><td>Cliente</td><td>{proposta.get('cliente', '—')}</td></tr>
  <tr><td>Decisor</td><td>{proposta.get('decisor', '—')}</td></tr>
  <tr><td>Serviço</td><td>{proposta.get('solucao_proposta', '—')}</td></tr>
  <tr><td>Valor</td><td>{proposta.get('valor_aoa', 0):,} AOA</td></tr>
  <tr><td>Prazo</td><td>{proposta.get('prazo_semanas', '—')} semanas</td></tr>
  <tr><td>Condições</td><td>{proposta.get('condicoes_pagamento', '—')}</td></tr>
  <tr><td>Validade</td><td>{proposta.get('validade_proposta_dias', 15)} dias</td></tr>
</table>
<h2>Problema Identificado</h2>
<p>{proposta.get('problema_identificado', '—')}</p>
<h2>Entregáveis</h2>
<ul>{entregaveis_html}</ul>
<div class="footer">
  BMST — Bisca Mais Sistemas e Tecnologias &nbsp;|&nbsp;
  Proposta gerada em {date.today().strftime('%d/%m/%Y')}
</div>
</body>
</html>"""


async def _upload_pdf_to_supabase(pdf_bytes: bytes, filename: str) -> str:
    """
    Upload a PDF to the Supabase 'propostas' storage bucket.

    Returns the public URL. The bucket must exist and have public-read access.
    Falls back to a local path string if Supabase storage fails.
    """
    try:
        from supabase import create_client
        client = await asyncio.to_thread(
            create_client, settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY
        )
        await asyncio.to_thread(
            client.storage.from_("propostas").upload,
            filename,
            pdf_bytes,
            {"content-type": "application/pdf"},
        )
        url = await asyncio.to_thread(
            client.storage.from_("propostas").get_public_url, filename
        )
        return url
    except Exception as exc:
        logger.warning("_upload_pdf_to_supabase failed — using fallback path: %s", exc)
        return f"local://{filename}"


# ── Node: iniciar_diagnostico ─────────────────────────────────────────────────

async def iniciar_diagnostico(state: CloserState) -> dict:
    """
    Send the first diagnostic question (P1) to the prospect via WhatsApp.

    After sending, interrupt() is called to pause the graph and wait for the
    prospect's reply.  The reply arrives via the /closer/webhook endpoint which
    calls Command(resume={"texto_prospect": "..."}).
    """
    phone    = state["phone"]
    empresa  = state["empresa"]
    sector   = state["sector"]

    # Generate a natural-sounding intro + P1 using Sonnet
    p1_raw = await create_message(
        system=APRESENTACAO_VERBAL_PROMPT,
        user=(
            f"Write ONLY the first diagnostic question for this prospect.\n"
            f"Company: {empresa}\n"
            f"Sector: {sector}\n"
            f"Question to ask (rephrase naturally): {PERGUNTAS_DIAGNOSTICO[0]}\n\n"
            f"Keep it to 2 short sentences maximum. No proposal. No closing."
        ),
        model="sonnet",
        agent_name=_AGENT,
        node_name="iniciar_diagnostico",
    )

    await evolution_client.send_text_message(phone, p1_raw.strip())
    await save_message(phone, "assistant", p1_raw.strip(), _AGENT)

    logger.info("closer.iniciar_diagnostico: P1 sent to %s (%s)", phone, empresa)

    # ── INTERRUPT: wait for P1 answer ────────────────────────────────────────
    resposta = interrupt({"fase": "diagnostico", "pergunta_num": 1})
    # ── RESUME POINT ─────────────────────────────────────────────────────────

    texto_prospect = resposta.get("texto_prospect", "")
    await save_message(phone, "user", texto_prospect, "prospect")

    logger.info("closer.iniciar_diagnostico: P1 answer received")

    return {
        "perguntas_feitas":  [p1_raw.strip()],
        "respostas_cliente": [texto_prospect],
        "proxima_acao":      "processar_resposta",
    }


# ── Node: processar_resposta_diagnostico ─────────────────────────────────────

async def processar_resposta_diagnostico(state: CloserState) -> dict:
    """
    Process the latest diagnostic answer, send the next question if needed,
    or mark diagnosis complete after 3 answered questions.

    Contains interrupt() calls for P2 and P3 — the graph loops back through this
    node via a backward edge until diagnostico_completo=True.
    """
    phone     = state["phone"]
    perguntas = state.get("perguntas_feitas") or []
    respostas = state.get("respostas_cliente") or []
    n         = len(perguntas)   # questions asked so far (1 or 2 at entry)

    context = _build_diagnostico_context(state)

    if n < 3:
        # Generate and send the next question
        next_q_raw = await create_message(
            system=APRESENTACAO_VERBAL_PROMPT,
            user=(
                f"Write ONLY the next diagnostic question.\n"
                f"Question to ask (rephrase naturally): {PERGUNTAS_DIAGNOSTICO[n]}\n"
                f"Previous exchange:\n{context}\n\n"
                f"1-2 sentences maximum. Acknowledge the previous answer briefly."
            ),
            model="haiku",   # classification-level task
            agent_name=_AGENT,
            node_name="processar_resposta_diagnostico",
        )
        next_q = next_q_raw.strip()

        await evolution_client.send_text_message(phone, next_q)
        await save_message(phone, "assistant", next_q, _AGENT)
        logger.info("closer.processar_resposta_diagnostico: Q%d sent", n + 1)

        # ── INTERRUPT: wait for next answer ──────────────────────────────────
        resposta = interrupt({"fase": "diagnostico", "pergunta_num": n + 1})
        # ── RESUME POINT ─────────────────────────────────────────────────────

        texto_prospect = resposta.get("texto_prospect", "")
        await save_message(phone, "user", texto_prospect, "prospect")

        return {
            "perguntas_feitas":  perguntas + [next_q],
            "respostas_cliente": respostas + [texto_prospect],
            "proxima_acao":      "continuar_diagnostico",
        }

    # All 3 questions answered — extract structured info with Haiku
    context_completo = _build_diagnostico_context(state)
    extract = await create_json_message(
        system=DIAGNOSTICO_EXTRACT_PROMPT,
        user=(
            f"Extract structured diagnosis for {state['empresa']} ({state['sector']}).\n\n"
            f"Full Q&A exchange:\n{context_completo}"
        ),
        schema=DiagnosisExtractSchema,
        model="haiku",
        agent_name=_AGENT,
        node_name="extrair_diagnostico",
    )

    logger.info(
        "closer.processar_resposta_diagnostico: complete — problema='%s'",
        extract.problema_principal,
    )

    return {
        "diagnostico_completo":  True,
        "problema_identificado": extract.problema_principal,
        "proxima_acao":          "seleccionar_solucao",
    }


# ── Node: seleccionar_solucao ─────────────────────────────────────────────────

async def seleccionar_solucao(state: CloserState) -> dict:
    """
    Map the identified problem to the most appropriate BMST service.

    Uses Sonnet to consider the full diagnosis and select a service with
    estimated price range and timeline.
    """
    context = _build_diagnostico_context(state)

    solucao = await create_json_message(
        system=SELECAO_SOLUCAO_PROMPT,
        user=(
            f"Select the best solution for:\n"
            f"Company: {state['empresa']}\n"
            f"Sector: {state['sector']}\n"
            f"Segment: {state['segmento']}\n"
            f"Problem identified: {state.get('problema_identificado', '')}\n\n"
            f"Full diagnostic exchange:\n{context}"
        ),
        schema=SolucaoSchema,
        model="sonnet",
        agent_name=_AGENT,
        node_name="seleccionar_solucao",
    )

    logger.info(
        "closer.seleccionar_solucao: %s | %s–%s AOA | %d weeks",
        solucao.servico_recomendado,
        f"{solucao.valor_minimo_aoa:,}",
        f"{solucao.valor_maximo_aoa:,}",
        solucao.prazo_semanas,
    )

    return {
        "servico_recomendado": solucao.servico_recomendado,
        "_solucao_cache": solucao.model_dump(),   # stored for use in apresentar_solucao_verbal
        "proxima_acao":   "apresentar_solucao",
    }


# ── Node: apresentar_solucao_verbal ──────────────────────────────────────────

async def apresentar_solucao_verbal(state: CloserState) -> dict:
    """
    Generate the verbal solution presentation text that will be sent to the
    prospect via WhatsApp.

    The generated text is passed to the REVISOR pipeline (preparar_para_revisor_closer
    bridge node follows immediately).  The REVISOR may auto-correct it or escalate
    to the founder for approval (interrupt #1).
    """
    solucao_cache = state.get("_solucao_cache") or {}

    texto = await create_message(
        system=APRESENTACAO_VERBAL_PROMPT,
        user=(
            f"Write the verbal solution presentation for:\n"
            f"Company: {state['empresa']} ({state['sector']})\n"
            f"Service: {solucao_cache.get('servico_recomendado', state.get('servico_recomendado', ''))}\n"
            f"Min price: {solucao_cache.get('valor_minimo_aoa', 180_000):,} AOA\n"
            f"Max price: {solucao_cache.get('valor_maximo_aoa', 400_000):,} AOA\n"
            f"Benefit 1: {solucao_cache.get('beneficio_1', '')}\n"
            f"Benefit 2: {solucao_cache.get('beneficio_2', '')}\n"
            f"Decision-maker: {state.get('responsavel', 'the decision-maker')}\n"
            f"Problem identified: {state.get('problema_identificado', '')}"
        ),
        model="sonnet",
        agent_name=_AGENT,
        node_name="apresentar_solucao_verbal",
    )

    logger.info(
        "closer.apresentar_solucao_verbal: generated %d chars", len(texto)
    )

    # texto_original is read by the REVISOR nodes in the next steps
    return {"texto_original": texto.strip()}


# ── Node: preparar_para_revisor_closer (REVISOR bridge — in) ─────────────────

async def preparar_para_revisor_closer(state: CloserState, config: RunnableConfig) -> dict:
    """
    Bridge node: set up REVISOR fields before the REVISOR pipeline runs.

    Also embeds the LangGraph thread_id so that preparar_aprovacao_apresentacao
    can send the Telegram approval request with the correct callback_data.
    """
    thread_id = config["configurable"].get("thread_id", "")

    return {
        "status":                "pendente",
        "texto_corrigido":       None,
        "problemas_encontrados": [],
        "auto_correcoes":        [],
        "qualidade_estimada":    "alta",
        "aprovacao_fundador":    None,
        "motivo_escalonamento":  None,
        "_revisor_contexto": {
            "empresa":   state.get("empresa", ""),
            "segmento":  state.get("segmento", ""),
            "canal":     "WhatsApp",
            "agente":    "CLOSER",
            "thread_id": thread_id,   # needed by preparar_aprovacao_apresentacao
        },
        "lead_id": state["phone"],    # phone used as lead_id for save_revisao
    }


# ── Node: preparar_aprovacao_apresentacao ─────────────────────────────────────

async def preparar_aprovacao_apresentacao(state: CloserState, config: RunnableConfig) -> dict:
    """
    CLOSER-specific approval node for the verbal presentation angle.

    Mirrors the REVISOR's preparar_aprovacao but:
      - Reads thread_id from RunnableConfig (not embedded in state)
      - Uses a CLOSER-specific Telegram message format
      - Interrupt #1: founder decides whether the approach angle is correct

    The interrupt resumes when the founder taps Approve / Edit / Reject
    on Telegram.  The /telegram/callback endpoint calls
    Command(resume={"aprovado": bool, "texto_editado": str | None}).
    """
    thread_id       = config["configurable"].get("thread_id", "")
    texto_proposto  = state.get("texto_corrigido") or state.get("texto_original", "")
    is_escalado     = state.get("status") == "escalado"

    # Build revision notes for the Telegram message
    from agents.revisor.nodes import _format_revisao_notes
    revisao_notas = _format_revisao_notes(state, is_escalado)

    # Save the review record (best-effort)
    try:
        await save_revisao(
            lead_id=state.get("lead_id", state["phone"]),
            texto_original=state.get("texto_original", ""),
            texto_final=texto_proposto,
            status=state.get("status", "pendente"),
            notas=revisao_notas,
        )
    except Exception as exc:
        logger.warning("preparar_aprovacao_apresentacao: save_revisao failed: %s", exc)

    # Send Telegram approval request with inline keyboard
    contexto = dict(state.get("_revisor_contexto") or {})
    message_id = await telegram_client.send_approval_request(
        mensagem_cliente=texto_proposto,
        contexto=contexto,
        revisao_notas=revisao_notas,
        thread_id=thread_id,
    )

    logger.info(
        "closer.preparar_aprovacao_apresentacao: Telegram sent (id=%s), entering interrupt",
        message_id,
    )

    # ── INTERRUPT #1: founder approves the verbal presentation angle ──────────
    decisao: dict = interrupt({
        "fase":                "aguarda_aprovacao_apresentacao",
        "telegram_message_id": message_id,
        "texto_proposto":      texto_proposto,
    })
    # ── RESUME POINT ─────────────────────────────────────────────────────────

    aprovado      = decisao.get("aprovado", False)
    texto_editado = decisao.get("texto_editado")
    final_text    = texto_editado or texto_proposto

    logger.info(
        "closer.preparar_aprovacao_apresentacao: aprovado=%s edited=%s",
        aprovado, bool(texto_editado),
    )

    return {
        "aprovacao_fundador": aprovado,
        "texto_corrigido":    final_text,
        "status":             "aprovado" if aprovado else "rejeitado",
        "proxima_acao":       "enviar_apresentacao" if aprovado else "perdido",
    }


# ── Node: processar_resultado_revisor_closer (REVISOR bridge — out) ───────────

async def processar_resultado_revisor_closer(state: CloserState) -> dict:
    """
    Bridge node: copy the REVISOR result to a dedicated field so subsequent
    CLOSER nodes don't accidentally read stale REVISOR state.

    Only runs when aprovacao_fundador=True (approved presentation).
    """
    from agents.revisor.nodes import _format_revisao_notes
    notas = _format_revisao_notes(state, state.get("status") == "escalado")

    return {
        "_texto_apresentacao_final": (
            state.get("texto_corrigido") or state.get("texto_original", "")
        ),
        "_revisao_notas_apresentacao": notas,
    }


# ── Node: enviar_apresentacao ─────────────────────────────────────────────────

async def enviar_apresentacao(state: CloserState) -> dict:
    """
    Send the approved verbal presentation to the prospect via WhatsApp.

    After sending, interrupt() waits for the prospect's reply (interest confirmation).
    The reply arrives via /closer/webhook with Command(resume={"texto_prospect": "..."}).
    """
    phone = state["phone"]
    texto = state.get("_texto_apresentacao_final") or state.get("texto_corrigido") or ""

    await evolution_client.send_text_message(phone, texto)
    await save_message(phone, "assistant", texto, _AGENT)

    logger.info("closer.enviar_apresentacao: sent to %s", phone)

    # ── INTERRUPT: wait for prospect's confirmation of interest ───────────────
    resposta = interrupt({"fase": "aguarda_confirmacao_interesse"})
    # ── RESUME POINT ─────────────────────────────────────────────────────────

    texto_prospect = resposta.get("texto_prospect", "")
    await save_message(phone, "user", texto_prospect, "prospect")

    # Quick classification: is the prospect interested in a full proposal?
    interesse_raw = await create_message(
        system=(
            "Classify the prospect's WhatsApp reply as INTERESSADO or NAO_INTERESSADO.\n"
            "INTERESSADO: any indication of yes, willingness, asking for the proposal.\n"
            "NAO_INTERESSADO: any indication of no, not now, not relevant.\n"
            "Respond with ONLY the category. Nothing else."
        ),
        user=f"Reply: {texto_prospect}",
        model="haiku",
        agent_name=_AGENT,
        node_name="classificar_interesse",
    )

    interessado = interesse_raw.strip().upper() == "INTERESSADO"
    logger.info("closer.enviar_apresentacao: prospect interest = %s", interessado)

    return {
        "proxima_acao": "gerar_proposta" if interessado else "perdido",
    }


# ── Node: gerar_rascunho_proposta ─────────────────────────────────────────────

async def gerar_rascunho_proposta(state: CloserState, config: RunnableConfig) -> dict:
    """
    Generate the full commercial proposal JSON draft, send it to the founder
    via Telegram for approval, then PAUSE until the founder responds.

    Interrupt #2: the founder taps Approve / Edit / Reject on Telegram.
    Resume via /telegram/callback with Command(resume={"aprovado": bool, "texto_editado": ...}).
    """
    thread_id = config["configurable"].get("thread_id", "")

    solucao_cache = state.get("_solucao_cache") or {}

    # Generate full proposal draft with Sonnet
    proposta_obj = await create_json_message(
        system=GERACAO_PROPOSTA_PROMPT,
        user=(
            f"Generate a complete proposal for:\n"
            f"Company: {state['empresa']}\n"
            f"Decision-maker: {state.get('responsavel', '—')}\n"
            f"Sector: {state['sector']}\n"
            f"Segment: {state['segmento']}\n"
            f"Problem identified: {state.get('problema_identificado', '')}\n"
            f"Recommended service: {state.get('servico_recomendado', '')}\n"
            f"Price range: {solucao_cache.get('valor_minimo_aoa', 180_000):,}–"
            f"{solucao_cache.get('valor_maximo_aoa', 400_000):,} AOA\n"
            f"Timeline: {solucao_cache.get('prazo_semanas', 4)} weeks\n"
            f"Diagnostic notes: {_build_diagnostico_context(state)}"
        ),
        schema=PropostaDraftSchema,
        model="sonnet",
        agent_name=_AGENT,
        node_name="gerar_rascunho_proposta",
    )

    rascunho = proposta_obj.model_dump()
    logger.info(
        "closer.gerar_rascunho_proposta: draft generated — %s | %s AOA",
        rascunho["solucao_proposta"],
        f"{rascunho['valor_aoa']:,}",
    )

    # Send to Telegram for founder approval
    message_id = await telegram_client.send_proposal_approval_request(
        proposta=rascunho,
        thread_id=thread_id,
    )

    logger.info(
        "closer.gerar_rascunho_proposta: Telegram sent (id=%s), entering interrupt",
        message_id,
    )

    # ── INTERRUPT #2: founder approves the full proposal ──────────────────────
    decisao: dict = interrupt({
        "fase":                "aguarda_aprovacao_proposta",
        "telegram_message_id": message_id,
        "rascunho":            rascunho,
    })
    # ── RESUME POINT ─────────────────────────────────────────────────────────

    aprovado      = decisao.get("aprovado", False)
    edicoes       = decisao.get("texto_editado")   # free-text edits from the founder

    logger.info(
        "closer.gerar_rascunho_proposta: fundador decision — aprovado=%s edicoes=%s",
        aprovado, bool(edicoes),
    )

    proxima: str
    if not aprovado:
        proxima = "perdido"
    elif edicoes:
        proxima = "incorporar_edicoes"
    else:
        proxima = "gerar_pdf"

    return {
        "rascunho_proposta": rascunho,
        "proposta_aprovada": aprovado,
        "edicoes_fundador":  edicoes,
        "proxima_acao":      proxima,
    }


# ── Node: incorporar_edicoes_fundador ─────────────────────────────────────────

async def incorporar_edicoes_fundador(state: CloserState) -> dict:
    """
    Apply the founder's free-text edits to the proposal draft.

    The founder's edits arrive as a natural-language string (e.g. "Change price
    to 350,000 AOA and reduce the timeline to 5 weeks").  Sonnet interprets the
    instruction and produces an updated proposal JSON.
    """
    rascunho = state.get("rascunho_proposta") or {}
    edicoes  = state.get("edicoes_fundador") or ""

    proposta_obj = await create_json_message(
        system=GERACAO_PROPOSTA_PROMPT,
        user=(
            f"Update the following proposal JSON based on the founder's instructions.\n\n"
            f"Current proposal:\n{json.dumps(rascunho, ensure_ascii=False, indent=2)}\n\n"
            f"Founder's instructions: {edicoes}\n\n"
            f"Apply ONLY the changes specified. Keep everything else identical."
        ),
        schema=PropostaDraftSchema,
        model="sonnet",
        agent_name=_AGENT,
        node_name="incorporar_edicoes_fundador",
    )

    rascunho_atualizado = proposta_obj.model_dump()
    logger.info(
        "closer.incorporar_edicoes_fundador: updated draft — new value=%s AOA",
        f"{rascunho_atualizado.get('valor_aoa', 0):,}",
    )

    return {
        "rascunho_proposta": rascunho_atualizado,
        "proxima_acao":      "gerar_pdf",
    }


# ── Node: gerar_pdf_proposta ──────────────────────────────────────────────────

async def gerar_pdf_proposta(state: CloserState) -> dict:
    """
    Generate a PDF from the approved proposal via Gotenberg, then upload it
    to Supabase Storage.

    Gotenberg (http://gotenberg.dev) converts HTML to PDF via headless Chromium.
    The 'propostas' storage bucket must exist and be public-readable in Supabase.
    """
    proposta = state.get("rascunho_proposta") or {}
    html     = await _render_proposta_html(proposta)

    gotenberg_url = settings.GOTENBERG_URL

    logger.info("closer.gerar_pdf_proposta: calling Gotenberg at %s", gotenberg_url)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{gotenberg_url}/forms/chromium/convert/html",
                files={"files": ("index.html", html.encode("utf-8"), "text/html")},
            )
            response.raise_for_status()
    except Exception as exc:
        logger.error("closer.gerar_pdf_proposta: Gotenberg call failed: %s", exc)
        return {"erro": f"pdf_generation_failed: {exc}", "pdf_url": None}

    pdf_bytes = response.content
    filename  = (
        f"proposta_{proposta.get('cliente', 'client').replace(' ', '_')}"
        f"_{int(time.time())}.pdf"
    )

    pdf_url = await _upload_pdf_to_supabase(pdf_bytes, filename)

    logger.info("closer.gerar_pdf_proposta: PDF ready at %s", pdf_url)

    return {"pdf_url": pdf_url, "proxima_acao": "enviar_proposta"}


# ── Node: enviar_proposta_cliente ─────────────────────────────────────────────

async def enviar_proposta_cliente(state: CloserState) -> dict:
    """
    Send the cover message and PDF to the prospect via WhatsApp.

    The cover message is a template-based text matching Template 7 from the
    BMST content library.  The PDF is sent as a document.
    """
    phone    = state["phone"]
    proposta = state.get("rascunho_proposta") or {}
    pdf_url  = state.get("pdf_url") or ""

    # Cover message — template-based, no LLM needed
    responsavel_name = (state.get("responsavel") or "").split()[0] or "bom dia"
    servico          = proposta.get("solucao_proposta", "a solução proposta")
    valor            = proposta.get("valor_aoa", 0)
    prazo            = proposta.get("prazo_semanas", "—")

    cover = (
        f"Olá {responsavel_name}! 😊\n\n"
        f"Conforme conversámos, segue em anexo a proposta detalhada para "
        f"a implementação de *{servico}*.\n\n"
        f"Em resumo:\n"
        f"• Investimento: *{valor:,} AOA*\n"
        f"• Prazo estimado: *{prazo} semanas*\n"
        f"• Condições: 50% na assinatura + 50% antes da entrega\n\n"
        f"Fico à disposição para qualquer dúvida. 🚀\n\n"
        f"Fidel | BMST — Bisca+"
    )

    # Send cover message
    await evolution_client.send_text_message(phone, cover)
    await save_message(phone, "assistant", cover, _AGENT)

    # Send PDF document (only if we have a real URL, not a fallback path)
    if pdf_url and not pdf_url.startswith("local://"):
        try:
            await evolution_client.send_document(phone, pdf_url, "proposta_bmst.pdf")
        except Exception as exc:
            logger.warning("closer.enviar_proposta_cliente: PDF send failed: %s", exc)

    # Update lead state
    await update_lead_state(phone, "proposta_enviada", _AGENT)

    logger.info("closer.enviar_proposta_cliente: proposal sent to %s", phone)

    return {
        "proposta_enviada": True,
        "followup_dia":     0,
        "proxima_acao":     "aguardar_resposta_proposta",
    }


# ── Node: processar_resposta_proposta ─────────────────────────────────────────

async def processar_resposta_proposta(state: CloserState) -> dict:
    """
    Wait for the prospect's reply to the proposal (WhatsApp), then classify it.

    Interrupt is resumed by /closer/webhook with Command(resume={"texto_prospect": ...}).
    Routing: ACEITE → fechado | OBJECAO_* → gerir_objecao | PRECISA_PENSAR → perdido |
             RECUSA → perdido
    """
    phone = state["phone"]

    # ── INTERRUPT: wait for prospect reply to the proposal ────────────────────
    resposta = interrupt({"fase": "aguarda_resposta_proposta"})
    # ── RESUME POINT ─────────────────────────────────────────────────────────

    texto_prospect = resposta.get("texto_prospect", "")
    await save_message(phone, "user", texto_prospect, "prospect")

    # Classify the response
    classificacao_obj = await create_json_message(
        system=CLASSIFICAR_RESPOSTA_PROMPT,
        user=f"Prospect reply: {texto_prospect}",
        schema=RespostaPropostaSchema,
        model="haiku",
        agent_name=_AGENT,
        node_name="processar_resposta_proposta",
    )

    logger.info(
        "closer.processar_resposta_proposta: classificacao=%s",
        classificacao_obj.classificacao,
    )

    proxima: str
    if classificacao_obj.classificacao == "ACEITE":
        proxima = "fechado"
        await update_lead_state(phone, "fechado", _AGENT)
    elif classificacao_obj.classificacao.startswith("OBJECAO"):
        proxima = "gerir_objecao"
    else:
        proxima = "perdido"   # PRECISA_PENSAR / RECUSA

    return {
        "_objecao_detectada": classificacao_obj.objecao_principal,
        "_classificacao_proposta": classificacao_obj.classificacao,
        "proxima_acao": proxima,
    }


# ── Node: gerir_objecao ───────────────────────────────────────────────────────

async def gerir_objecao(state: CloserState) -> dict:
    """
    Generate and send a consultant-tone objection response via WhatsApp.

    Strategy:
      - OBJECAO_PRECO  → reduce scope (never lower the price)
      - OBJECAO_PRAZO  → clarify priority and accelerate phase 1
      - Other          → clarify and give time

    All responses go through the REVISOR evaluation inline (avaliar_texto + auto_corrigir)
    without routing back through the full REVISOR graph to keep complexity manageable.
    """
    phone              = state["phone"]
    classificacao      = state.get("_classificacao_proposta", "OBJECAO_PRECO")
    objecao_principal  = state.get("_objecao_detectada") or ""
    proposta           = state.get("rascunho_proposta") or {}

    resposta_obj = await create_json_message(
        system=GERIR_OBJECAO_PROMPT,
        user=(
            f"Respond to this objection.\n"
            f"Objection type: {classificacao}\n"
            f"Exact objection: {objecao_principal or '(not provided)'}\n"
            f"Company: {state['empresa']}\n"
            f"Service proposed: {proposta.get('solucao_proposta', '')}\n"
            f"Value: {proposta.get('valor_aoa', 0):,} AOA\n"
            f"Timeline: {proposta.get('prazo_semanas', '—')} weeks"
        ),
        schema=ObjecaoResponseSchema,
        model="sonnet",   # quality matters for objection handling
        agent_name=_AGENT,
        node_name="gerir_objecao",
    )

    await evolution_client.send_text_message(phone, resposta_obj.resposta)
    await save_message(phone, "assistant", resposta_obj.resposta, _AGENT)

    logger.info(
        "closer.gerir_objecao: resposta enviada (estrategia=%s)",
        resposta_obj.estrategia,
    )

    # Route back to processar_resposta_proposta to wait for the next reply
    return {"proxima_acao": "aguardar_resposta_proposta"}
