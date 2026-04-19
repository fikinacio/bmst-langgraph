"""
Testes da API FastAPI
"""
from fastapi.testclient import TestClient
import os

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("BMST_API_KEY", "test-internal-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-supabase-key")

from api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("ok", "degraded")
    assert "redis" in data["services"]


def test_hunter_batch_sem_api_key_retorna_422():
    response = client.post("/hunter/batch", json={})
    assert response.status_code == 422  # Header X-Api-Key obrigatório em falta


def test_hunter_webhook_sem_autenticacao():
    """Webhook da Evolution API não requer autenticação interna."""
    response = client.post("/hunter/webhook", json={
        "phone": "+244923000000",
        "message": "Sim, tenho interesse.",
        "message_id": "test-msg-001",
        "timestamp": 1713236400,
    })
    assert response.status_code == 200
