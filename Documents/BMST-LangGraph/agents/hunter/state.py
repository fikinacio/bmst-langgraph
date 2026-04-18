# agents/hunter/state.py — State definition for the HUNTER agent

from typing import Literal
from typing_extensions import TypedDict


class HunterState(TypedDict):
    """
    Full state for one HUNTER execution (batch or single-lead mode).

    Fields are grouped by lifecycle phase:
      1. Input fields       — loaded from Google Sheets or WhatsApp webhook
      2. Processing fields  — populated during HUNTER logic
      3. REVISOR integration— subset of RevisorState, written by bridge nodes
      4. Result fields      — final outcome for the current lead
      5. Batch tracking     — counters for the daily batch run
    """

    # ── 1. Input: current lead (populated by preparar_lead_atual) ─────────────
    lead_id:          str | None
    sheet_row_index:  int | None       # 1-based row in the Google Sheet
    empresa:          str | None
    sector:           str | None
    segmento:         Literal["A", "B", "C"] | None
    responsavel:      str | None
    whatsapp:         str | None
    notas_abordagem:  str | None       # PROSPECTOR's hook — MUST be used in message
    oportunidade:     str | None       # identified business opportunity
    servico_bmst:     str | None       # recommended BMST service
    valor_est_aoa:    int | None       # estimated deal value in AOA

    # ── 2. HUNTER processing ──────────────────────────────────────────────────
    qualificado:      bool | None      # False = lead rejected before REVISOR
    motivo_rejeicao:  str | None       # reason if qualificado == False
    template_usado:   str | None       # e.g. "saude", "hotelaria"
    mensagem_gerada:  str | None       # raw output from GERACAO_MENSAGEM_PROMPT
    nota_interna:     str | None       # NOTA_INTERNA block from the LLM output

    # ── 3. REVISOR integration (written by bridge nodes) ──────────────────────
    # These mirror the RevisorState field names so REVISOR nodes can be added
    # directly to the HUNTER graph without a compiled sub-graph wrapper.
    texto_original:           str | None   # = mensagem_gerada (bridge sets this)
    texto_corrigido:          str | None   # REVISOR output
    status:                   str | None   # REVISOR lifecycle status
    problemas_encontrados:    list[str]    # violations detected
    auto_correcoes:           list[str]    # auto-fixes applied
    qualidade_estimada:       str | None   # "alta" | "media" | "baixa"
    motivo_escalonamento:     str | None   # set when REVISOR escalates
    aprovacao_fundador:       bool | None  # founder decision via Telegram

    # Summaries written by processar_resultado_revisor (for API response / logs)
    revisao_status:           str | None
    revisao_texto_final:      str | None
    revisao_notas:            str | None

    # ── 4. Result ─────────────────────────────────────────────────────────────
    mensagem_enviada:         bool          # True if WhatsApp send succeeded
    whatsapp_message_id:      str | None    # Evolution API message ID
    proxima_acao:             str | None    # routing hint for the graph
    erro:                     str | None    # error detail if something failed

    # ── 5. Batch tracking (shared across all leads in a daily run) ────────────
    leads_pendentes:          list[dict]    # full list loaded from the sheet
    leads_processados:        int           # index of the next lead to process
    mensagens_enviadas:       int           # counter for the daily report
