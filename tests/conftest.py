# tests/conftest.py — shared fixtures and mock infrastructure
#
# CRITICAL: env vars MUST be set before any import of core.* modules.
# core/settings.py and core/memory.py read env vars at import time.
# This file is loaded by pytest before any test module is imported.

import os

# ── Carregar .env ANTES de qualquer setdefault ────────────────────────────────
# Lemos o .env com dotenv_values() (não toca em os.environ) e depois
# definimos cada variável apenas quando ela está AUSENTE ou VAZIA no ambiente
# do sistema. Isto garante que:
#   • Chaves reais no .env chegam aos testes de integração
#   • Vars já definidas pelo CI (não-vazias) não são sobrescritas
try:
    from dotenv import dotenv_values as _dotenv_values
    for _k, _v in _dotenv_values().items():
        if _v and not os.environ.get(_k):   # ausente ou vazio no sistema
            os.environ[_k] = _v
except ImportError:
    pass   # python-dotenv não instalado — vars devem vir do ambiente do sistema

os.environ.setdefault("ANTHROPIC_API_KEY",    "test-key-not-real")
os.environ.setdefault("SUPABASE_URL",          "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_KEY",  "test-service-key")
os.environ.setdefault("REDIS_URL",             "redis://localhost:6379")
os.environ.setdefault("EVOLUTION_API_URL",     "http://test-evolution")
os.environ.setdefault("EVOLUTION_API_KEY",     "test-evo-key")
os.environ.setdefault("EVOLUTION_INSTANCE",    "test-instance")
os.environ.setdefault("TELEGRAM_BOT_TOKEN",    "123:test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID",      "999")
os.environ.setdefault("APP_ENV",               "test")
os.environ.setdefault("BMST_API_KEY",          "test-api-key")

import pytest


# ── Autouse fixture: silence all external I/O ─────────────────────────────────

@pytest.fixture(autouse=True)
def mock_external_calls(mocker):
    """
    Patch all I/O so unit tests never hit real services.

    Applied automatically to every test in the suite.
    Integration tests that need real calls must override specific patches.
    """
    mocker.patch("core.memory.save_message",      return_value=True)
    mocker.patch("core.memory.update_lead_state", return_value=True)
    mocker.patch("core.memory.save_revisao",      return_value=True)
    mocker.patch("core.memory.upsert_lead",       return_value={})
    mocker.patch("core.memory.get_lead",          return_value=None)
    mocker.patch("core.redis_client.is_duplicate", return_value=False)
    mocker.patch("core.redis_client.mark_sent",    return_value=None)
    mocker.patch("core.redis_client.hash_message", return_value="test-hash")


# ── State factory helpers ─────────────────────────────────────────────────────

def make_hunter_state(**overrides) -> dict:
    """
    Return a minimal valid HunterState dict for unit tests.

    All optional fields are set to safe defaults so nodes never raise KeyError.
    Use overrides to customise individual fields for a specific test scenario.
    """
    base: dict = {
        "lead_id":                "lead-001",
        "sheet_row_index":        1,
        "empresa":                "Clínica Bem-Estar",
        "sector":                 "saude",
        "segmento":               "B",
        "responsavel":            "Dr. Santos",
        "whatsapp":               "+244923000001",
        "notas_abordagem": (
            "Instagram activo mas sem resposta aos comentários. "
            "Site menciona consultas mas não tem marcação online."
        ),
        "oportunidade":           "Automatização de marcações",
        "servico_bmst":           "Chatbot WhatsApp básico",
        "valor_est_aoa":          250_000,
        "qualificado":            None,
        "motivo_rejeicao":        None,
        "template_usado":         None,
        "mensagem_gerada":        None,
        "nota_interna":           None,
        "texto_original":         None,
        "texto_corrigido":        None,
        "status":                 None,
        "problemas_encontrados":  [],
        "auto_correcoes":         [],
        "qualidade_estimada":     None,
        "motivo_escalonamento":   None,
        "aprovacao_fundador":     None,
        "revisao_status":         None,
        "revisao_texto_final":    None,
        "revisao_notas":          None,
        "mensagem_enviada":       False,
        "whatsapp_message_id":    None,
        "proxima_acao":           None,
        "erro":                   None,
        "leads_pendentes":        [],
        "leads_processados":      0,
        "mensagens_enviadas":     0,
        "_revisor_contexto":      {},
    }
    base.update(overrides)
    return base


