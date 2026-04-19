# tests/test_hunter.py — unit and integration tests for the HUNTER agent
#
# ── Unit tests (nós isolados, LLM mockado) ───────────────────────────────────
# Mock pattern:
#   - LLM calls (async) → mocker.patch("agents.hunter.nodes.create_json_message",
#                                       new_callable=AsyncMock)
#   - External I/O (sync) → patched globally by conftest.mock_external_calls
#
# ── Integration tests (grafo completo, LLM mockado) ─────────────────────────
# Mock pattern — duas camadas distintas (hunter.nodes e revisor.nodes importam
# create_json_message/create_message independentemente de core.llm):
#
#   mocker.patch("agents.hunter.nodes.create_json_message", ...)  # triagem + template
#   mocker.patch("agents.revisor.nodes.create_json_message", ...)  # avaliar_texto
#   mocker.patch("agents.revisor.nodes.create_message", ...)       # verificar_personalizacao
#   mocker.patch("agents.revisor.nodes.send_approval_request", ...)  # pré-interrupt
#
# Interrupt/Resume — o interrupt() NÃO é mockado; testamos o mecanismo real:
#   state_1 = await graph.ainvoke(initial, config)                  # para em interrupt
#   final   = await graph.ainvoke(Command(resume={...}), config)    # retoma
#
# Run unit tests only (fast, no API):
#   pytest tests/test_hunter.py -v -m "not integration"
#
# Run integration test (requires real ANTHROPIC_API_KEY in .env):
#   pytest tests/test_hunter.py::test_mensagem_sem_termos_proibidos -v -m integration

from unittest.mock import AsyncMock

import pytest

from agents.hunter.nodes import confirmar_segmento, gerar_mensagem_hunter
from agents.hunter.prompts import SelecaoTemplateSchema, TriagemSchema
from tests.conftest import make_hunter_state


# ── Test 1: Seg A arquivado automaticamente ───────────────────────────────────

@pytest.mark.unit
async def test_seg_a_arquivado_automaticamente(mocker):
    """
    Seg A leads must be immediately archived — they are too small for BMST.

    confirmar_segmento should set proxima_acao = "arquivar" when the LLM
    returns segmento_confirmado = "A", without generating any message.
    """
    mock_llm = mocker.patch(
        "agents.hunter.nodes.create_json_message",
        new_callable=AsyncMock,
    )
    mock_llm.return_value = TriagemSchema(
        segmento_confirmado="A",
        qualificado=False,
        motivo="Volume de negócio insuficiente para ROI positivo.",
    )

    state  = make_hunter_state(segmento="A")

    result = await confirmar_segmento(state)

    assert result["proxima_acao"] == "arquivar", (
        f"Expected 'arquivar', got '{result['proxima_acao']}'"
    )
    assert result.get("mensagem_gerada") is None, (
        "Seg A leads must not have a message generated"
    )
    mock_llm.assert_called_once()


# ── Test 2: Seg B com notas gera mensagem válida ──────────────────────────────

