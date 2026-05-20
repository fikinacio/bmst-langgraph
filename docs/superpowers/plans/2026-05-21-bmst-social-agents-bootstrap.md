# BMST Social Agents — Project Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the complete project skeleton for `bmst-social-agents/`, a LangGraph-based multi-agent social media system with 5 agents (SCOUT, WRITER, CAROUSEL, REVISOR, PUBLISHER) — no agent logic, only structure and config files.

**Architecture:** A Python monorepo under `bmst-social-agents/` sitting alongside the existing BMST agents project in this worktree. Each subdirectory under `src/` maps to one architectural concern (agents, orchestrator, tools, memory, config, protocols, scheduler, api). All agent logic is deferred; only `__init__.py` stubs are created now.

**Tech Stack:** Python 3.11+, LangGraph ≥0.2, LangChain ≥0.3, langchain-anthropic, FastAPI, Redis, Supabase, APScheduler, Langfuse, Pydantic v2, pytest.

---

## File Map

```
bmst-social-agents/
├── README.md                          # Project overview + setup + run instructions
├── .env.example                       # All env var keys with inline comments
├── .gitignore                         # Python + LangGraph gitignore
├── pyproject.toml                     # Build system + all dependencies + tool config
├── Makefile                           # install / run / test / lint / docker-up / docker-down
├── docker-compose.yml                 # API + Redis + (placeholder) Supabase services
├── docs/                              # Empty — reserved for architecture docs
├── src/
│   ├── __init__.py                    # Package marker
│   ├── config/
│   │   └── __init__.py                # Config package marker
│   ├── protocols/
│   │   └── __init__.py                # Protocols package marker
│   ├── memory/
│   │   └── __init__.py                # Memory package marker
│   ├── tools/
│   │   └── __init__.py                # Tools package marker
│   ├── agents/
│   │   └── __init__.py                # Agents package marker
│   ├── orchestrator/
│   │   └── __init__.py                # Orchestrator package marker
│   ├── scheduler/
│   │   └── __init__.py                # Scheduler package marker
│   └── api/
│       └── __init__.py                # API package marker
├── tests/
│   ├── __init__.py                    # Tests package marker
│   └── datasets/                      # Empty — reserved for test fixtures
└── infra/
    └── supabase/                      # Empty — reserved for Supabase migrations
```

---

### Task 1: Directory Skeleton

**Files:**
- Create: `bmst-social-agents/` and all subdirectories listed in the file map above

- [ ] **Step 1: Create all directories**

```powershell
$base = "bmst-social-agents"
$dirs = @(
  "$base/docs",
  "$base/src/config",
  "$base/src/protocols",
  "$base/src/memory",
  "$base/src/tools",
  "$base/src/agents",
  "$base/src/orchestrator",
  "$base/src/scheduler",
  "$base/src/api",
  "$base/tests/datasets",
  "$base/infra/supabase"
)
foreach ($d in $dirs) { New-Item -ItemType Directory -Force $d | Out-Null }
Write-Host "Directories created."
```

Run: `ls bmst-social-agents/`
Expected: all listed directories present

- [ ] **Step 2: Create all `__init__.py` stubs**

```powershell
$inits = @(
  "bmst-social-agents/src/__init__.py",
  "bmst-social-agents/src/config/__init__.py",
  "bmst-social-agents/src/protocols/__init__.py",
  "bmst-social-agents/src/memory/__init__.py",
  "bmst-social-agents/src/tools/__init__.py",
  "bmst-social-agents/src/agents/__init__.py",
  "bmst-social-agents/src/orchestrator/__init__.py",
  "bmst-social-agents/src/scheduler/__init__.py",
  "bmst-social-agents/src/api/__init__.py",
  "bmst-social-agents/tests/__init__.py"
)
foreach ($f in $inits) { New-Item -Force $f | Out-Null }
Write-Host "Init files created."
```

- [ ] **Step 3: Commit**

```bash
git add bmst-social-agents/
git commit -m "chore: create bmst-social-agents directory skeleton"
```

---

### Task 2: `pyproject.toml`

**Files:**
- Create: `bmst-social-agents/pyproject.toml`

- [ ] **Step 1: Write `pyproject.toml`**

Create `bmst-social-agents/pyproject.toml` with this exact content:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "bmst-social-agents"
version = "0.1.0"
description = "Multi-agent social media system for BMST — SCOUT, WRITER, CAROUSEL, REVISOR, PUBLISHER"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }

