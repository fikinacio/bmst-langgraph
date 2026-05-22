"""Unit tests for the WhatsApp webhook handler.

Covers:
    - Decision parsing for EN + PT keywords with various punctuations
    - Sender authorisation (only the configured approver phone is accepted)
    - Lookup → update → resume integration via mocks
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.api import webhooks


# ---------------------------------------------------------------------------
# _parse_decision — pure function tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message,expected",
    [
        # Approve variants
        ("APROVADO", ("approved", None)),
        ("aprovado", ("approved", None)),
        ("APPROVED!", ("approved", None)),
        ("Approve.", ("approved", None)),
        # Reject variants — bare
        ("REJEITADO", ("rejected", None)),
        ("REJECTED", ("rejected", None)),
        # Reject variants — with reason
        ("REJEITADO: tom errado", ("rejected", "tom errado")),
        ("REJECT: poor quality", ("rejected", "poor quality")),
        ("rejected - off-brand", ("rejected", "off-brand")),
        # Revise — note required
        ("REVISÃO: adicionar exemplos", ("revision_requested", "adicionar exemplos")),
        ("REVISION: more concrete examples", ("revision_requested", "more concrete examples")),
        ("revise: shorter hook", ("revision_requested", "shorter hook")),
        # Unrecognised
        ("Olá, tudo bem?", (None, None)),
        ("", (None, None)),
        ("Aproveito para...", (None, None)),  # "aprov" prefix but not "aprovado"
    ],
)
def test_parse_decision(message, expected):
    assert webhooks._parse_decision(message) == expected


# ---------------------------------------------------------------------------
# Webhook endpoint tests
# ---------------------------------------------------------------------------


def _evolution_payload(sender: str, body: str) -> dict:
    """Build a minimal Evolution-API webhook payload shape."""
    return {
        "data": {
            "key": {"remoteJid": f"{sender.lstrip('+')}@s.whatsapp.net"},
            "message": {"conversation": body},
            "messageTimestamp": int(datetime.now(timezone.utc).timestamp()),
        }
    }


@pytest.fixture
def fastapi_client():
    """FastAPI TestClient with checkpointer startup patched to no-op."""
    from fastapi.testclient import TestClient

    # Patch setup_checkpointer in main.py so the lifespan startup doesn't
    # try to talk to a real Redis instance during tests.
    with patch("src.api.main.setup_checkpointer", new=AsyncMock(return_value=None)):
        from src.api.main import app
        with TestClient(app) as client:
            yield client


def _patch_webhook_deps(*, session_id: str | None):
    """Patch SupabaseMemory + compiled_graph used by the webhook handler."""
    supa_mock = AsyncMock()
    supa_mock.connect = AsyncMock(return_value=None)
    supa_mock.get_latest_pending_session = AsyncMock(return_value=session_id)
    supa_mock.update_approval_by_session = AsyncMock(return_value=None)

    graph_mock = MagicMock()
    graph_mock.aupdate_state = AsyncMock(return_value=None)
    graph_mock.ainvoke = AsyncMock(return_value={"status": "ok"})

    return [
        patch.object(webhooks, "SupabaseMemory", return_value=supa_mock),
        patch.object(webhooks, "compiled_graph", graph_mock),
        patch.object(webhooks, "setup_checkpointer", new=AsyncMock(return_value=None)),
    ], supa_mock, graph_mock


def test_webhook_approve_resumes_graph(fastapi_client):
    """Valid approver + APROVADO → graph resumed with decision=approved."""
    patches, supa, graph = _patch_webhook_deps(session_id="sess-123")
    payload = _evolution_payload("+41795748225", "APROVADO")

    with patches[0], patches[1], patches[2]:
        response = fastapi_client.post("/webhook/whatsapp", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resumed"
    assert body["session_id"] == "sess-123"
    assert body["decision"] == "approved"

    # update_approval_by_session called with the resolved session_id
    supa.update_approval_by_session.assert_awaited_once_with("sess-123", "approved", None)

    # Graph state was updated as REVISOR, then ainvoke(None)
    graph.aupdate_state.assert_awaited_once()
    args, kwargs = graph.aupdate_state.call_args
    config = args[0] if args else kwargs.get("config")
    state_delta = args[1] if len(args) > 1 else kwargs.get("values")
    assert config["configurable"]["thread_id"] == "sess-123"
    assert state_delta["approval_decision"] == "approved"
    assert state_delta["pending_approval"] is False
    assert kwargs.get("as_node") == "revisor"
    graph.ainvoke.assert_awaited_once_with(None, config=config)


def test_webhook_reject_with_reason(fastapi_client):
    """REJEITADO: tom errado → decision=rejected, note='tom errado'."""
    patches, supa, _ = _patch_webhook_deps(session_id="sess-456")
    payload = _evolution_payload("+41795748225", "REJEITADO: tom errado")

    with patches[0], patches[1], patches[2]:
        response = fastapi_client.post("/webhook/whatsapp", json=payload)

    assert response.json()["decision"] == "rejected"
    supa.update_approval_by_session.assert_awaited_once_with(
        "sess-456", "rejected", "tom errado"
    )


def test_webhook_revise_with_note(fastapi_client):
    """REVISÃO: adicionar exemplos → revision_requested with note."""
    patches, supa, _ = _patch_webhook_deps(session_id="sess-789")
    payload = _evolution_payload("+41795748225", "REVISÃO: adicionar exemplos")

    with patches[0], patches[1], patches[2]:
        response = fastapi_client.post("/webhook/whatsapp", json=payload)

    assert response.json()["decision"] == "revision_requested"
    supa.update_approval_by_session.assert_awaited_once_with(
        "sess-789", "revision_requested", "adicionar exemplos"
    )


def test_webhook_wrong_sender_ignored(fastapi_client):
    """Message from a non-approver number is ignored with 200 OK."""
    patches, supa, graph = _patch_webhook_deps(session_id="sess-123")
    payload = _evolution_payload("+244912345678", "APROVADO")

    with patches[0], patches[1], patches[2]:
        response = fastapi_client.post("/webhook/whatsapp", json=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    # No DB write, no graph resume
    supa.update_approval_by_session.assert_not_awaited()
    graph.aupdate_state.assert_not_awaited()


def test_webhook_no_pending_session(fastapi_client):
    """Valid approver but no pending review_log row → 200 no_pending."""
    patches, supa, graph = _patch_webhook_deps(session_id=None)
    payload = _evolution_payload("+41795748225", "APROVADO")

    with patches[0], patches[1], patches[2]:
        response = fastapi_client.post("/webhook/whatsapp", json=payload)

    assert response.json()["status"] == "no_pending"
    supa.update_approval_by_session.assert_not_awaited()
    graph.aupdate_state.assert_not_awaited()