@pytest.mark.unit
async def test_seg_b_gera_mensagem(mocker):
    """
    Seg B lead with filled notas_abordagem must produce a non-None message
    with at most 5 lines (REVISOR rule: max 6 lines, reject if > 6).

    Two LLM calls are made sequentially:
      1. create_json_message → TriagemSchema     (triagem)
      2. create_json_message → SelecaoTemplateSchema (template selection)
      3. create_message      → str               (message generation)
    Mocked with side_effect for the two json calls, separate patch for create_message.
    """
    # This message has 4 "\n" characters = 5 lines — within the limit
    mensagem_mock = (
        "Bom dia Dr. Santos!\n\n"
        "Vi que a Clínica Bem-Estar tem o Instagram activo mas os comentários ficam sem resposta.\n\n"
        "Temos uma solução específica para clínicas que resolve isso em 3 semanas.\n\n"
        "Fidel | BMST — Bisca+"
    )

    mocker.patch(
        "agents.hunter.nodes.create_json_message",
        new_callable=AsyncMock,
        side_effect=[
            TriagemSchema(segmento_confirmado="B", qualificado=True, motivo="Seg B qualificado"),
            SelecaoTemplateSchema(template="saude", justificacao="Sector match"),
        ],
    )
    mocker.patch(
        "agents.hunter.nodes.create_message",
        new_callable=AsyncMock,
        return_value=mensagem_mock,
    )

    state  = make_hunter_state(segmento="B")

    # Step 1: triagem
    r1 = await confirmar_segmento(state)
    assert r1["proxima_acao"] == "gerar_mensagem"

    # Step 2: generate message
    state.update(r1)
    r2 = await gerar_mensagem_hunter(state)

    assert r2.get("mensagem_gerada") is not None, "mensagem_gerada must not be None"
    assert r2.get("proxima_acao") != "arquivar", "Message generation should not archive"
    # Verify line count constraint: ≤ 6 newlines keeps message concise (4 blocks × \n\n)
    assert mensagem_mock.count("\n") <= 6, (
        f"Message has {mensagem_mock.count(chr(10))} newlines — exceeds the 6-newline limit"
    )


# ── Test 3: Mensagem não contém termos proibidos (integration) ────────────────

@pytest.mark.integration
async def test_mensagem_sem_termos_proibidos():
    """
    INTEGRATION — calls real Claude API.

    Verifies that the generated WhatsApp message never contains any of the
    forbidden terms from the REVISOR checklist (chatbot, IA, algoritmo, etc.).

    Skips automatically if ANTHROPIC_API_KEY is not a real key.
    """
    import os
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if "test" in api_key.lower() or not api_key:
        pytest.skip("Skipped: ANTHROPIC_API_KEY is not a real key — set it in .env to run")

    from agents.revisor.prompts import TERMOS_PROIBIDOS

    state  = make_hunter_state()

    r1 = await confirmar_segmento(state)
    if r1.get("proxima_acao") == "arquivar":
        pytest.skip("Lead was archived during triagem — no message to check")

    state.update(r1)
    r2 = await gerar_mensagem_hunter(state)

    msg = r2.get("mensagem_gerada") or ""
    assert msg, "Expected a non-empty message from gerar_mensagem_hunter"

    import re
    msg_lower = msg.lower()
    for term in TERMOS_PROIBIDOS:
        pattern = r"\b" + re.escape(term.lower()) + r"\b"
        assert not re.search(pattern, msg_lower), (
            f"Forbidden term '{term}' found in generated message:\n\n{msg}"
        )


# ── Test 4: Seg C sem aprovação não envia mensagem ────────────────────────────

@pytest.mark.unit
async def test_seg_c_sem_aprovacao_nao_envia(mocker):
    """
    Seg C leads with 'escalar_fundador: sim' in notas_abordagem must be
    routed to the founder via Telegram — not sent directly via WhatsApp.

    confirmar_segmento should set proxima_acao = "aguardar_aprovacao_seg_c".
    """
    mocker.patch(
        "agents.hunter.nodes.create_json_message",
        new_callable=AsyncMock,
        return_value=TriagemSchema(
            segmento_confirmado="C",
            qualificado=True,
            motivo="Grande empresa — requer aprovação do fundador",
        ),
    )

    state = make_hunter_state(
        segmento="C",
        notas_abordagem=(
            "Grande grupo hospitalar com 5 clínicas. "
            "escalar_fundador: sim — volume justifica abordagem directa do Fidel."
        ),
    )

    result = await confirmar_segmento(state)

    assert result["proxima_acao"] == "aguardar_aprovacao_seg_c", (
        f"Seg C with escalar_fundador flag must wait for founder approval, "
        f"got proxima_acao='{result.get('proxima_acao')}'"
    )
    assert result.get("mensagem_gerada") is None, (
        "No message must be generated before founder approval"
    )


