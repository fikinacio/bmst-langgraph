"""
Testes da API FastAPI
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
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
    assert data["status"] == "ok"
    assert "hunter" in data["agents"]


def test_hunter_run_sem_api_key_retorna_401():
    response = client.post("/hunter/run", json={"triggered_by": "manual"})
    assert response.status_code == 422  # Header obrigatório em falta


def test_hunter_webhook_sem_autenticacao():
    """Webhook da Evolution API não requer autenticação interna."""
    response = client.post("/hunter/webhook", json={
        "lead_id": "1",
        "whatsapp": "+244923000000",
        "mensagem": "Sim, tenho interesse.",
        "timestamp": "2026-04-16T09:00:00",
    })
    assert response.status_code == 200
