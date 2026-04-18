# BMST Agents — Autonomous AI Workforce

![Python](https://img.shields.io/badge/python-3.12-blue)
![LangGraph](https://img.shields.io/badge/langgraph-0.2+-green)
![FastAPI](https://img.shields.io/badge/fastapi-0.115+-orange)
![Claude API](https://img.shields.io/badge/claude-API-purple)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

Most small technology companies spend a significant part of their time on tasks that do not generate revenue: qualifying leads, writing proposals, following up on invoices, updating clients on project progress. This project automates that entire cycle.

BMST Agents is a system of four autonomous AI agents that handle the complete business operation of a technology services company, from the first contact with a prospect to the final invoice. It was built for BMST, but it is designed to be adapted to any company or sector that follows a similar cycle: find clients, close deals, deliver work, get paid.

---

## The Problem It Solves

Running a small professional services company means context-switching constantly. A founder or consultant spends time prospecting, then switches to writing a proposal, then to managing a project, then to chasing an unpaid invoice. Each switch has a cost, and none of that time is billable.

The goal here was to automate the routine parts of that cycle without losing control over the decisions that matter. A system that prospects and qualifies leads automatically, but only sends a proposal after the founder approves it. A system that manages client communication during a project, but alerts a human when something needs attention. Automation where it saves time, human judgment where it matters.

The system is also deliberately simple to deploy and cheap to run. It does not require a dedicated server or a large infrastructure budget. It runs alongside existing tools and does not replace anything that is already working.

---

## How It Works

The architecture separates three distinct responsibilities.

**n8n** handles orchestration. It receives WhatsApp messages, fires scheduled jobs, routes requests, and manages human approval flows via Telegram. This layer already existed and continues to work exactly as before.

**LangGraph** handles reasoning. Each agent is a state graph where nodes call Claude, read from a database, or apply business rules. The graph structure makes the logic explicit and testable.

**FastAPI** connects the two. Each agent is an HTTP endpoint. n8n calls these endpoints the same way it would call any other API, which means the agent implementation can change without touching a single workflow.

```
WhatsApp / Telegram / Scheduled triggers
                |
                v
        n8n  (orchestration layer)
                |
                | HTTP POST
                v
        FastAPI  (API layer)
                |
        +-------+-------+-------+
        |       |       |       |
     HUNTER  CLOSER  DELIVERY  LEDGER
        |       |       |       |
        +-------+-------+-------+
                |
        Claude API + Supabase + Redis
```

---

## The Four Agents

### HUNTER

Qualifies business prospects and generates personalised outreach messages. Before any LLM call, a fast classification step segments the company. Non-viable leads are archived immediately without generating a message, which keeps token costs low and avoids wasted outreach.

```
START > qualify_company > [router] > archive          > END
                                   > escalate_human   > END
                                   > generate_message > END
```

### CLOSER

Runs discovery conversations, drafts commercial proposals, and manages the approval flow. No proposal reaches a client without explicit founder approval. This is enforced at the graph level using LangGraph `interrupt()`, not just as a convention.

```
START > discovery > process_answers > generate_draft
     > [interrupt: human approval via Telegram]
     > generate_pdf > send_proposal > END
```

### DELIVERY

Manages active client projects. Sends automated progress updates twice a week, requests phase approvals, and alerts the founder when something needs attention or a deadline is at risk.

### LEDGER

Handles invoicing and payment tracking. Generates invoices at the right moments in the project lifecycle, monitors due dates, sends escalating reminders, and produces a monthly financial summary.

---

## Technical Stack

| Layer | Tool | Why |
|---|---|---|
| Agent framework | LangGraph 0.2+ | Stateful graphs, testable transitions, `interrupt()` for human review |
| LLM | Claude API (Haiku + Sonnet) | Haiku for classification, Sonnet for client-facing content |
| API layer | FastAPI 0.115+ | Async, typed, auto-documentation at `/docs` |
| Orchestration | n8n | Already in production, no migration needed |
| Memory | Supabase (pgvector) | Lead history, conversation context, RAG |
| Cache | Redis | Session state, deduplication of WhatsApp messages |
| Observability | Langfuse | Traces, token costs, error rates per agent |
| Deploy | Docker + EasyPanel | Self-hosted, same VPS as n8n |

---

## Design Decisions Worth Explaining

**Why LangGraph instead of a visual builder**

Visual builders are fast to prototype but hard to test. With code, you can write a test that proves the system does what you think it does. For a system that sends messages to real clients and generates real invoices, that difference matters. Every state transition here has a test. That is not possible with a drag-and-drop tool.

**Why two models**

Lead qualification is a structured classification task. It does not need a powerful model. Proposal generation is a writing task where quality shows up directly in client outcomes. Using a smaller, cheaper model for classification and a stronger model for writing cuts inference costs significantly without any visible quality loss.

**Why `interrupt()` for proposal approval**

Every commercial proposal requires the founder to approve it before it reaches the client. `interrupt()` pauses the graph at a specific point and only resumes when a human responds via Telegram. It is not a soft guideline. The graph cannot proceed without the approval signal.

**Output format enforcement**

Every agent response is structured as two blocks separated by `---`. The first block goes to WhatsApp, clean text only. The second goes to Telegram as internal metadata for the founder. The system prompt includes a self-check step before the model responds, which prevents internal notes from leaking into client messages.

**Adapting this to another company**

The business logic lives in `agents/[name]/prompts.py` and the `TypedDict` state definitions. The core modules, FastAPI layer, and graph structure are reusable. Replacing the prompts and adjusting the state fields is enough to adapt the system to a different sector or business model.

---

## Project Structure

```
bmst-agents/
├── agents/
│   ├── hunter/
│   │   ├── state.py      TypedDict state definition
│   │   ├── nodes.py      Node functions
│   │   ├── graph.py      StateGraph assembly
│   │   └── prompts.py    System prompts as string constants
│   ├── closer/
│   ├── delivery/
│   └── ledger/
├── core/
│   ├── llm.py            Anthropic client with retry logic
│   ├── memory.py         Supabase read/write operations
│   ├── redis_client.py   Session state and deduplication
│   └── alerts.py         Telegram alerts for anomalies
├── api/
│   ├── main.py           FastAPI app and all routes
│   ├── models.py         Pydantic request/response models
│   └── dependencies.py   API key verification
├── tests/
│   ├── test_hunter.py
│   ├── test_closer.py
│   └── test_api.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Getting Started

### Requirements

- Python 3.12+
- Docker and docker-compose
- Anthropic API key
- Supabase project (free tier is enough to start)

### Run locally

```bash
git clone https://github.com/fidel-kussunga/bmst-agents
cd bmst-agents

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Fill in .env with your API keys

docker-compose up
# API at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### Test the HUNTER endpoint

```bash
curl -X POST http://localhost:8000/hunter \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key" \
  -d '{
    "empresa": "Example Healthcare Group",
    "sector": "Private Healthcare",
    "phone": "+244923000000",
    "decisor": "Dr. António Ferreira"
  }'
```

### Run tests

```bash
pytest tests/ -v
pytest -m "not integration" -v    # fast, no LLM calls
pytest -m integration -v          # slow, calls real Claude API
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check Supabase and Redis connectivity |
| GET | `/metrics` | Conversion rates, costs, error rates |
| GET | `/docs` | Interactive OpenAPI documentation |
| POST | `/hunter` | Qualify and message a single prospect |
| POST | `/hunter/batch` | Process up to 20 prospects in parallel |
| POST | `/closer/diagnose` | Start discovery conversation |
| POST | `/closer/propose` | Generate proposal (triggers human approval) |
| POST | `/delivery/start` | Start project management for a new client |
| POST | `/delivery/update` | Generate weekly progress update |
| POST | `/ledger/invoice` | Generate and send invoice |
| POST | `/ledger/check-payments` | Check and remind overdue payments |
| POST | `/ledger/monthly-report` | Generate monthly P&L summary |

---

## Current Status

- [x] HUNTER agent
- [x] CLOSER agent with human-in-the-loop
- [ ] DELIVERY agent
- [ ] LEDGER agent
- [ ] Langfuse observability
- [ ] CI/CD via GitHub Actions

---

## About

I am Fidel Inácio Kussunga, a software engineer based between Lausanne and Luanda.

My background is in embedded systems. I spent several years writing C and C++ for automotive and industrial hardware, working with protocols like CAN, FlexRay and Automotive Ethernet on ARM microcontrollers, at companies in Portugal and Switzerland. I hold an MSc in Industrial Electronics and Computer Engineering from the University of Minho, with a specialisation in Automation, Control and Robotics. That experience across two markets gave me a broader perspective on how software is built and delivered in different contexts, which shaped how I think about system design.

The decision to transition into AI engineering was a deliberate response to where the market is heading. The job market has changed in a way that is not temporary. I saw that the skills I had built over years in embedded systems, rigorous design, state machine thinking, real-time constraints, testing, and documentation, were directly applicable to building AI agent systems. The transition was not a reinvention. It was a combination.

What changed is the tooling. I now work with Claude Code, Cursor, and similar tools that accelerate development significantly. But I approach them the same way I approached embedded systems: I need to understand what the code does before I trust it in production. Vibe-coding and traditional engineering thinking are not opposites. The first makes you fast. The second keeps you from shipping systems you cannot debug or maintain. Using both together is what I find genuinely interesting about this moment in software development.

This project is a concrete example of that approach. It is the infrastructure that runs my own business, built with the same rigour I would apply to any production system.

[LinkedIn](https://www.linkedin.com/in/fidelkussunga/) · fikinacio@gmail.com
