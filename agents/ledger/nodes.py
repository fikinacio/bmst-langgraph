# agents/ledger/nodes.py — LEDGER agent node implementations
#
# Interrupt points:
#   - preparar_aprovacao_ledger  → founder reviews D+14 reminder before sending (Telegram)
#
# Graph entry is dispatched by proxima_acao:
#   "emitir_adiantamento" → emitir_factura_adiantamento
#   "emitir_saldo"        → emitir_factura_saldo
#   "verificar"           → verificar_pagamentos
#   "lembrete"            → gerar_lembrete_pagamento
#   "relatorio"           → gerar_relatorio_mensal

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, timedelta

import httpx
from langchain_core.runnables import RunnableConfig
from langgraph.types import interrupt

from agents.ledger.state import LedgerState
from agents.ledger.prompts import (
    LEDGER_SYSTEM_PROMPT,
    FACTURA_NOTIFICACAO_PROMPT,
    LEMBRETE_D3_PROMPT,
    LEMBRETE_D7_PROMPT,
    LEMBRETE_D14_PROMPT,
    ALERTA_FUNDADOR_TEMPLATE,
    RELATORIO_MENSAL_PROMPT,
    FacturaNotificacaoSchema,
    LembreteSchema,
    RelatorioSchema,
)
from core.llm import create_json_message
from core.memory import save_message, save_revisao
from core import evolution_client, telegram_client
from core.settings import settings

logger = logging.getLogger(__name__)
_AGENT = "ledger"


# ── Private helpers ───────────────────────────────────────────────────────────

async def _invoiceninja_create_invoice(
    empresa: str,
    responsavel: str,
    valor_aoa: int,
    due_date_str: str,
    description: str,
) -> str:
    """
    Create an invoice in InvoiceNinja via the REST API.

    Returns the InvoiceNinja invoice ID on success, or "" if InvoiceNinja is
    not configured or the request fails.  The caller continues gracefully either way.
    """
    if not settings.INVOICENINJA_KEY:
        logger.warning(
            "_invoiceninja_create_invoice: INVOICENINJA_KEY not set — skipping"
        )
        return ""

    body = {
        "client": {
            "name": empresa,
            "contacts": [{"first_name": responsavel.split()[0] if responsavel else responsavel}],
        },
        "line_items": [
            {
                "product_key":  description,
                "notes":        description,
                "cost":         valor_aoa,
                "quantity":     1,
            }
        ],
        "due_date": due_date_str,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{settings.INVOICENINJA_URL}/api/v1/invoices",
                headers={
                    "X-Api-Key":     settings.INVOICENINJA_KEY,
                    "Content-Type":  "application/json",
                },
                json=body,
            )
            response.raise_for_status()
            data     = response.json()
            inv_id   = data.get("data", {}).get("id", "")
            logger.info(
                "_invoiceninja_create_invoice: created invoice %s for %s", inv_id, empresa
            )
            return str(inv_id)
    except Exception as exc:
        logger.error(
            "_invoiceninja_create_invoice: failed for %s — %s", empresa, exc
        )
        return ""


# ── Node: emitir_factura_adiantamento ─────────────────────────────────────────

