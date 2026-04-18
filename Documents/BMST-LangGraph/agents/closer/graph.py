# agents/closer/graph.py — CLOSER agent StateGraph
#
# Interrupt points:
#   1. preparar_aprovacao_apresentacao — founder approves the verbal pitch (Telegram)
#   2. gerar_rascunho_proposta         — founder approves the full proposal (Telegram)
#
# WhatsApp-reply interrupts (resumed via /closer/webhook):
#   - iniciar_diagnostico              → waits for P1 answer
#   - processar_resposta_diagnostico   → waits for P2, P3 answers (loop)
#   - enviar_apresentacao              → waits for interest confirmation
#   - processar_resposta_proposta      → waits for proposal reply (loop)
#
# Graph structure:
#
#   START
#     │
#   iniciar_diagnostico ←──────────────────────────────────────────┐
#     │ (interrupt: wait for P1)                                    │
#   processar_resposta_diagnostico  ─────── continuar ─────────────┘
#     │ (interrupt: wait for P2/P3; loops until diagnostico_completo)
#   seleccionar_solucao
#     │
#   apresentar_solucao_verbal
#     │
#   preparar_para_revisor_closer   ← bridge: sets texto_original
#     │
#   avaliar_texto
#     ├── aprovado/corrigido → auto_corrigir (if corrigido) → verificar_personalizacao
#     └── escalado ──────────────────────────────────────────────────────────┐
#   verificar_personalizacao                                                  │
#     └──────────────────────────────────────────────────────────────────────┘
#     │ (always → preparar_aprovacao_apresentacao)
#   preparar_aprovacao_apresentacao   ← INTERRUPT #1 (founder approves angle)
#     │ aprovado
#   processar_resultado_revisor_closer  ← bridge: copies texto to dedicated field
#     │
#   enviar_apresentacao
#     │ (interrupt: wait for prospect interest reply)
#     ├── interessado → gerar_rascunho_proposta
#     └── NAO_INTERESSADO → perdido → END
#   gerar_rascunho_proposta   ← INTERRUPT #2 (founder approves proposal)
#     ├── aprovado + sem edicoes → gerar_pdf_proposta
#     ├── aprovado + com edicoes → incorporar_edicoes_fundador → gerar_pdf_proposta
#     └── rejeitado → perdido → END
#   gerar_pdf_proposta
#     │
#   enviar_proposta_cliente
#     │
#   processar_resposta_proposta ←────────────────────────────────────────────┐
#     │ (interrupt: wait for WhatsApp reply)                                  │
#     ├── ACEITE   → END (fechado)                                            │
#     ├── OBJECAO  → gerir_objecao ─────────────────────────────────────────┘
#     └── RECUSA / PRECISA_PENSAR → END (perdido)

from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END

from agents.closer.state import CloserState
from agents.closer.nodes import (
    iniciar_diagnostico,
    processar_resposta_diagnostico,
    seleccionar_solucao,
    apresentar_solucao_verbal,
    preparar_para_revisor_closer,
    preparar_aprovacao_apresentacao,
    processar_resultado_revisor_closer,
    enviar_apresentacao,
    gerar_rascunho_proposta,
    incorporar_edicoes_fundador,
    gerar_pdf_proposta,
    enviar_proposta_cliente,
    processar_resposta_proposta,
    gerir_objecao,
)
# REVISOR nodes — imported directly (same pattern as HUNTER)
from agents.revisor.nodes import (
    avaliar_texto,
    auto_corrigir,
    verificar_personalizacao,
)


# ── Routing functions ─────────────────────────────────────────────────────────

def _route_diagnostico(state: CloserState) -> str:
    """Loop back if diagnostic Q&A is not yet complete."""
    if state.get("diagnostico_completo"):
        return "seleccionar_solucao"
    return "continuar_diagnostico"   # → processar_resposta_diagnostico


def _route_avaliacao(state: CloserState) -> str:
    """After REVISOR evaluation: choose the correction path."""
    status = state.get("status", "escalado")
    if status == "aprovado":
        return "verificar_personalizacao"
    if status == "corrigido":
        return "auto_corrigir"
    return "preparar_aprovacao_apresentacao"   # escalado → founder review


