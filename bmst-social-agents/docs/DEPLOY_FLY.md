# Deploy no Fly.io — bmst-social-agents

Guia passo a passo para colocar o pipeline em produção no Fly.io usando a conta existente
(app `lusambu` já activo na região `cdg`).

---

## Pré-requisitos

| Requisito | Verificação |
|-----------|-------------|
| `flyctl` instalado | `fly version` → v0.2+ |
| Sessão activa | `fly auth whoami` → mostra o teu email |
| Redis Upstash disponível | `fly redis list` → pelo menos uma instância listada |
| Repo clonado e no directório `bmst-social-agents/` | `ls fly.toml` → ficheiro presente |

Se o `flyctl` não estiver instalado:
```bash
# macOS / Linux
curl -L https://fly.io/install.sh | sh

# Windows (PowerShell)
iwr https://fly.io/install.ps1 -useb | iex
```

---

## Passo 1 — Criar a app no Fly.io

A primeira vez, cria a app usando o nome definido em `fly.toml`:

```bash
fly apps create bmst-social-agents --region cdg
```

Confirma que a app foi criada:
```bash
fly apps list | grep bmst-social-agents
```

---

## Passo 2 — Configurar os secrets

Copia `.fly/secrets.example` para um ficheiro local (não commitado), preenche os valores reais
e importa para o Fly.io. **Nunca commites o ficheiro com valores reais.**

```bash
cp .fly/secrets.example .fly/secrets.local
# Edita .fly/secrets.local com os valores reais
fly secrets import < .fly/secrets.local
```

Ou define cada secret individualmente:

```bash
fly secrets set \
  ANTHROPIC_API_KEY="sk-ant-api03-..." \
  BMST_API_KEY="$(openssl rand -hex 32)" \
  SUPABASE_URL="https://xxxx.supabase.co" \
  SUPABASE_SERVICE_KEY="eyJ..." \
  EVOLUTION_API_URL="https://evolution.example.com" \
  EVOLUTION_API_KEY="..." \
  EVOLUTION_INSTANCE="biscaplus" \
  REVISOR_APPROVER_PHONE="+41795748225" \
  APP_ENV="production" \
  TAVILY_API_KEY="tvly-..." \
  GPTZERO_API_KEY="..." \
  CANVA_API_TOKEN="..." \
  CANVA_BRAND_KIT_ID="..." \
  CANVA_TEMPLATE_ID="..." \
  LINKEDIN_CLIENT_ID="..." \
  LINKEDIN_CLIENT_SECRET="..." \
  LINKEDIN_ACCESS_TOKEN="..." \
  LINKEDIN_ORG_URN="urn:li:organization:..." \
  INSTAGRAM_ACCESS_TOKEN="..." \
  INSTAGRAM_ACCOUNT_ID="..." \
  FACEBOOK_PAGE_ID="..."
```

Verifica os secrets definidos (valores são ocultados):
```bash
fly secrets list
```

> **Nota sobre `REVISOR_APPROVER_PHONE`:** deve estar em formato E.164 — `+` seguido de 7 a 15
> dígitos (ex: `+41795748225`). O validador da app rejeita qualquer outro formato.

---

## Passo 3 — Attach ao Redis Upstash

Este comando cria o secret `REDIS_URL` automaticamente com o URL `rediss://` (TLS) correcto.
**Não definas `REDIS_URL` manualmente.**

Lista as instâncias Redis disponíveis:
```bash
fly redis list
```

Faz attach à instância existente (substitui `<redis-name>` pelo nome real):
```bash
fly redis attach <redis-name> --app bmst-social-agents
```

Confirma que o secret foi criado:
```bash
fly secrets list | grep REDIS_URL
```

---

## Passo 4 — Primeiro deploy

```bash
fly deploy --app bmst-social-agents
```

O Fly.io irá:
1. Construir a imagem usando `Dockerfile.fly`
2. Lançar 1 máquina para o processo `api`
3. Verificar o health check em `GET /health` (porta 8080)

O deploy demora tipicamente 2–4 minutos na primeira vez (instalação de dependências Python).

---

## Passo 5 — Escalar o processo scheduler

Após o primeiro deploy, o processo `scheduler` existe na configuração mas precisa de uma
máquina atribuída:

```bash
fly scale count scheduler=1 --region cdg --app bmst-social-agents
```

Verifica que ambos os processos têm máquinas activas:
```bash
fly status --app bmst-social-agents
```

Deves ver algo como:
```
Machines
ID       PROCESS    VERSION  REGION  STATE    ROLE
...      api        1        cdg     started
...      scheduler  1        cdg     started
```

---

## Passo 6 — Verificar o deploy

### Health check

```bash
curl https://bmst-social-agents.fly.dev/health
# {"status": "ok", "env": "production"}
```

### Logs em tempo real

```bash
# Todos os processos
fly logs --app bmst-social-agents

# Apenas o scheduler
fly logs --app bmst-social-agents --instance <scheduler-machine-id>
```