async def emitir_factura_adiantamento(state: LedgerState) -> dict:
    """
    Issue a 50% advance invoice and generate the WhatsApp notification message.

    The notification text is stored in texto_original and then routed through
    the REVISOR pipeline before being sent to the client.

    Due date: today + 7 days (short term for advance payment).
    """
    if not state.get("valor_aoa") or state["valor_aoa"] <= 0:
        return {"erro": "valor_aoa must be greater than 0 to issue an invoice"}

    today    = date.today()
    due_date = today + timedelta(days=7)
    desc     = f"Adiantamento 50% — {state.get('servico', 'Projecto')}"

    invoice_id = await _invoiceninja_create_invoice(
        empresa=state["empresa"],
        responsavel=state.get("responsavel", ""),
        valor_aoa=state["valor_aoa"],
        due_date_str=due_date.isoformat(),
        description=desc,
    )

    # Generate the WhatsApp notification (Template 13) via LLM
    user_context = (
        f"Client name: {state.get('responsavel', state['empresa'])}\n"
        f"Service: {state.get('servico', 'Projecto')}\n"
        f"Amount: {state['valor_aoa']:,} AOA\n"
        f"Due date: {due_date.strftime('%d/%m/%Y')}\n"
        f"Invoice reference: {invoice_id or state['projecto_id']}"
    )

    try:
        notif = await create_json_message(
            system=FACTURA_NOTIFICACAO_PROMPT,
            user=user_context,
            schema=FacturaNotificacaoSchema,
            model="haiku",
            agent_name=_AGENT,
            node_name="emitir_factura_adiantamento",
        )
        texto = notif.mensagem
    except Exception as exc:
        logger.warning("emitir_factura_adiantamento: LLM failed, using fallback text: %s", exc)
        texto = (
            f"Bom dia {state.get('responsavel', state['empresa'])}!\n\n"
            f"Segue a factura de adiantamento para o projecto {state.get('servico', '')} "
            f"no valor de {state['valor_aoa']:,} AOA, com vencimento a "
            f"{due_date.strftime('%d/%m/%Y')}.\n\n"
            f"Após pagamento, pedimos confirmação por esta via.\n\n"
            f"Fidel | BMST — Bisca+"
        )

    logger.info(
        "ledger.emitir_factura_adiantamento: invoice=%s empresa=%s valor=%d",
        invoice_id, state["empresa"], state["valor_aoa"],
    )

    return {
        "invoice_ninja_id":  invoice_id or None,
        "estado_pagamento":  "pendente",
        "data_emissao":      today.isoformat(),
        "data_vencimento":   due_date.isoformat(),
        "texto_original":    texto,
        "lead_id":           state.get("projecto_id", ""),
    }


# ── Node: emitir_factura_saldo ────────────────────────────────────────────────

async def emitir_factura_saldo(state: LedgerState) -> dict:
    """
    Issue the final 50% balance invoice after project delivery.

    Guard: do not re-issue if final payment is already confirmed.
    Due date: today + 14 days (longer term for final settlement).
    """
    if state.get("pagamento_final_confirmado"):
        logger.info(
            "ledger.emitir_factura_saldo: final payment already confirmed — skipping"
        )
        return {"erro": "Final payment already confirmed — invoice not reissued"}

    today    = date.today()
    due_date = today + timedelta(days=14)
    desc     = f"Saldo final 50% — {state.get('servico', 'Projecto')}"

    invoice_id = await _invoiceninja_create_invoice(
        empresa=state["empresa"],
        responsavel=state.get("responsavel", ""),
        valor_aoa=state["valor_aoa"],
        due_date_str=due_date.isoformat(),
        description=desc,
    )

    user_context = (
        f"Client name: {state.get('responsavel', state['empresa'])}\n"
        f"Service: {state.get('servico', 'Projecto')}\n"
        f"Amount: {state['valor_aoa']:,} AOA\n"
        f"Due date: {due_date.strftime('%d/%m/%Y')}\n"
        f"Invoice reference: {invoice_id or state['projecto_id']}\n"
        f"Note: This is the final balance invoice — project is complete."
    )

    try:
        notif = await create_json_message(
            system=FACTURA_NOTIFICACAO_PROMPT,
            user=user_context,
            schema=FacturaNotificacaoSchema,
            model="haiku",
            agent_name=_AGENT,
            node_name="emitir_factura_saldo",
        )
        texto = notif.mensagem
    except Exception as exc:
        logger.warning("emitir_factura_saldo: LLM failed, using fallback text: %s", exc)
        texto = (
            f"Bom dia {state.get('responsavel', state['empresa'])}!\n\n"
            f"Segue a factura de saldo final do projecto {state.get('servico', '')} "
            f"no valor de {state['valor_aoa']:,} AOA, com vencimento a "
            f"{due_date.strftime('%d/%m/%Y')}.\n\n"
            f"Após pagamento, pedimos confirmação por esta via.\n\n"
            f"Fidel | BMST — Bisca+"
        )

    logger.info(
        "ledger.emitir_factura_saldo: invoice=%s empresa=%s valor=%d",
        invoice_id, state["empresa"], state["valor_aoa"],
    )

    return {
        "invoice_ninja_id": invoice_id or None,
        "estado_pagamento": "pendente",
        "data_emissao":     today.isoformat(),
        "data_vencimento":  due_date.isoformat(),
        "texto_original":   texto,
        "lead_id":          state.get("projecto_id", ""),
    }


