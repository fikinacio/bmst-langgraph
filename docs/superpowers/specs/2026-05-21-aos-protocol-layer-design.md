# AOS Protocol Layer — Design Spec

**Goal:** Implement the Agent Operating System protocol layer — the shared type contracts, I/O schemas, fault handling, and configuration that all five agents (SCOUT, WRITER, CAROUSEL, REVISOR, PUBLISHER) depend on.

**Architecture:** 4 files under `src/protocols/` and `src/config/`. No agent logic, no LangGraph graphs. Pure Python types + Pydantic models + a stateless fault handler class. Zero circular imports: `vocabulary` has no deps; `io_schema` imports only `vocabulary`; `fault_handler` imports `vocabulary` and `io_schema`; `settings` has no deps on the other three.

**Tech Stack:** Python 3.11+, Pydantic v2, pydantic-settings, stdlib (`enum`, `logging`, `re`, `datetime`).

---

## File Responsibilities

### `src/protocols/vocabulary.py`
Pure enums, no imports from this project.

- `ActionType`: `SEND_MESSAGE`, `REQUEST_APPROVAL`, `ESCALATE_HUMAN`, `WAIT`, `DELEGATE_AGENT`, `COMPLETE`, `FAIL`
- `StatusType`: `NEEDS_APPROVAL`, `TASK_COMPLETE`, `BLOCKED`, `NEEDS_MORE_CONTEXT`, `FAILED`
- `FaultType`: `EXECUTION_FAULT`, `SCHEMA_FAULT`, `CONFIDENCE_FAULT`, `SCOPE_FAULT`, `LOOP_FAULT`, `SAFETY_FAULT`
- `Platform`: `INSTAGRAM`, `LINKEDIN`, `FACEBOOK`, `TIKTOK`

### `src/protocols/io_schema.py`
Pydantic v2 models. Imports only `vocabulary` and stdlib.

**`AgentInput`** — what every agent receives:
- `source: str` — `human | agent | system | webhook`
- `payload: dict` — arbitrary agent-specific data
- `context_ref: str | None` — Redis key for prior state
- `timestamp: datetime`
- `session_id: str`

**`AgentOutput`** — what every agent returns:
- `block_client: str | None` — shown to end user / sent via WhatsApp. `None` for internal-only outputs
- `block_internal: str` — always present; reasoning note for the founder / n8n routing
- `action: ActionType`
- `status: StatusType`
- `confidence: float` — 0.0–1.0, validated
- `timestamp: datetime`
- `to_wire() -> str` — formats `block_client + "\n---\n" + block_internal` (or just `block_internal` if `block_client` is None). Matches n8n split-on-`---` convention.

**Domain output models** (one per agent downstream consumer):
- `ResearchBrief` — SCOUT output; `summary` ≤ 150 words (word-count validator)
- `PlatformPost` — WRITER output; `char_count` auto-computed from `caption`
- `CarouselSlide` — CAROUSEL sub-model; `body` ≤ 30 words (word-count validator)
- `CarouselOutput` — CAROUSEL output; `slides` min 3 / max 10
- `ReviewResult` — REVISOR output; `decision` literal `approved | rejected | revision_requested`
- `PublicationResult` — PUBLISHER output; `status` literal `published | failed | manual_delivery`

### `src/protocols/fault_handler.py`
Stateless `FaultHandler` class. Imports `vocabulary` + `io_schema`.

`handle(fault_type, context, retry_count) -> AgentOutput`:

| Fault | Behaviour |
|-------|-----------|
| `EXECUTION_FAULT` | Exponential backoff: retry ≤ 3 times (delays 2s, 4s, 8s). After 3 retries → escalate |
| `SCHEMA_FAULT` | Immediate fail with `StatusType.FAILED`; no retry |
| `CONFIDENCE_FAULT` | Escalate human with `ActionType.ESCALATE_HUMAN` |
| `SCOPE_FAULT` | Fail immediately |
| `LOOP_FAULT` | Hard cap at 3 iterations; fail on 4th |
| `SAFETY_FAULT` | Immediate escalate, no retry, `confidence=0.0` |

Every fault logs at `ERROR` level: `fault_type`, `retry_count`, `context` keys.

### `src/config/settings.py`
`pydantic_settings.BaseSettings` subclass. Reads `.env` automatically.

**Required fields** (missing = startup `ValidationError`):
- `anthropic_api_key`, `bmst_api_key`
- `redis_url`, `supabase_url`, `supabase_service_key`
- `evolution_api_url`, `evolution_api_key`, `evolution_instance`
- `revisor_approver_phone` — validated against E.164: `^\+[1-9]\d{6,14}$`

**Optional fields with defaults:**
- App: `app_env="development"`, `log_level="INFO"`
- Scout: `brave_search_api_key=None`, `scout_lookback_days=1`, `scout_max_articles=10`, `scout_rss_feeds=[]`
- Writer: `writer_model="claude-sonnet-4-6"`, `writer_max_tokens=1024`, `writer_language="pt"`
- Carousel: `canva_api_token=None`, `canva_brand_kit_id=None`, `carousel_default_slides=5`
- Reviewer: `revisor_approval_timeout_seconds=3600`
- Publisher: `linkedin_client_id=None`, `linkedin_client_secret=None`, `linkedin_access_token=None`, `linkedin_org_urn=None`, `instagram_access_token=None`, `instagram_account_id=None`
- Langfuse: `langfuse_public_key=None`, `langfuse_secret_key=None`, `langfuse_host="https://cloud.langfuse.com"`
- Scheduler: `scheduler_cron="0 7 * * 1-5"`, `scheduler_timezone="Africa/Luanda"`

URL fields (`redis_url`, `supabase_url`, `evolution_api_url`, `langfuse_host`) validated as `AnyHttpUrl` or `RedisDsn` where applicable. Exported as module-level singleton `settings = Settings()`.

---

## Key Design Decisions

1. **E.164 phone validation** — `revisor_approver_phone` uses `^\+[1-9]\d{6,14}$`. The approver is Swiss (+41795748225); Angola-specific patterns are wrong here.
2. **`to_wire()` separator** — `---` on its own line, matching the existing n8n split convention documented in `docs/ARCHITECTURE.md`.
3. **`block_client` is `None`-able** — agents that produce only internal outputs (e.g. a monitoring check) don't have to fabricate a client message.
4. **Settings singleton** — `settings = Settings()` at module level; agents import `from src.config.settings import settings`. Fails at import time if required vars are missing, which is preferable to silent runtime failures.
5. **`FaultHandler` is stateless** — retry state lives in `retry_count` passed by the caller (the agent graph node), not inside the handler. This keeps the handler testable without mocking state.
