# agents/hunter/graph.py — HUNTER agent StateGraph with batch loop and REVISOR integration

from __future__ import annotations

import os
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.hunter.state import HunterState
from agents.hunter.nodes import (
    carregar_leads_sheet,
    preparar_lead_atual,
    confirmar_segmento,
    gerar_mensagem_hunter,
    preparar_para_revisor,
    processar_resultado_revisor,
    arquivar_lead,
    notificar_seg_c,
    enviar_whatsapp,
    avancar_lead,
    gerar_relatorio_diario,
)
# REVISOR nodes — added directly to the HUNTER graph (not as a compiled sub-graph)
# Bridge nodes (preparar_para_revisor / processar_resultado_revisor) handle field mapping
from agents.revisor.nodes import (
    avaliar_texto,
    auto_corrigir,
    verificar_personalizacao,
    preparar_aprovacao,
)


# ── Routing functions ─────────────────────────────────────────────────────────

def _route_tem_leads(state: HunterState) -> str:
    """After loading the sheet: route to loop or report."""
    return "sem_leads" if state.get("proxima_acao") == "sem_leads_hoje" else "tem_leads"


def _route_segmento(state: HunterState) -> str:
    """After confirming segment: decide processing path."""
    proxima = state.get("proxima_acao", "")
    if proxima == "arquivar":
        return "arquivar"
    if proxima == "aguardar_aprovacao_seg_c":
        return "seg_c"
    if state.get("erro"):
        return "arquivar"
    return "gerar"


def _route_apos_geracao(state: HunterState) -> str:
    """After message generation: proceed to REVISOR or archive on error."""
    if state.get("erro") or state.get("proxima_acao") == "arquivar":
        return "arquivar"
    return "revisor"


def _route_apos_avaliacao(state: HunterState) -> str:
    """After REVISOR evaluation: choose correction path."""
    status = state.get("status", "escalado")
    if status == "aprovado":
        return "verificar_personalizacao"
    if status == "corrigido":
        return "auto_corrigir"
    return "preparar_aprovacao"   # escalado → go directly to founder


def _route_apos_auto_correcao(state: HunterState) -> str:
    """After auto-correction: check personalisation or escalate to founder."""
    if state.get("status") == "escalado":
        return "preparar_aprovacao"
    return "verificar_personalizacao"


def _route_apos_aprovacao(state: HunterState) -> str:
    """After founder responds (interrupt resumes): send or archive."""
    if state.get("aprovacao_fundador"):
        return "enviar"
    return "arquivar"


