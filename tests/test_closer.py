# tests/test_closer.py — unit tests for the CLOSER agent
#
# Mock pattern for interrupt():
#   mocker.patch("agents.closer.nodes.interrupt", return_value={...})
#   The patched interrupt() returns the dict immediately instead of pausing the graph.
#   This lets us test the post-interrupt decision logic in a single synchronous call.
#
# Mock pattern for Telegram:
#   mocker.patch("agents.closer.nodes.telegram_client.send_proposal_approval_request",
#                new_callable=AsyncMock, return_value="msg-id")
#
# Run:
#   pytest tests/test_closer.py -v

from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from agents.closer.nodes import gerar_rascunho_proposta
from agents.closer.prompts import PropostaDraftSchema, SolucaoSchema
from tests.conftest import make_closer_state


# ── Test 1: Proposta não enviada quando fundador rejeita ─────────────────────

@pytest.mark.unit
async def test_proposta_nao_enviada_sem_aprovacao(mocker):
    """
    When the founder rejects the proposal draft, proposta_enviada must remain
    False and proxima_acao must be set to "perdido".

    Flow tested:
      gerar_rascunho_proposta
        → create_json_message   (proposal draft — mocked)
        → telegram_client.send_proposal_approval_request  (Telegram — mocked)
        → interrupt()           (founder reviews — mocked to return rejected)
        → returns proxima_acao = "perdido", proposta_enviada unchanged (False)
    """
    # Mock 1: proposal draft LLM call
    mocker.patch(
        "agents.closer.nodes.create_json_message",
        new_callable=AsyncMock,
        return_value=PropostaDraftSchema(
            cliente="Clínica Bem-Estar",
            decisor="Dr. Santos",
            problema_identificado="Alto volume de mensagens WhatsApp sem resposta",
            solucao_proposta="Chatbot WhatsApp básico",
            entregaveis=[
                "Configuração e personalização do chatbot",
                "Integração com o WhatsApp Business da clínica",
                "Treino da equipa (2 sessões)",
            ],
            prazo_semanas=4,
            valor_aoa=250_000,
            condicoes_pagamento="50% à assinatura + 50% antes da entrega",
            validade_proposta_dias=15,
            notas_fundador="Lead muito receptivo. Referenciado por parceiro.",
        ),
    )

    # Mock 2: Telegram send (called BEFORE interrupt to notify founder)
    mocker.patch(
        "agents.closer.nodes.telegram_client.send_proposal_approval_request",
        new_callable=AsyncMock,
        return_value="telegram-msg-id-999",
    )

    # Mock 3: interrupt() — founder rejects the proposal
    mocker.patch(
        "agents.closer.nodes.interrupt",
        return_value={"aprovado": False, "texto_editado": None},
    )

    state  = make_closer_state()
    config = {"configurable": {"thread_id": "closer-+244923000001"}}

    result = await gerar_rascunho_proposta(state, config)

    # Proposal must not be marked as sent
    assert result.get("proposta_enviada") is not True, (
        "proposta_enviada must remain False when founder rejects"
    )
    # Lead must be marked as lost
    assert result.get("proxima_acao") == "perdido", (
        f"proxima_acao must be 'perdido' after rejection, got '{result.get('proxima_acao')}'"
    )
    # Proposal draft must still be stored (for audit purposes)
    assert result.get("rascunho_proposta") is not None, (
        "The draft must be stored even when rejected"
    )
    assert result.get("proposta_aprovada") is False


# ── Test 2: Regra de negócio — mínimo 180.000 AOA ────────────────────────────

@pytest.mark.unit
def test_valor_minimo_180000_aoa():
    """
    SolucaoSchema enforces a minimum valor_minimo_aoa of 180,000 AOA via
    Pydantic Field(ge=180_000).

    Any value below this threshold must raise a ValidationError, ensuring
    the CLOSER never proposes a project below BMST's minimum viable rate.

    This is a pure schema-level test — no async, no mocks.
    """
    with pytest.raises(ValidationError) as exc_info:
        SolucaoSchema(
            servico_recomendado="Chatbot WhatsApp básico",
            justificacao="Opção de menor custo para pequenas clínicas",
            valor_minimo_aoa=100_000,   # below the 180,000 AOA minimum
            valor_maximo_aoa=200_000,
            prazo_semanas=4,
            beneficio_1="Resposta automática 24/7 sem custo de staff",
            beneficio_2="Redução de chamadas perdidas em 60%",
        )

    errors = exc_info.value.errors()
    field_names = [str(e.get("loc", "")) for e in errors]

    assert any("valor_minimo_aoa" in name for name in field_names), (
        f"ValidationError must reference 'valor_minimo_aoa', got fields: {field_names}"
    )


# ── Bonus: schema validates correctly above the minimum ───────────────────────