# ── Node: verificar_pagamentos ────────────────────────────────────────────────

async def verificar_pagamentos(state: LedgerState) -> dict:
    """
    Check the payment status of the invoice in InvoiceNinja.

    Called daily at 09:30 by the n8n scheduler.
    InvoiceNinja status_id 4 = Paid.

    If InvoiceNinja is not configured, calculates dias_atraso from data_vencimento
    alone so the reminder pipeline can still function.
    """
    invoice_id   = state.get("invoice_ninja_id")
    data_venc    = state.get("data_vencimento")
    today        = date.today()

    paid = False

    if invoice_id and settings.INVOICENINJA_KEY:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.INVOICENINJA_URL}/api/v1/invoices/{invoice_id}",
                    headers={"X-Api-Key": settings.INVOICENINJA_KEY},
                )
                resp.raise_for_status()
                data      = resp.json()
                status_id = data.get("data", {}).get("status_id", 0)
                paid      = int(status_id) == 4   # 4 = Paid in InvoiceNinja
                logger.info(
                    "ledger.verificar_pagamentos: invoice=%s status_id=%s paid=%s",
                    invoice_id, status_id, paid,
                )
        except Exception as exc:
            logger.error(
                "ledger.verificar_pagamentos: InvoiceNinja check failed (%s) — %s",
                invoice_id, exc,
            )
    else:
        logger.warning(
            "ledger.verificar_pagamentos: InvoiceNinja not configured — "
            "calculating dias_atraso from data_vencimento only"
        )

    if paid:
        return {
            "estado_pagamento":          "pago",
            "dias_atraso":               0,
            "pagamento_final_confirmado": True,
        }

    # Calculate days overdue from due date
    dias_atraso = 0
    if data_venc:
        try:
            venc        = date.fromisoformat(data_venc)
            dias_atraso = max(0, (today - venc).days)
        except ValueError:
            logger.warning("verificar_pagamentos: invalid data_vencimento: %s", data_venc)

    novo_estado = "em_atraso" if dias_atraso > 0 else "pendente"

    logger.info(
        "ledger.verificar_pagamentos: invoice=%s dias_atraso=%d estado=%s",
        invoice_id, dias_atraso, novo_estado,
    )

    return {
        "estado_pagamento": novo_estado,
        "dias_atraso":      dias_atraso,
    }


# ── Node: gerar_lembrete_pagamento ────────────────────────────────────────────

