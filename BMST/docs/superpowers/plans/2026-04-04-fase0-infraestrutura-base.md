# Fase 0 — Infraestrutura Base: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Instalar e configurar Supabase, Langfuse e InvoiceNinja no EasyPanel, criar o schema completo da base de dados, configurar todas as credenciais no n8n e importar o seed inicial de 50 empresas.

**Architecture:** Três serviços self-hosted no EasyPanel via Docker. Supabase serve de CRM + memória + RAG para todos os agentes. Langfuse usa o PostgreSQL do Supabase (base separada). InvoiceNinja usa MariaDB dedicado. Todas as ligações ao n8n via credenciais guardadas no gestor interno.

**Tech Stack:** EasyPanel, Docker, Supabase (PostgreSQL 15 + pgvector), Langfuse, InvoiceNinja, MariaDB 10.11, n8n

---

## Ficheiros deste plano

| Ficheiro | Função |
|---|---|
| `infra/supabase/migrations/001_initial_schema.sql` | Schema completo — executar no Supabase SQL Editor |
| `infra/supabase/seed/empresas_seed_template.csv` | Template CSV para seed inicial de 50 empresas |

---

## Task 1: Instalar Supabase self-hosted no EasyPanel

**Files:**
- Reference: `infra/supabase/migrations/001_initial_schema.sql`

- [ ] **Step 1: Abrir o EasyPanel e ir a Apps → + Create App**

  Seleccionar **Template** no canto superior direito.
  Pesquisar por `Supabase` e seleccionar o template oficial.

- [ ] **Step 2: Preencher as variáveis de ambiente obrigatórias**

  O template pede estas variáveis — gerar valores aleatórios seguros:
  ```
  POSTGRES_PASSWORD=<gerar com: openssl rand -base64 32>
  JWT_SECRET=<gerar com: openssl rand -base64 32>
  ANON_KEY=<JWT com role=anon, assinado com JWT_SECRET>
  SERVICE_ROLE_KEY=<JWT com role=service_role, assinado com JWT_SECRET>
  DASHBOARD_USERNAME=bmst_admin
  DASHBOARD_PASSWORD=<password forte>
  ```

  Para gerar ANON_KEY e SERVICE_ROLE_KEY rapidamente, usar o gerador online:
  https://supabase.com/docs/guides/self-hosting/docker#generate-api-keys

  > Guardar TODAS estas variáveis num ficheiro seguro (ex: password manager).

- [ ] **Step 3: Configurar domínio no EasyPanel**

  No campo Domain do serviço `supabase-studio`, adicionar subdomínio:
  `supabase.seudominio.com` (ou usar o domínio EasyPanel gerado automaticamente).

  Fazer o mesmo para `supabase-kong` (API): `api-supabase.seudominio.com`

- [ ] **Step 4: Fazer Deploy e aguardar containers**

  Clicar em **Deploy**. Aguardar todos os containers ficarem verdes no EasyPanel (~2-3 min).
  Containers esperados: `supabase-db`, `supabase-auth`, `supabase-rest`, `supabase-realtime`,
  `supabase-storage`, `supabase-studio`, `supabase-kong`.

- [ ] **Step 5: Verificar acesso ao Supabase Studio**

  Abrir `https://supabase.seudominio.com` no browser.
  Login com `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD`.
  Resultado esperado: dashboard do Supabase Studio carrega sem erros.

- [ ] **Step 6: Commit**

  ```bash
  git add infra/supabase/
  git commit -m "infra: add Supabase migration and seed template files"
  ```

---

## Task 2: Criar o schema Supabase

**Files:**
- Reference: `infra/supabase/migrations/001_initial_schema.sql`

- [ ] **Step 1: Abrir o SQL Editor no Supabase Studio**

  No Studio: menu lateral → **SQL Editor** → **New Query**.

- [ ] **Step 2: Colar e executar o schema completo**

  Abrir `infra/supabase/migrations/001_initial_schema.sql` e copiar todo o conteúdo.
  Colar no SQL Editor. Clicar em **Run** (ou Ctrl+Enter).

  Resultado esperado: mensagem `Success. No rows returned` para cada statement.

