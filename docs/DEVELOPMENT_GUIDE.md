# Development Guide

This document covers the build sequence, testing approach, and deployment process for contributors and for the author's own reference.

---

## Background: Coming from C++

If you have an embedded systems background, the LangGraph mental model will feel familiar. The concepts map directly.

| C++ embedded | LangGraph |
|---|---|
| State machine | `StateGraph` |
| State enum | `TypedDict` |
| Transition function | Node function |
| Switch on current state | Router with conditional edges |
| Struct | `TypedDict` state |
| Unit test with mock HAL | `pytest` with mocked LLM responses |

The main difference is that instead of writing to a GPIO or reading from a sensor, each node calls an LLM or a database. The state machine structure is the same.

---

## Python Patterns Used Here

### Type hints

Used in every state definition. Coming from C++, think of `TypedDict` as a struct and `Literal` as a constrained enum.

```python
from typing import TypedDict, Literal

class HunterState(TypedDict):
    segmento: Literal["A", "B", "C"] | None
    qualificado: bool | None
    mensagem_cliente: str | None
    erro: str | None
```

### Pydantic for validating LLM outputs

LLMs return text. We need typed data. Pydantic converts and validates.

```python
from pydantic import BaseModel

class QualificationOutput(BaseModel):
    segmento: Literal["A", "B", "C"]
    qualificado: bool
    pain_point: str
```

If the LLM returns invalid JSON or a field is missing, Pydantic raises a validation error that we can handle cleanly in the node.

### async/await

FastAPI and LangGraph are async throughout. Each node that calls an external service should be async.

```python
async def qualify_company(state: HunterState) -> HunterState:
    result = await client.messages.create(...)
    return {**state, "segmento": parse(result)}
```

---

## Build Sequence

Work through these in order. Each session assumes the previous one is working and tested.

**Session 1:** Project structure and dependencies  
Create the folder layout, `requirements.txt`, `.env.example`, `.gitignore`. Nothing runs yet.

**Session 2:** Core modules  
Implement `core/llm.py` with retry logic, `core/memory.py` for Supabase, `core/redis_client.py`.

**Session 3:** HUNTER: state and nodes  
Write `state.py`, `prompts.py`, and `nodes.py`. No graph yet, just the functions.

**Session 4:** HUNTER: graph and tests  
Assemble the graph in `graph.py`. Write `tests/test_hunter.py` using mocked LLM responses.

**Session 5:** FastAPI  
Add `api/models.py` and implement `/hunter` and `/hunter/batch` in `api/main.py`.

**Session 6:** Docker and deployment  
Write `Dockerfile` and `docker-compose.yml`. Deploy to EasyPanel.

**Session 7:** CLOSER  
Implement the CLOSER agent using `interrupt()` for the human approval step.

**Session 8:** Observability  
Add Langfuse traces to all agents. Add the `/metrics` endpoint.

**Session 9:** DELIVERY and LEDGER  
Implement the two remaining agents following the same pattern.

**Session 10:** Final polish  
Complete README, add GitHub Actions, publish.

---

## Testing

```bash
# Fast tests, no real LLM calls, mocked responses
pytest -m "not integration" -v

# Slow tests, calls real Claude API (costs tokens)
pytest -m integration -v

# Single agent
pytest tests/test_hunter.py -v
```

Unit tests mock all LLM responses and test state transitions deterministically. They run on every change.

Integration tests call the real Claude API and check business rule compliance, for example that client-facing messages contain no technical jargon. These run in CI only.

---

## Environment Variables

```env
ANTHROPIC_API_KEY=sk-ant-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...
REDIS_URL=redis://localhost:6379
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
API_KEY=your-internal-api-key
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
GOTENBERG_URL=http://gotenberg:3000
```

---

## Deployment

The FastAPI app runs on the same EasyPanel VPS as n8n and Evolution API.

Estimated RAM at idle:

```
n8n               ~400MB
Evolution API     ~300MB
Redis             ~50MB
PostgreSQL        ~200MB
bmst-agents       ~300-500MB
Total             ~1.3-1.5GB on a 4GB VPS
```

**EasyPanel setup steps:**
1. New Service > App
2. Source: GitHub repository
3. Build: Dockerfile
4. Port: 8000
5. Environment: paste `.env` contents
6. Domain: connect via Cloudflare DNS

---

## Contributing

This is a personal project. If you are using it as a starting point for your own agent system, the parts most worth adapting are the `prompts.py` files in each agent and the `TypedDict` state definitions. The core modules, FastAPI layer, and graph structure can be reused with minimal changes.

Issues and pull requests are welcome for bugs or documentation improvements.
