# agents/delivery/state.py — DELIVERY agent state definition

from __future__ import annotations

from typing import Literal
from typing_extensions import TypedDict


class DeliveryState(TypedDict):
    """
    Full state for the DELIVERY agent.

    Field groups:
      - Project info    : projecto_id, empresa, servico, phone, responsavel, segmento
      - Phase state     : fase_atual, data_inicio, data_entrega_prevista
      - Progress items  : itens_concluidos, itens_pendentes
      - Client comms    : aguarda_aprovacao_fase, mensagem_actualizacao, feedback_cliente
      - Integrations    : notion_page_id, pagamento_final_confirmado
      - Routing         : proxima_acao, erro
      - REVISOR shared  : texto_original, texto_corrigido, status, ...
    """

    # ── Project info ───────────────────────────────────────────────────────────
    projecto_id: str
    empresa: str
    servico: str
    phone: str
    responsavel: str
    segmento: str   # "B" or "C" — used for REVISOR context

    # ── Phase state (from user spec) ───────────────────────────────────────────
    fase_atual: Literal[
        "onboarding",
        "desenvolvimento",
        "revisao",
        "entrega_final",
        "concluido",
    ]
    data_inicio: str | None              # ISO date
    data_entrega_prevista: str | None    # ISO date

    # ── Progress items (from user spec) ───────────────────────────────────────
    itens_concluidos: list[str]
    itens_pendentes: list[str]

    # ── Client comms (from user spec) ─────────────────────────────────────────
    aguarda_aprovacao_fase: bool         # True when phase change approval is needed
    mensagem_actualizacao: str | None    # generated update/onboarding text (pre-REVISOR)
    feedback_cliente: str | None         # client's reply to phase approval or final survey

    # ── Integrations ──────────────────────────────────────────────────────────
    notion_page_id: str | None           # Notion page ID created on onboarding
    pagamento_final_confirmado: bool     # set by LEDGER when final payment is received

    # ── Routing ───────────────────────────────────────────────────────────────
    proxima_acao: str | None
    # Valid values:
    #   "iniciar"              → run iniciar_projecto (called once at project start)
    #   "actualizar"           → run gerar_actualizacao (called 2x/week)
    #   "solicitar_aprovacao"  → run solicitar_aprovacao_fase (before phase change)
    #   "encerrar"             → run encerrar_projecto (when project is done)
    erro: str | None

    # ── REVISOR shared fields ─────────────────────────────────────────────────
    # Required for REVISOR nodes (avaliar_texto, auto_corrigir, etc.) to work
    # inline in this graph without modification.
    texto_original: str | None
    texto_corrigido: str | None
    status: Literal["pendente", "aprovado", "corrigido", "escalado", "rejeitado"]
    problemas_encontrados: list[str]
    auto_correcoes: list[str]
    qualidade_estimada: Literal["alta", "media", "baixa"] | None
    aprovacao_fundador: bool | None
    motivo_escalonamento: str | None
    _revisor_contexto: dict
    lead_id: str   # projecto_id used as lead_id for save_revisao
