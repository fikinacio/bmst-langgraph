# agents/revisor/state.py — State definition for the REVISOR shared module

from typing import Literal
from typing_extensions import TypedDict


class RevisorState(TypedDict):
    """
    State carried through the REVISOR sub-graph.

    This TypedDict is merged into the parent agent's state (HunterState,
    CloserState) — every field is prefixed with no namespace to keep access
    simple inside nodes.
    """

    # Input: the raw text produced by the parent agent before sending to client
    texto_original: str

    # Output: the final approved text (may be identical to texto_original)
    texto_corrigido: str | None

    # Lifecycle status of the review
    status: Literal["pendente", "aprovado", "corrigido", "escalado", "rejeitado"]

    # List of rule violations detected during evaluation
    problemas_encontrados: list[str]

    # Human-readable descriptions of each change the LLM made automatically
    auto_correcoes: list[str]

    # Overall quality signal used to decide routing
    qualidade_estimada: Literal["alta", "media", "baixa"]

    # Set to True/False only after the founder responds via Telegram
    aprovacao_fundador: bool | None

    # Populated only when status == "escalado" — sent to the founder as context
    motivo_escalonamento: str | None