- [ ] **Step 3: Verificar as tabelas criadas**

  No SQL Editor, executar:
  ```sql
  SELECT table_name
  FROM information_schema.tables
  WHERE table_schema = 'public'
  ORDER BY table_name;
  ```

  Resultado esperado (7 tabelas):
  ```
  contactos
  deals
  embeddings
  empresas
  facturas
  mensagens
  projectos
  ```

- [ ] **Step 4: Verificar extensão pgvector**

  ```sql
  SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
  ```

  Resultado esperado:
  ```
  vector | 0.x.x
  ```

- [ ] **Step 5: Testar o trigger de updated_at**

  ```sql
  INSERT INTO empresas (nome, segmento, estado)
  VALUES ('Empresa Teste', 'B', 'prospecto');

  SELECT id, nome, created_at, updated_at FROM empresas WHERE nome = 'Empresa Teste';
  -- created_at e updated_at devem ser iguais

  UPDATE empresas SET nome = 'Empresa Teste Actualizada' WHERE nome = 'Empresa Teste';

  SELECT id, nome, created_at, updated_at FROM empresas WHERE nome = 'Empresa Teste Actualizada';
  -- updated_at deve ser posterior a created_at

  -- Limpar registo de teste
  DELETE FROM empresas WHERE nome = 'Empresa Teste Actualizada';
  ```

---

## Task 3: Instalar Langfuse no EasyPanel

**Files:** nenhum ficheiro novo

- [ ] **Step 1: Criar base de dados `langfuse` no PostgreSQL do Supabase**

  No Supabase SQL Editor:
  ```sql
  CREATE DATABASE langfuse;
  ```

  > Nota: o utilizador `postgres` do Supabase tem permissões para criar bases de dados.

- [ ] **Step 2: No EasyPanel, criar nova App → Template → pesquisar Langfuse**

  Seleccionar o template oficial Langfuse.

- [ ] **Step 3: Preencher as variáveis de ambiente**

  ```
  DATABASE_URL=postgresql://postgres:<POSTGRES_PASSWORD>@supabase-db:5432/langfuse
  NEXTAUTH_URL=https://langfuse.seudominio.com
  NEXTAUTH_SECRET=<gerar com: openssl rand -base64 32>
  SALT=<gerar com: openssl rand -base64 32>
  ```

  > `supabase-db` é o nome interno do container PostgreSQL do Supabase na rede Docker do EasyPanel. Verificar o nome exacto no EasyPanel se necessário.

- [ ] **Step 4: Configurar domínio: `langfuse.seudominio.com`**

  Deploy e aguardar container verde (~1 min).

- [ ] **Step 5: Verificar acesso e criar conta admin**

  Abrir `https://langfuse.seudominio.com`.
  Criar conta com email e password na primeira visita.
  Resultado esperado: dashboard Langfuse carrega, projecto por omissão visível.

- [ ] **Step 6: Obter API Keys do Langfuse**

  No Langfuse: **Settings** → **API Keys** → **Create new API key**.
  Guardar `Public Key` e `Secret Key` — necessários para o n8n na Task 5.

---

## Task 4: Instalar InvoiceNinja + MariaDB no EasyPanel

**Files:** nenhum ficheiro novo

- [ ] **Step 1: No EasyPanel, criar nova App → Template → pesquisar MariaDB**

  Variáveis:
  ```
  MYSQL_ROOT_PASSWORD=<gerar com: openssl rand -base64 32>
  MYSQL_DATABASE=invoiceninja
  MYSQL_USER=ninja
  MYSQL_PASSWORD=<gerar com: openssl rand -base64 16>
  ```

  Nome do serviço: `mariadb-ninja`. Deploy e aguardar verde.

- [ ] **Step 2: No EasyPanel, criar nova App → Template → pesquisar InvoiceNinja**

  Variáveis:
  ```
  APP_URL=https://invoices.seudominio.com
  DB_HOST=mariadb-ninja
  DB_PORT=3306
  DB_DATABASE=invoiceninja
  DB_USERNAME=ninja
  DB_PASSWORD=<password do step 1>
  APP_KEY=<gerar com: php -r "echo base64_encode(random_bytes(32));"> 
  ```

  Domínio: `invoices.seudominio.com`. Deploy e aguardar verde (~2 min).

