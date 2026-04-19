# Design: PROSPECTOR Activation + n8n Configuration

**Date:** 2026-04-20
**Status:** Approved
**Scope:** Fix PROSPECTOR code, validate pipeline layers, configure n8n for production

---

## Context

The PROSPECTOR agent discovers leads from Google Places, enriches them via website/Instagram scraping, generates personalised approach notes with Claude Haiku, and writes qualified leads to Google Sheets. The system is deployed on a VPS with all env vars set. Two problems block production use:

1. **Code bugs** — schema/state/mapping mismatches prevent the sheet from being filled correctly
2. **n8n config** — credentials and base URLs not yet registered in the n8n instance

---

## Phase 1 — Code Fixes + Pipeline Validation

### 1a. Code Fixes (3 files)

**`agents/prospector/prompts.py`**
- Remove `pain_point` field from `ApproachNotesSchema` — no corresponding column in the Google Sheet
- Final schema fields: `approach_notes`, `opportunity`, `recommended_service`

**`agents/prospector/state.py`**
- Remove `pain_point` field
- Add `opportunity: str | None` and `recommended_service: str | None` (were missing, causing `None` writes to sheet)

**`agents/prospector/nodes.py`**
- `gerar_abordagem` node: return all 3 fields (`approach_notes`, `opportunity`, `recommended_service`) to state
- `write_lead_to_sheet` node: fix column mapping:
  - `approach_notes` → `notas_abordagem`
  - `opportunity` → `oportunidade`
  - `recommended_service` → `servico_bmst`

### 1b. Test Script (`scripts/test_prospector.py`)

Three independent tests, each printing `✓ OK` or `✗ FALHOU: <reason>`:

| Test | What it validates |
|------|-------------------|
| `test_places()` | Google Places API — searches "clínica" in Luanda, prints 3 results with name + address + phone |
| `test_scraper()` | Website scraper — scrapes a real clinic website, prints extracted WhatsApp number |
| `test_instagram()` | Instagram scraper — scrapes a real public profile, prints followers count + contact |

Run with: `python scripts/test_prospector.py`

### 1c. End-to-End Test

Trigger via API with a small batch:
```bash
curl -X POST https://<VPS>/prospector/run \
  -H "X-Api-Key: $BMST_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"sector": "saude", "city": "Luanda", "max_companies": 3}'
```

Success criteria:
- Response: `202 Accepted`
- Sheet receives 3 rows with all columns filled (`notas_abordagem`, `oportunidade`, `servico_bmst`, `valor_est_aoa`, `segmento`, `whatsapp`)
- Telegram report received by founder

---

## Phase 2 — n8n Configuration

### 2a. Register Credentials

In n8n → Settings → Credentials, create two Header Auth credentials with **exact names**:

| Credential name | Header name | Value |
|----------------|-------------|-------|
| `bmst-api-key` | `X-Api-Key` | `$BMST_API_KEY` |
| `supabase-key` | `apikey` | `$SUPABASE_SERVICE_KEY` |

### 2b. Base URL

Check all HTTP Request nodes across the 3 workflows. Replace any `http://api:8000` or `localhost` with the VPS base URL (e.g. `https://api.bmst.ao`).

Affected workflows: `01_daily_schedule.json`, `02_inbound_whatsapp.json`, `03_telegram_callback.json`

### 2c. Telegram Webhook

Register the n8n webhook URL with Telegram:
```
POST https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook
  ?url=https://<N8N_HOST>/webhook/telegram
```

### 2d. Verification

- Trigger `01_daily_schedule` manually in n8n → confirm `/prospector/run` returns 202
- Check VPS logs: `docker compose logs -f api | grep prospector`
- Confirm cron fires at 07:00 UTC Monday–Friday

---

## What Does NOT Change

- `agents/prospector/graph.py` — routing is correct
- `core/` utilities — sheets_client, telegram_client, evolution_client
- `main.py` — `/prospector/run` endpoint is correct
- n8n workflow structure (JSON node topology is correct)

---

## Files Modified

| File | Change |
|------|--------|
| `agents/prospector/prompts.py` | Remove `pain_point` from `ApproachNotesSchema` |
| `agents/prospector/state.py` | Remove `pain_point`, add `opportunity` + `recommended_service` |
| `agents/prospector/nodes.py` | Fix `gerar_abordagem` return + `write_lead_to_sheet` mapping |
| `scripts/test_prospector.py` | New file — 3-layer pipeline test script |
