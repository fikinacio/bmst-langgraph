# PROSPECTOR Activation + n8n Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix PROSPECTOR schema/mapping bugs, validate the Google Places + scraper pipeline with a test script, run a 3-company end-to-end test, and configure n8n credentials to activate the daily cron.

**Architecture:** Two code fixes (prompts.py + nodes.py) eliminate the phantom `pain_point` field. A standalone test script (`scripts/test_prospector.py`) validates each pipeline layer independently on the VPS before running the full agent. n8n configuration is done via the n8n UI.

**Tech Stack:** Python 3.11, LangGraph, httpx, Google Places API, Google Sheets API (gspread), n8n, Telegram Bot API

---

## File Map

| File | Action | What changes |
|------|--------|-------------|
| `agents/prospector/prompts.py` | Modify | Remove `pain_point` field from `ApproachNotesSchema` |
| `agents/prospector/nodes.py` | Modify | Remove `"pain_point"` key from `lead_row` in `write_lead_to_sheet` |
| `scripts/test_prospector.py` | Create | 3-layer integration test script |

---

## Task 1: Remove `pain_point` from `ApproachNotesSchema`

**Files:**
- Modify: `agents/prospector/prompts.py:49-61`

`pain_point` is defined in the schema but has no column in the sheet and no corresponding field in `ProspectorState`. Removing it stops the LLM from generating a field that is immediately discarded.

- [ ] **Step 1: Edit `agents/prospector/prompts.py`**

Replace:
```python
class ApproachNotesSchema(BaseModel):
    approach_notes: str = Field(
        description="Specific, evidence-based hook for the HUNTER outreach message."
    )
    opportunity: str = Field(
        description="Detailed description of the automation opportunity found (internal use)."
    )
    recommended_service: str = Field(
        description="Most relevant BMST service slug for this company."
    )
    pain_point: str = Field(
        description="One-sentence description of the main operational pain point."
    )
```

With:
```python
class ApproachNotesSchema(BaseModel):
    approach_notes: str = Field(
        description="Specific, evidence-based hook for the HUNTER outreach message."
    )
    opportunity: str = Field(
        description="Detailed description of the automation opportunity found (internal use)."
    )
    recommended_service: str = Field(
        description="Most relevant BMST service slug for this company."
    )
```

- [ ] **Step 2: Verify import in nodes.py still works**

Run:
```bash
cd /app && python -c "from agents.prospector.prompts import ApproachNotesSchema; print(list(ApproachNotesSchema.model_fields.keys()))"
```

Expected output:
```
['approach_notes', 'opportunity', 'recommended_service']
```

- [ ] **Step 3: Commit**

```bash
git add agents/prospector/prompts.py
git commit -m "fix: remove pain_point from ApproachNotesSchema — no matching sheet column or state field"
```

---

## Task 2: Remove `pain_point` from `write_lead_to_sheet`

**Files:**
- Modify: `agents/prospector/nodes.py:476`

`lead_row` currently maps `approach_notes` to the `pain_point` column (duplicating `notas_abordagem`). Removing this key prevents a duplicate/wrong write.

- [ ] **Step 1: Edit `agents/prospector/nodes.py`**

In `write_lead_to_sheet`, find the `lead_row` dict and remove the `pain_point` line:

Remove this line from the `lead_row` dict:
```python
        "pain_point":      state.get("approach_notes", ""),
```

The surrounding lines should now read:
```python
        "nr_funcionarios": 0,
        "servico_bmst":    state.get("recommended_service", ""),
        "valor_est_aoa":   state.get("estimated_value_aoa", 0),
        "notas_abordagem": state.get("approach_notes", ""),
        "notas":           notes,
        "oportunidade":    state.get("opportunity", ""),
```

- [ ] **Step 2: Verify node parses cleanly**

```bash
cd /app && python -c "from agents.prospector.nodes import write_lead_to_sheet; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add agents/prospector/nodes.py
git commit -m "fix: remove pain_point from write_lead_to_sheet lead_row mapping"
```

---

## Task 3: Create test script `scripts/test_prospector.py`

**Files:**
- Create: `scripts/test_prospector.py`

Validates Google Places, website scraper, and Instagram scraper independently. Each test prints `✓ OK` or `✗ FALHOU: <reason>`.

- [ ] **Step 1: Create `scripts/test_prospector.py`**