### Estado completo

```bash
fly status --app bmst-social-agents
```

### Testar o trigger manual

```bash
curl -X POST https://bmst-social-agents.fly.dev/run/manual \
  -H "X-API-Key: $BMST_API_KEY"
# {"session_id": "...", "status": "started"}
```

### Verificar estado de um run

```bash
curl https://bmst-social-agents.fly.dev/runs/<session_id> \
  -H "X-API-Key: $BMST_API_KEY"
```

---

## Passo 7 — Aplicar o schema Supabase (primeira vez)

Se ainda não aplicaste o schema na base de dados:

```bash
psql "$DATABASE_URL" < infra/supabase/schema.sql
```

Ou via Supabase CLI:
```bash
supabase db push --linked
```

Ou copia o conteúdo de `infra/supabase/schema.sql` para o SQL Editor do Supabase.

---

## Passo 8 — Configurar o webhook no Evolution API

Após o deploy, configura o Evolution API para enviar as respostas de aprovação WhatsApp
para o endpoint correcto:

**Webhook URL:**
```
https://bmst-social-agents.fly.dev/webhook/whatsapp
```

No painel do Evolution API:
1. Abre a instância `biscaplus`
2. Vai a **Webhook** → Events
3. Define o URL acima
4. Activa o evento `MESSAGES_UPSERT`

---

## Passo 9 — Domínio customizado (opcional)

```bash
fly certs create api.bmst.ao --app bmst-social-agents
```

Segue as instruções para adicionar o registo DNS CNAME. O certificado TLS é emitido
automaticamente via Let's Encrypt.

---

## Operações do dia-a-dia

### Redeploy após push

```bash
# Deploy manual
fly deploy --app bmst-social-agents

# Ou configura CI/CD: o GitHub Actions em .github/workflows/test.yml
# pode ser extendido com um job de deploy após os testes passarem.
```

### Rollback para a versão anterior

```bash
fly releases --app bmst-social-agents   # lista releases
fly deploy --image registry.fly.io/bmst-social-agents:<versao-anterior>
```

### Actualizar um secret sem redeploy

```bash
fly secrets set ANTHROPIC_API_KEY="novo-valor" --app bmst-social-agents
```

### Ver e escalar máquinas

```bash
fly scale show --app bmst-social-agents
fly scale count api=1 scheduler=1 --region cdg --app bmst-social-agents
```

### SSH na máquina api

```bash
fly ssh console --app bmst-social-agents --process-group api
```

---

## Troubleshooting

### Deploy falha na build: `No module named 'src'`

Verifica que `pyproject.toml` e `src/` estão presentes no contexto de build:
```bash
fly deploy --verbose --app bmst-social-agents
```
O Dockerfile.fly copia `pyproject.toml` e `src/` antes do `pip install .`.

### Health check falha: timeout

O FastAPI leva alguns segundos a iniciar (setup do checkpointer Redis + Supabase).
O health check tem `grace_period = "30s"` — aguarda esse período antes de reportar falha.
Se persistir, verifica os logs:
```bash
fly logs --app bmst-social-agents
```

### `REDIS_URL must start with redis:// or rediss://`

O secret `REDIS_URL` não foi definido. Repete o Passo 3:
```bash
fly redis attach <redis-name> --app bmst-social-agents
```

### `revisor_approver_phone must be E.164 format`

O número de telefone não tem o `+` inicial ou tem formato errado. Corrige:
```bash
fly secrets set REVISOR_APPROVER_PHONE="+41795748225" --app bmst-social-agents
```

### Scheduler não dispara

1. Confirma que a máquina está activa: `fly status --app bmst-social-agents`
2. Se a máquina não existe: `fly scale count scheduler=1 --region cdg`
3. Verifica o cron expression: `fly secrets list | grep SCHEDULER_CRON`
4. O cron está em UTC — `0 7 * * 1-5` = 07:00 UTC = 08:00 Luanda (WAT = UTC+1)

### WhatsApp: mensagens de aprovação não chegam

1. Verifica se o webhook do Evolution API aponta para `https://bmst-social-agents.fly.dev/webhook/whatsapp`
2. Testa o endpoint manualmente:
   ```bash
   curl -X POST https://bmst-social-agents.fly.dev/webhook/whatsapp \
     -H "Content-Type: application/json" \
     -d '{"data":{"key":{"remoteJid":"351900000000@s.whatsapp.net"},"message":{"conversation":"teste"}}}'
   ```

---

## Custos estimados (Fly.io shared-cpu-1x 512mb)

| Recurso | Custo estimado |
|---------|----------------|
| api (1 máquina, sempre activa) | ~$1.94/mês |
| scheduler (1 máquina, sempre activa) | ~$1.94/mês |
| Upstash Redis (Free tier: 256mb) | $0/mês |
| Tráfego de saída (primeiros 100GB) | $0/mês |
| **Total estimado** | **~$4/mês** |

Preços actualizados em [fly.io/pricing](https://fly.io/pricing).