async def gerar_lembrete_pagamento(state: LedgerState) -> dict:
    """
    Generate the appropriate payment reminder text based on days overdue.

    D+3  → Template 14 (friendly) via Haiku — sent directly
    D+7  → Template 15 (professional) via Haiku — sent directly
    D+14 → Template 16 (firm) via Sonnet — requires founder approval (Telegram interrupt)

    Guards:
    - Does not re-send a reminder that was already sent this cycle.
    - Returns {} (no-op) if no reminder is due.
    """
    dias = state.get("dias_atraso", 0)

    # Determine which reminder to send
    if dias >= 14 and not state.get("lembrete_d14_enviado"):
        prompt       = LEMBRETE_D14_PROMPT
        model        = "sonnet"   # firm message warrants better model
        flag_field   = "lembrete_d14_enviado"
    elif dias >= 7 and not state.get("lembrete_d7_enviado"):
        prompt       = LEMBRETE_D7_PROMPT
        model        = "haiku"
        flag_field   = "lembrete_d7_enviado"
    elif dias >= 3 and not state.get("lembrete_d3_enviado"):
        prompt       = LEMBRETE_D3_PROMPT
        model        = "haiku"
        flag_field   = "lembrete_d3_enviado"
    else:
        logger.info(
            "ledger.gerar_lembrete_pagamento: no reminder due "
            "(dias_atraso=%d, flags d3=%s d7=%s d14=%s)",
            dias,
            state.get("lembrete_d3_enviado"),
            state.get("lembrete_d7_enviado"),
            state.get("lembrete_d14_enviado"),
        )
        return {}

    ref   = state.get("invoice_ninja_id") or state.get("projecto_id", "")
    valor = f"{state.get('valor_aoa', 0):,}"
    venc  = state.get("data_vencimento", "—")

    user_context = (
        f"NOME: {state.get('responsavel', state.get('empresa', ''))}\n"
        f"REFERENCIA: {ref}\n"
        f"VALOR: {valor} AOA\n"
        f"DATA_VENCIMENTO: {venc}\n"
        f"BANCO: [BANCO]\n"
        f"NIB: [NIB]"
    )

    try:
        lembrete = await create_json_message(
            system=LEDGER_SYSTEM_PROMPT,
            user=f"{prompt}\n\n{user_context}",
            schema=LembreteSchema,
            model=model,
            agent_name=_AGENT,
            node_name="gerar_lembrete_pagamento",
        )
        texto = lembrete.mensagem
    except Exception as exc:
        logger.error("gerar_lembrete_pagamento: LLM call failed: %s", exc)
        return {"erro": str(exc)}

    logger.info(
        "ledger.gerar_lembrete_pagamento: generated %s reminder for %s",
        flag_field, state.get("empresa"),
    )

    return {
        "texto_original": texto,
        flag_field:       True,
        "lead_id":        state.get("projecto_id", ""),
    }


# ── Node: alertar_fundador_divida ─────────────────────────────────────────────

async def alertar_fundador_divida(state: LedgerState) -> dict:
    """
    Send a critical Telegram alert to the founder when a payment is > 21 days overdue.

    Uses a static template (no LLM) for maximum reliability — a critical alert
    must not fail because the AI model is unavailable.

    Idempotent: does nothing if fundador_alertado is already True.
    """
    if state.get("fundador_alertado"):
        logger.info(
            "ledger.alertar_fundador_divida: already alerted — skipping"
        )
        return {}

    dias_atraso = state.get("dias_atraso", 0)
    if dias_atraso <= 21:
        logger.warning(
            "ledger.alertar_fundador_divida: called with dias_atraso=%d (<=21) — skipping",
            dias_atraso,
        )
        return {}

    # Determine last reminder sent label
    if state.get("lembrete_d14_enviado"):
        ultimo_lembrete = "D+14"
    elif state.get("lembrete_d7_enviado"):
        ultimo_lembrete = "D+7"
    elif state.get("lembrete_d3_enviado"):
        ultimo_lembrete = "D+3"
    else:
        ultimo_lembrete = "Nenhum"

    msg = ALERTA_FUNDADOR_TEMPLATE.format(
        empresa=state.get("empresa", "—"),
        invoice_ref=state.get("invoice_ninja_id") or state.get("projecto_id", "—"),
        valor_aoa=state.get("valor_aoa", 0),
        dias_atraso=dias_atraso,
        ultimo_lembrete=ultimo_lembrete,
    )

    try:
        await telegram_client.send_message(msg)
        logger.info(
            "ledger.alertar_fundador_divida: critical alert sent for %s (%d days)",
            state.get("empresa"), dias_atraso,
        )
    except Exception as exc:
        logger.error("alertar_fundador_divida: Telegram send failed: %s", exc)
        # Still mark as alerted to avoid repeat attempts
        return {"fundador_alertado": True, "erro": str(exc)}

    return {"fundador_alertado": True}


