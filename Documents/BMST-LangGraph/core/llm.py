# core/llm.py — cliente Anthropic centralizado com retry, logging e Langfuse

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Literal

import anthropic
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# ── Utilitário: extracção de JSON de code fences ──────────────────────────────

_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

def _extract_json(raw: str) -> str:
    """
    Remove marcas de code fence Markdown antes de json.loads().

    O Claude por vezes devolve:
        ```json
        { ... }
        ```
    Esta função extrai apenas o conteúdo entre as marcas, ou devolve
    o raw original se não houver code fence.
    """
    m = _CODE_FENCE_RE.search(raw)
    return m.group(1).strip() if m else raw.strip()


# ── Modelos ───────────────────────────────────────────────────────────────────

MODEL_HAIKU  = "claude-haiku-4-5-20251001"   # classificação, triagem, revisão básica
MODEL_SONNET = "claude-sonnet-4-6"            # geração de mensagens, propostas

_MODEL_MAP: dict[str, str] = {
    "haiku":  MODEL_HAIKU,
    "sonnet": MODEL_SONNET,
}

# ── Cliente Anthropic (síncrono por baixo; usamos asyncio.to_thread) ──────────

def _get_client() -> anthropic.Anthropic:
    """Devolve cliente Anthropic. Falha imediatamente se a key não existir."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY não está definida no ambiente.")
    return anthropic.Anthropic(api_key=api_key)


# ── Langfuse (opcional) ───────────────────────────────────────────────────────

def _get_langfuse():
    """Devolve cliente Langfuse ou None se não estiver configurado."""
    public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
    host       = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")
    if not public_key or not secret_key:
        return None
    try:
        from langfuse import Langfuse
        return Langfuse(public_key=public_key, secret_key=secret_key, host=host)
    except Exception as exc:  # langfuse não instalado ou erro de config
        logger.warning("Langfuse indisponível: %s", exc)
        return None


# ── Compact mode — message sanitisation & history compaction ──────────────────

#: Maximum messages to keep before compacting (older ones are summarised).
COMPACT_THRESHOLD: int = 20

#: Number of recent messages to always keep verbatim after compaction.
COMPACT_KEEP_RECENT: int = 6


def _sanitize_messages(
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Remove or repair content blocks that would cause a 400 from the Anthropic API.

    The specific error this guards against:
        "cache_control cannot be set for empty text blocks"  (messages.N.content.M.text)

    Rules applied to every content block of every message:
      - If a text block has an empty (or whitespace-only) ``text`` field AND a
        ``cache_control`` key, the ``cache_control`` key is removed.
      - Text blocks whose ``text`` is empty after stripping are dropped entirely,
        unless they are the only block in the message (in which case the block is
        kept without ``cache_control`` so the message remains valid).
      - Non-text blocks (``type != "text"``) are left untouched.
    """
    sanitized: list[dict[str, Any]] = []
    for msg in messages:
        content = msg.get("content")

        # Plain-string content — nothing to sanitise.
        if not isinstance(content, list):
            sanitized.append(msg)
            continue

        cleaned: list[dict[str, Any]] = []
        for block in content:
            if block.get("type") != "text":
                cleaned.append(block)
                continue

            text = block.get("text", "")
            if not isinstance(text, str) or text.strip():
                # Non-empty text — keep the block as-is.
                cleaned.append(block)
            else:
                # Empty text block: drop cache_control to avoid the 400.
                b = {k: v for k, v in block.items() if k != "cache_control"}
                cleaned.append(b)

        # Drop blocks that are now truly empty text (no content value at all),
        # but always leave at least one block so the message is non-empty.
        non_empty = [
            b for b in cleaned
            if b.get("type") != "text" or (b.get("text") or "").strip()
        ]
        sanitized.append({**msg, "content": non_empty if non_empty else cleaned})

    return sanitized