def make_revisor_state(**overrides) -> dict:
    """
    Return a minimal valid REVISOR state dict.

    The REVISOR state is embedded inside HunterState / CloserState — these
    fields are shared across all agents via the TypedDict inheritance pattern.
    """
    base: dict = {
        "texto_original":        "Bom dia Dr. Santos!",
        "texto_corrigido":       None,
        "status":                "pendente",
        "problemas_encontrados": [],
        "auto_correcoes":        [],
        "qualidade_estimada":    "alta",
        "aprovacao_fundador":    None,
        "motivo_escalonamento":  None,
        "_revisor_contexto": {
            "empresa":   "Clínica Bem-Estar",
            "segmento":  "B",
            "canal":     "WhatsApp",
            "agente":    "HUNTER",
            "thread_id": "hunter-test-001",
        },
        "lead_id": "+244923000001",
    }
    base.update(overrides)
    return base


def make_sheet_lead(**overrides) -> dict:
    """
    Return a lead dict in the exact format returned by sheets_client.get_pending_leads().

    Used in graph-level integration tests to bypass the Google Sheets API.
    _extrair_campos_lead() maps these keys to HunterState field names.
    """
    base: dict = {
        "id":               "sheet-lead-001",
        "_row_index":       2,
        "empresa":          "Clínica Bem-Estar",
        "sector":           "saude",
        "segmento":         "B",
        "responsavel":      "Dr. Santos",
        "whatsapp":         "+244923000001",
        "notas_abordagem": (
            "Instagram activo mas sem resposta aos comentários. "
            "Site menciona consultas mas não tem marcação online."
        ),
        "oportunidade":     "Automatização de marcações",
        "servico_bmst":     "Chatbot WhatsApp básico",
        "valor_est_aoa":    250_000,
    }
    base.update(overrides)
    return base


def make_closer_state(**overrides) -> dict:
    """
    Return a minimal valid CloserState dict for unit tests.

    Initialised with a lead that has completed the 3-question diagnostic phase
    and is ready for solution selection and proposal generation.
    """
    base: dict = {
        "phone":              "+244923000001",
        "empresa":            "Clínica Bem-Estar",
        "sector":             "saude",
        "segmento":           "B",
        "responsavel":        "Dr. Santos",
        "historico_conversa": [],
        "perguntas_feitas":   ["Quantas mensagens recebe por dia?"],
        "respostas_cliente":  ["Umas 50, não consigo responder a todas."],
        "diagnostico_completo":  True,
        "problema_identificado": "Alto volume de mensagens não respondidas",
        "servico_recomendado":   "Chatbot WhatsApp básico",
        "rascunho_proposta":  None,
        "proposta_aprovada":  None,
        "edicoes_fundador":   None,
        "pdf_url":            None,
        "proposta_enviada":   False,
        "followup_dia":       0,
        "proxima_acao":       None,
        "erro":               None,
        # Internal cache
        "_solucao_cache":                 None,
        "_texto_apresentacao_final":      None,
        "_revisao_notas_apresentacao":    None,
        "_objecao_detectada":             None,
        "_classificacao_proposta":        None,
        # REVISOR shared fields
        "texto_original":         None,
        "texto_corrigido":        None,
        "status":                 "pendente",
        "problemas_encontrados":  [],
        "auto_correcoes":         [],
        "qualidade_estimada":     None,
        "aprovacao_fundador":     None,
        "motivo_escalonamento":   None,
        "_revisor_contexto":      {},
        "lead_id":                "+244923000001",
    }
    base.update(overrides)
    return base
