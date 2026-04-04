# Spec — Fase 0: Infraestrutura Base
**Projecto:** BMST — Skeleton Crew (Agentes IA Autónomos)
**Data:** 2026-04-04
**Abordagem escolhida:** B — Stack sem HubSpot
**Estado:** Aprovado

---

## 1. Contexto

A BMST opera no mercado angolano com uma arquitectura de 4 agentes IA autónomos (HUNTER, CLOSER, DELIVERY, LEDGER) orquestrados por n8n. Esta fase estabelece a infraestrutura base que suporta todos os agentes.

**Já configurado:** n8n, Dify (Hostinger), Evolution API
**Stack escolhida:** Supabase self-hosted substitui HubSpot — serve de CRM interno, memória dos agentes e RAG numa única base. Menos serviços = mais fiabilidade para operação solo.

---

## 2. Serviços a Instalar (EasyPanel + Docker)

| Serviço | Imagem | Porta | Depende de |
|---|---|---|---|
| Supabase | Stack oficial supabase/postgres:15 + serviços | 5432 (pg), 8000 (API) | — |
| Langfuse | langfuse/langfuse:latest | 3000 | PostgreSQL do Supabase (base separada) |
| InvoiceNinja | invoiceninja/invoiceninja:latest | 9000 | MariaDB dedicado |
| MariaDB | mariadb:10.11 | 3306 | — |

**Ordem de instalação:**
1. Supabase (base de tudo)
2. Langfuse (usa o PostgreSQL do Supabase, base de dados separada)
3. MariaDB + InvoiceNinja

**Nota:** Supabase self-hosted = ~7 containers (db, auth, rest, realtime, storage, studio, kong). Usar template oficial do EasyPanel.

---

## 3. Schema Supabase

### 3.1 Tabelas

#### `empresas`
Base de prospecção do HUNTER. Regista todas as empresas-alvo e o seu estado no funil.

```sql
CREATE TABLE empresas (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  nome        text NOT NULL,
  sector      text,
  segmento    char(1) CHECK (segmento IN ('A','B','C')),
  website     text,
  whatsapp    text,
  localizacao text,
  n_funcionarios_est int,
  estado      text DEFAULT 'prospecto'
              CHECK (estado IN ('prospecto','contactado','interessado',
                                'neutro','fora_perfil','cliente')),
  fonte       text,
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now()
);

-- Trigger para actualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$ BEGIN NEW.updated_at = now(); RETURN NEW; END; $$ LANGUAGE plpgsql;

CREATE TRIGGER empresas_updated_at
  BEFORE UPDATE ON empresas
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

#### `contactos`
Pessoas de contacto dentro de cada empresa.

```sql
CREATE TABLE contactos (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id uuid REFERENCES empresas(id),
  nome       text,
  cargo      text,
  whatsapp   text,
  email      text,
  created_at timestamptz DEFAULT now()
);
```

#### `deals`
Pipeline comercial gerido pelo CLOSER.

```sql
CREATE TABLE deals (
  id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id              uuid REFERENCES empresas(id),
  contacto_id             uuid REFERENCES contactos(id),
  servico                 text,
  valor_aoa               numeric,
  valor_usd               numeric,
  estado                  text DEFAULT 'novo'
                          CHECK (estado IN ('novo','diagnostico','proposta_enviada',
                                            'negociacao','fechado','perdido')),
  aprovado_pelo_fundador  boolean DEFAULT false,
  data_proposta           date,
  data_fecho              date,
  created_at              timestamptz DEFAULT now()
);
```

#### `mensagens`
Histórico completo de comunicações (WhatsApp/Email) por empresa.

```sql
CREATE TABLE mensagens (
  id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  empresa_id uuid REFERENCES empresas(id),
  direcao    text CHECK (direcao IN ('entrada','saida')),
  canal      text CHECK (canal IN ('whatsapp','email')),
  conteudo   text,
  agente     text CHECK (agente IN ('hunter','closer','delivery','ledger','humano')),
  timestamp  timestamptz DEFAULT now()
);
```

#### `projectos`
Projectos activos geridos pelo DELIVERY.

```sql
CREATE TABLE projectos (
  id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id               uuid REFERENCES deals(id),
  empresa_id            uuid REFERENCES empresas(id),
  nome                  text,
  estado                text DEFAULT 'onboarding'
                        CHECK (estado IN ('onboarding','em_curso','bloqueado','concluido')),
  progresso_pct         int DEFAULT 0 CHECK (progresso_pct BETWEEN 0 AND 100),
  data_inicio           date,
  data_entrega_prevista date,
  created_at            timestamptz DEFAULT now()
);
```

#### `facturas`
Facturação gerida pelo LEDGER, sincronizada com InvoiceNinja.

```sql
CREATE TABLE facturas (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id          uuid REFERENCES deals(id),
  empresa_id       uuid REFERENCES empresas(id),
  valor_aoa        numeric,
  valor_usd        numeric,
  estado           text DEFAULT 'rascunho'
                   CHECK (estado IN ('rascunho','enviada','paga','atrasada')),
  data_emissao     date,
  data_vencimento  date,
  invoice_ninja_id text,
  created_at       timestamptz DEFAULT now()
);
```

### 3.2 pgvector — RAG

```sql
CREATE EXTENSION IF NOT EXISTS vector;