dependencies = [
  "langgraph>=0.2.0",
  "langchain>=0.3.0",
  "langchain-anthropic>=0.3.0",
  "anthropic>=0.40.0",
  "fastapi>=0.115.0",
  "uvicorn>=0.30.0",
  "redis>=5.0.0",
  "supabase>=2.0.0",
  "apscheduler>=3.10.0",
  "pydantic>=2.0.0",
  "pydantic-settings>=2.0.0",
  "httpx>=0.27.0",
  "python-dotenv>=1.0.0",
  "langfuse>=2.0.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0",
  "pytest-asyncio>=0.23.0",
  "ruff>=0.4.0",
  "mypy>=1.10.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]
```

- [ ] **Step 2: Verify the file parses**

```bash
python -c "import tomllib; tomllib.load(open('bmst-social-agents/pyproject.toml', 'rb'))" && echo "OK"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add bmst-social-agents/pyproject.toml
git commit -m "chore: add pyproject.toml with all dependencies"
```

---

### Task 3: `.env.example`

**Files:**
- Create: `bmst-social-agents/.env.example`

- [ ] **Step 1: Write `.env.example`**

Create `bmst-social-agents/.env.example` with this exact content:

```dotenv
# =============================================================================
# bmst-social-agents — environment variables
# Copy to .env and fill in values before starting containers
# NEVER commit the .env file
# =============================================================================

# ── ANTHROPIC ─────────────────────────────────────────────────────────────────
# Get at: https://console.anthropic.com/settings/keys
ANTHROPIC_API_KEY=sk-ant-api03-...

# ── INTERNAL API ──────────────────────────────────────────────────────────────
# Shared key between n8n → bmst-social-agents (header X-Api-Key)
# Generate with: openssl rand -hex 32
BMST_API_KEY=

# ── APP SETTINGS ──────────────────────────────────────────────────────────────
# Environment: development | production
APP_ENV=development
# Log level: DEBUG | INFO | WARNING | ERROR
LOG_LEVEL=INFO

# ── REDIS ─────────────────────────────────────────────────────────────────────
# In Docker: redis://redis:6379
# Local:     redis://localhost:6379
REDIS_URL=redis://redis:6379

# ── SUPABASE ──────────────────────────────────────────────────────────────────
# Get at: https://app.supabase.com → Project Settings → API
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# ── LANGFUSE (observability) ──────────────────────────────────────────────────
# Get at: https://cloud.langfuse.com → Settings → API Keys
# Or self-hosted: http://langfuse:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# ── SCOUT AGENT — news research ───────────────────────────────────────────────
# Brave Search API key for web search
# Get at: https://api.search.brave.com/app/keys
BRAVE_SEARCH_API_KEY=BSA...
# Comma-separated list of RSS feed URLs SCOUT monitors
SCOUT_RSS_FEEDS=https://feeds.bbci.co.uk/news/technology/rss.xml
# How many days back SCOUT searches for news
SCOUT_LOOKBACK_DAYS=1
# Max articles per run
SCOUT_MAX_ARTICLES=10

# ── WRITER AGENT — content creation ───────────────────────────────────────────
# Claude model used for content writing (default: claude-sonnet-4-6)
WRITER_MODEL=claude-sonnet-4-6
# Max tokens per generated post
WRITER_MAX_TOKENS=1024
# Target language: pt | en
WRITER_LANGUAGE=pt

# ── CAROUSEL AGENT — carousel + Canva images ──────────────────────────────────
# Canva API token
# Get at: https://www.canva.com/developers/
CANVA_API_TOKEN=
# Canva brand kit ID (from your Canva brand settings)
CANVA_BRAND_KIT_ID=
# Default number of slides per carousel
CAROUSEL_DEFAULT_SLIDES=5

# ── REVISOR AGENT — quality gate + human approval ─────────────────────────────
# Evolution API (WhatsApp) for sending approval requests
# In Docker on the same network: http://evolution-api:8080
EVOLUTION_API_URL=http://evolution-api:8080
EVOLUTION_API_KEY=
# WhatsApp instance name configured in Evolution
EVOLUTION_INSTANCE=biscaplus
# WhatsApp number to receive approval requests (international format, no +)
REVISOR_APPROVER_PHONE=244XXXXXXXXX
# Timeout in seconds before auto-rejection if no human response
REVISOR_APPROVAL_TIMEOUT_SECONDS=3600

# ── PUBLISHER AGENT — social media publishing ─────────────────────────────────
# LinkedIn OAuth2 credentials
# Get at: https://www.linkedin.com/developers/apps
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_ACCESS_TOKEN=
# LinkedIn organisation URN (for company page posts)
LINKEDIN_ORG_URN=urn:li:organization:XXXXXXXXX

# Instagram via Facebook Graph API
# Get at: https://developers.facebook.com/apps/
INSTAGRAM_ACCESS_TOKEN=
# Instagram Business Account ID
INSTAGRAM_ACCOUNT_ID=

# ── SCHEDULER ─────────────────────────────────────────────────────────────────
# Cron expression for the daily pipeline run (UTC)
# Default: weekdays at 07:00 UTC (08:00 Luanda time)
SCHEDULER_CRON=0 7 * * 1-5
# Timezone for the scheduler
SCHEDULER_TIMEZONE=Africa/Luanda
```

- [ ] **Step 2: Verify the file was written**

```bash
grep -c "=" bmst-social-agents/.env.example
```

Expected: a number ≥ 30

- [ ] **Step 3: Commit**

```bash
git add bmst-social-agents/.env.example
git commit -m "chore: add .env.example with all agent configuration keys"
```

---

### Task 4: `.gitignore`

**Files:**
- Create: `bmst-social-agents/.gitignore`

- [ ] **Step 1: Write `.gitignore`**

Create `bmst-social-agents/.gitignore` with this exact content:

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
.venv/
venv/
env/
ENV/
env.bak/
venv.bak/

# Environment variables — NEVER commit
.env
.env.local
.env.*.local
secrets/
*.pem
*.key

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/
coverage.xml
*.cover

# Type checking
.mypy_cache/
.dmypy.json
dmypy.json
.pytype/

# Ruff
.ruff_cache/

# LangGraph / LangChain
.langgraph_cache/
langchain_cache/

# Jupyter
.ipynb_checkpoints/
*.ipynb

# Docker
*.tar

# Logs
*.log
logs/

# OS
Thumbs.db
```

- [ ] **Step 2: Commit**

```bash
git add bmst-social-agents/.gitignore
git commit -m "chore: add .gitignore for Python + LangGraph project"
```

---

### Task 5: `README.md`

**Files:**
- Create: `bmst-social-agents/README.md`

- [ ] **Step 1: Write `README.md`**

Create `bmst-social-agents/README.md` with this exact content:

```markdown
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
|-------|---------------|
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
   ┌────┴────────────────┐
   │                     │
LangGraph graphs    Redis (state cache)
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

### 1. Clone and enter the directory

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
```

- [ ] **Step 2: Commit**

```bash
git add bmst-social-agents/README.md
git commit -m "docs: add README with architecture overview and setup instructions"
```

---

### Task 6: `Makefile`

**Files:**
- Create: `bmst-social-agents/Makefile`

- [ ] **Step 1: Write `Makefile`**

Create `bmst-social-agents/Makefile` with this exact content (note: indentation must be a TAB character, not spaces):

```makefile
.PHONY: install run test lint docker-up docker-down

install:
	pip install -e ".[dev]"

run:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest tests/ -v

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

docker-up:
	docker compose up -d

docker-down:
	docker compose down
```

- [ ] **Step 2: Verify TAB indentation**

```bash
cat -A bmst-social-agents/Makefile | grep "^\^I"
```

Expected: lines starting with `^I` (TAB character). If empty, the Makefile uses spaces — redo with actual TABs.

- [ ] **Step 3: Commit**

```bash
git add bmst-social-agents/Makefile
git commit -m "chore: add Makefile with install/run/test/lint/docker targets"
```

---

### Task 7: `docker-compose.yml`

**Files:**
- Create: `bmst-social-agents/docker-compose.yml`

- [ ] **Step 1: Write `docker-compose.yml`**

Create `bmst-social-agents/docker-compose.yml` with this exact content:

```yaml
services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - redis
    restart: unless-stopped
    volumes:
      - ./src:/app/src:ro

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --save 60 1 --loglevel warning

volumes:
  redis_data:
```

- [ ] **Step 2: Validate YAML syntax**

```bash
python -c "import yaml; yaml.safe_load(open('bmst-social-agents/docker-compose.yml'))" && echo "OK"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add bmst-social-agents/docker-compose.yml
git commit -m "chore: add docker-compose.yml with API and Redis services"
```

---

## Self-Review

### Spec Coverage

| Requirement | Task |
|-------------|------|
| `bmst-social-agents/` directory with all subdirs | Task 1 |
| `src/__init__.py` and all package `__init__.py` stubs | Task 1 |
| `tests/datasets/` directory | Task 1 |
| `infra/supabase/` directory | Task 1 |
| `pyproject.toml` with all specified dependencies | Task 2 |
| `.env.example` with all variables + comments | Task 3 |
| `.gitignore` for Python + LangGraph | Task 4 |
| `README.md` with description, architecture, setup, run | Task 5 |
| `Makefile` with install/run/test/lint/docker-up/docker-down | Task 6 |
| `docker-compose.yml` | Task 7 |
| `docs/` directory | Task 1 |
| No agent logic implemented | ✓ all tasks are skeleton-only |

### Dependencies Specified in Spec

All listed in `pyproject.toml`:
- `langgraph>=0.2.0` ✓
- `langchain>=0.3.0` ✓
- `langchain-anthropic>=0.3.0` ✓
- `anthropic>=0.40.0` ✓
- `fastapi>=0.115.0` ✓
- `uvicorn>=0.30.0` ✓
- `redis>=5.0.0` ✓
- `supabase>=2.0.0` ✓
- `apscheduler>=3.10.0` ✓
- `pydantic>=2.0.0` ✓
- `pydantic-settings>=2.0.0` ✓
- `httpx>=0.27.0` ✓
- `python-dotenv>=1.0.0` ✓
- `langfuse>=2.0.0` ✓
- `pytest>=8.0.0` ✓
- `pytest-asyncio>=0.23.0` ✓

### Gaps Found

- `Dockerfile` is not in the spec but `docker-compose.yml` references one. Added as a note — the docker-compose service will fail to build without it, but since this is skeleton-only, a minimal placeholder Dockerfile could be added in a follow-up task. The `make docker-up` command will still start Redis correctly since it uses a direct image reference.

### Placeholder Scan

No TBD/TODO/placeholder patterns in task content. All files have exact content specified.