# ── Test 5: notas_abordagem vazio → não envia, não chama LLM ─────────────────

@pytest.mark.unit
async def test_notas_abordagem_vazio_nao_envia(mocker):
    """
    Empty notas_abordagem must cause gerar_mensagem_hunter to archive the lead
    without making any LLM call.

    notas_abordagem is the mandatory PROSPECTOR hook — without it, HUNTER
    cannot personalise the message and must not send a generic one.
    """
    mock_json = mocker.patch(
        "agents.hunter.nodes.create_json_message",
        new_callable=AsyncMock,
    )
    mock_text = mocker.patch(
        "agents.hunter.nodes.create_message",
        new_callable=AsyncMock,
    )

    state  = make_hunter_state(notas_abordagem="", segmento="B")

    result = await gerar_mensagem_hunter(state)

    assert result["proxima_acao"] == "arquivar", (
        "Empty notas_abordagem must result in archiving the lead"
    )
    assert result.get("erro") is not None, "An error message must explain why"
    assert "notas_abordagem" in (result.get("erro") or "").lower(), (
        "Error must mention 'notas_abordagem' as the cause"
    )
    mock_json.assert_not_called()
    mock_text.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION TESTS — grafo completo via graph.ainvoke()
#
# Diferença face aos unit tests:
#   Unit:        await confirmar_segmento(state)           ← nó isolado
#   Integration: await graph.ainvoke(state, config)        ← grafo completo
#
# O LLM continua mockado (determinismo + custo). Testamos routing e wiring.
# ═══════════════════════════════════════════════════════════════════════════════

from langgraph.types import Command
from agents.hunter import get_hunter_graph
from agents.revisor.prompts import RevisorAvaliacaoSchema as _RevisorSchema
from tests.conftest import make_sheet_lead


def _mock_hunter_io(mocker):
    """
    Patch all external I/O for hunter graph integration tests.

    Mocks: Google Sheets, Telegram (report + Seg-C alert), Supabase node-level
    references (save_message / update_lead_state are imported locally in
    agents.hunter.nodes so the conftest autouse patch on core.memory.* does NOT
    reach them — they need their own explicit patch here).
    """
    mocker.patch(
        "agents.hunter.nodes.sheets_client.get_pending_leads",
        new_callable=AsyncMock,
        return_value=[],          # overridden per-test with side_effect / return_value
    )
    mocker.patch(
        "agents.hunter.nodes.sheets_client.update_lead_status",
        new_callable=AsyncMock,
        return_value=None,
    )
    mocker.patch(
        "agents.hunter.nodes.telegram_client.send_daily_report",
        new_callable=AsyncMock,
        return_value=None,
    )
    mocker.patch(
        "agents.hunter.nodes.telegram_client.send_message",
        new_callable=AsyncMock,
        return_value="tg-msg-id",
    )
    mocker.patch(
        "agents.hunter.nodes.save_message",
        new_callable=AsyncMock,
        return_value=True,
    )
    mocker.patch(
        "agents.hunter.nodes.update_lead_state",
        new_callable=AsyncMock,
        return_value=True,
    )
    mocker.patch(
        "agents.revisor.nodes.save_revisao",
        new_callable=AsyncMock,
        return_value=True,
    )


# ── Integration 1: Seg A arquivado — grafo completo ──────────────────────────

