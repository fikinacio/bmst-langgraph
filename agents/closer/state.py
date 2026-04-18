# agents/closer/state.py — CLOSER agent state definition

from __future__ import annotations

from typing import Literal
from typing_extensions import TypedDict


class CloserState(TypedDict):
    """
    Full state for the CLOSER agent.

    Field groups:
      - Input from HUNTER   : phone, empresa, sector, segmento, responsavel, historico_conversa
      - Diagnosis            : perguntas_feitas, respostas_cliente, diagnostico_completo, ...
      - Proposal             : rascunho_proposta, proposta_aprovada, edicoes_fundador, ...
      - Follow-up            : followup_dia, proxima_acao, erro
      - REVISOR shared fields: texto_original, texto_corrigido, status, ...
                               (required for REVISOR nodes to work inline)
    """

    # ── Input from HUNTER ─────────────────────────────────────────────────────
    phone: str
    empresa: str
    sector: str
    segmento: str                    # "B" or "C"
    responsavel: str                 # decision-maker name
    historico_conversa: list[dict]   # [{role, content}] from HUNTER phase

    # ── Diagnosis ─────────────────────────────────────────────────────────────
    perguntas_feitas: list[str]      # questions sent to the prospect (P1, P2, P3)
    respostas_cliente: list[str]     # matching answers received
    diagnostico_completo: bool       # True after all 3 questions answered
    problema_identificado: str | None
    servico_recomendado: str | None  # chosen BMST service

    # ── Proposal ──────────────────────────────────────────────────────────────
    rascunho_proposta: dict | None
    # Proposal dict schema (used by gerar_rascunho_proposta and gerar_pdf_proposta):
    #   cliente           : str
    #   decisor           : str
    #   problema_identificado: str
    #   solucao_proposta  : str
    #   entregaveis       : list[str]
    #   prazo_semanas     : int
    #   valor_aoa         : int
    #   condicoes_pagamento: str      (default "50% assinatura + 50% antes entrega")
    #   validade_proposta_dias: int   (default 15)
    #   notas_fundador    : str

    proposta_aprovada: bool | None   # True = founder approved, False = rejected
    edicoes_fundador: str | None     # free-text edits from founder (if data=="editar")
    pdf_url: str | None              # Supabase Storage public URL of the generated PDF
    proposta_enviada: bool           # True once the proposal has been sent to the prospect

    # ── Follow-up ─────────────────────────────────────────────────────────────
    followup_dia: int                # days since proposal sent: 0, 3, 7, 14
    proxima_acao: str | None         # routing signal between nodes
    erro: str | None                 # set when a non-fatal error occurs

    # ── Internal processing cache ─────────────────────────────────────────────
    # These fields are set by nodes and read by later nodes in the same run.
    # They are not meaningful as API output but must survive graph serialisation.
    _solucao_cache: dict | None              # SolucaoSchema.model_dump() cached by seleccionar_solucao
    _texto_apresentacao_final: str | None    # approved presentation text (post-REVISOR)
    _revisao_notas_apresentacao: str | None  # REVISOR notes for presentation
    _objecao_detectada: str | None           # extracted objection phrase
    _classificacao_proposta: str | None      # ACEITE / OBJECAO_* / PRECISA_PENSAR / RECUSA

    # ── REVISOR shared fields ─────────────────────────────────────────────────
    # These mirror RevisorState so that REVISOR nodes (avaliar_texto,
    # auto_corrigir, verificar_personalizacao) can be reused in the CLOSER
    # graph without modification.  Bridge nodes copy values in and out.
    texto_original: str | None
    texto_corrigido: str | None
    status: Literal["pendente", "aprovado", "corrigido", "escalado", "rejeitado"]
    problemas_encontrados: list[str]
    auto_correcoes: list[str]
    qualidade_estimada: Literal["alta", "media", "baixa"] | None
    aprovacao_fundador: bool | None
    motivo_escalonamento: str | None
    _revisor_contexto: dict          # injected by preparar_para_revisor_closer
    lead_id: str                     # phone used as lead_id for save_revisao
