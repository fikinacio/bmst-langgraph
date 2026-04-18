# agents/ledger/graph.py — LangGraph graph definition for the LEDGER agent
#
# Entry dispatch (via proxima_acao field):
#   "emitir_adiantamento" → emitir_factura_adiantamento → REVISOR pipeline → enviar_lembrete_wa
#   "emitir_saldo"        → emitir_factura_saldo        → REVISOR pipeline → enviar_lembrete_wa
#   "verificar"           → verificar_pagamentos → route by days overdue:
#                             0 days  → END
#                             3-20d   → gerar_lembrete_pagamento → direct / REVISOR → enviar
#                             > 21d   → alertar_fundador_divida → END
#   "lembrete"            → gerar_lembrete_pagamento (same routing as above)
#   "relatorio"           → gerar_relatorio_mensal → END
#
# REVISOR pipeline (inline, used for invoice notifications + D+14 reminders):
#   preparar_para_revisor_ledger → avaliar_texto → auto_corrigir
#   → verificar_personalizacao → preparar_aprovacao_ledger (interrupt: Telegram)
#   → processar_resultado_revisor_ledger → enviar_lembrete_wa → END

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agents.ledger.state import LedgerState
from agents.ledger.nodes import (
    emitir_factura_adiantamento,
    emitir_factura_saldo,
    verificar_pagamentos,
    gerar_lembrete_pagamento,
    alertar_fundador_divida,
    gerar_relatorio_mensal,
    enviar_lembrete_wa,
    preparar_para_revisor_ledger,
    preparar_aprovacao_ledger,
    processar_resultado_revisor_ledger,
)
from agents.revisor.nodes import avaliar_texto, auto_corrigir, verificar_personalizacao


# ── Routing helpers ───────────────────────────────────────────────────────────

def _dispatch_by_proxima_acao(state: LedgerState) -> str:
    """
    Entry dispatcher: route to the correct pipeline based on proxima_acao.

    Called as a conditional edge from START.
    """
    acao = state.get("proxima_acao") or "verificar"
    routes = {
        "emitir_adiantamento": "emitir_factura_adiantamento",
        "emitir_saldo":        "emitir_factura_saldo",
        "verificar":           "verificar_pagamentos",
        "lembrete":            "gerar_lembrete_pagamento",
        "relatorio":           "gerar_relatorio_mensal",
    }
    return routes.get(acao, "verificar_pagamentos")


def _route_after_verificar(state: LedgerState) -> str:
    """
    After payment verification, decide what action to take based on payment state.

    - Paid or 0 days overdue → END (nothing to do)
    - > 21 days overdue      → critical founder alert
    - 3–21 days overdue      → generate appropriate reminder
    """
    if state.get("estado_pagamento") == "pago":
        return END

    dias = state.get("dias_atraso", 0)
    if dias == 0:
        return END
    if dias > 21:
        return "alertar_fundador_divida"
    # 3–21 days: generate the correct reminder (D+3, D+7, D+14)
    return "gerar_lembrete_pagamento"