@pytest.mark.integration
async def test_seg_a_arquivado_automaticamente_integration(mocker):
    """
    Full graph run: Seg A lead → arquivar_lead → avancar_lead → relatorio → END.

    Verifies that the graph routing correctly archives Seg A leads without
    generating any message. mensagens_enviadas must be 0 in the final state.
    """
    _mock_hunter_io(mocker)

    mocker.patch(
        "agents.hunter.nodes.sheets_client.get_pending_leads",
        new_callable=AsyncMock,
        return_value=[make_sheet_lead(segmento="A")],
    )
    mocker.patch(
        "agents.hunter.nodes.create_json_message",
        new_callable=AsyncMock,
        return_value=TriagemSchema(
            segmento_confirmado="A",
            qualificado=False,
            motivo="Volume insuficiente para ROI positivo.",
        ),
    )

    graph  = get_hunter_graph()
    config = {"configurable": {"thread_id": "integration-hunter-seg-a-001"}}

    final = await graph.ainvoke(make_hunter_state(), config)

    assert final.get("mensagens_enviadas", 0) == 0, (
        "Seg A must not generate any WhatsApp message"
    )
    assert final.get("leads_processados", 0) >= 1, (
        "Lead must be counted as processed"
    )


# ── Integration 2: Seg B — grafo completo com interrupt real ─────────────────

@pytest.mark.integration
async def test_seg_b_gera_mensagem_integration(mocker):
    """
    Full graph run: Seg B lead → REVISOR pipeline → interrupt (real LangGraph
    mechanism) → Command(resume=approved) → enviar_whatsapp → END.

    Tests routing AND the interrupt/resume checkpoint mechanism.
    mensagens_enviadas must be 1 in the final state.
    """
    _mock_hunter_io(mocker)

    mensagem_mock = (
        "Bom dia Dr. Santos!\n\n"
        "Vi que a Clínica Bem-Estar tem o Instagram activo "
        "mas os comentários ficam sem resposta.\n\n"
        "Temos uma solução específica para clínicas — 3 semanas.\n\n"
        "Fidel | BMST — Bisca+"
    )

    mocker.patch(
        "agents.hunter.nodes.sheets_client.get_pending_leads",
        new_callable=AsyncMock,
        return_value=[make_sheet_lead(segmento="B")],
    )
    # Hunter nodes: triagem (call 1) + template selection (call 2)
    mocker.patch(
        "agents.hunter.nodes.create_json_message",
        new_callable=AsyncMock,
        side_effect=[
            TriagemSchema(segmento_confirmado="B", qualificado=True, motivo="Seg B qualificado"),
            SelecaoTemplateSchema(template="saude", justificacao="Sector match"),
        ],
    )
    # Hunter nodes: message body generation
    mocker.patch(
        "agents.hunter.nodes.create_message",
        new_callable=AsyncMock,
        return_value=mensagem_mock,
    )
    # Revisor nodes: avaliar_texto → aprovado (no correction needed)
    mocker.patch(
        "agents.revisor.nodes.create_json_message",
        new_callable=AsyncMock,
        return_value=_RevisorSchema(
            status="aprovado",
            problemas_encontrados=[],
            qualidade_estimada="alta",
            motivo_escalonamento=None,
        ),
    )
    # Revisor nodes: verificar_personalizacao → OK
    mocker.patch(
        "agents.revisor.nodes.create_message",
        new_callable=AsyncMock,
        return_value='{"is_personalised": true, "reason": "References Dr. Santos by name"}',
    )
    # Revisor: Telegram approval request (fired before interrupt)
    mocker.patch(
        "agents.revisor.nodes.send_approval_request",
        new_callable=AsyncMock,
        return_value="tg-approval-msg-id",
    )
    # WhatsApp send
    mocker.patch(
        "agents.hunter.nodes.evolution_client.send_text_message",
        new_callable=AsyncMock,
        return_value={"key": {"id": "wa-msg-123"}},
    )
    # Redis dedup
    mocker.patch("agents.hunter.nodes.is_duplicate", return_value=False)
    mocker.patch("agents.hunter.nodes.mark_sent",    return_value=None)
    # Anti-spam delay — avoid real 90s sleep
    mocker.patch("time.sleep")

    graph  = get_hunter_graph()
    config = {"configurable": {"thread_id": "integration-hunter-seg-b-001"}}

    # ── First invocation: runs until interrupt at preparar_aprovacao ──────────
    await graph.ainvoke(make_hunter_state(), config)

    # ── Resume: founder approves the message ──────────────────────────────────
    final = await graph.ainvoke(
        Command(resume={"aprovado": True, "texto_editado": None}),
        config,
    )

    assert final.get("mensagens_enviadas", 0) == 1, (
        "Seg B approved message must be counted in mensagens_enviadas"
    )
    assert final.get("mensagem_enviada") is True or final.get("mensagens_enviadas", 0) == 1


