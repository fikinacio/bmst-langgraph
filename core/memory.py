# core/memory.py — cliente Supabase: leads, mensagens e revisões

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from functools import lru_cache

from supabase import Client, create_client

logger = logging.getLogger(__name__)

# ── Nomes de tabelas / colunas (ajustar se o schema Supabase mudar) ───────────
_TABLE_LEADS     = "deals"       # tabela de leads/prospects
_TABLE_MENSAGENS = "mensagens"   # tabela de histórico de mensagens
_TABLE_REVISOES  = "revisoes"    # tabela de revisões do REVISOR
_COL_MSG_CONTENT = "conteudo"    # texto da mensagem
_COL_MSG_ROLE    = "direcao"     # "user" | "assistant" | "system"
_COL_MSG_TS      = "timestamp"   # data/hora da mensagem
_COL_MSG_CANAL   = "canal"       # canal de comunicação (ex: "whatsapp")

# ── Cliente ───────────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_client() -> Client:
    """Singleton Supabase. Falha imediatamente se as variáveis não existirem."""
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL e SUPABASE_SERVICE_KEY têm de estar definidas no ambiente."
        )
    return create_client(url, key)


# ── Leads ─────────────────────────────────────────────────────────────────────

def get_lead(phone: str) -> dict | None:
    """
    Devolve o lead com o número de telefone indicado, ou None se não existir.

    Tabela: leads
    Chave:  phone (unique)
    """
    try:
        result = (
            _get_client()
            .table(_TABLE_LEADS)
            .select("*")
            .eq("phone", phone)
            .limit(1)
            .execute()
        )
        if result.data:
            logger.debug("get_lead: encontrado phone=%s", phone)
            return result.data[0]
        logger.debug("get_lead: não encontrado phone=%s", phone)
        return None
    except Exception as exc:
        logger.error("get_lead falhou (phone=%s): %s", phone, exc)
        return None


def upsert_lead(lead_data: dict) -> dict:
    """
    Insere ou actualiza um lead. O campo 'phone' é a chave de conflito.

    lead_data deve conter pelo menos {'phone': '+244...'}
    Devolve o registo após upsert, ou {} em caso de erro.
    """
    try:
        result = (
            _get_client()
            .table(_TABLE_LEADS)
            .upsert(lead_data, on_conflict="phone")
            .execute()
        )
        if result.data:
            logger.debug("upsert_lead: ok phone=%s", lead_data.get("phone"))
            return result.data[0]
        return {}
    except Exception as exc:
        logger.error("upsert_lead falhou (phone=%s): %s", lead_data.get("phone"), exc)
        return {}


def update_lead_state(phone: str, estado: str, agente: str) -> bool:
    """
    Actualiza o estado e o agente responsável de um lead.

    Devolve True se a actualização afectou pelo menos uma linha, False caso contrário.
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        result = (
            _get_client()
            .table(_TABLE_LEADS)
            .update({"estado": estado, "agente": agente, "updated_at": now})
            .eq("phone", phone)
            .execute()
        )
        updated = bool(result.data)
        if updated:
            logger.debug(
                "update_lead_state: phone=%s estado=%s agente=%s", phone, estado, agente
            )
        else:
            logger.warning(
                "update_lead_state: nenhuma linha afectada (phone=%s)", phone
            )
        return updated
    except Exception as exc:
        logger.error(
            "update_lead_state falhou (phone=%s estado=%s): %s", phone, estado, exc
        )
        return False


# ── Mensagens ─────────────────────────────────────────────────────────────────

def save_message(phone: str, role: str, content: str, agente: str) -> bool:
    """
    Guarda uma mensagem no histórico de conversas.

    Args:
        phone:   Número WhatsApp do lead.
        role:    "user" | "assistant" | "system"
        content: Texto da mensagem.
        agente:  Nome do agente que enviou/recebeu ("hunter", "closer", etc.)

    Devolve True em caso de sucesso, False em caso de erro.
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        _get_client().table(_TABLE_MENSAGENS).insert({
            "phone":          phone,
            _COL_MSG_ROLE:    role,
            _COL_MSG_CONTENT: content,
            _COL_MSG_CANAL:   "whatsapp",
            "agente":         agente,
            _COL_MSG_TS:      now,
        }).execute()
        logger.debug("save_message: ok phone=%s role=%s agente=%s", phone, role, agente)
        return True
    except Exception as exc:
        logger.error(
            "save_message falhou (phone=%s agente=%s): %s", phone, agente, exc
        )
        return False


def get_conversation_history(phone: str, limit: int = 10) -> list[dict]:
    """
    Devolve as últimas `limit` mensagens de um lead, ordenadas da mais antiga
    para a mais recente (ordem correcta para contexto LLM).

    Devolve [] em caso de erro.
    """
    try:
        result = (
            _get_client()
            .table(_TABLE_MENSAGENS)
            .select(f"{_COL_MSG_ROLE}, {_COL_MSG_CONTENT}, agente, {_COL_MSG_TS}")
            .eq("phone", phone)
            .order(_COL_MSG_TS, desc=True)
            .limit(limit)
            .execute()
        )
        # Inverter para ordem cronológica (mais antigo primeiro)
        history = list(reversed(result.data or []))
        logger.debug(
            "get_conversation_history: phone=%s mensagens=%d", phone, len(history)
        )
        return history
    except Exception as exc:
        logger.error(
            "get_conversation_history falhou (phone=%s): %s", phone, exc
        )
        return []


# ── Revisões ──────────────────────────────────────────────────────────────────

def save_revisao(
    lead_id: str,
    texto_original: str,
    texto_final: str,
    status: str,
    notas: str,
) -> bool:
    """
    Guarda o registo de uma revisão feita pelo REVISOR.

    Args:
        lead_id:         ID do lead (FK → leads.id).
        texto_original:  Texto enviado ao REVISOR.
        texto_final:     Texto após revisão (pode ser igual ao original).
        status:          "aprovado" | "corrigido" | "escalado" | "rejeitado"
        notas:           Notas internas do REVISOR sobre as alterações feitas.

    Devolve True em caso de sucesso, False em caso de erro.
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        _get_client().table(_TABLE_REVISOES).insert({
            "lead_id":        lead_id,
            "texto_original": texto_original,
            "texto_final":    texto_final,
            "status":         status,
            "notas":          notas,
            "created_at":     now,
        }).execute()
        logger.debug(
            "save_revisao: ok lead_id=%s status=%s", lead_id, status
        )
        return True
    except Exception as exc:
        logger.error(
            "save_revisao falhou (lead_id=%s status=%s): %s", lead_id, status, exc
        )
        return False
