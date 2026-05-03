# Landing Page — BMST Acquisition Engine

Single-file lead-capture form deployed on Vercel at `audit.biscaplus.com`.

## How it works

1. Visitor fills in Nome, Empresa, Setor, and WhatsApp number.
2. On submit, the form POSTs JSON to the n8n inbound webhook.
3. On success, the browser redirects to a WhatsApp deep link with a pre-filled
   message addressed to the BMST business number.

---

## Deploy to Vercel

### 1. Import the repository

In the Vercel dashboard → **Add New Project** → import `bmst-acquisition-engine`
from GitHub.

Set the **Root Directory** to `landing_page` (or deploy the full repo and configure
the output directory).

### 2. Set environment variables

In **Project Settings → Environment Variables**, add:

| Variable | Value |
|----------|-------|
| `NEXT_PUBLIC_N8N_WEBHOOK_URL` | `https://your-n8n.com/webhook/inbound` |
| `BMST_WHATSAPP_NUMBER` | `244XXXXXXXXX` (digits only, no +) |

### 3. Configure the build command

The HTML file uses `%%NEXT_PUBLIC_N8N_WEBHOOK_URL%%` as a placeholder that is
replaced at build time. Add the following to `vercel.json` at the repo root:

```json
{
  "buildCommand": "sed -i 's|%%NEXT_PUBLIC_N8N_WEBHOOK_URL%%|'\"$NEXT_PUBLIC_N8N_WEBHOOK_URL\"'|g' landing_page/index.html && sed -i 's|244942000000|'\"$BMST_WHATSAPP_NUMBER\"'|g' landing_page/index.html",
  "outputDirectory": "landing_page",
  "framework": null
}
```

> **Note:** On macOS/BSD `sed -i` requires an empty string argument: `sed -i '' ...`.
> The command above uses the Linux syntax that Vercel's build environment expects.

### 4. Deploy

Push to `main`. Vercel will build and deploy automatically.

---

## Configure the CNAME subdomain (audit.biscaplus.com)

### Step 1 — Add domain in Vercel

In **Project Settings → Domains**, click **Add**, type `audit.biscaplus.com`,
and confirm.

Vercel will show you the required DNS record.

### Step 2 — Add CNAME in your DNS provider

| Type | Name | Value |
|------|------|-------|
| CNAME | `audit` | `cname.vercel-dns.com` |

DNS propagation typically takes 5–30 minutes.

### Step 3 — Verify

Visit `https://audit.biscaplus.com` — you should see the landing page with a
valid SSL certificate issued by Vercel.

---

## Local testing

```bash
# Serve the file locally (Python built-in server)
cd landing_page
python -m http.server 3000
# Open http://localhost:3000

# Before testing the form, replace the placeholder in a local copy:
WEBHOOK_URL="https://your-n8n.com/webhook/inbound"
sed 's|%%NEXT_PUBLIC_N8N_WEBHOOK_URL%%|'"$WEBHOOK_URL"'|g' index.html > index_local.html
open index_local.html   # macOS
```

---

## Performance notes

- No external CDN dependencies (fonts, icons, analytics).
- All CSS is inlined — single HTTP request to load the page.
- Target: < 2 s First Contentful Paint on 3G (Lighthouse throttling).
