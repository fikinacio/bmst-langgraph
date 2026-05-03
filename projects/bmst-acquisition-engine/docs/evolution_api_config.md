# Evolution API Configuration — BMST WhatsApp Router

This document covers everything needed to wire Evolution API to the n8n WhatsApp router
(Workflow 03). Complete these steps after deploying n8n and before going live.

---

## 1. Configure the Webhook URL

Evolution API pushes all WhatsApp events to a webhook URL you define per instance.

### Steps

1. Open the Evolution API Manager (your instance dashboard or Swagger UI at `EVOLUTION_API_URL/docs`).
2. Navigate to **Webhook → Set Webhook** or call the endpoint directly:

```bash
curl -X POST "$EVOLUTION_API_URL/webhook/set/$EVOLUTION_INSTANCE" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "'"$N8N_WEBHOOK_BASE_URL"'/webhook/whatsapp-router",
    "webhook_by_events": false,
    "webhook_base64": false,
    "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]
  }'
```

3. Confirm the webhook was saved:

```bash
curl "$EVOLUTION_API_URL/webhook/find/$EVOLUTION_INSTANCE" \
  -H "apikey: $EVOLUTION_API_KEY"
```

Expected response includes `"url": "https://www.n8n.biscaplus.com/webhook/whatsapp-router"`.

### URL format

The n8n webhook path is defined in Workflow 03, node **Webhook — Evolution API**:

```
POST https://www.n8n.biscaplus.com/webhook/whatsapp-router
```

This must be a publicly reachable HTTPS URL. Evolution API will not deliver to `localhost`.

---

## 2. Events to Subscribe To

| Event | Constant in API | Required | Purpose |
|-------|-----------------|----------|---------|
| `messages.upsert` | `MESSAGES_UPSERT` | **Yes** | Triggers on every new inbound or outbound message |
| `connection.update` | `CONNECTION_UPDATE` | Recommended | Monitor instance connectivity — alerts when QR code expires or instance disconnects |
| `messages.update` | `MESSAGES_UPDATE` | No | Delivery receipts (read/delivered status) — not used by this workflow |
| `send.message` | `SEND_MESSAGE` | No | Confirms messages you sent — workflow already filters `fromMe: true` |

**Minimum required:** `MESSAGES_UPSERT` only. Add `CONNECTION_UPDATE` to catch disconnections early.

### How Workflow 03 filters events

The **Code — Normalise remoteJid** node silently stops execution (returns `[]`) for:

- Any event other than `messages.upsert`
- Messages where `fromMe: true` (sent by the bot)
- Non-text messages (audio, video, stickers, reactions, location)

No error is thrown — n8n simply produces no output and the execution completes silently.

---

## 3. Instance Connection

The Evolution API instance must be connected (QR code scanned) before messages can flow.

```bash
# Check instance status
curl "$EVOLUTION_API_URL/instance/fetchInstances" \
  -H "apikey: $EVOLUTION_API_KEY"
```

Look for `"state": "open"` in the response for your instance. If `"state": "close"` or `"connecting"`:

```bash
# Get a fresh QR code
curl "$EVOLUTION_API_URL/instance/connect/$EVOLUTION_INSTANCE" \
  -H "apikey: $EVOLUTION_API_KEY"
```

Open the returned QR URL in a browser and scan with the BMST WhatsApp account.

---

## 4. Test with a Real WhatsApp Message

### Step 1 — Send a message from your test number to the BMST business number

Send any text message from your personal WhatsApp to `+$BMST_WHATSAPP_NUMBER`.

### Step 2 — Check the n8n execution log

In n8n: **Executions → Workflow 03 — WhatsApp Router**. Confirm the execution ran and check each node's output data.

### Step 3 — Verify the message text was extracted

Open the **Code — Normalise remoteJid** node output. You should see:

```json
{
  "remote_jid": "244XXXXXXXXXX@s.whatsapp.net",
  "whatsapp_number": "244XXXXXXXXXX",
  "message_text": "your message here",
  "message_type": "conversation"
}
```

### Step 4 — Send a test message via Evolution API (outbound test)

```bash
curl -X POST "$EVOLUTION_API_URL/message/sendText/$EVOLUTION_INSTANCE" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "244XXXXXXXXXX",
    "text": "Teste de conexão BMST — sistema operacional.",
    "delay": 1500
  }'
```

Replace `244XXXXXXXXXX` with the recipient number (digits only, no `+`).

### Step 5 — Simulate a full qualification turn (curl)

```bash
curl -X POST "http://localhost:$API_PORT/qualify" \
  -H "Content-Type: application/json" \
  -d '{
    "company_record": {
      "id": "recTEST000001",
      "fields": {
        "company_name": "Empresa Teste",
        "contact_name": "Ana Silva",
        "whatsapp_number": "244912000000",
        "sector": "Logística",
        "state": "contacted",
        "conversation_stage": "Q1"
      }
    },
    "incoming_message": "Somos 12 pessoas no total"
  }'
```

Expected response:

```json
{
  "reply_text": "...",
  "new_state": "qualification",
  "new_stage": "Q2",
  "updates": { "team_size": "12", "state": "qualification", "conversation_stage": "Q2" }
}
```

---

## 5. Evolution API Payload Format Reference

When Evolution API fires `messages.upsert`, the n8n webhook receives:

```json
{
  "event": "messages.upsert",
  "instance": "bmst_instance",
  "data": {
    "key": {
      "remoteJid": "244912345678@s.whatsapp.net",
      "fromMe": false,
      "id": "3EB0A2B5C6D7E8F9"
    },
    "pushName": "João Silva",
    "messageType": "conversation",
    "message": {
      "conversation": "Olá, tenho interesse na automação"
    },
    "status": "PENDING"
  }
}
```

**Extended text messages** (forwarded or formatted text) use a different key:

```json
"message": {
  "extendedTextMessage": {
    "text": "Olá, tenho interesse"
  }
}
```

Workflow 03 handles both formats in the Code node.

---

## 6. remoteJid Format Variants

Evolution API may send JIDs in different formats depending on the WhatsApp client version:

| Format | Example | Handled by Code node |
|--------|---------|---------------------|
| Standard | `244912345678@s.whatsapp.net` | ✅ Pass-through |
| Multi-device | `244912345678:5@s.whatsapp.net` | ✅ Strip `:5` suffix |
| LID (experimental) | `244912345678@lid` | ✅ Replace with `@s.whatsapp.net` |
| Group chat | `120363XXXXXXXXXX@g.us` | ✅ Silently ignored (no `@s.whatsapp.net`) |

Group messages are filtered out because `whatsapp_number` extraction from `@g.us` JIDs produces garbage that will return no Airtable record, causing the workflow to stop silently at the Airtable lookup step.

---

## 7. Common Issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Webhook never fires | Wrong URL or HTTP (not HTTPS) | Verify URL is public HTTPS; check n8n workflow is active |
| `fromMe` messages trigger the bot | Evolution API `fromMe` flag inconsistent | Code node guards against this; no action needed |
| `whatsapp_number` lookup returns nothing | Number format mismatch | Ensure Airtable stores numbers as digits only (no `+`, no spaces) |
| `/qualify` times out | FastAPI service down or `FASTAPI_BASE_URL` wrong | Check `uvicorn` is running; verify env var |
| Slack notification not sent | `SLACK_WEBHOOK_URL` not set | Add the Slack incoming webhook URL to `.env` |
| n8n `airtable-cred` not found | Credential not imported | Create an Airtable Token credential named **Airtable (BMST)** in n8n |
