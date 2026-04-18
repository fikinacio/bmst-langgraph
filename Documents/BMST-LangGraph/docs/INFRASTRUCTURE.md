# Decisão de Infraestrutura — LangGraph BMST Agents
## Análise e Recomendação

---

## Estado Actual

| Serviço | VPS | RAM | Custo est. |
|---|---|---|---|
| Dify (self-hosted) | Hostinger KVM mínimo | ~4GB | ~$5–8/mês |
| n8n + Evolution API + Redis + Supabase | EasyPanel | 4GB | ~$10–15/mês |
| LangGraph agents (a adicionar) | ? | ? | ? |

---

## Opção Recomendada: EasyPanel VPS (mesmo servidor que o n8n)

**Porquê funciona:**
- FastAPI + LangGraph é uma aplicação Python leve — consome ~200–400MB RAM em idle
- 4GB RAM com n8n + Evolution API + Redis usa normalmente ~2–2.5GB → sobra margem
- EasyPanel suporta deploy de aplicações Docker com um clique
- Custo adicional: **$0** — o servidor já está pago

**Arquitectura no EasyPanel:**
```
EasyPanel VPS (4GB RAM)
├── n8n                    ~400MB
├── Evolution API          ~300MB
├── Redis                  ~50MB
├── PostgreSQL             ~200MB
└── bmst-agents (FastAPI)  ~300–500MB
                           ─────────
                           ~1.3–1.5GB total → sobram ~2.5GB ✅
```

**Como fazer o deploy no EasyPanel:**
1. EasyPanel → New Service → App
2. Source: GitHub repo (liga o teu repositório)
3. Build: Dockerfile (que vamos criar)
4. Port: 8000
5. Domain: `agents.biscaplus.com` (Cloudflare DNS → EasyPanel)

---

## E o Hostinger?

O Hostinger a correr apenas Dify é desperdício se o plano mínimo custa $5–8/mês só para isso.

**Opção A — Manter como está**
Dify no Hostinger, LangGraph no EasyPanel. Simples, sem migração.

**Opção B — Migrar Dify para o EasyPanel e cancelar Hostinger**
- Poupa $5–8/mês
- Risco: EasyPanel fica com 3–3.5GB utilizados → pouco margem
- Só recomendado quando tiveres LangGraph estável e Dify for secundário

**Decisão agora:** Manter Hostinger + adicionar LangGraph no EasyPanel.
Revisar em 3 meses quando o LangGraph estiver em produção.

---

## Alternativas Mais Baratas (para referência futura)

| Fornecedor | Plano | RAM | CPU | Custo/mês | Notas |
|---|---|---|---|---|---|
| **Hetzner CX22** | VPS | 4GB | 2 vCPU | €4.35 | Melhor preço/perf Europa |
| **Contabo VPS S** | VPS | 8GB | 4 vCPU | €5.99 | Muito RAM por este preço |
| **Railway.app** | Starter | variável | variável | $5 créditos | Ideal para FastAPI dev |
| **Render.com** | Free → Starter | 512MB→2GB | shared | $0→$7 | Bom para portfólio público |

**Recomendação para o portfólio GitHub:**
Usar **Render.com** para o deploy público do projecto LangGraph. É gratuito, tem URL público, e impressiona em entrevistas de AI Engineer — qualquer recrutador pode testar a API ao vivo.

---

## Setup de Rede Final

```
                    Cloudflare DNS
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
  dify.biscaplus.com  n8n.biscaplus.com  agents.biscaplus.com
         │               │               │
   Hostinger VPS    EasyPanel VPS    EasyPanel VPS
      (Dify)          (n8n)           (FastAPI/LangGraph)
                         │               │
                    Evolution API    Claude API
                    Redis            Supabase
                    PostgreSQL       Langfuse
```

Todos os serviços internos comunicam via Docker network interna no EasyPanel — sem exposição desnecessária à internet.