# ── Node: gerar_relatorio_mensal ──────────────────────────────────────────────

async def gerar_relatorio_mensal(state: LedgerState) -> dict:
    """
    Generate and send a monthly financial report to the founder.

    Aggregates invoice data from Supabase for the current month.
    Triggered on the 1st of each month at 08:00 by the n8n scheduler.
    """
    today    = date.today()
    mes_ano  = today.strftime("%B %Y")   # e.g. "April 2026"

    # Build aggregates from Supabase (best-effort)
    agg_data = {
        "mes_ano":        mes_ano,
        "total_faturado": 0,
        "total_recebido": 0,
        "total_em_atraso": 0,
        "num_facturas":   0,
        "num_pagas":      0,
        "num_atraso":     0,
    }

    try:
        from core.settings import settings as s
        from supabase import create_client

        supabase = create_client(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)
        first_of_month = today.replace(day=1).isoformat()

        # Fetch all invoices for this month
        result = await asyncio.to_thread(
            lambda: supabase.table("facturas")
            .select("valor_aoa, estado_pagamento")
            .gte("data_emissao", first_of_month)
            .execute()
        )
        rows = result.data or []

        for row in rows:
            valor   = row.get("valor_aoa", 0) or 0
            estado  = row.get("estado_pagamento", "pendente")
            agg_data["num_facturas"]   += 1
            agg_data["total_faturado"] += valor
            if estado == "pago":
                agg_data["num_pagas"]      += 1
                agg_data["total_recebido"] += valor
            elif estado in ("em_atraso", "pendente"):
                agg_data["num_atraso"]      += 1
                agg_data["total_em_atraso"] += valor

        logger.info(
            "ledger.gerar_relatorio_mensal: aggregated %d invoices for %s",
            len(rows), mes_ano,
        )
    except Exception as exc:
        logger.warning(
            "gerar_relatorio_mensal: Supabase aggregation failed — %s. "
            "Generating with placeholder data.", exc
        )

    # Generate the report summary via LLM
    try:
        relatorio = await create_json_message(
            system=RELATORIO_MENSAL_PROMPT,
            user=json.dumps(agg_data, ensure_ascii=False),
            schema=RelatorioSchema,
            model="haiku",
            agent_name=_AGENT,
            node_name="gerar_relatorio_mensal",
        )
    except Exception as exc:
        logger.error("gerar_relatorio_mensal: LLM call failed: %s", exc)
        return {"erro": str(exc)}

    # Format for Telegram
    destaques_str = "\n".join(f"• {d}" for d in relatorio.destaques)
    texto = (
        f"💰 <b>LEDGER — Relatório {relatorio.mes_ano}</b>\n\n"
        f"<b>FACTURAÇÃO:</b>\n"
        f"• Emitido: {relatorio.total_faturado:,} AOA\n"
        f"• Recebido: {relatorio.total_recebido:,} AOA\n"
        f"• Em atraso: {relatorio.total_em_atraso:,} AOA\n\n"
        f"<b>FACTURAS:</b> {relatorio.num_facturas} total | "
        f"{relatorio.num_pagas} pagas | {relatorio.num_atraso} em atraso\n\n"
        f"<b>DESTAQUES:</b>\n{destaques_str}"
    )

    try:
        await telegram_client.send_message(texto)
        logger.info("ledger.gerar_relatorio_mensal: report sent to founder")
    except Exception as exc:
        logger.error("gerar_relatorio_mensal: Telegram send failed: %s", exc)

    return {"relatorio_mensal": texto}


# ── Node: enviar_lembrete_wa ──────────────────────────────────────────────────