```python
#!/usr/bin/env python3
"""scripts/test_prospector.py — validates each layer of the PROSPECTOR pipeline."""
from __future__ import annotations

import asyncio
import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.prospector.tools import (
    google_places_search,
    scrape_website_for_whatsapp,
    try_instagram_bio,
)


async def test_places(api_key: str) -> tuple[bool, list[dict]]:
    print("[1/3] Google Places API — a pesquisar 'saúde' em Luanda...")
    try:
        results = await google_places_search(
            sector="saúde",
            city="Luanda",
            api_key=api_key,
            max_results=3,
        )
    except Exception as exc:
        print(f"  ✗ FALHOU: {exc}")
        return False, []

    if not results:
        print("  ✗ FALHOU: nenhum resultado retornado — verificar GOOGLE_PLACES_API_KEY e billing")
        return False, []

    for r in results:
        print(f"  • {r['name']}")
        print(f"    morada:  {r['address']}")
        print(f"    tel:     {r['phone'] or '(sem telefone no Places)'}")
        print(f"    website: {r['website'] or '(sem website)'}")
        print(f"    rating:  {r['rating']}")

    print(f"  ✓ OK — {len(results)} empresa(s) encontrada(s)\n")
    return True, results


async def test_scraper(url: str) -> bool:
    print(f"[2/3] Website Scraper — a fazer scrape de {url} ...")
    try:
        result = await scrape_website_for_whatsapp(url)
    except Exception as exc:
        print(f"  ✗ FALHOU: {exc}")
        return False

    phones = result.get("phones", [])
    insta  = result.get("instagram_url")
    fb     = result.get("facebook_url")
    snip   = (result.get("text_snippet") or "")[:120]

    print(f"  • WhatsApp(s) encontrado(s): {phones if phones else '(nenhum)'}")
    print(f"  • Instagram: {insta or '(não encontrado)'}")
    print(f"  • Facebook:  {fb or '(não encontrado)'}")
    print(f"  • Snippet:   {snip}...")

    if phones:
        print(f"  ✓ OK — WhatsApp: {phones[0]}\n")
    else:
        print("  ⚠ OK — sem WhatsApp directo (normal para muitos sites angolanos)\n")
    return True


async def test_instagram(company_name: str) -> bool:
    print(f"[3/3] Instagram Scraper — a pesquisar perfil para '{company_name}' ...")
    try:
        result = await try_instagram_bio(company_name)
    except Exception as exc:
        print(f"  ✗ FALHOU: {exc}")
        return False

    phones = result.get("phones", [])
    bio    = result.get("bio", "")

    print(f"  • Bio:    {bio[:120] if bio else '(não encontrado)'}")
    print(f"  • Phones: {phones if phones else '(nenhum)'}")

    if bio:
        print(f"  ✓ OK — perfil encontrado\n")
    else:
        print("  ⚠ OK — perfil Instagram não encontrado (normal — muitas PME angolanas não têm)\n")
    return True


async def main() -> None:
    print("=" * 60)
    print("PROSPECTOR — Validação de Pipeline")
    print("=" * 60)
    print()

    api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        print("ERRO: GOOGLE_PLACES_API_KEY não está definido no ambiente.")
        print("  Execute: export GOOGLE_PLACES_API_KEY=<chave>")
        sys.exit(1)

    places_ok, companies = await test_places(api_key)

    # Use first result's website for scraper test; fallback to a known URL
    test_url = ""
    company_name = "Clínica Katondo"
    if places_ok and companies:
        test_url     = companies[0].get("website", "")
        company_name = companies[0].get("name", company_name)

    if not test_url:
        test_url = "https://clinicakatondo.ao"
        print(f"  (nenhum website no 1º resultado — a usar fallback: {test_url})\n")

    await test_scraper(test_url)
    await test_instagram(company_name)

    print("=" * 60)
    print("Validação concluída. Se todos os testes passaram, corre:")
    print()
    print('  curl -X POST https://<VPS>/prospector/run \\')
    print('    -H "X-Api-Key: $BMST_API_KEY" \\')
    print('    -H "Content-Type: application/json" \\')
    print("    -d '{\"sector\": \"saude\", \"city\": \"Luanda\", \"max_companies\": 3}'")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Commit**

```bash
git add scripts/test_prospector.py
git commit -m "feat: add PROSPECTOR pipeline validation script"
```

---

## Task 4: Run test script on VPS

SSH into the VPS and run:

- [ ] **Step 1: Pull latest code**

```bash
cd /app
git pull origin main
```

- [ ] **Step 2: Run test script**

```bash
docker compose exec api python scripts/test_prospector.py
```

Expected output pattern:
```
============================================================
PROSPECTOR — Validação de Pipeline
============================================================

[1/3] Google Places API — a pesquisar 'saúde' em Luanda...
  • Clínica General Katondo
    morada:  Travessa dos Mirantes, Rua A, Talatona, Luanda
    tel:     +244923168644
    website: https://clinicakatondo.ao
    rating:  4.1
  ✓ OK — 3 empresa(s) encontrada(s)

[2/3] Website Scraper — a fazer scrape de https://clinicakatondo.ao ...
  • WhatsApp(s) encontrado(s): ['+244923168644']
  ✓ OK — WhatsApp: +244923168644

[3/3] Instagram Scraper — a pesquisar perfil para 'Clínica General Katondo' ...
  ⚠ OK — perfil Instagram não encontrado (normal)
```

- [ ] **Step 3: If Places returns ZERO_RESULTS or REQUEST_DENIED**

Check API key and billing:
```bash
docker compose exec api python -c "
import os, httpx, asyncio
async def check():
    key = os.environ['GOOGLE_PLACES_API_KEY']
    r = await httpx.AsyncClient().get(
        'https://maps.googleapis.com/maps/api/place/textsearch/json',
        params={'query': 'clinica luanda angola', 'key': key}
    )
    print(r.json()['status'], r.json().get('error_message', ''))