async def compact_conversation_history(
    messages: list[dict[str, Any]],
    model: Literal["haiku", "sonnet"] = "haiku",
    keep_recent: int = COMPACT_KEEP_RECENT,
) -> list[dict[str, Any]]:
    """
    Summarise the oldest messages in a conversation when it grows too long.

    Compact mode strategy:
      1. Keep the ``keep_recent`` most-recent messages verbatim.
      2. Summarise everything older into a single ``{"role": "user", ...}``
         context block prepended to the kept messages.

    This prevents the ``messages.N.content...`` 400 errors that occur when a
    long conversation is serialised with ``cache_control`` on empty text blocks,
    and keeps token usage under control for ongoing CLOSER conversations.

    Args:
        messages:    List of ``{"role": ..., "content": ...}`` dicts.
        model:       Which model to use for the summary (haiku is sufficient).
        keep_recent: How many recent messages to keep verbatim.

    Returns:
        A shorter messages list: one summary block + ``keep_recent`` tail messages.
    """
    if len(messages) <= keep_recent:
        return messages

    to_summarise = messages[: len(messages) - keep_recent]
    recent       = messages[len(messages) - keep_recent :]

    # Build a plain-text transcript for the LLM to summarise.
    transcript = "\n".join(
        f"{m['role'].upper()}: {m['content'] if isinstance(m['content'], str) else json.dumps(m['content'], ensure_ascii=False)}"
        for m in to_summarise
    )

    summary_text = await create_message(
        system=(
            "You are a concise conversation summariser. "
            "Summarise the following conversation transcript in 3-5 sentences, "
            "preserving only the key facts, decisions, and context needed to "
            "continue the conversation. Reply with the summary only."
        ),
        user=f"Transcript to summarise:\n\n{transcript}",
        model=model,
        agent_name="compact",
        node_name="compact_conversation_history",
    )

    summary_msg = {
        "role":    "user",
        "content": f"[Conversation summary — earlier context]\n{summary_text.strip()}",
    }
    return [summary_msg] + recent


# ── Retry ─────────────────────────────────────────────────────────────────────

_RETRY_DELAYS = [2, 4, 8]   # segundos entre tentativas (backoff exponencial)
_RETRYABLE    = (
    anthropic.RateLimitError,
    anthropic.APITimeoutError,
    anthropic.InternalServerError,
)


async def _call_with_retry(
    system: str,
    model_id: str,
    max_tokens: int,
    messages: list[dict[str, Any]],
) -> anthropic.types.Message:
    """
    Chama a API Anthropic com até 3 tentativas e backoff exponencial.
    Lança anthropic.APIError em caso de falha definitiva.

    ``messages`` are sanitised before every attempt via ``_sanitize_messages``
    to strip ``cache_control`` from empty text blocks (prevents HTTP 400).
    """
    client       = _get_client()
    last_exc: Exception | None = None
    clean_msgs   = _sanitize_messages(messages)

    for attempt, delay in enumerate([0] + _RETRY_DELAYS, start=1):
        if delay:
            logger.warning(
                "LLM retry %d/3 em %ds (modelo=%s)", attempt - 1, delay, model_id
            )
            await asyncio.sleep(delay)
        try:
            # A SDK Anthropic síncrona — corre em thread para não bloquear o event loop
            response = await asyncio.to_thread(
                client.messages.create,
                model=model_id,
                max_tokens=max_tokens,
                system=system,
                messages=clean_msgs,
            )
            return response
        except _RETRYABLE as exc:
            last_exc = exc
            continue
        except anthropic.APIError:
            raise   # erros de auth, bad request, etc. — não adianta retentar

    raise RuntimeError(
        f"LLM falhou após 3 tentativas (modelo={model_id}): {last_exc}"
    ) from last_exc


# ── Função principal ──────────────────────────────────────────────────────────

