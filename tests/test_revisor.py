# tests/test_revisor.py — unit and integration tests for the REVISOR agent nodes
#
# The REVISOR is a shared inline pipeline (not compiled separately).
# It is tested here by calling its node functions directly.
#
# Mock pattern:
#   - avaliar_texto calls create_json_message → mock "agents.revisor.nodes.create_json_message"
#   - auto_corrigir calls create_message      → mock "agents.revisor.nodes.create_message"
#
# Run:
#   pytest tests/test_revisor.py -v

from unittest.mock import AsyncMock

import pytest

from agents.revisor.nodes import avaliar_texto, auto_corrigir
from agents.revisor.prompts import RevisorAvaliacaoSchema
from tests.conftest import make_revisor_state


# ── Test 1: Detecta termo proibido — "inteligência artificial" ────────────────

@pytest.mark.unit
async def test_detecta_termo_proibido_ia(mocker):
    """
    Text containing 'inteligência artificial' must NOT be approved.

    The REVISOR is expected to return status "corrigido" or "escalado",
    never "aprovado", when a forbidden AI term appears in the message.
    """
    mocker.patch(
        "agents.revisor.nodes.create_json_message",
        new_callable=AsyncMock,
        return_value=RevisorAvaliacaoSchema(
            status="corrigido",
            problemas_encontrados=[
                "Contains forbidden term 'inteligência artificial' — must be removed or rephrased"
            ],
            qualidade_estimada="media",
            motivo_escalonamento=None,
        ),
    )

    state = make_revisor_state(
        texto_original=(
            "Bom dia! A nossa solução de inteligência artificial "
            "responde a todos os seus clientes automaticamente 24/7."
        )
    )

    result = await avaliar_texto(state)

    assert result["status"] != "aprovado", (
        "Text with 'inteligência artificial' must not be approved"
    )
    assert len(result["problemas_encontrados"]) > 0, (
        "At least one problem must be reported"
    )


# ── Test 2: Detecta frase banida de abertura ──────────────────────────────────

@pytest.mark.unit
async def test_detecta_frase_banida(mocker):
    """
    Text opening with 'Espero que este email o encontre bem' must be flagged.

    This is a canonical banned phrase that signals generic, AI-generated content.
    The REVISOR must return status "corrigido" (fixable) or "escalado" (too structural).
    """
    mocker.patch(
        "agents.revisor.nodes.create_json_message",
        new_callable=AsyncMock,
        return_value=RevisorAvaliacaoSchema(
            status="corrigido",
            problemas_encontrados=[
                "Banned opening phrase detected: 'Espero que este email o encontre bem' — replace with direct opener"
            ],
            qualidade_estimada="baixa",
            motivo_escalonamento=None,
        ),
    )

    state = make_revisor_state(
        texto_original=(
            "Espero que este email o encontre bem. "
            "Sou da BMST e gostaria de apresentar a nossa solução..."
        )
    )

    result = await avaliar_texto(state)

    assert result["status"] in ("corrigido", "escalado"), (
        f"Banned phrase should cause status=corrigido/escalado, got '{result['status']}'"
    )
    assert len(result["problemas_encontrados"]) > 0, (
        "The banned phrase must be listed in problemas_encontrados"
    )
    # At least one problem description must reference the phrase or the ban
    problem_text = " ".join(result["problemas_encontrados"]).lower()
    assert "espero" in problem_text or "banned" in problem_text or "proibid" in problem_text, (
        f"Expected problem to mention the banned phrase, got: {result['problemas_encontrados']}"
    )


# ── Test 3: Aprova texto correcto ─────────────────────────────────────────────

