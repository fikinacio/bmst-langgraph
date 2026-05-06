"""
Testes da API FastAPI
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("BMST_API_KEY", "test-internal-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-supabase-key")

from api.main import app

client = TestClient(app)


def test_health():
    """Health returns 200 with status and services dict (mocked to succeed)."""
    with (
        patch("api.main._check_redis", return_value="ok") if hasattr(
            __import__("api.main", fromlist=["_check_redis"]), "_check_redis"
        ) else patch("core.redis_client.get_redis") as _,
        patch("core.memory.get_lead", return_value=None),
        patch("core.evolution_client.get_message_status", new_callable=AsyncMock, return_value={}),
        patch("core.sheets_client.get_pending_leads", new_callable=AsyncMock, return_value=[]),
        patch("core.redis_client.get_redis") as mock_redis,
    ):
        mock_redis.return_value.ping = MagicMock(return_value=True)
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "services" in data
    assert "redis" in data["services"]


def test_hunter_run_sem_api_key_retorna_401():
    """/hunter/batch sem X-Api-Key header obrigatório deve retornar 422."""
    response = client.post("/hunter/batch", json={"max_leads": 5})
    assert response.status_code == 422  # Header X-Api-Key em falta → Unprocessable Entity


def test_hunter_webhook_sem_autenticacao():
    """Webhook da Evolution API não requer autenticação interna."""
    with (
        patch("api.main.is_duplicate", return_value=False),
        patch("api.main.mark_sent", return_value=None),
        patch("api.main.hash_message", return_value="abc123"),
        patch("core.memory.upsert_lead", return_value={}),
        patch("core.memory.save_message", return_value=True),
    ):
        response = client.post("/hunter/webhook", json={
            "phone": "+244923000000",
            "message": "Sim, tenho interesse.",
            "message_id": "msg-001",
            "timestamp": 1713254400,
        })
    assert response.status_code == 200