-- Dimensão 1536 = OpenAI text-embedding-ada-002 (default Dify).
-- Ajustar se usares modelo diferente no Dify (ex: 768 para nomic-embed-text).
CREATE TABLE embeddings (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conteudo      text,
  embedding     vector(1536),
  tipo          text CHECK (tipo IN ('empresa','deal','mensagem','documento')),
  referencia_id uuid,
  created_at    timestamptz DEFAULT now()
);

CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops);
```

---

## 4. Ligações n8n → Serviços

Todas as credenciais guardadas no gestor de credenciais do n8n — nenhuma chave em código.

| Serviço | Tipo de Credencial n8n | Campos |
|---|---|---|
| Supabase (PostgreSQL) | Postgres | host (interno EasyPanel), porta 5432, user, password, database |
| Langfuse | HTTP Header Auth | `x-api-key` = Public Key + Secret Key |
| InvoiceNinja | HTTP Header Auth | `X-Ninja-Token` |
| Dify | HTTP Header Auth | `Authorization: Bearer <api-key>` |
| Telegram Bot | Telegram (nativo) | Bot Token |
| Evolution API | Já configurado | — |

**Padrão Langfuse em cada workflow n8n:**
- Início: HTTP POST `/api/public/traces` — abre trace com nome do agente + empresa_id
- Fim: HTTP PATCH `/api/public/traces/{id}` — fecha trace com resultado e duração

**Invocação Dify via n8n:**
```
POST /v1/chat-messages
Authorization: Bearer <api-key>
{ "inputs": {}, "query": "...", "user": "n8n-agent" }
```

---

## 5. Seed Inicial — 50 Empresas-Alvo

**Formato CSV para importação no Supabase Studio:**
```
nome,sector,segmento,website,whatsapp,localizacao,n_funcionarios_est,fonte,estado
```

**Critérios de selecção:**
- Sectores: clínicas privadas, hotéis, retalho organizado, seguradoras, imobiliárias
- Localização: Luanda (Talatona, Miramar, Maianga, Alvalade)
- Segmento B obrigatório: website activo OU presença organizada nas redes sociais
- Todas entram com `estado = 'prospecto'`

**Processo de importação:**
1. Preparar CSV com 50 empresas
2. Supabase Studio → Table Editor → `empresas` → Import CSV

---

## 6. Critério de Conclusão da Fase 0

- [ ] Supabase Studio acessível e schema criado com sucesso
- [ ] Langfuse dashboard acessível, trace de teste criado via n8n
- [ ] InvoiceNinja acessível, configurado com AOA + USD
- [ ] Credenciais de todos os serviços guardadas no n8n
- [ ] 50 empresas importadas na tabela `empresas` com estado `prospecto`
- [ ] n8n consegue fazer SELECT e INSERT na tabela `empresas` via Postgres node
