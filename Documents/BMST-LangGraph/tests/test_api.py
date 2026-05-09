"""
Testes da API FastAPI
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("BMST_API_KEY", "test-internal-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-supabase-key")

from api.main import app

client = TestClient(app)


def test_health(mocker):
    """Health check deve retornar 200 (degraded aceitável em ambiente de teste)."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "services" in data
    assert "redis" in data["services"]


def test_hunter_batch_sem_api_key_retorna_401():
    """O endpoint /hunter/batch requer X-Api-Key — sem ela deve retornar 401."""
    response = client.post(
        "/hunter/batch",
        json={"max_leads": 5},
        headers={"X-Api-Key": "chave-errada"},
    )
    assert response.status_code == 401


def test_hunter_webhook_aceita_payload_correcto(mocker):
    """Webhook da Evolution API deve aceitar o payload correcto sem autenticação."""
    mocker.patch("core.redis_client.is_duplicate", return_value=False)
    mocker.patch("core.redis_client.mark_sent", return_value=True)
    mocker.patch("core.memory.save_message", return_value=True)
    mocker.patch("core.memory.upsert_lead", return_value={})

    response = client.post("/hunter/webhook", json={
        "phone":      "+244923000000",
        "message":    "Sim, tenho interesse.",
        "message_id": "msg-001",
        "timestamp":  1713261600,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
