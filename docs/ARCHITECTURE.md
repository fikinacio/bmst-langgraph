# Guia de Arquitectura Técnica — BMST Angola
## n8n + LangGraph: Como os dois trabalham juntos

---

## A Separação de Responsabilidades

```
┌─────────────────────────────────────────────────────────────┐
│                        n8n                                   │
│  "Sistema Nervoso" — conecta, roteia, executa               │
│                                                             │
│  • Recebe webhooks (WhatsApp, Telegram, Evolution API)      │
│  • Executa schedules (rotinas diárias)                      │
│  • Chama APIs externas (Google Maps, HubSpot, Notion)       │
│  • Chama agentes LangGraph via HTTP POST (FastAPI)          │
│  • Envia respostas ao canal correcto                        │
│  • Gere aprovações humanas via Telegram (webhook de retorno)│
│  • Gere estado e cache via Redis                            │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP POST  (X-API-Key)
┌──────────────────────────▼──────────────────────────────────┐
│                  FastAPI + LangGraph                         │
│  "Cérebro" — raciocina, decide, gera                        │
│                                                             │
│  • Recebe contexto do n8n via request body                  │
│  • Executa o grafo de estados do agente correcto            │
│  • Consulta knowledge bases via Supabase pgvector (RAG)     │
│  • Aplica regras de negócio em cada nó do grafo             │
│  • Raciocina com Claude API (Haiku ou Sonnet)               │
│  • Pausa execução para aprovação humana via interrupt()     │
│  • Devolve JSON estruturado com dois blocos separados       │
└─────────────────────────────────────────────────────────────┘
```

O n8n não sabe o que corre por trás do endpoint. Chama `/hunter`, `/closer`, `/delivery` ou `/ledger` exactamente como chamaria qualquer outra API. Isto significa que a implementação dos agentes pode evoluir sem tocar nos workflows do n8n.

---

## Fluxo Completo: Mensagem WhatsApp de Prospect

```
1. Prospect envia mensagem WhatsApp
       ↓
2. Evolution API recebe e dispara webhook para o n8n
       ↓
3. n8n recebe webhook
   → Extrai número de telefone e texto da mensagem
   → Consulta Supabase: lead novo ou existente?
   → Determina qual agente deve responder (HUNTER ou CLOSER)
       ↓
4. n8n faz HTTP POST para FastAPI
   → URL: https://agents.biscaplus.com/hunter
   → Body: { empresa, sector, phone, decisor, mensagem_cliente }
   → Header: X-API-Key
       ↓
5. LangGraph executa o grafo do HUNTER:
   → Nó "qualificar": chama Claude Haiku, classifica em Seg A/B/C
   → Router: decide próximo nó com base no segmento
   → Nó "gerar_mensagem": chama Claude Haiku, gera dois blocos
   → Devolve JSON com MENSAGEM_CLIENTE e NOTA_INTERNA
       ↓
6. n8n processa a resposta:
   → Faz split pelo separador "---"
   → MENSAGEM_CLIENTE → Evolution API → WhatsApp do prospect
   → NOTA_INTERNA → Telegram Bot → fundador
   → Actualiza estado do lead no Supabase
   → Actualiza deal no HubSpot
```

---

## Fluxo de Aprovação de Proposta (interrupt + Telegram)

O LangGraph `interrupt()` pausa o grafo do CLOSER e aguarda resposta do fundador. O n8n gere o ciclo completo de aprovação.

```
CLOSER gera rascunho de proposta
       ↓
LangGraph atinge o nó interrupt()
   → Pausa execução e guarda estado no checkpointer (PostgreSQL)
   → Devolve ao n8n: { status: "awaiting_approval", thread_id, rascunho }
       ↓
n8n envia rascunho ao fundador via Telegram
   → Botões inline: [✅ Aprovar] [❌ Rejeitar] [✏️ Editar]
       ↓
Fundador clica num botão
       ↓
Telegram dispara webhook de retorno ao n8n
       ↓
n8n retoma o grafo via HTTP POST para FastAPI
   → URL: https://agents.biscaplus.com/closer/resume
   → Body: { thread_id, decisao: "aprovar" | "rejeitar" | "editar" }
       ↓
LangGraph retoma a partir do ponto de interrupção:
   → Se aprovar: gera PDF via Gotenberg → envia ao cliente via WhatsApp
   → Se rejeitar: regista e notifica fundador
   → Se editar: aguarda novas instruções via Telegram
```

---

## Estrutura dos Endpoints FastAPI

```
POST /hunter                   Qualifica prospect e gera mensagem
POST /hunter/batch             Processa até 20 prospects em paralelo
POST /closer/diagnose          Inicia conversa de diagnóstico
POST /closer/propose           Gera proposta (dispara interrupt)
POST /closer/resume            Retoma após aprovação humana
POST /delivery/start           Inicia gestão de projecto
POST /delivery/update          Gera actualização semanal
POST /ledger/invoice           Emite factura
POST /ledger/check-payments    Verifica pagamentos em atraso
POST /ledger/monthly-report    Gera relatório mensal
GET  /health                   Estado dos serviços
GET  /metrics                  Métricas operacionais
```

