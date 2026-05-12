# agents/prospector/state.py — State definition for the PROSPECTOR agent

from typing import Literal
from typing_extensions import TypedDict


class ProspectorState(TypedDict):
    """
    Full state for one PROSPECTOR execution (batch mode).

    The PROSPECTOR is the top-of-funnel agent: it enriches raw company data,
    classifies leads as A/B/C, and writes complete rows to Google Sheets so
    the HUNTER can pick them up.

    Fields are grouped by lifecycle phase:
      1. Current lead    — raw input for the lead being processed
      2. Analysis        — LLM-derived insights
      3. Output          — fields written to Google Sheets
      4. Control         — routing hints and error tracking
      5. Batch tracking  — counters across the full batch run
    """

    # ── 1. Current lead (populated by preparar_lead_raw) ──────────────────────
    empresa:         str | None
    sector:          str | None
    responsavel:     str | None
    whatsapp:        str | None
    website:         str | None
    instagram:       str | None
    localizacao:     str | None   # city / province in Angola
    nr_funcionarios: str | None   # number of employees (kept as string)
    fonte:           str | None   # lead source (e.g. "manual", "Instagram", "referência")
    notas_manuais:   str | None   # extra context not stored in the sheet

    # ── 2. Analysis (populated by analisar_e_qualificar) ──────────────────────
    pain_points:    list[str]    # 2-4 specific pain points identified
    presenca_resumo: str | None  # 1-2 sentence summary of digital presence

    # ── 3. Output → Google Sheets ─────────────────────────────────────────────
    segmento:        Literal["A", "B", "C"] | None
    valor_est_aoa:   int | None
    oportunidade:    str | None   # one sentence: what BMST can do for this company
    servico_bmst:    str | None   # recommended service (e.g. "WhatsApp Business + atendimento")
    notas_abordagem: str | None   # the hook the HUNTER MUST use as the opening line

    # ── 4. Control ────────────────────────────────────────────────────────────
    qualificado:     bool | None
    motivo_rejeicao: str | None   # reason when qualificado == False or segmento == "A"
    lead_gravado:    bool          # True after a row is written to the sheet
    proxima_acao:    str | None
    erro:            str | None

    # ── 5. Batch tracking ─────────────────────────────────────────────────────
    leads_raw:        list[dict]  # raw input list passed at startup
    leads_processados: int        # index of the next lead to process
    leads_gravados:   int         # how many rows were written to the sheet
