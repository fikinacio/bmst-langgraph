# agents/prospector/graph.py — PROSPECTOR agent StateGraph

from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from agents.prospector.state import ProspectorState
from agents.prospector.nodes import (
    preparar_lead_raw,
    verificar_duplicado,
    analisar_e_qualificar,
    gerar_hook,
    registar_lead,
    avancar_lead,
    gerar_relatorio,
)


# ── Routing functions ─────────────────────────────────────────────────────────

def _route_apos_duplicado(state: ProspectorState) -> str:
    """Skip to avancar_lead if duplicate, otherwise qualify."""
    return "duplicado" if state.get("proxima_acao") == "duplicado" else "qualificar"


def _route_apos_qualificacao(state: ProspectorState) -> str:
    """Segment A (or not qualified) → archive directly. B/C → generate hook."""
    return "arquivar" if state.get("proxima_acao") == "arquivar" else "gerar_hook"


def _route_avancar(state: ProspectorState) -> str:
    """Loop router: more leads → loop back; done → report."""
    return "continuar" if state.get("proxima_acao") == "continuar" else "finalizar"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_prospector_graph() -> StateGraph:
    """
    Assemble the PROSPECTOR StateGraph.

    Loop structure:
        START → preparar_lead_raw ◄────────────────────────────────────────┐
                      ↓                                                     │ LOOP
               verificar_duplicado                                          │
               ↓ (not dup)        ↓ (dup) ──────────────────────────────┐  │
        analisar_e_qualificar                                             │  │
        ↓ (seg B/C)    ↓ (seg A)                                         │  │
        gerar_hook     │                                                  │  │
              ↓        ↓                                                  │  │
           registar_lead                                                  │  │
                 ↓                                                        │  │
            avancar_lead ←────────────────────────────────────────────────┘  │
         ↓ (continuar)  ↓ (finalizar)                                        │
         └──────────────────────────────────────────────────────────────────┘
                        gerar_relatorio → END
    """
    g = StateGraph(ProspectorState)

    g.add_node("preparar_lead_raw",     preparar_lead_raw)
    g.add_node("verificar_duplicado",   verificar_duplicado)
    g.add_node("analisar_e_qualificar", analisar_e_qualificar)
    g.add_node("gerar_hook",            gerar_hook)
    g.add_node("registar_lead",         registar_lead)
    g.add_node("avancar_lead",          avancar_lead)
    g.add_node("gerar_relatorio",       gerar_relatorio)

    # Entry
    g.add_edge(START, "preparar_lead_raw")
    g.add_edge("preparar_lead_raw", "verificar_duplicado")

    # Duplicate check
    g.add_conditional_edges(
        "verificar_duplicado",
        _route_apos_duplicado,
        {"duplicado": "avancar_lead", "qualificar": "analisar_e_qualificar"},
    )

    # Qualification result
    g.add_conditional_edges(
        "analisar_e_qualificar",
        _route_apos_qualificacao,
        {"arquivar": "registar_lead", "gerar_hook": "gerar_hook"},
    )

    # Hook → register
    g.add_edge("gerar_hook", "registar_lead")

    # Register → advance
    g.add_edge("registar_lead", "avancar_lead")

    # Loop or finish
    g.add_conditional_edges(
        "avancar_lead",
        _route_avancar,
        {"continuar": "preparar_lead_raw", "finalizar": "gerar_relatorio"},
    )

    g.add_edge("gerar_relatorio", END)

    return g


# ── Compiled graph factory ────────────────────────────────────────────────────

def get_prospector_graph(checkpointer=None):
    """
    Return a compiled PROSPECTOR graph.

    The PROSPECTOR does not use interrupt(), so a checkpointer is optional.
    In production a RedisSaver is still recommended for observability.

    Args:
        checkpointer: LangGraph checkpointer instance (optional).

    Usage:
        graph = get_prospector_graph()
        await graph.ainvoke(
            {"leads_raw": [...], "leads_processados": 0, "leads_gravados": 0},
            config={"configurable": {"thread_id": "prospector-2026-05-10"}},
        )
    """
    if checkpointer is None:
        checkpointer = MemorySaver()
    return build_prospector_graph().compile(checkpointer=checkpointer)