def _route_auto_correcao(state: CloserState) -> str:
    """After auto-correction: check personalisation or escalate."""
    if state.get("status") == "escalado":
        return "preparar_aprovacao_apresentacao"
    return "verificar_personalizacao"


def _route_apos_aprovacao_apresentacao(state: CloserState) -> str:
    """After founder approves / rejects the verbal pitch."""
    if state.get("aprovacao_fundador"):
        return "processar_resultado_revisor_closer"
    return "perdido"


def _route_apos_interesse_prospect(state: CloserState) -> str:
    """After prospect confirms (or declines) interest in the full proposal."""
    proxima = state.get("proxima_acao", "perdido")
    if proxima == "gerar_proposta":
        return "gerar_rascunho_proposta"
    return "perdido"


def _route_apos_proposta_fundador(state: CloserState) -> str:
    """After founder approves / rejects / edits the proposal draft."""
    proxima = state.get("proxima_acao", "perdido")
    if proxima == "incorporar_edicoes":
        return "incorporar_edicoes_fundador"
    if proxima == "gerar_pdf":
        return "gerar_pdf_proposta"
    return "perdido"


def _route_resposta_proposta(state: CloserState) -> str:
    """After prospect replies to the proposal."""
    proxima = state.get("proxima_acao", "perdido")
    if proxima == "fechado":
        return "fechado"
    if proxima == "gerir_objecao":
        return "gerir_objecao"
    return "perdido"


def _route_perdido(state: CloserState) -> str:
    """Terminal state: lead lost."""
    return END


