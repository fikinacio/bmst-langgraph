# BMST Social Agents

Autonomous multi-agent pipeline that researches AI news, writes social media posts in pt-PT,
generates carousel slides with Canva images, routes content through human WhatsApp approval,
and publishes to LinkedIn, Instagram, and Facebook — daily, fully automated.

Built on [LangGraph](https://github.com/langchain-ai/langgraph), the
[Anthropic API](https://docs.anthropic.com), and the
[AOS (Agent Operating System) framework](aos-contracts.yaml).

---

## Architecture

Five agents run in a sequential LangGraph pipeline. Each agent is an autonomous node with a
defined identity contract, fault handling, and confidence scoring.

```
 ┌──────────────────────────────────────────────────────────────┐
 │                   APScheduler (08:00 Luanda)                 │
 └──────────────────────────┬───────────────────────────────────┘
                            │ run_graph(session_id)
                            ▼
 ┌──────┐    ┌────────┐    ┌──────────┐    ┌─────────┐    ┌───────────┐
 │SCOUT │───▶│ WRITER │───▶│ CAROUSEL │───▶│ REVISOR │───▶│ PUBLISHER │
 └──────┘    └────────┘    └──────────┘    └─────────┘    └───────────┘
    │             │              │               │                │
    ▼             ▼              ▼               ▼                ▼
  Tavily      Claude API    Claude API +    Claude API +    Meta Graph API
  Search      (pt-PT)       Canva MCP       GPTZero +       LinkedIn API v2
    │                                      WhatsApp HITL    WhatsApp (TikTok)
    ▼
 Supabase                                    ▲
 (dedup)                    revision loop ───┘
                            (max 3 rounds)
```

```
 Infrastructure:
   FastAPI (HTTP layer)  ──  /webhook/whatsapp  (n8n approval relay)
                          ──  /run/manual        (ad-hoc trigger)
                          ──  /runs/{id}         (pipeline status)
   Redis (LangGraph checkpointer + working cache)
   Supabase (publication log, topic history, review audit)
```

### Agent responsibilities

| Agent | Responsibility |
|-------|----------------|
| **SCOUT** | Searches AI/automation news with Tavily, deduplicates against Supabase topic history, scores relevance, picks the best topic for the day |
| **WRITER** | Writes 4 platform-specific posts (Instagram, LinkedIn, Facebook, TikTok) in pt-PT, enforcing brand voice, hashtag ranges, and prohibited terms |
| **CAROUSEL** | Generates a 5–7 slide educational carousel with Claude and creates images for every slide via Canva MCP |
| **REVISOR** | Quality gate: checks compliance and AI-detection score (GPTZero), routes back to WRITER for revision or sends content to a human for WhatsApp approval |
| **PUBLISHER** | Verifies Supabase approval record, publishes to Meta Graph API (Instagram + Facebook) and LinkedIn API v2, delivers TikTok manually via WhatsApp |

---

## AOS Compliance

Every agent follows the **Agent Operating System (AOS)** framework defined in
[`aos-contracts.yaml`](aos-contracts.yaml):

- **Identity contract** — scoped authority, hard limits, escalation rules
- **Typed fault protocol** — `EXECUTION_FAULT`, `CONFIDENCE_FAULT`, `SAFETY_FAULT`,
  `SCHEMA_FAULT`, `LOOP_FAULT` with retry budgets and backoff
- **Confidence scoring** — every node returns a `0.0–1.0` confidence field; the pipeline
  will not publish below threshold
- **Human-in-the-loop gate** — REVISOR pauses the graph via LangGraph `interrupt_after`
  and waits for a WhatsApp webhook before resuming

---

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| Python 3.11+ | Tested on 3.11 and 3.14 |
| Docker + Docker Compose | For Redis container |
| Supabase project | Free tier works |
| Anthropic API key | claude-sonnet-4-6 (default) |
| Tavily API key | Free tier: 1 000 searches/month |
| GPTZero API key | AI-detection for REVISOR |
| Canva Developer token | For CAROUSEL slide images |
| Canva brand kit + template IDs | From your Canva brand settings |
| LinkedIn developer app | OAuth2 access token + org URN |
| Meta developer app | Instagram Business + Facebook Page |
| Evolution API instance | WhatsApp gateway for approvals |

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/biscaplus/bmst-social-agents.git
cd bmst-social-agents
```

### 2. Copy and fill environment variables

```bash
cp .env.example .env
# Open .env and fill every required value (no value must remain empty)
```

Key variables at a glance:

```
ANTHROPIC_API_KEY       # console.anthropic.com
BMST_API_KEY            # openssl rand -hex 32
SUPABASE_URL / SERVICE_KEY
TAVILY_API_KEY          # app.tavily.com
GPTZERO_API_KEY         # app.gptzero.me
CANVA_API_TOKEN / BRAND_KIT_ID / TEMPLATE_ID
LINKEDIN_CLIENT_ID / SECRET / ACCESS_TOKEN / ORG_URN
INSTAGRAM_ACCESS_TOKEN / ACCOUNT_ID
FACEBOOK_PAGE_ID
EVOLUTION_API_URL / API_KEY / INSTANCE
REVISOR_APPROVER_PHONE  # international format, no +
SCHEDULER_CRON          # default: "0 7 * * 1-5" (weekdays 08:00 Luanda)
```

### 3. Apply the Supabase schema

Open your Supabase project → SQL Editor and run:

```bash
cat infra/supabase/schema.sql | pbcopy  # then paste into the SQL editor
```

Or with the Supabase CLI:

```bash
supabase db push --linked
```

### 4. Install Python dependencies

```bash
make install
```

### 5. Start Redis

```bash
make docker-up   # starts only the redis container
```

---

## Running locally

```bash
# API server only (port 8000)
make run-api

# Scheduler only (blocks, fires daily)
make run-scheduler

# Both in parallel (local dev shortcut)
make run-all
```

API docs: `http://localhost:8000/docs`

### Trigger the pipeline manually

```bash
curl -X POST http://localhost:8000/run/manual \
  -H "X-API-Key: $BMST_API_KEY"
```

Response: `{"session_id": "...", "status": "started"}`

### Check pipeline status

```bash
curl http://localhost:8000/runs/<session_id> \
  -H "X-API-Key: $BMST_API_KEY"
```

### List recent publications

```bash
curl http://localhost:8000/publications \
  -H "X-API-Key: $BMST_API_KEY"
```

---

## Running tests

All external APIs are mocked — no credentials required:

```bash
make test-all      # pytest with short tracebacks
make test          # pytest verbose
```

Current status: **92 tests, 0 failures**.

Test structure:
```
tests/
├── conftest.py                  # env var stubs
├── test_scout.py                # 12 tests (unit + 8 dataset-driven)
├── test_writer.py               # 15 tests (unit + 10 dataset-driven)
├── test_carousel.py             # 11 tests (unit + 6 dataset-driven)
├── test_revisor.py              # 16 tests (unit + 10 dataset-driven)
├── test_publisher.py            # 14 tests (unit + 8 dataset-driven)
├── test_webhook.py              # 10 tests
└── datasets/                   # YAML evaluation cases per agent
```

---

## Agent descriptions

### SCOUT

SCOUT runs first. It queries Tavily for recent AI and automation news, filters results below
a 0.60 relevance score, deduplicates against the Supabase `published_topics` table (avoiding
topics covered in recent runs), and classifies the winning article into one of two content
pillars (`ai` or `automation`) using keyword scoring with rotation logic. It builds a
`ResearchBrief` Pydantic model and caches the selected topic in Redis for 24 hours.

### WRITER

WRITER receives the `ResearchBrief` from SCOUT and calls Claude to produce four distinct
platform posts (Instagram, LinkedIn, Facebook, TikTok) in pt-PT in the voice of Fidel Inácio
Kussunga. It enforces platform-specific character limits, hashtag count ranges, and a list of
prohibited AI-sounding terms ("IA", "chatbot", "algoritmo", etc.). Each post is scored 0.0–1.0
across four criteria; the mean becomes the node's confidence. In revision mode the previous
posts and the reviewer's note are injected into the prompt.

### CAROUSEL

CAROUSEL builds a 5–7 slide educational carousel on the day's topic, asking Claude to produce
structured JSON (title, slides with headline/body/visual brief, caption, hashtags). It then
calls the Canva MCP in parallel for each slide to generate a branded image. Slides where image
generation fails keep `canva_asset_url = null`; each failure reduces confidence by 0.15.

### REVISOR

REVISOR is the quality gate. It runs three independent checks: a Claude judge call that scores
content quality and lists issues; a GPTZero AI-detection call across all post texts; and
structural compliance checks (character limits, hashtag counts, prohibited terms). If confidence
falls below 0.80 or structural violations exist, the content is routed back to WRITER. If the
AI-detection score exceeds 0.70, an automatic revision is requested without human involvement.
Otherwise, a formatted preview is sent to the approver via WhatsApp (Evolution API) and the
LangGraph graph pauses via `interrupt_after` until the webhook resumes it.

### PUBLISHER

PUBLISHER verifies that the session has an approved record in Supabase (`is_session_approved`)
before posting anything — a SAFETY_FAULT triggers if this check fails. It publishes to Meta
Graph API (Instagram carousel + Facebook), LinkedIn API v2, and sends the TikTok post to the
approver via WhatsApp for manual upload. After all publish attempts it logs results to Supabase,
saves the topic to the dedup table, and sends a summary message via WhatsApp.

---

## WhatsApp approval guide

When REVISOR sends you a content preview, reply with one of:

| Reply | Action |
|-------|--------|
| `APROVADO` or `APPROVED` | Publish immediately |
| `REJEITADO: <reason>` or `REJECTED: <reason>` | Discard and stop the pipeline |
| `REVISÃO: <note>` or `REVISION: <note>` | Send back to WRITER with your note |

Matching is case-insensitive. Anything else (greetings, unrelated messages) is ignored.

**Timeout:** if no reply arrives within `REVISOR_APPROVAL_TIMEOUT_SECONDS` (default 3600s),
the pipeline auto-rejects and logs the timeout in Supabase.

---

## Platform API setup

### Meta (Instagram + Facebook)
1. Create a Meta developer app at [developers.facebook.com](https://developers.facebook.com/apps/)
2. Add the **Instagram Graph API** and **Facebook Pages API** products
3. Generate a long-lived page access token (60 days)
4. Note your Instagram Business Account ID and Facebook Page ID

### LinkedIn
1. Create an app at [linkedin.com/developers/apps](https://www.linkedin.com/developers/apps)
2. Request the **Share on LinkedIn** and **Sign In with LinkedIn using OpenID Connect** products
3. Generate an OAuth2 access token with `w_member_social` and `w_organization_social` scopes
4. Note your organisation URN (format: `urn:li:organization:XXXXXXXXX`)

### Evolution API (WhatsApp)
1. Deploy Evolution API on your VPS or use a managed provider
2. Create an instance and connect your WhatsApp Business account
3. Configure a webhook pointing to `https://your-domain/webhook/whatsapp`
4. The webhook payload must include `data.key.remoteJid` and `data.message.conversation`

---

## Deployment (EasyPanel on Hostinger VPS)

### Docker Compose (recommended)

```bash
# Build and start all services
docker compose up -d --build

# Check logs
docker compose logs -f api
docker compose logs -f scheduler
```

Services started: `api` (port 8000), `scheduler` (cron), `redis`.

### EasyPanel

1. Push your code to GitHub
2. In EasyPanel, create a new **Docker Compose** service pointing to this repository
3. Set all environment variables in the EasyPanel UI (copy from `.env.example`)
4. EasyPanel will build and deploy automatically on push to `main`
5. Add a custom domain and enable HTTPS via EasyPanel → Domain settings

### Health check

```bash
curl https://your-domain.com/health
# {"status": "ok", "env": "production"}
```

### Supabase schema (production)

Apply the schema once before first deploy:
```bash
psql $DATABASE_URL < infra/supabase/schema.sql
```

---

## Contributing: adding a new agent

See [`docs/AGENT_GUIDE.md`](docs/AGENT_GUIDE.md) for the full step-by-step guide.

Quick summary:
1. Define the AOS Identity Contract in `aos-contracts.yaml`
2. Create `src/agents/<name>/node.py` with a `<name>_node(state)` async function
3. Register the node in `src/orchestrator/graph.py`
4. Add routing logic in `src/orchestrator/router.py`
5. Create `tests/datasets/<name>_cases.yaml` with ≥6 test cases
6. Add `test_<name>_dataset` parametrized function in `tests/test_<name>.py`
7. Update this README

---

## License

MIT © 2025 BMST — Bisca Mais Sistemas e Tecnologias
