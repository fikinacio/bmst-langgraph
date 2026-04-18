# core/llm.py — cliente Anthropic centralizado com retry, logging e Langfuse

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Literal

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


# ── Retry ─────────────────────────────────────────────────────────────────────

_RETRY_DELAYS = [2, 4, 8]   # segundos entre tentativas (backoff exponencial)
_RETRYABLE    = (
    anthropic.RateLimitError,
    anthropic.APITimeoutError,
    anthropic.InternalServerError,
)


async def _call_with_retry(
    system: str,
    user: str,
    model_id: str,
    max_tokens: int,
) -> anthropic.types.Message:
    """
    Chama a API Anthropic com até 3 tentativas e backoff exponencial.
    Lança anthropic.APIError em caso de falha definitiva.
    """
    client = _get_client()
    last_exc: Exception | None = None

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
                messages=[{"role": "user", "content": user}],
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

    Returns:
        Texto da resposta do Claude (content[0].text).

    Raises:
        RuntimeError: Se a API falhar após todas as tentativas.
    """
    model_id = _MODEL_MAP[model]
    t0 = time.perf_counter()

    # Langfuse trace (se configurado)
    lf = _get_langfuse()
    trace = generation = None
    if lf:
        trace = lf.trace(name=f"{agent_name}.{node_name}", tags=[agent_name, model])
        generation = trace.generation(
            name=node_name,
            model=model_id,
            input={"system": system, "user": user},
        )

    try:
        response = await _call_with_retry(system, user, model_id, max_tokens)
    except Exception:
        if generation:
            generation.end(level="ERROR")
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
