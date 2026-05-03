# Setup Guide — BMST Acquisition Engine

Complete setup walkthrough from zero to live. Follow the phases in order — each one depends on the previous.

---

## Prerequisites Checklist

Complete every item before starting Phase 1.

| # | Item | Where to get it |
|---|------|-----------------|
| 1 | **Airtable account** + Personal Access Token (PAT) | airtable.com → Account → Developer Hub |
| 2 | **Anthropic API key** | console.anthropic.com → API Keys |
| 3 | **VPS or cloud server** (Ubuntu 22.04, min 2 vCPU / 4 GB RAM) | Hetzner, Contabo, or any provider |
| 4 | **Evolution API** running on VPS | github.com/EvolutionAPI/evolution-api |
| 5 | **n8n instance** (self-hosted recommended) | n8n.io → self-host on same VPS |
| 6 | **Google Cloud project** with Calendar API enabled | console.cloud.google.com |
| 7 | **Google Service Account** JSON key with Calendar access | IAM & Admin → Service Accounts |
| 8 | **Apify account** + API token | console.apify.com → Settings → Integrations |
| 9 | **Vercel account** (free tier sufficient) | vercel.com |
| 10 | **Domain with DNS access** (for `audit.biscaplus.com`) | your domain registrar |
| 11 | **Slack workspace** with an Incoming Webhook URL | api.slack.com → Apps → Incoming Webhooks |
| 12 | **WhatsApp Business number** connected to Evolution API | Meta Business Suite |

---

## Phase 1 — Repository & Dependencies

```bash
git clone https://github.com/biscaplus/bmst-acquisition-engine.git
cd bmst-acquisition-engine
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and fill in **every** value. Leave no placeholder unchanged.

**Test:**
```bash
python -c "import dotenv; dotenv.load_dotenv(); import os; print(os.environ['ANTHROPIC_API_KEY'][:10])"
# Should print the first 10 chars of your key
```

---

## Phase 2 — Airtable Schema

1. Create a new Airtable base named **BMST Acquisition Engine**.
2. Copy the base ID from the URL (`appXXXXXXXXXXXXXX`) into `.env` as `AIRTABLE_BASE_ID`.
3. Set `AIRTABLE_API_KEY` to your Personal Access Token.
4. Run the schema creator:

```bash
python airtable/create_schema.py
```

Expected output: three tables created — `companies`, `interactions`, `errors`.

**Test:** Open Airtable and verify all three tables exist with their fields.

---

## Phase 3 — Landing Page (Vercel)

1. In the Vercel dashboard, create a new project linked to the `landing_page/` directory.
2. Add environment variable `NEXT_PUBLIC_N8N_WEBHOOK_URL` pointing to your n8n webhook URL:
   `https://your-n8n.com/webhook/inbound`
3. Deploy. Vercel injects the env var into the HTML at build time.

**Test:**
```bash
curl -s https://your-landing-page.vercel.app | grep "webhook"
# Should show the injected webhook URL
```

---

## Phase 4 — n8n Workflow 01 (Inbound Webhook)

1. In n8n, open **Settings → Environment Variables** and add `AIRTABLE_BASE_ID` and `N8N_WEBHOOK_BASE_URL`.
2. Import `n8n_workflows/01_inbound_webhook.json`.
3. Set the Airtable credential (`airtable-cred`) to your Personal Access Token.
4. Activate the workflow.

**Test:**
```bash
curl -X POST https://your-n8n.com/webhook/inbound \
  -H "Content-Type: application/json" \
  -d '{"company_name":"Empresa Teste","contact_name":"João Silva","sector":"Retalho e Comércio","whatsapp_number":"244912345678","source":"landing_page"}'
# Expected: 200 OK. Check Airtable — a new row should appear in companies.
```

---

## Phase 5 — Qualification Bot (FastAPI + LangGraph)

1. Set `GOOGLE_SERVICE_ACCOUNT_JSON` to the path of your service account JSON file.
2. Set `GOOGLE_CALENDAR_ID` to your audit calendar ID.
3. Start the FastAPI service:

```bash
uvicorn api.main:app --host $API_HOST --port $API_PORT
```

Or as a systemd service (recommended for production):

```ini
[Unit]
Description=BMST Acquisition Engine API

[Service]
WorkingDirectory=/path/to/bmst-acquisition-engine
EnvironmentFile=/path/to/bmst-acquisition-engine/.env
ExecStart=/usr/bin/python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Test:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}

curl -X POST http://localhost:8000/qualify \
  -H "Content-Type: application/json" \
  -d '{
    "company_record": {
      "id": "recTEST",
      "fields": {
        "company_name": "Empresa Teste",
        "contact_name": "João",
        "whatsapp_number": "244912345678",
        "sector": "Retalho e Comércio",
        "conversation_stage": "greeting",
        "qualification_score": 0
      }
    },
    "incoming_message": "Olá"
  }'
# Expected: {"reply_text":"...","new_state":"contacted","new_stage":"Q1","updates":{...}}
```

---

## Phase 6 — Evolution API + WhatsApp Router (WF03)

1. Follow `docs/evolution_api_config.md` to connect your WhatsApp number and configure the webhook.
2. Set `EVOLUTION_API_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE` in n8n env.
3. Set `FASTAPI_BASE_URL` to the URL where your FastAPI service is reachable from n8n (e.g. `http://localhost:8000` if co-located).
4. Set `SLACK_WEBHOOK_URL` for human-handoff notifications.
5. Import `n8n_workflows/03_whatsapp_router.json`.
6. Set the Airtable credential.
7. Activate the workflow.

**Test:**
Send a WhatsApp message from any number to your BMST WhatsApp number.