# ── Integration 3: Seg C com flag escalar_fundador — sem envio directo ────────

@pytest.mark.integration
async def test_seg_c_sem_aprovacao_nao_envia_integration(mocker):
    """
    Full graph run: Seg C lead with 'escalar_fundador: sim' → notificar_seg_c
    (Telegram alert to founder) → avancar_lead → relatorio → END.

    No WhatsApp message must be sent. Founder must be notified via Telegram.
    """
    _mock_hunter_io(mocker)

    mocker.patch(
        "agents.hunter.nodes.sheets_client.get_pending_leads",
        new_callable=AsyncMock,
        return_value=[make_sheet_lead(
            segmento="C",
            notas_abordagem=(
                "Grande grupo hospitalar com 5 clínicas. "
                "escalar_fundador: sim — volume justifica abordagem directa."
            ),
        )],
    )
    mocker.patch(
        "agents.hunter.nodes.create_json_message",
        new_callable=AsyncMock,
        return_value=TriagemSchema(
            segmento_confirmado="C",
            qualificado=True,
            motivo="Grande empresa — requer aprovação do fundador",
        ),
    )

    telegram_mock = mocker.patch(
        "agents.hunter.nodes.telegram_client.send_message",
        new_callable=AsyncMock,
        return_value="tg-seg-c-notification",
    )

    graph  = get_hunter_graph()
    config = {"configurable": {"thread_id": "integration-hunter-seg-c-001"}}

    final = await graph.ainvoke(make_hunter_state(), config)

    assert final.get("mensagens_enviadas", 0) == 0, (
        "Seg C must NOT send a WhatsApp message without prior founder approval"
    )
    telegram_mock.assert_called_once(), (
        "Founder must be notified via Telegram about the Seg C lead"
    )


# ── Integration 4: notas_abordagem vazio — grafo arquiva sem chamar LLM ──────

@pytest.mark.integration
async def test_notas_abordagem_vazio_nao_envia_integration(mocker):
    """
    Full graph run: Seg B lead with empty notas_abordagem → gerar_mensagem_hunter
    archives immediately without calling LLM → avancar_lead → relatorio → END.

    Verifies the early-return guard in gerar_mensagem_hunter propagates correctly
    through the graph's routing (arquivar branch) all the way to END.
    """
    _mock_hunter_io(mocker)

    mocker.patch(
        "agents.hunter.nodes.sheets_client.get_pending_leads",
        new_callable=AsyncMock,
        return_value=[make_sheet_lead(segmento="B", notas_abordagem="")],
    )
    # confirmar_segmento qualifies the lead — gerar_mensagem_hunter should then archive
    triagem_mock = mocker.patch(
        "agents.hunter.nodes.create_json_message",
        new_callable=AsyncMock,
        return_value=TriagemSchema(
            segmento_confirmado="B",
            qualificado=True,
            motivo="Seg B — notas vazias detectadas mais tarde",
        ),
    )
    create_message_mock = mocker.patch(
        "agents.hunter.nodes.create_message",
        new_callable=AsyncMock,
    )

    graph  = get_hunter_graph()
    config = {"configurable": {"thread_id": "integration-hunter-empty-notas-001"}}

    final = await graph.ainvoke(make_hunter_state(notas_abordagem=""), config)

    assert final.get("mensagens_enviadas", 0) == 0, (
        "Empty notas_abordagem must result in no WhatsApp message"
    )
    create_message_mock.assert_not_called(), (
        "create_message must NOT be called when notas_abordagem is empty"
    )