def _route_after_lembrete(state: LedgerState) -> str:
    """
    After generating a reminder, decide whether to go through REVISOR or send directly.

    - D+14 reminders (dias_atraso >= 14) route through the full REVISOR pipeline
      because they are firm in tone and require founder approval before sending.
    - D+3 and D+7 reminders are sent directly — lower stakes, faster response.
    - If no texto_original was produced (already sent / not due), skip to END.
    """
    if not state.get("texto_original"):
        # gerar_lembrete_pagamento returned {} — nothing to send
        return END

    dias = state.get("dias_atraso", 0)
    if dias >= 14:
        return "preparar_para_revisor_ledger"   # D+14: founder approval required

    return "enviar_lembrete_wa"   # D+3, D+7: send directly


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_ledger_graph() -> StateGraph:
    """
    Assemble the LEDGER StateGraph.

    Returns an uncompiled graph — call .compile(checkpointer=...) or use
    get_ledger_graph() which handles checkpointer defaulting.
    """
    g = StateGraph(LedgerState)

    # ── Nodes ─────────────────────────────────────────────────────────────────

    # Entry / pipeline nodes
    g.add_node("emitir_factura_adiantamento", emitir_factura_adiantamento)
    g.add_node("emitir_factura_saldo",        emitir_factura_saldo)
    g.add_node("verificar_pagamentos",        verificar_pagamentos)
    g.add_node("gerar_lembrete_pagamento",    gerar_lembrete_pagamento)
    g.add_node("alertar_fundador_divida",     alertar_fundador_divida)
    g.add_node("gerar_relatorio_mensal",      gerar_relatorio_mensal)
    g.add_node("enviar_lembrete_wa",          enviar_lembrete_wa)

    # REVISOR pipeline (inline)
    g.add_node("preparar_para_revisor_ledger",      preparar_para_revisor_ledger)
    g.add_node("avaliar_texto",                      avaliar_texto)
    g.add_node("auto_corrigir",                      auto_corrigir)
    g.add_node("verificar_personalizacao",           verificar_personalizacao)
    g.add_node("preparar_aprovacao_ledger",          preparar_aprovacao_ledger)
    g.add_node("processar_resultado_revisor_ledger", processar_resultado_revisor_ledger)

    # ── Edges ─────────────────────────────────────────────────────────────────

    # Entry: START → dispatcher
    g.add_conditional_edges(
        START,
        _dispatch_by_proxima_acao,
        {
            "emitir_factura_adiantamento": "emitir_factura_adiantamento",
            "emitir_factura_saldo":        "emitir_factura_saldo",
            "verificar_pagamentos":        "verificar_pagamentos",
            "gerar_lembrete_pagamento":    "gerar_lembrete_pagamento",
            "gerar_relatorio_mensal":      "gerar_relatorio_mensal",
        },
    )

    # Invoice emission paths → always go through REVISOR (founder approves outbound msgs)
    g.add_edge("emitir_factura_adiantamento", "preparar_para_revisor_ledger")
    g.add_edge("emitir_factura_saldo",        "preparar_para_revisor_ledger")

    # Payment verification → conditional routing
    g.add_conditional_edges(
        "verificar_pagamentos",
        _route_after_verificar,
        {
            "gerar_lembrete_pagamento": "gerar_lembrete_pagamento",
            "alertar_fundador_divida":  "alertar_fundador_divida",
            END: END,
        },
    )

    # After generating a reminder → conditional routing (REVISOR or direct)
    g.add_conditional_edges(
        "gerar_lembrete_pagamento",
        _route_after_lembrete,
        {
            "preparar_para_revisor_ledger": "preparar_para_revisor_ledger",
            "enviar_lembrete_wa":           "enviar_lembrete_wa",
            END: END,
        },
    )

    # Simple terminal edges
    g.add_edge("alertar_fundador_divida", END)
    g.add_edge("gerar_relatorio_mensal",  END)

    # REVISOR pipeline (linear)
    g.add_edge("preparar_para_revisor_ledger",      "avaliar_texto")
    g.add_edge("avaliar_texto",                      "auto_corrigir")
    g.add_edge("auto_corrigir",                      "verificar_personalizacao")
    g.add_edge("verificar_personalizacao",           "preparar_aprovacao_ledger")
    g.add_edge("preparar_aprovacao_ledger",          "processar_resultado_revisor_ledger")
    g.add_edge("processar_resultado_revisor_ledger", "enviar_lembrete_wa")

    # Final send → END
    g.add_edge("enviar_lembrete_wa", END)

    return g


# ── Public factory ────────────────────────────────────────────────────────────

def get_ledger_graph(checkpointer=None):
    """
    Return a compiled LEDGER graph.

    Args:
        checkpointer: LangGraph checkpointer instance.  If None, a MemorySaver
                      is created (suitable for local testing only).  In
                      production pass the RedisSaver from get_checkpointer().
    """
    if checkpointer is None:
        checkpointer = MemorySaver()
    return build_ledger_graph().compile(checkpointer=checkpointer)
