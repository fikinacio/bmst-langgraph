# agents/delivery/graph.py — LangGraph graph definition for the DELIVERY agent
#
# Entry dispatch (via proxima_acao field):
#   "iniciar"             → iniciar_projecto  → REVISOR pipeline → enviar_mensagem_delivery
#   "actualizar"          → gerar_actualizacao → REVISOR pipeline → enviar_mensagem_delivery
#   "solicitar_aprovacao" → solicitar_aprovacao_fase → registar_feedback
#   "encerrar"            → encerrar_projecto  → REVISOR pipeline → enviar_mensagem_delivery
#
# REVISOR pipeline (inline, shared across iniciar / actualizar / encerrar):
#   preparar_para_revisor_delivery → avaliar_texto → auto_corrigir
#   → verificar_personalizacao → preparar_aprovacao_delivery (interrupt: Telegram)
#   → processar_resultado_revisor_delivery
#
# After enviar_mensagem_delivery:
#   - if aguarda_aprovacao_fase=True → solicitar_aprovacao_fase → registar_feedback → END
#   - else                           → END

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agents.delivery.state import DeliveryState
from agents.delivery.nodes import (
    iniciar_projecto,
    gerar_actualizacao,
    solicitar_aprovacao_fase,
    encerrar_projecto,
    enviar_mensagem_delivery,
    registar_feedback,
    preparar_para_revisor_delivery,
    preparar_aprovacao_delivery,
    processar_resultado_revisor_delivery,
)
from agents.revisor.nodes import avaliar_texto, auto_corrigir, verificar_personalizacao


# ── Routing helpers ───────────────────────────────────────────────────────────

def _dispatch_by_proxima_acao(state: DeliveryState) -> str:
    """
    Entry dispatcher: route to the correct pipeline based on proxima_acao.

    Called as a conditional edge from START.
    """
    acao = state.get("proxima_acao") or "iniciar"
    routes = {
        "iniciar":             "iniciar_projecto",
        "actualizar":          "gerar_actualizacao",
        "solicitar_aprovacao": "solicitar_aprovacao_fase",
        "encerrar":            "encerrar_projecto",
    }
    return routes.get(acao, "gerar_actualizacao")


def _route_after_send(state: DeliveryState) -> str:
    """
    After sending the approved message, check whether the client's phase
    approval is still pending.

    If aguarda_aprovacao_fase is True the project phase change needs a
    client confirmation — route into solicitar_aprovacao_fase.
    Otherwise the run is complete.
    """
    if state.get("aguarda_aprovacao_fase"):
        return "solicitar_aprovacao_fase"
    return END


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_delivery_graph() -> StateGraph:
    """
    Assemble the DELIVERY StateGraph.

    Returns an uncompiled graph — call .compile(checkpointer=...) on the result
    or use get_delivery_graph() which handles checkpointer defaulting.
    """
    g = StateGraph(DeliveryState)

    # ── Nodes ─────────────────────────────────────────────────────────────────

    # Entry pipeline nodes
    g.add_node("iniciar_projecto",   iniciar_projecto)
    g.add_node("gerar_actualizacao", gerar_actualizacao)
    g.add_node("encerrar_projecto",  encerrar_projecto)

    # Client phase approval (also reachable after send)
    g.add_node("solicitar_aprovacao_fase", solicitar_aprovacao_fase)
    g.add_node("registar_feedback",        registar_feedback)

    # REVISOR pipeline (inline — same nodes as HUNTER/CLOSER, no separate graph)
    g.add_node("preparar_para_revisor_delivery",      preparar_para_revisor_delivery)
    g.add_node("avaliar_texto",                        avaliar_texto)
    g.add_node("auto_corrigir",                        auto_corrigir)
    g.add_node("verificar_personalizacao",             verificar_personalizacao)
    g.add_node("preparar_aprovacao_delivery",          preparar_aprovacao_delivery)
    g.add_node("processar_resultado_revisor_delivery", processar_resultado_revisor_delivery)

    # Output node
    g.add_node("enviar_mensagem_delivery", enviar_mensagem_delivery)

    # ── Edges ─────────────────────────────────────────────────────────────────

    # Entry: START → dispatcher → one of the four entry nodes
    g.add_conditional_edges(
        START,
        _dispatch_by_proxima_acao,
        {
            "iniciar_projecto":        "iniciar_projecto",
            "gerar_actualizacao":      "gerar_actualizacao",
            "solicitar_aprovacao_fase": "solicitar_aprovacao_fase",
            "encerrar_projecto":       "encerrar_projecto",
        },
    )

    # All three content-generating nodes feed into the REVISOR pipeline
    for entry_node in ("iniciar_projecto", "gerar_actualizacao", "encerrar_projecto"):
        g.add_edge(entry_node, "preparar_para_revisor_delivery")

    # REVISOR pipeline (linear)
    g.add_edge("preparar_para_revisor_delivery",      "avaliar_texto")
    g.add_edge("avaliar_texto",                        "auto_corrigir")
    g.add_edge("auto_corrigir",                        "verificar_personalizacao")
    g.add_edge("verificar_personalizacao",             "preparar_aprovacao_delivery")
    g.add_edge("preparar_aprovacao_delivery",          "processar_resultado_revisor_delivery")
    g.add_edge("processar_resultado_revisor_delivery", "enviar_mensagem_delivery")

    # After sending: optionally route to phase approval
    g.add_conditional_edges(
        "enviar_mensagem_delivery",
        _route_after_send,
        {
            "solicitar_aprovacao_fase": "solicitar_aprovacao_fase",
            END: END,
        },
    )

    # Phase approval sub-flow
    g.add_edge("solicitar_aprovacao_fase", "registar_feedback")
    g.add_edge("registar_feedback", END)

    return g


# ── Public factory ────────────────────────────────────────────────────────────

def get_delivery_graph(checkpointer=None):
    """
    Return a compiled DELIVERY graph.

    Args:
        checkpointer: LangGraph checkpointer instance.  If None, a MemorySaver
                      is created (suitable for local testing only).  In
                      production pass the RedisSaver from get_checkpointer().
    """
    if checkpointer is None:
        checkpointer = MemorySaver()
    return build_delivery_graph().compile(checkpointer=checkpointer)