async def create_message(
    system: str,
    user: str,
    model: Literal["haiku", "sonnet"] = "haiku",
    max_tokens: int = 1024,
    agent_name: str = "unknown",
    node_name: str = "unknown",
    history: list[dict[str, Any]] | None = None,
) -> str:
    """
    Envia uma mensagem ao Claude e devolve o texto da resposta.

    Args:
        system:     Prompt de sistema (instruções do agente).
        user:       Mensagem do utilizador / input do nó.
        model:      "haiku" (rápido/barato) ou "sonnet" (melhor qualidade).
        max_tokens: Limite de tokens na resposta.
        agent_name: Nome do agente (para logging e Langfuse).
        node_name:  Nome do nó LangGraph (para logging e Langfuse).
        history:    Optional list of prior ``{"role", "content"}`` messages for
                    multi-turn conversations.  When provided the list is
                    automatically compacted if it exceeds ``COMPACT_THRESHOLD``
                    and sanitised before sending to the API.

    Returns:
        Texto da resposta do Claude (content[0].text).

    Raises:
        RuntimeError: Se a API falhar após todas as tentativas.
    """
    model_id = _MODEL_MAP[model]
    t0 = time.perf_counter()

    # Build the messages list, compacting history when needed.
    if history:
        prior = (
            await compact_conversation_history(history, model=model)
            if len(history) > COMPACT_THRESHOLD
            else list(history)
        )
        messages = prior + [{"role": "user", "content": user}]
    else:
        messages = [{"role": "user", "content": user}]

    # Langfuse trace (se configurado)
    lf = _get_langfuse()
    trace = generation = None
    if lf:
        try:
            trace = lf.trace(name=f"{agent_name}.{node_name}", tags=[agent_name, model])
            generation = trace.generation(
                name=node_name,
                model=model_id,
                input={"system": system, "user": user},
            )
        except Exception as lf_exc:
            logger.warning("Langfuse trace failed (ignored): %s", lf_exc)
            trace = generation = None

    try:
        response = await _call_with_retry(system, model_id, max_tokens, messages)
    except Exception:
        if generation:
            try:
                generation.end(level="ERROR")
            except Exception:
                pass
        raise

    latency_ms = int((time.perf_counter() - t0) * 1000)
    text       = response.content[0].text
    usage      = response.usage  # input_tokens, output_tokens

    logger.info(
        "LLM | agente=%-10s nó=%-20s modelo=%-30s "
        "tokens_in=%d tokens_out=%d latência=%dms",
        agent_name, node_name, model_id,
        usage.input_tokens, usage.output_tokens, latency_ms,
    )

    if generation:
        generation.end(
            output=text,
            usage={
                "input":  usage.input_tokens,
                "output": usage.output_tokens,
                "unit":   "TOKENS",
            },
            metadata={"latency_ms": latency_ms},
        )

    return text


# ── JSON structured output ────────────────────────────────────────────────────

_JSON_SUFFIX = (
    "\n\nResponde APENAS com JSON válido. "
    "Sem texto antes ou depois. Sem backticks. Sem markdown. Apenas o JSON."
)

_JSON_RETRY_SUFFIX = (
    "\n\nATENÇÃO: a resposta anterior não era JSON válido. "
    "Devolve EXCLUSIVAMENTE um objecto JSON. "
    "Nenhuma palavra antes ou depois. Nenhum caracter extra. Apenas { ... }."
)


async def create_json_message(
    system: str,
    user: str,
    schema: type[BaseModel],
    model: Literal["haiku", "sonnet"] = "haiku",
    history: list[dict[str, Any]] | None = None,
    **kwargs,
) -> BaseModel:
    """
    Chama o Claude e faz parse da resposta para um modelo Pydantic.

    Se o parse falhar: retenta uma vez com instrução mais explícita.
    Se voltar a falhar: lança ValueError com o output raw para debugging.

    Args:
        system: Prompt de sistema.
        user:   Input do nó.
        schema: Classe Pydantic que descreve o JSON esperado.
        model:  "haiku" ou "sonnet".
        **kwargs: Passados directamente a create_message (agent_name, node_name, etc.).

    Returns:
        Instância validada do schema Pydantic.

    Raises:
        ValueError: Se o LLM não produzir JSON válido após 2 tentativas.
    """
    # 1ª tentativa
    raw = await create_message(
        system=system + _JSON_SUFFIX,
        user=user,
        model=model,
        history=history,
        **kwargs,
    )
    try:
        return schema.model_validate(json.loads(raw))
    except (json.JSONDecodeError, ValueError):
        logger.warning(
            "create_json_message: parse falhou na 1ª tentativa. Raw=%r", raw[:200]
        )

    # 2ª tentativa — instrução mais explícita
    raw2 = await create_message(
        system=system + _JSON_RETRY_SUFFIX,
        user=f"Input original:\n{user}\n\nResposta anterior (inválida):\n{raw}",
        model=model,
        history=history,
        **kwargs,
    )
    try:
        return schema.model_validate(json.loads(raw2))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(
            f"create_json_message: o LLM não produziu JSON válido após 2 tentativas.\n"
            f"Schema: {schema.__name__}\n"
            f"Output raw (tentativa 2): {raw2!r}"
        ) from exc
