"""
Pydantic request / response models for the BMST Agents API.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ── HUNTER ────────────────────────────────────────────────────────────────────

class HunterBatchRequest(BaseModel):
    """Trigger a HUNTER batch run against Google Sheets."""
    sheet_id: str = Field(
        default="",
        description="Override the Google Sheets ID from settings (leave blank to use default).",
    )
    max_leads: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Maximum number of leads to process in this batch.",
    )


class HunterWebhookRequest(BaseModel):
    """Incoming WhatsApp message forwarded by Evolution API."""
    phone: str = Field(..., description="Sender phone number (E.164 or local Angola format).")
    message: str = Field(..., description="Raw message text.")
    message_id: str = Field(..., description="Evolution message ID (for deduplication).")
    timestamp: int = Field(..., description="Unix epoch timestamp of the message.")


# ── TELEGRAM ──────────────────────────────────────────────────────────────────

class TelegramCallbackRequest(BaseModel):
    """
    Payload sent by the Telegram webhook when the founder taps an inline button.

    The `thread_id` field carries the LangGraph thread_id embedded in the
    callback_data when the approval request was sent.  It is used to resume
    the correct interrupted HUNTER graph instance.
    """
    callback_query_id: str = Field(
        ...,
        description="Telegram callback query ID — must be answered within 10 seconds.",
    )
    message_id: int = Field(..., description="Telegram message ID of the approval request.")
    data: Literal["aprovar", "editar", "rejeitar"] = Field(
        ...,
        description="Action selected by the founder.",
    )
    thread_id: str = Field(
        ...,
        description="LangGraph thread_id of the interrupted HUNTER run to resume.",
    )
    edited_text: str | None = Field(
        default=None,
        description="Replacement text provided by the founder (only when data='editar').",
    )


# ── CLOSER ────────────────────────────────────────────────────────────────────

class CloserDiagnoseRequest(BaseModel):
    """Start a CLOSER conversational run for a qualified lead passed from HUNTER."""
    phone: str
    empresa: str
    sector: str = Field(default="", description="Business sector (e.g. 'saúde', 'retalho').")
    segmento: str = Field(default="B", description="BMST segment: 'B' or 'C'.")
    responsavel: str = Field(default="", description="Name of the prospect's decision-maker.")
    historico: list[dict] = Field(
        default_factory=list,
        description="Previous conversation turns [{role, content}] from the HUNTER phase.",
    )


class CloserProposeRequest(BaseModel):
    """Ask the CLOSER agent to generate a commercial proposal."""
    phone: str
    empresa: str
    diagnostico: dict = Field(..., description="Output from /closer/diagnose.")


# ── DELIVERY ──────────────────────────────────────────────────────────────────

class DeliveryStartRequest(BaseModel):
    """Start the DELIVERY pipeline for a new project after payment confirmation."""
    projecto_id: str
    empresa: str
    servico: str
    phone: str
    responsavel: str
    segmento: str = Field(default="B", description="BMST segment: 'B' or 'C'.")
    data_entrega_prevista: str | None = Field(
        default=None, description="Expected delivery date (ISO format, e.g. '2026-06-30')."
    )


class DeliveryUpdateRequest(BaseModel):
    """Trigger a DELIVERY agent action on an active project."""
    projecto_id: str
    proxima_acao: Literal["actualizar", "solicitar_aprovacao", "encerrar"]
    itens_concluidos: list[str] = Field(
        default_factory=list,
        description="Items completed since the last update.",
    )
    itens_pendentes: list[str] = Field(
        default_factory=list,
        description="Items still in progress or upcoming.",
    )


class DeliveryWebhookRequest(BaseModel):
    """
    Client WhatsApp reply to a phase-approval request (Template 12).

    Evolution API calls /delivery/webhook when the client responds.
    The thread_id identifies the paused DELIVERY graph run to resume.
    """
    thread_id: str = Field(
        ..., description="LangGraph thread_id of the paused DELIVERY run."
    )
    phone: str
    aprovado: bool = Field(
        ..., description="True if the client approved the phase transition."
    )


# ── LEDGER ────────────────────────────────────────────────────────────────────

class LedgerInvoiceRequest(BaseModel):
    """Issue an invoice (advance or final balance) and start the billing pipeline."""
    projecto_id: str
    empresa: str
    phone: str
    responsavel: str
    tipo_factura: Literal["adiantamento", "saldo", "retainer"]
    valor_aoa: int = Field(..., ge=1, description="Invoice amount in AOA.")
    servico: str = Field(
        default="", description="Service description used in the invoice line item."
    )


class LedgerCheckPaymentsRequest(BaseModel):
    """Trigger a payment verification run for a pending invoice."""
    projecto_id: str
    invoice_ninja_id: str = Field(
        default="",
        description="InvoiceNinja invoice ID to verify (leave blank to check all pending).",
    )


# ── SHARED RESPONSES ──────────────────────────────────────────────────────────

class BatchResponse(BaseModel):
    """Summary of a completed (or failed) HUNTER batch run."""
    leads_processados: int
    mensagens_enviadas: int
    erros: list[str]
    tempo_execucao_segundos: float


class WebhookResponse(BaseModel):
    """Generic response for webhook and callback endpoints."""
    success: bool
    action: str
    thread_id: str | None = None


class HealthResponse(BaseModel):
    """Health check response — always returns 200, degraded flag in status."""
    status: Literal["ok", "degraded"]
    services: dict[str, str]  # {"redis": "ok", "supabase": "ok", ...}
    version: str = "1.0.0"


class MetricsResponse(BaseModel):
    """Aggregated operational metrics."""
    leads_total: int
    leads_hoje: int
    mensagens_hoje: int
    mensagens_enviadas_hoje: int


# ── PROSPECTOR ────────────────────────────────────────────────────────────────

class ProspectorRunRequest(BaseModel):
    """Trigger a PROSPECTOR session (normally called by the n8n cron at 07:00 UTC)."""
    sector: str = Field(
        default="",
        description="Override the sector for this session. Leave blank to use the day-of-week calendar.",
    )
    max_companies: int = Field(
        default=30,
        ge=1,
        le=50,
        description="Maximum number of companies to search (caps the Google Places API cost).",
    )
    city: str = Field(
        default="Luanda",
        description="Target city for Google Places search.",
    )