def _route_avancar(state: HunterState) -> str:
    """Loop router: more leads → loop back; done → daily report."""
    proxima = state.get("proxima_acao", "finalizar")
    return "continuar" if proxima == "continuar" else "finalizar"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_hunter_graph() -> StateGraph:
    """
    Assemble the full HUNTER StateGraph.

    Loop structure:
        START → carregar_leads_sheet → preparar_lead_atual ◄──────────────┐
                                             ↓                             │  LOOP
                                      confirmar_segmento                   │
                                             ↓                             │
                          ┌──────────────────┼──────────────────┐         │
                        seg A            seg B/C          seg C (flag)     │
                          ↓                ↓                  ↓            │
                     arquivar_lead  gerar_mensagem     notificar_seg_c     │
                          │              ↓                  │              │
                          │         [REVISOR nodes]         │              │
                          │         avaliar_texto           │              │
                          │              ↓                  │              │
                          │    auto_corrigir (if needed)    │              │
                          │              ↓                  │              │
                          │    verificar_personalizacao     │              │
                          │              ↓                  │              │
                          │    preparar_aprovacao ← interrupt()            │
                          │              ↓ (founder responds)              │
                          │    processar_resultado_revisor                 │
                          │              ↓                                 │
                          │       [aprovado?]                              │
                          │      aprovado → enviar_whatsapp                │
                          │      rejeitado ──────────────────┐             │
                          │                                  ↓             │
                          └──────────────────────────── avancar_lead ──────┘
                                                             ↓
                                                    [mais leads?]
                                                    finalizar → gerar_relatorio → END
    """
    g = StateGraph(HunterState)

    # ── Register all nodes ────────────────────────────────────────────────────

    # Batch management
    g.add_node("carregar_leads_sheet",        carregar_leads_sheet)
    g.add_node("preparar_lead_atual",         preparar_lead_atual)

    # HUNTER logic
    g.add_node("confirmar_segmento",          confirmar_segmento)
    g.add_node("gerar_mensagem_hunter",       gerar_mensagem_hunter)

    # REVISOR bridge (in)
    g.add_node("preparar_para_revisor",       preparar_para_revisor)

    # REVISOR nodes (imported from agents.revisor.nodes)
    g.add_node("avaliar_texto",               avaliar_texto)
    g.add_node("auto_corrigir",               auto_corrigir)
    g.add_node("verificar_personalizacao",    verificar_personalizacao)
    g.add_node("preparar_aprovacao",          preparar_aprovacao)   # contains interrupt()

    # REVISOR bridge (out)
    g.add_node("processar_resultado_revisor", processar_resultado_revisor)

    # Actions
    g.add_node("arquivar_lead",               arquivar_lead)
    g.add_node("notificar_seg_c",             notificar_seg_c)
    g.add_node("enviar_whatsapp",             enviar_whatsapp)
    g.add_node("avancar_lead",                avancar_lead)
    g.add_node("gerar_relatorio_diario",      gerar_relatorio_diario)

    # ── Edges ─────────────────────────────────────────────────────────────────

    # Entry
    g.add_edge(START, "carregar_leads_sheet")

    # After loading: has leads?
    g.add_conditional_edges(
        "carregar_leads_sheet",
        _route_tem_leads,
        {"sem_leads": "gerar_relatorio_diario", "tem_leads": "preparar_lead_atual"},
    )

    # Loop entry point → segment confirmation
    g.add_edge("preparar_lead_atual", "confirmar_segmento")

    # After confirmation: route by segment
    g.add_conditional_edges(
        "confirmar_segmento",
        _route_segmento,
        {
            "arquivar": "arquivar_lead",
            "seg_c":    "notificar_seg_c",
            "gerar":    "gerar_mensagem_hunter",
        },
    )

    # After generation: go to REVISOR or archive on error
    g.add_conditional_edges(
        "gerar_mensagem_hunter",
        _route_apos_geracao,
        {"revisor": "preparar_para_revisor", "arquivar": "arquivar_lead"},
    )

    # REVISOR pipeline
    g.add_edge("preparar_para_revisor", "avaliar_texto")

    g.add_conditional_edges(
        "avaliar_texto",
        _route_apos_avaliacao,
        {
            "auto_corrigir":           "auto_corrigir",
            "verificar_personalizacao": "verificar_personalizacao",
            "preparar_aprovacao":       "preparar_aprovacao",
        },
    )

    g.add_conditional_edges(
        "auto_corrigir",
        _route_apos_auto_correcao,
        {
            "verificar_personalizacao": "verificar_personalizacao",
            "preparar_aprovacao":       "preparar_aprovacao",
        },
    )

    g.add_edge("verificar_personalizacao", "preparar_aprovacao")

    # After interrupt resumes: process result then route by decision
    g.add_edge("preparar_aprovacao", "processar_resultado_revisor")

    g.add_conditional_edges(
        "processar_resultado_revisor",
        _route_apos_aprovacao,
        {"enviar": "enviar_whatsapp", "arquivar": "arquivar_lead"},
    )

    # All lead-terminal nodes → avancar_lead
    g.add_edge("arquivar_lead",   "avancar_lead")
    g.add_edge("notificar_seg_c", "avancar_lead")
    g.add_edge("enviar_whatsapp", "avancar_lead")

    # Loop router: back to start of loop OR to final report
    g.add_conditional_edges(
        "avancar_lead",
        _route_avancar,
        {"continuar": "preparar_lead_atual", "finalizar": "gerar_relatorio_diario"},
    )

    # Exit
    g.add_edge("gerar_relatorio_diario", END)

    return g


# ── Compiled graph factory ────────────────────────────────────────────────────

def get_hunter_graph(checkpointer=None):
    """
    Return a compiled HUNTER graph with an attached checkpointer.

    The checkpointer is REQUIRED for interrupt() to work. Without it,
    preparar_aprovacao will raise an error when trying to pause execution.

    Args:
        checkpointer: A LangGraph checkpointer instance.
                      - Development: MemorySaver() (lost on restart)
                      - Production:  RedisSaver from core.redis_client

    Usage:
        from core.redis_client import get_checkpointer
        graph = get_hunter_graph(checkpointer=get_checkpointer())
        result = await graph.ainvoke(initial_state, config={"configurable": {"thread_id": "hunter-run-20260417"}})
    """
    if checkpointer is None:
        # Default to in-memory for local development
        checkpointer = MemorySaver()

    return build_hunter_graph().compile(checkpointer=checkpointer)
