# agents/ledger/state.py — LEDGER agent state definition
#
# Field groups:
#   - Project info    : projecto_id, empresa, phone, responsavel, servico
#   - Invoice info    : tipo_factura, valor_aoa, data_emissao, data_vencimento
#   - Payment state   : estado_pagamento, dias_atraso, invoice_ninja_id
#   - Reminders       : mensagem_lembrete, lembrete_d3_enviado, ..., fundador_alertado
#   - Routing         : proxima_acao, erro
#   - REVISOR shared  : texto_original, texto_corrigido, status, ...

from __future__ import annotations

from typing import Literal
from typing_extensions import TypedDict


class LedgerState(TypedDict):
    """
    Full state for the LEDGER billing agent.

    The LEDGER manages the full invoice lifecycle:
      1. Issue advance invoice (adiantamento 50%) at project start
      2. Issue final invoice (saldo 50%) when DELIVERY is ready to close
      3. Track payments daily (09:30 via n8n scheduler)
      4. Send reminders at D+3, D+7, D+14 after due date
      5. Alert the founder when a payment is > 21 days overdue
      6. Generate monthly financial report on day 1 at 08:00
    """

    # ── Project / invoice info ─────────────────────────────────────────────────
    projecto_id: str
    empresa: str
    phone: str
    responsavel: str
    servico: str                    # service name — used in invoice description

    tipo_factura: Literal["adiantamento", "saldo", "retainer"]
    valor_aoa: int
    data_emissao: str | None        # ISO date — set when invoice is created
    data_vencimento: str | None     # ISO date — payment due date

    # ── Payment tracking ───────────────────────────────────────────────────────
    estado_pagamento: Literal["pendente", "pago", "em_atraso", "cancelado"]
    dias_atraso: int                # 0 when not overdue; set by verificar_pagamentos
    invoice_ninja_id: str | None    # InvoiceNinja invoice ID

    # ── Reminder tracking ─────────────────────────────────────────────────────
    mensagem_lembrete: str | None   # last generated reminder text (for logging/audit)
    lembrete_d3_enviado: bool
    lembrete_d7_enviado: bool
    lembrete_d14_enviado: bool
    fundador_alertado: bool          # True once the > 21 day critical alert was sent
    pagamento_final_confirmado: bool  # set True on full payment — signals DELIVERY

    # ── Monthly report ────────────────────────────────────────────────────────
    relatorio_mensal: str | None

    # ── Routing ───────────────────────────────────────────────────────────────
    proxima_acao: str | None
    # Valid values:
    #   "emitir_adiantamento" → emitir_factura_adiantamento
    #   "emitir_saldo"        → emitir_factura_saldo
    #   "verificar"           → verificar_pagamentos
    #   "lembrete"            → gerar_lembrete_pagamento
    #   "relatorio"           → gerar_relatorio_mensal
    erro: str | None

    # ── REVISOR shared fields ─────────────────────────────────────────────────
    # Required so that REVISOR nodes (avaliar_texto, auto_corrigir,
    # verificar_personalizacao) can run inline in this graph without modification.
    texto_original: str | None
    texto_corrigido: str | None
    status: Literal["pendente", "aprovado", "corrigido", "escalado", "rejeitado"]
    problemas_encontrados: list[str]
    auto_correcoes: list[str]
    qualidade_estimada: Literal["alta", "media", "baixa"] | None
    aprovacao_fundador: bool | None
    motivo_escalonamento: str | None
    _revisor_contexto: dict
    lead_id: str   # projecto_id used as lead_id for save_revisao calls