def _route_fechado(state: CloserState) -> str:
    """Terminal state: deal closed."""
    return END


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_closer_graph() -> StateGraph:
    """Assemble the full CLOSER StateGraph (without checkpointer)."""
    g = StateGraph(CloserState)

    # ── Register all nodes ────────────────────────────────────────────────────

    # Diagnostic phase
    g.add_node("iniciar_diagnostico",               iniciar_diagnostico)
    g.add_node("processar_resposta_diagnostico",    processar_resposta_diagnostico)
    g.add_node("seleccionar_solucao",               seleccionar_solucao)

    # REVISOR pipeline (presentation angle)
    g.add_node("apresentar_solucao_verbal",          apresentar_solucao_verbal)
    g.add_node("preparar_para_revisor_closer",        preparar_para_revisor_closer)
    g.add_node("avaliar_texto",                       avaliar_texto)
    g.add_node("auto_corrigir",                       auto_corrigir)
    g.add_node("verificar_personalizacao",            verificar_personalizacao)
    g.add_node("preparar_aprovacao_apresentacao",     preparar_aprovacao_apresentacao)   # INTERRUPT #1
    g.add_node("processar_resultado_revisor_closer",  processar_resultado_revisor_closer)

    # Presentation → proposal pipeline
    g.add_node("enviar_apresentacao",               enviar_apresentacao)
    g.add_node("gerar_rascunho_proposta",           gerar_rascunho_proposta)             # INTERRUPT #2
    g.add_node("incorporar_edicoes_fundador",       incorporar_edicoes_fundador)
    g.add_node("gerar_pdf_proposta",                gerar_pdf_proposta)
    g.add_node("enviar_proposta_cliente",           enviar_proposta_cliente)

    # Post-proposal follow-up
    g.add_node("processar_resposta_proposta",       processar_resposta_proposta)
    g.add_node("gerir_objecao",                     gerir_objecao)

    # Terminal pseudo-nodes (just route to END)
    g.add_node("perdido",  lambda s: {})
    g.add_node("fechado",  lambda s: {})

    # ── Edges ─────────────────────────────────────────────────────────────────

    # Entry
    g.add_edge(START, "iniciar_diagnostico")

    # Diagnostic loop
    g.add_conditional_edges(
        "iniciar_diagnostico",
        _route_diagnostico,
        {
            "seleccionar_solucao":            "seleccionar_solucao",
            "continuar_diagnostico":          "processar_resposta_diagnostico",
        },
    )

    g.add_conditional_edges(
        "processar_resposta_diagnostico",
        _route_diagnostico,
        {
            "seleccionar_solucao":            "seleccionar_solucao",
            "continuar_diagnostico":          "processar_resposta_diagnostico",  # ← loop
        },
    )

    # Solution selection → verbal presentation
    g.add_edge("seleccionar_solucao",          "apresentar_solucao_verbal")
    g.add_edge("apresentar_solucao_verbal",    "preparar_para_revisor_closer")
    g.add_edge("preparar_para_revisor_closer", "avaliar_texto")

    # REVISOR pipeline routing
    g.add_conditional_edges(
        "avaliar_texto",
        _route_avaliacao,
        {
            "auto_corrigir":                  "auto_corrigir",
            "verificar_personalizacao":       "verificar_personalizacao",
            "preparar_aprovacao_apresentacao": "preparar_aprovacao_apresentacao",
        },
    )

    g.add_conditional_edges(
        "auto_corrigir",
        _route_auto_correcao,
        {
            "verificar_personalizacao":       "verificar_personalizacao",
            "preparar_aprovacao_apresentacao": "preparar_aprovacao_apresentacao",
        },
    )

    # verificar_personalizacao always flows into the founder approval
    g.add_edge("verificar_personalizacao", "preparar_aprovacao_apresentacao")

    # Founder approval of presentation angle (INTERRUPT #1)
    g.add_conditional_edges(
        "preparar_aprovacao_apresentacao",
        _route_apos_aprovacao_apresentacao,
        {
            "processar_resultado_revisor_closer": "processar_resultado_revisor_closer",
            "perdido":                            "perdido",
        },
    )

    g.add_edge("processar_resultado_revisor_closer", "enviar_apresentacao")

    # Prospect interest confirmation
    g.add_conditional_edges(
        "enviar_apresentacao",
        _route_apos_interesse_prospect,
        {
            "gerar_rascunho_proposta": "gerar_rascunho_proposta",
            "perdido":                 "perdido",
        },
    )

    # Proposal generation → founder approval (INTERRUPT #2)
    g.add_conditional_edges(
        "gerar_rascunho_proposta",
        _route_apos_proposta_fundador,
        {
            "incorporar_edicoes_fundador": "incorporar_edicoes_fundador",
            "gerar_pdf_proposta":          "gerar_pdf_proposta",
            "perdido":                     "perdido",
        },
    )

    g.add_edge("incorporar_edicoes_fundador", "gerar_pdf_proposta")
    g.add_edge("gerar_pdf_proposta",          "enviar_proposta_cliente")
    g.add_edge("enviar_proposta_cliente",     "processar_resposta_proposta")

    # Post-proposal routing
    g.add_conditional_edges(
        "processar_resposta_proposta",
        _route_resposta_proposta,
        {
            "fechado":     "fechado",
            "gerir_objecao": "gerir_objecao",
            "perdido":     "perdido",
        },
    )

    # Objection loop: handle, then wait for next reply
    g.add_edge("gerir_objecao", "processar_resposta_proposta")   # ← loop

    # Terminal exits
    g.add_edge("perdido", END)
    g.add_edge("fechado", END)

    return g


# ── Compiled graph factory ────────────────────────────────────────────────────

def get_closer_graph(checkpointer=None):
    """
    Return a compiled CLOSER graph with an attached checkpointer.

    The checkpointer is REQUIRED for interrupt() to function.  Without it,
    all interrupt() calls will raise an error.

    Args:
        checkpointer: A LangGraph checkpointer instance.
                      - Production:  RedisSaver from core.redis_client
                      - Tests:       MemorySaver()

    Usage:
        from core.redis_client import get_checkpointer
        graph = get_closer_graph(checkpointer=get_checkpointer())
        config = {"configurable": {"thread_id": f"closer-{phone}"}}

        # Start: initial invocation
        await graph.ainvoke(initial_state, config)

        # Resume after WhatsApp reply:
        await graph.ainvoke(Command(resume={"texto_prospect": msg}), config)

        # Resume after Telegram founder approval:
        await graph.ainvoke(Command(resume={"aprovado": True, "texto_editado": None}), config)
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    return build_closer_graph().compile(checkpointer=checkpointer)