async def enviar_lembrete_wa(state: LedgerState) -> dict:
    """
    Send the final (approved) reminder or invoice notification via WhatsApp.

    Uses texto_corrigido if the REVISOR pipeline ran (D+14 / invoice notifs),
    otherwise falls back to texto_original (D+3, D+7 go direct).
    """
    texto = state.get("texto_corrigido") or state.get("texto_original") or ""
    if not texto:
        logger.info("ledger.enviar_lembrete_wa: no text to send — skipping")
        return {}

    phone = state.get("phone", "")
    if not phone:
        logger.warning("ledger.enviar_lembrete_wa: no phone number in state")
        return {}

    try:
        await evolution_client.send_text_message(phone, texto)
        await save_message(phone, "assistant", texto, _AGENT)
        logger.info(
            "ledger.enviar_lembrete_wa: sent to %s (%d chars)", phone, len(texto)
        )
    except Exception as exc:
        logger.error("ledger.enviar_lembrete_wa: send failed: %s", exc)
        return {"erro": str(exc)}

    return {"mensagem_lembrete": texto}


# ── REVISOR bridge nodes ──────────────────────────────────────────────────────

async def preparar_para_revisor_ledger(
    state: LedgerState,
    config: RunnableConfig,
) -> dict:
    """
    Bridge: populate REVISOR shared fields before the REVISOR pipeline runs.

    Called before avaliar_texto for invoice notifications (adiantamento/saldo)
    and for D+14 reminders (which require founder approval).
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
            "segmento":  "B",          # LEDGER only serves existing B-segment clients
            "canal":     "WhatsApp",
            "agente":    "LEDGER",
            "thread_id": thread_id,
        },
        "lead_id": state.get("projecto_id", ""),
    }


async def preparar_aprovacao_ledger(
    state: LedgerState,
    config: RunnableConfig,
) -> dict:
    """
    LEDGER-specific founder approval node for D+14 reminders and invoice notifications.

    Sends the REVISOR-reviewed text to the founder via Telegram, then interrupts
    until the founder taps Approve / Edit / Reject.

    The interrupt resumes via /telegram/callback with a "ledger-*" thread_id.
    """
    thread_id      = config["configurable"].get("thread_id", "")
    texto_proposto = state.get("texto_corrigido") or state.get("texto_original", "")
    is_escalado    = state.get("status") == "escalado"

    from agents.revisor.nodes import _format_revisao_notes
    revisao_notas = _format_revisao_notes(state, is_escalado)

    try:
        await save_revisao(
            lead_id=state.get("lead_id", state.get("projecto_id", "")),
            texto_original=state.get("texto_original", ""),
            texto_final=texto_proposto,
            status=state.get("status", "pendente"),
            notas=revisao_notas,
        )
    except Exception as exc:
        logger.warning("preparar_aprovacao_ledger: save_revisao failed: %s", exc)

    contexto   = dict(state.get("_revisor_contexto") or {})
    message_id = await telegram_client.send_approval_request(
        mensagem_cliente=texto_proposto,
        contexto=contexto,
        revisao_notas=revisao_notas,
        thread_id=thread_id,
    )

    logger.info(
        "ledger.preparar_aprovacao: Telegram sent (id=%s), entering interrupt",
        message_id,
    )

    # ── INTERRUPT: founder reviews the outbound message ───────────────────────
    decisao: dict = interrupt({
        "fase":                "aguarda_aprovacao_lembrete",
        "telegram_message_id": message_id,
        "texto_proposto":      texto_proposto,
    })
    # ── RESUME POINT ─────────────────────────────────────────────────────────

    aprovado      = decisao.get("aprovado", False)
    texto_editado = decisao.get("texto_editado")

    return {
        "aprovacao_fundador": aprovado,
        "texto_corrigido":    texto_editado or texto_proposto,
        "status":             "aprovado" if aprovado else "rejeitado",
    }


async def processar_resultado_revisor_ledger(state: LedgerState) -> dict:
    """
    Bridge: extract the final approved text after the REVISOR pipeline completes.

    Sets mensagem_lembrete so enviar_lembrete_wa knows what to send.
    """
    return {
        "mensagem_lembrete": (
            state.get("texto_corrigido") or state.get("texto_original", "")
        ),
    }