- [ ] **Step 3: Completar setup inicial do InvoiceNinja**

  Abrir `https://invoices.seudominio.com/setup`.
  Preencher:
  - Company Name: `BMST — Bisca Mais Sistemas e Tecnologias`
  - Email: email do fundador
  - Password: password forte

  Clicar **Submit**.

- [ ] **Step 4: Configurar moedas AOA e USD**

  No InvoiceNinja: **Settings** → **Localization**:
  - Currency: `Angolan Kwanza (AOA)`
  - Timezone: `Africa/Luanda`

  Para adicionar USD como moeda secundária:
  **Settings** → **Currencies** → activar `US Dollar (USD)`.

- [ ] **Step 5: Obter API Token do InvoiceNinja**

  **Settings** → **API Tokens** → **Create Token**.
  Nome: `n8n-agent`. Guardar o token.

---

## Task 5: Configurar credenciais no n8n

**Files:** nenhum ficheiro novo

- [ ] **Step 1: Credencial PostgreSQL (Supabase)**

  No n8n: **Credentials** → **Add Credential** → pesquisar `Postgres`.
  Preencher:
  ```
  Name: Supabase BMST
  Host: supabase-db  (nome interno EasyPanel)
  Database: postgres
  User: postgres
  Password: <POSTGRES_PASSWORD do Task 1>
  Port: 5432
  SSL: desactivado (rede interna Docker)
  ```
  Clicar **Test Connection** → resultado esperado: `Connection tested successfully`.

- [ ] **Step 2: Credencial Langfuse**

  **Add Credential** → `Basic Auth`.
  ```
  Name: Langfuse BMST
  User: <Public Key do Langfuse>
  Password: <Secret Key do Langfuse>
  ```

  > A API Langfuse usa HTTP Basic Auth: Public Key como username, Secret Key como password.
  > Nos nós HTTP Request do n8n: Authentication → Predefined Credential Type → Basic Auth → Langfuse BMST.

- [ ] **Step 3: Credencial InvoiceNinja**

  **Add Credential** → `Header Auth`.
  ```
  Name: InvoiceNinja BMST
  Name (header): X-Ninja-Token
  Value: <API Token do InvoiceNinja>
  ```

- [ ] **Step 4: Credencial Dify**

  **Add Credential** → `Header Auth`.
  ```
  Name: Dify BMST
  Name (header): Authorization
  Value: Bearer <API Key do Dify>
  ```

  > API Key do Dify: no painel Dify → seleccionar a app → API Access → API Key.

- [ ] **Step 5: Credencial Telegram**

  **Add Credential** → `Telegram API`.
  ```
  Name: Telegram BMST Fundador
  Access Token: <Bot Token do BotFather>
  ```

  > Se ainda não tens o bot criado: no Telegram, falar com @BotFather → /newbot → seguir instruções → guardar token.
  > Obter o chat_id pessoal: falar com @userinfobot no Telegram.

---

## Task 6: Testar ligação n8n → Supabase (SELECT + INSERT)

**Files:** nenhum ficheiro novo

- [ ] **Step 1: Criar workflow de teste no n8n**

  **Workflows** → **New Workflow** → nome: `[TESTE] Supabase Connection`.

- [ ] **Step 2: Adicionar nó Manual Trigger**

  Clicar **+** → pesquisar `Manual Trigger` → adicionar.

- [ ] **Step 3: Adicionar nó Postgres — INSERT**

  Clicar **+** após o trigger → pesquisar `Postgres` → adicionar.
  Configurar:
  ```
  Credential: Supabase BMST
  Operation: Insert
  Table: empresas
  Columns: nome, segmento, estado, fonte
  Values:
    nome: "Empresa Teste n8n"
    segmento: "B"
    estado: "prospecto"
    fonte: "teste_n8n"
  ```

- [ ] **Step 4: Adicionar nó Postgres — SELECT**

  Clicar **+** após o INSERT → adicionar outro nó `Postgres`.
  Configurar:
  ```
  Credential: Supabase BMST
  Operation: Execute Query
  Query: SELECT id, nome, estado FROM empresas WHERE fonte = 'teste_n8n'
  ```