---

## Formato de Output dos Agentes

Todos os agentes devolvem o mesmo formato base:

```json
{
  "mensagem_cliente": "Texto limpo para WhatsApp (sem metadados)",
  "nota_interna": "Informação estruturada para Telegram do fundador",
  "segmento": "B",
  "proxima_acao": "send_message | archive | escalate | awaiting_approval",
  "qualificado": true,
  "erro": null
}
```

O `mensagem_cliente` vai directamente ao WhatsApp do prospect.
O `nota_interna` vai ao Telegram do fundador.
Os dois nunca se misturam.

---

## Schema Supabase

```sql
-- Leads e Prospects
CREATE TABLE leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_number TEXT UNIQUE NOT NULL,
  empresa TEXT,
  sector TEXT,
  segmento TEXT CHECK (segmento IN ('A','B','C')),
  decisor TEXT,
  estado TEXT DEFAULT 'novo',
  agente_atual TEXT DEFAULT 'HUNTER',
  lg_thread_id TEXT,        -- ID do thread LangGraph para retomar grafos
  hubspot_deal_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Propostas
CREATE TABLE propostas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  lead_id UUID REFERENCES leads(id),
  servico TEXT NOT NULL,
  valor_aoa NUMERIC NOT NULL,
  estado TEXT DEFAULT 'rascunho',
  aprovada_por TEXT,
  aprovada_em TIMESTAMPTZ,
  pdf_url TEXT,
  validade_ate DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Projectos
CREATE TABLE projectos (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  proposta_id UUID REFERENCES propostas(id),
  empresa TEXT NOT NULL,
  servico TEXT NOT NULL,
  valor_total_aoa NUMERIC NOT NULL,
  adiantamento_recebido BOOLEAN DEFAULT FALSE,
  saldo_recebido BOOLEAN DEFAULT FALSE,
  fase_atual TEXT DEFAULT 'onboarding',
  data_inicio DATE,
  data_entrega_prevista DATE,
  data_entrega_real DATE,
  notion_workspace_url TEXT,
  estado TEXT DEFAULT 'ativo',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Facturas
CREATE TABLE facturas (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  projecto_id UUID REFERENCES projectos(id),
  tipo TEXT CHECK (tipo IN ('adiantamento','saldo','retainer','outro')),
  valor_aoa NUMERIC NOT NULL,
  estado TEXT DEFAULT 'emitida',
  data_emissao DATE DEFAULT CURRENT_DATE,
  data_vencimento DATE,
  data_pagamento DATE,
  invoice_ninja_id TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Nota: a coluna `lg_thread_id` substitui o `dify_conversation_id` anterior. Guarda o `thread_id` do LangGraph para que o n8n possa retomar grafos pausados em `interrupt()`.

---

## Variáveis de Ambiente

```env
# Evolution API (WhatsApp)
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=[SEU_KEY]
EVOLUTION_INSTANCE=bmst_angola

# FastAPI / LangGraph Agents
AGENTS_BASE_URL=https://agents.biscaplus.com
AGENTS_API_KEY=[SEU_KEY_INTERNO]

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Telegram
TELEGRAM_BOT_TOKEN=[SEU_TOKEN]
TELEGRAM_CHAT_ID=[SEU_CHAT_ID]

# Supabase
SUPABASE_URL=[SEU_URL]
SUPABASE_KEY=[SEU_KEY]

# Redis
REDIS_URL=redis://localhost:6379

# HubSpot
HUBSPOT_TOKEN=[SEU_TOKEN]

# InvoiceNinja
INVOICE_NINJA_URL=http://localhost:9000
INVOICE_NINJA_KEY=[SEU_KEY]

# Notion
NOTION_TOKEN=[SEU_TOKEN]
NOTION_DB_PROJECTOS=[DATABASE_ID]

# Gotenberg (PDFs)
GOTENBERG_URL=http://localhost:3001

# Langfuse (observabilidade)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

---

## Ordem de Implementação

```
Semana 1-2:
  □ Configurar Telegram Bot e testar notificações no n8n
  □ Criar schema Supabase (tabelas acima)
  □ Deploy do bmst-agents (FastAPI) no EasyPanel
  □ Testar endpoint GET /health a partir do n8n

Semana 3-4:
  □ Integrar Evolution API com n8n (webhook de entrada WhatsApp)
  □ Workflow: WA recebido → HTTP POST /hunter → split output → WA enviado + Telegram
  □ Activar seed de 50 empresas-alvo no Supabase
  □ Testar ciclo completo end-to-end com número real

Semana 5-6:
  □ Activar endpoint /closer/propose com fluxo de aprovação
  □ Workflow n8n: lead qualificado → /closer/diagnose → /closer/propose
  □ Implementar ciclo de interrupt: Telegram → webhook → /closer/resume
  □ Integrar Gotenberg para geração de PDF da proposta

Semana 7-8:
  □ Activar endpoints /delivery e /ledger
  □ Workflow: projecto criado → actualizações 2x/semana automáticas
  □ Workflow: factura emitida → lembretes automáticos de pagamento
  □ Relatório semanal automático (sábado 08h00 → Telegram)
```