Expected flow:
1. Evolution API fires webhook → n8n WF03 receives it
2. WF03 looks up the number in Airtable
3. If found in active state: calls `/qualify` → bot replies via Evolution API
4. Check Airtable `interactions` for the logged exchange

---

## Phase 7 — Prospecting Agent (crewAI)

**Test:**
```bash
curl -X POST http://localhost:8000/run-prospecting
# Expected: {"status":"ok","prospects_found":N}
# Also check Airtable — new companies should appear with source="prospecting_agent"
```

> Note: This makes live HTTP requests to Angolan job boards and Apify. Budget ~60–120 seconds.

---

## Phase 8 — Content Engine (LangChain)

**Test:**
```bash
curl -X POST http://localhost:8000/generate-content \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Empresa Interna",
    "sector": "Logística e Transportes",
    "pain_description": "Processos de facturação manual com 3+ dias de ciclo",
    "audit_notes": "Equipa de 15 pessoas, 60% do tempo em tarefas administrativas",
    "market": "Angola"
  }'
# Expected: {"linkedin_body":"...","instagram_body":"...audit.biscaplus.com","suggested_visual":"..."}
```

---

## Phase 9 — Nurture Sequence (WF06)

1. Import `n8n_workflows/06_nurture_sequence.json`.
2. Set the Airtable credential.
3. Activate the workflow.

The workflow runs daily at 09:30 WAT (Mon–Fri). No manual trigger needed.

**Test manually:**
In n8n, open WF06 and click **Execute Workflow** once. Check:
- Any companies with `state=nurture` and `last_activity_at` ~14/30/60/75 days ago should receive a WhatsApp touch
- `interactions` table should have a new `type=nurture` record
- `last_activity_at` should be updated on the company record

---

## Phase 10 — Error Handler (WF05)

1. Import `n8n_workflows/05_error_handler.json`.
2. Set the Airtable and Slack credentials.
3. Activate the workflow **before** activating any other workflow.

WF05 must be active and its webhook URL reachable by n8n before the other workflows can forward errors to it.

**Test:**
```bash
curl -X POST https://your-n8n.com/webhook/error-handler \
  -H "Content-Type: application/json" \
  -d '{"workflow_name":"test","node_name":"test node","error_message":"test error"}'
# Expected: Slack notification received; new row in Airtable errors table
```

---

## Environment Variables Reference

| Variable | Used by | Purpose |
|----------|---------|---------|
| `AIRTABLE_API_KEY` | Python, n8n | Airtable Personal Access Token |
| `AIRTABLE_BASE_ID` | Python, n8n | Airtable base identifier (`appXXX…`) |
| `ANTHROPIC_API_KEY` | Python | Claude API key for all LLM calls |
| `APIFY_API_TOKEN` | Python | Apify actor runs (LinkedIn lookup) |
| `EVOLUTION_API_URL` | n8n | Evolution API base URL (no trailing slash) |
| `EVOLUTION_API_KEY` | n8n | Evolution API key |
| `EVOLUTION_INSTANCE` | n8n | Instance name (e.g. `bmst_instance`) |
| `FASTAPI_BASE_URL` | n8n | FastAPI URL reachable from n8n |
| `GOOGLE_CALENDAR_ID` | Python | Google Calendar ID for audit bookings |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Python | Path to service account JSON file |
| `N8N_WEBHOOK_BASE_URL` | Python, n8n | Base URL of the n8n instance |
| `N8N_PROSPECTING_WEBHOOK_PATH` | Python | Path suffix for prospecting webhook |
| `NEXT_PUBLIC_N8N_WEBHOOK_URL` | Landing page | Full URL injected by Vercel at build time |
| `NOTIFICATION_EMAIL` | WF05 (Slack msg) | Email address included in error alerts |
| `SLACK_WEBHOOK_URL` | n8n | Slack Incoming Webhook URL |
| `API_HOST` | uvicorn | FastAPI bind host (default `0.0.0.0`) |
| `API_PORT` | uvicorn | FastAPI bind port (default `8000`) |
| `BMST_WHATSAPP_NUMBER` | Landing page | BMST WhatsApp number (digits only) |

---

## Common Errors

### `AIRTABLE_API_KEY not set` on startup
→ `.env` was not loaded. Run `cp .env.example .env` and fill in values, then restart.

### `ChatAnthropic` raises `AuthenticationError`
→ `ANTHROPIC_API_KEY` is wrong or expired. Regenerate at console.anthropic.com.

### Evolution API webhook not firing
→ Confirm the webhook is registered: run the curl in `docs/evolution_api_config.md §1`. Check that your n8n instance is publicly reachable (not `localhost`).

### n8n WF03 IF node always routes to FALSE
→ The Airtable lookup returned no records. The WhatsApp number sent does not match any `companies.whatsapp_number`. Numbers must be digits-only (no `+`, no spaces).

### `/qualify` returns `500` with `Graph invocation failed`
→ Usually a JSON parse failure in a bot node. Check API logs (`loguru` output). Add `ANTHROPIC_API_KEY` to the FastAPI service env.

### Calendar slots return empty list
→ `GOOGLE_SERVICE_ACCOUNT_JSON` path is wrong, or the service account lacks Calendar access. Verify the service account has been shared on the calendar with "Make changes to events" permission.

### `validate_linkedin_post` keeps failing on word count
→ Claude occasionally generates slightly out-of-range posts. The chain retries once automatically. If both attempts fail, a `422` is returned — check `audit_notes` length (very short inputs lead to short posts).

### WF06 sends no touches even for old nurture leads
→ `last_activity_at` may be null or in an unexpected format. The Code node defaults to 999 days, which is outside all touch windows. Set `last_activity_at` manually in Airtable for testing.

### Airtable `errors` table not found in WF05
→ Run `python airtable/create_schema.py` to ensure all tables exist before activating WF05.