@pytest.mark.unit
async def test_aprovado_texto_correcto(mocker):
    """
    A clean, personalised WhatsApp message must receive status = "aprovado".

    When no violations are found: problemas_encontrados must be empty and
    qualidade_estimada must reflect the text quality.
    """
    mocker.patch(
        "agents.revisor.nodes.create_json_message",
        new_callable=AsyncMock,
        return_value=RevisorAvaliacaoSchema(
            status="aprovado",
            problemas_encontrados=[],
            qualidade_estimada="alta",
            motivo_escalonamento=None,
        ),
    )

    state = make_revisor_state(
        texto_original=(
            "Bom dia Dr. Santos!\n\n"
            "Vi que a Clínica Bem-Estar tem um Instagram muito activo "
            "mas vi que alguns comentários ficam sem resposta há vários dias.\n\n"
            "Temos uma solução usada por outras clínicas em Luanda que resolve "
            "exactamente isso — e que demora 3 semanas a implementar.\n\n"
            "Podemos falar 10 minutos esta semana?\n\n"
            "Fidel | BMST — Bisca+"
        )
    )

    result = await avaliar_texto(state)

    assert result["status"] == "aprovado", (
        f"Clean text must be approved, got status='{result['status']}'"
    )
    assert result["problemas_encontrados"] == [], (
        "No problems must be reported for a clean message"
    )
    assert result.get("qualidade_estimada") == "alta"


# ── Test 4: auto_corrigir substitui "chatbot" ─────────────────────────────────