asyncio.run(check())
"
```

---

## Task 5: End-to-end test — 3 companies

- [ ] **Step 1: Trigger PROSPECTOR with 3 companies**

```bash
curl -X POST https://<VPS_URL>/prospector/run \
  -H "X-Api-Key: $BMST_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"sector": "saude", "city": "Luanda", "max_companies": 3}'
```

Expected response:
```json
{"status": "accepted", "message": "PROSPECTOR session started in background"}
```

- [ ] **Step 2: Tail logs to confirm progression**

```bash
docker compose logs -f api | grep -E "prospector\.|PROSPECTOR"
```

Expected log sequence:
```
prospector.initialize_session: date=... sector=saude city=Luanda max=3
prospector.discover_companies: 3 companies found
prospector.prepare_current_company: processing Clínica ...
prospector.generate_approach_notes: service=whatsapp_chatbot_basico for '...'
prospector.qualify_lead: segment=B value=250000 AOA for '...'
prospector.write_lead_to_sheet: wrote lead #1 — '...' (seg B)
```

- [ ] **Step 3: Verify Google Sheet**

Open the sheet and confirm 3 new rows with:
- `empresa` — company name (not empty)
- `whatsapp` — phone in `+244XXXXXXXXX` format (or empty if not found)
- `notas_abordagem` — specific hook text (not generic)
- `oportunidade` — automation opportunity description
- `servico_bmst` — one of the 6 valid service slugs
- `valor_est_aoa` — a number between 50000 and 2000000
- `segmento` — "B" or "C"
- `estado_hunter` — "pendente"

- [ ] **Step 4: Confirm Telegram report received**

The founder should receive a Telegram message like:
```
📊 PROSPECTOR — Relatório Diário
Sector: Saúde | Data: 2026-04-20
✅ Leads escritos: 3
⏭ Leads ignorados: 0
```

---

## Task 6: Configure n8n credentials

In n8n: **Settings → Credentials → Add Credential**

- [ ] **Step 1: Create `bmst-api-key` credential**

- Type: **Header Auth**
- Name (must be exact): `bmst-api-key`
- Header Name: `X-Api-Key`
- Header Value: value of `BMST_API_KEY` from the VPS `.env`

- [ ] **Step 2: Create `supabase-key` credential**

- Type: **Header Auth**
- Name (must be exact): `supabase-key`
- Header Name: `apikey`
- Header Value: value of `SUPABASE_SERVICE_KEY` from the VPS `.env`

- [ ] **Step 3: Update base URL in all 3 workflows**

In n8n, open each workflow and check every HTTP Request node. Replace any occurrence of `http://api:8000` or `localhost:8000` with the VPS base URL (e.g. `https://api.bmst.ao`).

Workflows to check:
- `01_daily_schedule` — PROSPECTOR, HUNTER, LEDGER nodes
- `02_inbound_whatsapp` — Router → CLOSER/DELIVERY/HUNTER nodes
- `03_telegram_callback` — Callback handler node

- [ ] **Step 4: Assign credentials to HTTP nodes**

In each workflow, open each HTTP Request node that calls the FastAPI API and set:
- Authentication: **Header Auth**
- Credential: `bmst-api-key`

For the Supabase node in `01_daily_schedule` (LEDGER pending invoices query):
- Authentication: **Header Auth**
- Credential: `supabase-key`

---

## Task 7: Register Telegram webhook

- [ ] **Step 1: Get the n8n webhook URL**

In n8n, open workflow `03_telegram_callback`. Click the Telegram Webhook trigger node and copy the **Production URL** (format: `https://<N8N_HOST>/webhook/telegram`).

- [ ] **Step 2: Register with Telegram**

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook?url=https://<N8N_HOST>/webhook/telegram"
```

Expected response:
```json
{"ok": true, "result": true, "description": "Webhook was set"}
```

- [ ] **Step 3: Verify**

```bash
curl "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getWebhookInfo"
```

Confirm `"url"` matches and `"last_error_message"` is absent.

---

## Task 8: Activate n8n workflows and verify cron

- [ ] **Step 1: Activate all 3 workflows**

In n8n, toggle each workflow to **Active**:
- `01_daily_schedule`
- `02_inbound_whatsapp`
- `03_telegram_callback`

- [ ] **Step 2: Trigger `01_daily_schedule` manually**

In n8n, click **Execute Workflow** on `01_daily_schedule`. Confirm:
- PROSPECTOR node returns HTTP 202
- HUNTER node returns HTTP 202
- LEDGER node runs without errors

- [ ] **Step 3: Confirm cron schedule**

In n8n, verify the trigger nodes show:
- PROSPECTOR: `0 7 * * 1-5` (07:00 UTC, Mon–Fri)
- HUNTER: `0 8 * * 1-5` (08:00 UTC, Mon–Fri)
- LEDGER: `30 8 * * *` (08:30 UTC, every day)