@pytest.mark.unit
def test_valor_acima_minimo_valido():
    """
    SolucaoSchema must accept any valor_minimo_aoa >= 180,000 AOA.

    Verifies the lower boundary is inclusive (180,000 is valid).
    """
    solucao = SolucaoSchema(
        servico_recomendado="Chatbot WhatsApp básico",
        justificacao="Solução base para clínicas com volume moderado",
        valor_minimo_aoa=180_000,   # exactly at the minimum — must be valid
        valor_maximo_aoa=280_000,
        prazo_semanas=4,
        beneficio_1="Resposta automática 24/7",
        beneficio_2="Redução da carga da equipa de atendimento",
    )

    assert solucao.valor_minimo_aoa == 180_000
    assert solucao.valor_maximo_aoa == 280_000


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS — LLM real (Claude API)
#
# O que NÃO se mocka:
#   - create_json_message   (LLM REAL — testamos o output da proposta)
#
# O que se continua a mockar:
#   - interrupt()           (mecanismo LangGraph — inviável ao nível de nó)
#   - telegram_client.*     (não notificar o fundador real)
#   - Supabase              (autouse em conftest)
#
# Skip automático se ANTHROPIC_API_KEY contiver "test".
# ═══════════════════════════════════════════════════════════════════════════════

import os as _os  # noqa: E402

from agents.closer.nodes import seleccionar_solucao  # noqa: E402


def _require_real_key_closer():
    key = _os.environ.get("ANTHROPIC_API_KEY", "")
    if not key or "test" in key.lower():
        pytest.skip("Skipped: set a real ANTHROPIC_API_KEY in .env to run integration tests")


# ── Integration 1: LLM gera proposta real — fundador rejeita ─────────────────

@pytest.mark.integration
async def test_proposta_nao_enviada_sem_aprovacao_integration(mocker):
    """
    Real LLM call — verifies that a real Claude-generated proposal is correctly
    stored as rascunho_proposta but NOT sent when the founder rejects it.

    Unlike the unit test (which uses a hand-crafted PropostaDraftSchema mock),
    this test verifies the LLM produces a structurally valid PropostaDraftSchema
    (Pydantic validation passes) and that the post-interrupt rejection logic works.
    """
    _require_real_key_closer()

    # Telegram: mock — we don't want to notify the real founder during tests
    mocker.patch(
        "agents.closer.nodes.telegram_client.send_proposal_approval_request",
        new_callable=AsyncMock,
        return_value="tg-integration-msg-id",
    )
    # interrupt(): mock to immediately return founder rejection
    mocker.patch(
        "agents.closer.nodes.interrupt",
        return_value={"aprovado": False, "texto_editado": None},
    )

    state  = make_closer_state(
        _solucao_cache={
            "servico_recomendado": "Chatbot WhatsApp básico",
            "valor_minimo_aoa":    180_000,
            "valor_maximo_aoa":    280_000,
            "prazo_semanas":       4,
            "beneficio_1":         "Resposta automática 24/7",
            "beneficio_2":         "Redução de mensagens sem resposta",
            "justificacao":        "Solução ideal para clínicas com volume moderado",
        }
    )
    config = {"configurable": {"thread_id": "integration-closer-rejected-001"}}

    result = await gerar_rascunho_proposta(state, config)

    # The LLM must have generated a structurally valid draft
    assert result.get("rascunho_proposta") is not None, (
        "Real LLM must produce a non-None rascunho_proposta"
    )
    # Rejection logic must hold regardless of LLM output
    assert result.get("proposta_enviada") is not True, (
        "proposta_enviada must remain False after rejection"
    )
    assert result.get("proxima_acao") == "perdido", (
        f"proxima_acao must be 'perdido' after rejection, got '{result.get('proxima_acao')}'"
    )
    assert result.get("proposta_aprovada") is False

    # Validate LLM output quality: valor_aoa must be within sane range
    draft = result["rascunho_proposta"]
    assert isinstance(draft, dict), "rascunho_proposta must be a dict"
    assert draft.get("valor_aoa", 0) >= 180_000, (
        f"LLM proposal valor_aoa must be >= 180,000 AOA, got {draft.get('valor_aoa')}"
    )


# ── Integration 2: LLM respeita o mínimo de 180.000 AOA ──────────────────────

@pytest.mark.integration
async def test_valor_minimo_180000_aoa_integration():
    """
    Real LLM call — verifies that seleccionar_solucao() never produces a
    valor_minimo_aoa below 180,000 AOA even for a very small business.

    The floor is enforced at two levels:
      1. Pydantic Field(ge=180_000) in SolucaoSchema — hard rejection
      2. The SELECAO_SOLUCAO_PROMPT instructs the LLM about the minimum

    This test verifies level 2: the real LLM respects the minimum without
    needing Pydantic to reject and retry.
    """
    _require_real_key_closer()

    # Minimal state: micro-business with very limited turnover
    state = make_closer_state(
        empresa="Mini Loja Luanda",
        sector="retalho",
        segmento="B",
        responsavel="João Ferreira",
        problema_identificado="Não tem presença online e perde clientes",
        perguntas_feitas=[
            "Quantos funcionários tem?",
            "Qual é a faturação mensal aproximada?",
        ],
        respostas_cliente=[
            "Apenas 3 funcionários.",
            "Faturação à volta de 300.000 AOA por mês.",
        ],
        diagnostico_completo=True,
    )

    result = await seleccionar_solucao(state)

    solucao = result.get("_solucao_cache") or {}
    valor_min = solucao.get("valor_minimo_aoa", 0)

    assert valor_min >= 180_000, (
        f"Real LLM must respect the 180,000 AOA floor — got valor_minimo_aoa={valor_min:,}\n"
        f"Full _solucao_cache: {solucao}"
    )
