# agents/revisor/graph.py — REVISOR sub-graph (included as a node in HUNTER and CLOSER)

from __future__ import annotations

from langgraph.graph import StateGraph, END

from agents.revisor.state import RevisorState
from agents.revisor.nodes import (
    avaliar_texto,
    auto_corrigir,
    verificar_personalizacao,
    preparar_aprovacao,
)


# ── Routing functions ─────────────────────────────────────────────────────────

def _route_after_avaliacao(state: RevisorState) -> str:
    """
    After avaliar_texto, decide the correction path:

    aprovado  → skip auto-correction, go straight to personalisation check
    corrigido → minor issues found, auto-correct them first
    escalado  → structural problem, skip correction, send directly to founder
    """
    status = state.get("status", "escalado")

    if status == "aprovado":
        return "verificar_personalizacao"
    if status == "corrigido":
        return "auto_corrigir"
    # escalado (or any unexpected value) → go to founder immediately
    return "preparar_aprovacao"


def _route_after_auto_correcao(state: RevisorState) -> str:
    """
    After auto_corrigir:

    If the LLM escalated (could not fix without restructuring) → skip to founder.
    Otherwise → personalisation check.
    """
    if state.get("status") == "escalado":
        return "preparar_aprovacao"
    return "verificar_personalizacao"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_revisor_graph() -> StateGraph:
    """
    Assemble the REVISOR sub-graph.

    Flow overview:
                            ┌─────────────────────────────────┐
                            │        avaliar_texto             │
                            └───────────────┬─────────────────┘
                                            │
              ┌─────────────────────────────┼──────────────────────────┐
              │ aprovado                    │ corrigido                │ escalado
              ▼                            ▼                          ▼
    verificar_personalizacao        auto_corrigir              preparar_aprovacao
              │                            │                          │ (interrupt)
              │                  ┌─────────┴──────────┐              │
              │              escalado            ok                   │
              │                  │                │                   │
              │                  ▼                ▼                   │
              │          preparar_aprovacao  verificar_personalizacao  │
              │                  │                │                   │
              └──────────────────┘                └───────────────────┘
                                                          │
                                                  preparar_aprovacao
                                                          │ (interrupt)
                                                          ▼
                                                         END

    IMPORTANT: This graph MUST be compiled with a checkpointer (RedisSaver)
    for interrupt() to work. The parent graph handles checkpointer attachment.
    """
    g = StateGraph(RevisorState)

    # Register nodes
    g.add_node("avaliar_texto",             avaliar_texto)
    g.add_node("auto_corrigir",             auto_corrigir)
    g.add_node("verificar_personalizacao",  verificar_personalizacao)
    g.add_node("preparar_aprovacao",        preparar_aprovacao)

    # Entry point
    g.set_entry_point("avaliar_texto")

    # avaliar_texto → conditional branch
    g.add_conditional_edges(
        "avaliar_texto",
        _route_after_avaliacao,
        {
            "verificar_personalizacao": "verificar_personalizacao",
            "auto_corrigir":            "auto_corrigir",
            "preparar_aprovacao":       "preparar_aprovacao",
        },
    )

    # auto_corrigir → conditional branch
    g.add_conditional_edges(
        "auto_corrigir",
        _route_after_auto_correcao,
        {
            "verificar_personalizacao": "verificar_personalizacao",
            "preparar_aprovacao":       "preparar_aprovacao",
        },
    )

    # verificar_personalizacao always leads to preparar_aprovacao
    # (the node itself sets status="escalado" if not personalised)
    g.add_edge("verificar_personalizacao", "preparar_aprovacao")

    # preparar_aprovacao ends the sub-graph (interrupt happens inside the node)
    g.add_edge("preparar_aprovacao", END)

    return g


# ── Compiled sub-graph (no checkpointer here — parent graph attaches it) ──────

revisor_subgraph = build_revisor_graph().compile()
"""
Pre-compiled REVISOR sub-graph without a checkpointer.

Usage in HUNTER / CLOSER:
    from agents.revisor.graph import build_revisor_graph
    from core.redis_client import get_checkpointer

    revisor = build_revisor_graph().compile(checkpointer=get_checkpointer())
    parent_graph.add_node("revisor", revisor)

The checkpointer MUST be attached at the parent level so that interrupt()
can persist the full graph state (including parent state fields) to Redis.
"""
