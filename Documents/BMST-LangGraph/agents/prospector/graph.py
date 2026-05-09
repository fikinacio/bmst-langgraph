# agents/prospector/graph.py — PROSPECTOR StateGraph

from __future__ import annotations

from langgraph.graph import StateGraph, START, END

from agents.prospector.state import ProspectorState
from agents.prospector.nodes import (
    determinar_sector,
    buscar_empresas,
    classificar_e_filtrar,
    escrever_no_sheet,
    enviar_relatorio,
)


def _route_apos_sector(state: ProspectorState) -> str:
    """Skip processing on weekends or if configuration is missing."""
    if state.get("erro"):
        return "relatorio"
    return "buscar"


def _route_apos_busca(state: ProspectorState) -> str:
    """Skip classification if no companies were found."""
    if state.get("erro"):
        return "relatorio"
    if not state.get("companies_raw"):
        return "relatorio"
    return "classificar"


def build_prospector_graph() -> StateGraph:
    """
    Assemble the PROSPECTOR StateGraph.

    Flow:
        START → determinar_sector
                    ↓ (weekend / error) → enviar_relatorio → END
                    ↓ (ok)
              buscar_empresas
                    ↓ (no results / error) → enviar_relatorio → END
                    ↓ (has results)
              classificar_e_filtrar
                    ↓
              escrever_no_sheet
                    ↓
              enviar_relatorio → END
    """
    g = StateGraph(ProspectorState)

    g.add_node("determinar_sector",   determinar_sector)
    g.add_node("buscar_empresas",     buscar_empresas)
    g.add_node("classificar_e_filtrar", classificar_e_filtrar)
    g.add_node("escrever_no_sheet",   escrever_no_sheet)
    g.add_node("enviar_relatorio",    enviar_relatorio)

    g.add_edge(START, "determinar_sector")

    g.add_conditional_edges(
        "determinar_sector",
        _route_apos_sector,
        {"buscar": "buscar_empresas", "relatorio": "enviar_relatorio"},
    )

    g.add_conditional_edges(
        "buscar_empresas",
        _route_apos_busca,
        {"classificar": "classificar_e_filtrar", "relatorio": "enviar_relatorio"},
    )

    g.add_edge("classificar_e_filtrar", "escrever_no_sheet")
    g.add_edge("escrever_no_sheet",     "enviar_relatorio")
    g.add_edge("enviar_relatorio",      END)

    return g


def get_prospector_graph():
    """Return a compiled PROSPECTOR graph (no checkpointer needed — no interrupts)."""
    return build_prospector_graph().compile()
