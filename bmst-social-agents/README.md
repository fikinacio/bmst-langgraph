# BMST Social Agents

Autonomous multi-agent pipeline that researches technology news, writes social media posts,
creates image carousels, routes them through a human approval step, and publishes to LinkedIn
and Instagram — fully automated, runs daily.

Built with [LangGraph](https://github.com/langchain-ai/langgraph) and the [Anthropic API](https://docs.anthropic.com).

---

## Architecture

Five agents work in sequence. Each is a LangGraph state graph exposed as a FastAPI endpoint.

```
SCOUT → WRITER → CAROUSEL → REVISOR → PUBLISHER
```

| Agent | Responsibility |
|-------|----------------|
| **SCOUT** | Searches news via Brave Search + RSS feeds, scores relevance, returns top articles |
| **WRITER** | Reads SCOUT output, writes LinkedIn posts and Instagram captions in Portuguese |
| **CAROUSEL** | Structures carousel content and generates slides via the Canva API |
| **REVISOR** | Quality gate: runs automated checks then sends content to a human via WhatsApp for approval |
| **PUBLISHER** | Receives approved content and publishes to LinkedIn and Instagram |

### Infrastructure

```
APScheduler (daily cron)
        │
        ▼
   FastAPI (HTTP layer)
        │
   ┌────┴──────────────────┐
   │                       │
LangGraph graphs     Redis (state cache)
        │
Claude API + Supabase (persistence) + Langfuse (observability)
```

---

## Setup

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- A Supabase project
- Anthropic API key
- Canva API token (for CAROUSEL)
- LinkedIn + Instagram developer apps (for PUBLISHER)
- Evolution API instance (for REVISOR WhatsApp approval)

### 1. Enter the project directory

```bash
cd bmst-social-agents
```

### 2. Copy and fill in environment variables

```bash
cp .env.example .env
# Edit .env and fill in all required values
```

### 3. Install dependencies (local development)

```bash
make install
```

### 4. Start infrastructure (Redis)

```bash
make docker-up
```

### 5. Run the API server

```bash
make run
```

The API will be available at `http://localhost:8000`. Documentation at `http://localhost:8000/docs`.

---

## Running

### Trigger the full pipeline manually

```bash
curl -X POST http://localhost:8000/pipeline/run \
  -H "X-Api-Key: $BMST_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"topic": "inteligência artificial em Angola"}'
```

### Run tests

```bash
make test
```

### Lint

```bash
make lint
```

---

## Project Structure

```
bmst-social-agents/
├── src/
│   ├── config/        # Pydantic settings, environment loading
│   ├── protocols/     # Shared TypedDicts and type aliases
│   ├── memory/        # Redis + Supabase persistence helpers
│   ├── tools/         # LangChain tools (search, Canva, LinkedIn, Instagram)
│   ├── agents/        # One subpackage per agent (scout, writer, carousel, revisor, publisher)
│   ├── orchestrator/  # LangGraph pipeline graph wiring all agents together
│   ├── scheduler/     # APScheduler setup and job definitions
│   └── api/           # FastAPI app, routers, middleware
├── tests/
│   └── datasets/      # Static test fixtures (mock API responses, sample articles)
└── infra/
    └── supabase/      # SQL migrations for state persistence tables
```

---

## License

MIT