@pytest.mark.unit
async def test_auto_corrige_chatbot(mocker):
    """
    auto_corrigir must replace 'chatbot' with an approved synonym such as
    'assistente de atendimento' or 'sistema de resposta rápida'.

    After correction:
    - texto_corrigido must NOT contain 'chatbot'
    - status must be 'corrigido' (never 'pendente')
    - auto_correcoes must be non-empty (lists what was changed)
    """
    corrected_text = (
        "O nosso assistente de atendimento responde automaticamente "
        "às perguntas dos seus clientes — 24 horas por dia."
    )

    mocker.patch(
        "agents.revisor.nodes.create_message",
        new_callable=AsyncMock,
        return_value=corrected_text,
    )

    state = make_revisor_state(
        texto_original=(
            "O nosso chatbot responde automaticamente "
            "às perguntas dos seus clientes — 24 horas por dia."
        ),
        status="corrigido",
        problemas_encontrados=["Contains forbidden term 'chatbot' in sentence 1"],
    )

    result = await auto_corrigir(state)

    assert "chatbot" not in (result.get("texto_corrigido") or "").lower(), (
        f"'chatbot' must be removed from texto_corrigido, got: {result.get('texto_corrigido')}"
    )
    assert result.get("status") in ("corrigido", "aprovado"), (
        f"status after correction must be 'corrigido', got '{result.get('status')}'"
    )
    assert len(result.get("auto_correcoes") or []) > 0, (
        "auto_correcoes must list the corrections that were applied"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS — LLM real (Claude API)
#
# O que NÃO se mocka:
#   - create_json_message / create_message  (LLM REAL — testamos o output)
#
# O que se continua a mockar:
#   - Supabase (autouse em conftest)
#
# Skip automático se ANTHROPIC_API_KEY contiver "test" (CI sem chave real):
#   import os; if "test" in os.environ.get("ANTHROPIC_API_KEY", "").lower(): pytest.skip(...)
# ═══════════════════════════════════════════════════════════════════════════════

import os as _os  # noqa: E402


def _require_real_key():
    """Skip the test if ANTHROPIC_API_KEY is a placeholder (CI / local without .env)."""
    key = _os.environ.get("ANTHROPIC_API_KEY", "")
    if not key or "test" in key.lower():
        pytest.skip("Skipped: set a real ANTHROPIC_API_KEY in .env to run integration tests")


# ── Integration 1: LLM detecta "inteligência artificial" ─────────────────────

@pytest.mark.integration
async def test_detecta_termo_proibido_ia_integration():
    """
    Real LLM call — verifies Claude classifies text with 'inteligência artificial'
    as non-approved and lists the violation in problemas_encontrados.

    Unlike the unit test (which mocks the LLM response), this test verifies
    that the actual model prompt correctly guides the evaluation.
    """
    _require_real_key()

    state = make_revisor_state(
        texto_original=(
            "Bom dia! A nossa solução de inteligência artificial "
            "responde a todos os seus clientes automaticamente 24/7."
        )
    )

    result = await avaliar_texto(state)

    assert result["status"] != "aprovado", (
        f"Real LLM must flag 'inteligência artificial' — got status='{result['status']}'"
    )
    assert len(result["problemas_encontrados"]) > 0, (
        "At least one problem must be reported for the forbidden AI term"
    )


# ── Integration 2: LLM detecta frase banida de abertura ──────────────────────

@pytest.mark.integration
async def test_detecta_frase_banida_integration():
    """
    Real LLM call — verifies Claude flags 'Espero que este email o encontre bem'
    as a banned opening phrase and returns status corrigido or escalado.
    """
    _require_real_key()

    state = make_revisor_state(
        texto_original=(
            "Espero que este email o encontre bem. "
            "Sou da BMST e gostaria de apresentar a nossa solução de automação."
        )
    )

    result = await avaliar_texto(state)

    assert result["status"] in ("corrigido", "escalado"), (
        f"Banned phrase must cause corrigido/escalado, got '{result['status']}'"
    )
    assert len(result["problemas_encontrados"]) > 0, (
        "The banned phrase must be listed in problemas_encontrados"
    )


# ── Integration 3: LLM aprova texto limpo ─────────────────────────────────────

@pytest.mark.integration
async def test_aprovado_texto_correcto_integration():
    """
    Real LLM call — verifies Claude approves a clean, personalised message
    with no forbidden terms or banned phrases.

    This is the golden path: a correctly written BMST WhatsApp message must
    pass the REVISOR without corrections.
    """
    _require_real_key()

    state = make_revisor_state(
        texto_original=(
            "Bom dia Dr. Santos!\n\n"
            "Vi que a Clínica Bem-Estar tem um Instagram muito activo "
            "mas alguns comentários ficam sem resposta há dias.\n\n"
            "Temos uma solução usada por outras clínicas em Luanda que resolve "
            "exactamente isso — em 3 semanas.\n\n"
            "Podemos falar 10 minutos esta semana?\n\n"
            "Fidel | BMST — Bisca+"
        )
    )

    result = await avaliar_texto(state)

    assert result["status"] == "aprovado", (
        f"Real LLM must approve a clean message, got status='{result['status']}'\n"
        f"Problems: {result.get('problemas_encontrados')}"
    )
    assert result["problemas_encontrados"] == [], (
        "No problems must be reported for a correctly written message"
    )


# ── Integration 4: LLM corrige "chatbot" com sinónimo aprovado ───────────────

@pytest.mark.integration
async def test_auto_corrige_chatbot_integration():
    """
    Real LLM call — verifies Claude replaces 'chatbot' with an approved synonym
    (e.g. 'assistente de atendimento', 'sistema de resposta rápida') and that
    the corrected text never contains the forbidden term.
    """
    _require_real_key()

    state = make_revisor_state(
        texto_original=(
            "O nosso chatbot responde automaticamente "
            "às perguntas dos seus clientes — 24 horas por dia."
        ),
        status="corrigido",
        problemas_encontrados=["Contains forbidden term 'chatbot'"],
    )

    result = await auto_corrigir(state)

    texto_final = (result.get("texto_corrigido") or "").lower()
    assert "chatbot" not in texto_final, (
        f"Real LLM must remove 'chatbot' from the corrected text.\n"
        f"texto_corrigido: {result.get('texto_corrigido')}"
    )
    assert result.get("status") in ("corrigido", "aprovado"), (
        f"Status after real correction must be 'corrigido', got '{result.get('status')}'"
    )
    assert len(result.get("auto_correcoes") or []) > 0, (
        "auto_correcoes must list what was changed"
    )