- [ ] **Step 5: Executar e verificar**

  Clicar **Test workflow**.
  Resultado esperado no nó SELECT: 1 linha com `nome = "Empresa Teste n8n"` e `estado = "prospecto"`.

- [ ] **Step 6: Limpar registo de teste e apagar workflow**

  No Supabase Studio SQL Editor:
  ```sql
  DELETE FROM empresas WHERE fonte = 'teste_n8n';
  ```

  Apagar o workflow de teste no n8n.

---

## Task 7: Testar ligação n8n → Langfuse (criar trace)

**Files:** nenhum ficheiro novo

- [ ] **Step 1: Criar workflow de teste no n8n**

  **Workflows** → **New Workflow** → nome: `[TESTE] Langfuse Trace`.

- [ ] **Step 2: Adicionar Manual Trigger + nó HTTP Request**

  Configurar o nó HTTP Request:
  ```
  Method: POST
  URL: https://langfuse.seudominio.com/api/public/traces
  Authentication: Predefined Credential Type → Basic Auth → Langfuse BMST
  Body (JSON):
  {
    "name": "teste-n8n",
    "userId": "fundador",
    "metadata": { "agente": "teste", "empresa_id": "000" },
    "input": { "mensagem": "trace de teste do n8n" }
  }
  ```

- [ ] **Step 3: Executar e verificar no Langfuse**

  Executar o workflow.
  No Langfuse dashboard → **Traces** → deve aparecer o trace `teste-n8n`.
  Resultado esperado: trace visível com `userId = fundador`.

- [ ] **Step 4: Apagar workflow de teste**

  Apagar o workflow `[TESTE] Langfuse Trace` no n8n.

---

## Task 8: Importar seed inicial — 50 empresas

**Files:**
- Reference: `infra/supabase/seed/empresas_seed_template.csv`

- [ ] **Step 1: Preparar o CSV com as 50 empresas reais**

  Abrir `infra/supabase/seed/empresas_seed_template.csv`.
  Preencher com as 50 empresas-alvo de Luanda seguindo os critérios:
  - Segmento B: website activo OU presença organizada nas redes
  - Sectores: clínicas, hotéis, retalho, seguradoras, imobiliárias
  - Localização: Talatona, Miramar, Maianga, Alvalade
  - `estado` = `prospecto` em todas
  - `fonte` = `google_maps` ou `instagram`

  Guardar como `infra/supabase/seed/empresas_seed_luanda.csv` (não alterar o template).

- [ ] **Step 2: Importar no Supabase Studio**

  Supabase Studio → **Table Editor** → tabela `empresas` → botão **Insert** → **Import data from CSV**.
  Seleccionar `empresas_seed_luanda.csv`.
  Verificar o mapeamento de colunas → **Import**.

- [ ] **Step 3: Verificar contagem**

  No SQL Editor:
  ```sql
  SELECT COUNT(*) FROM empresas;
  SELECT segmento, COUNT(*) FROM empresas GROUP BY segmento;
  SELECT sector, COUNT(*) FROM empresas GROUP BY sector ORDER BY count DESC;
  ```

  Resultado esperado:
  - `COUNT(*)` = 50
  - Apenas segmento `B` (nenhum A ou C no seed inicial)

- [ ] **Step 4: Commit do CSV preenchido**

  ```bash
  git add infra/supabase/seed/empresas_seed_luanda.csv
  git commit -m "infra: add initial seed of 50 target companies in Luanda"
  ```

---

## Critério de Conclusão da Fase 0

Todos estes pontos devem estar verdes antes de avançar para a Fase 1 (Dify ↔ n8n):

- [ ] Supabase Studio acessível em `supabase.seudominio.com`
- [ ] Schema criado: 7 tabelas + pgvector activo
- [ ] Trigger `updated_at` testado e funcional
- [ ] Langfuse dashboard acessível, trace de teste criado com sucesso via n8n
- [ ] InvoiceNinja acessível, configurado com AOA + Luanda timezone
- [ ] 5 credenciais guardadas no n8n (Postgres, Langfuse, InvoiceNinja, Dify, Telegram)
- [ ] n8n consegue fazer INSERT e SELECT na tabela `empresas`
- [ ] 50 empresas importadas com `estado = 'prospecto'`
