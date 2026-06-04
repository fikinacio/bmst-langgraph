# PLANO SEMANAL BMST — W22 (25–29 Mai 2026)

> Gerado por: ATLAS | Data: 2026-05-25 | W22 — segunda-feira
> Semana de recuperação após W21 sem execução. Foco: novas actividades comerciais + encerramento controlado Clínica Vitória.
> **Actualizado: 2026-05-29 (sexta-feira) — D5 da semana — FECHO W22 + ARRANQUE PLANO COMERCIAL**

---

## Situação de entrada

| Indicador | Estado |
|-----------|--------|
| Instância WhatsApp `biscaplus` | ✅ Activa — credencial nova validada |
| Email Resend (nexus@biscaplus.com) | ✅ Activa |
| LinkedIn — access token | 🆕 NOVO em W22 — pronto para publicar via `bmst-linkedin-publish` |
| Servidor EasyPanel | ✅ Actualizado 2026-05-19 |
| Clínica Vitória (BMST-PROJ-001) | ❌ DESCARTADO — confirmado demo data em 2026-05-25, removido do pipeline |
| Leads no pipeline | 30 total — 9 contactados sem resposta, 3 top score 8 ainda virgens |
| Receita confirmada Maio | USD 0 (Clínica Vitória era demo, não houve recebimento real) |
| Meta Maio | Adiada para Junho — fechar 1 contrato Segmento B até 30 Jun 2026 |
| Infra Op B | FastAPI inbound webhook a construir esta semana (FORGE) |

---

## Prioridades da semana

### 🔴 CRÍTICO

| # | Agente | Tarefa | Prazo | Tipo | Estado W22 |
|---|--------|--------|-------|------|------------|
| 1 | FORGE | Construir `bmst-workspace/api/` — FastAPI inbound webhook Evolution API (receber respostas WhatsApp do CEO suíço), deploy Fly.io. Substitui dependência n8n para aprovações. | Qui 28 Mai | ✅ | ✅ Construído + deploy Fly.io 27 Mai — bmst-api.fly.dev activo |
| 2 | CLOSER | Primeiro contacto Fresmart — Grupo Newaco (COM-001, score 8) | Ter 26 Mai | ⏳ CEO | ✅ Email enviado 25 Mai (Resend) — follow-up Sex 29 Mai |
| 3 | CLOSER | Primeiro contacto ACE Audit Consulting (SRV-001, score 8) | Qua 27 Mai | ⏳ CEO | ✅ Email enviado 25 Mai (Resend) — follow-up Sex 29 Mai |
| 4 | CLOSER | Primeiro contacto Multipessoal Angola (SRV-002, score 8) | Qua 27 Mai | ⏳ CEO | ✅ Email enviado 25 Mai (Resend) — follow-up Sex 29 Mai |

---

### 🟠 ALTA

| # | Agente | Tarefa | Prazo | Tipo | Estado W22 |
|---|--------|--------|-------|------|------------|
| 5 | CLOSER | Follow-up com os 9 leads contactados sem resposta: Visão Magna, LTI, MD Clinic Angola, Alimenta Angola, Zopo, Real Express, EDACO, Labuta + 1 a confirmar canal. | Qui 28 Mai | ⏳ CEO | ✅ Parcial — 5 enviados 25 Mai (Visão Magna/LTI/Zopo/MD Clinic WA + Alimenta email) + Labuta LinkedIn invite 26 Mai. Bloqueados: Real Express (sem perfil LI), EDACO (Instagram 401 → email pendente aprovação), Adilson/Connectis (URL LI) |
| 6 | VOICE | Calendário de conteúdo W22 — 5 posts (LinkedIn 3 + Instagram 2). Tema central: automação no comércio + caso de estudo Vamos Longe (turismo) | Ter 26 Mai | ✅ | ✅ Calendário criado 28 Mai — 3 LI prontos + 1 IG (aguarda imagem) |
| 7 | VOICE | Publicar primeiro post no novo LinkedIn token — caso de estudo Vamos Longe (sem valores) — valida pipeline LinkedIn Publisher | Qua 27 Mai | ⏳ CEO | ✅ Publicado 27 Mai via Buffer GraphQL — CEO editou manualmente (post sem acentos corrigido) |
| 8 | HUNTER | Prospecção Finanças e Seguros — 5 leads Seg B em Luanda (seguradoras, corretoras, gestoras de activos) | Sex 29 Mai | ✅ | ✅ FIN-001 a FIN-005 prospectados (W21, válidos) — adicionados ao pipeline 27 Mai |
| 9 | FORGE | Validar webhook `bmst-linkedin-publish` + `bmst-instagram-publish` Buffer. Reportar estado 4 webhooks | Ter 26 Mai | ✅ | ❌ 4 webhooks n8n = 404 (offline). Buffer API = 401/400. LinkedIn via Buffer bloqueado. |

---

### 🟡 MÉDIA

| # | Agente | Tarefa | Prazo | Tipo | Estado W22 |
|---|--------|--------|-------|------|------------|
| 10 | HUNTER | Prospecção Telecomunicações — 5 leads Seg B (operadoras, ISPs, distribuidores de equipamento) | Sex 29 Mai | ✅ | ✅ TEL-001 a TEL-005 prospectados 26 Mai — CONNECTIS (score 9) já contactado 26 Mai |
| 11 | SCOUT | Monitorização Genesis.ao + actualização concorrentes Angola. Capturar movimentos ANGOTIC 2026 | Qui 28 Mai | ✅ | ✅ Concluído 28 Mai — relatório `reports/scout-genesis-angotic-2026-05-28.md` |
| 12 | LEDGER | Actualizar `finances/estado-financeiro-2026-05.md` — Maio USD 0, projecção Junho | Ter 26 Mai | ✅ | ✅ Actualizado 25 Mai |
| 13 | VOICE | Posts educativos genéricos sobre automação no comércio e logística (sem mencionar clientes) | Qui 28 Mai | ✅ | ✅ Post publicado 28 Mai — "WhatsApp que não escala" (post_id `6a1783f...`) |

---

### 🟢 BAIXA

| # | Agente | Tarefa | Prazo | Tipo |
|---|--------|--------|-------|------|
| 14 | CLOSER | Rascunho interno de proposta para Fresmart (COM-001) — antecipar caso de resposta positiva ainda esta semana | Sex 29 Mai | ✅ |
| 15 | EDITOR | Revisão final de todos os textos antes de envio (mensagens, posts, email Clínica) — score IA < 65% | Contínuo | ✅ |

---

## Estado do pipeline comercial

### Pipeline Comercial
- **30 leads** — 9 contactados sem resposta confirmada, 21 por contactar
- **Top 3 por contactar (foco W22):** Fresmart (8), ACE Audit (8), Multipessoal (8)
- **Follow-ups pendentes:** Visão Magna, LTI, MD Clinic, Alimenta, Zopo, Real Express, EDACO, Labuta
- **Meta revista:** Fechar 1 contrato Seg B até 30 Jun 2026

### Projecto em pausa
- Clínica Vitória (BMST-PROJ-001) — retoma prevista Jul 2026 — USD 1.250 mantido como crédito

---

## Acções CEO (Fidel) ⏳ — Estado 27 Mai

| # | Prioridade | Acção | Estado |
|---|-----------|-------|--------|
| 1 | ~~🔴 CRÍTICO~~ | ~~Aprovar mensagem KEEPER ao Dr. António Mendes — pausa Clínica Vitória~~ | ✅ Removido — Clínica Vitória era demo |
| 2 | ~~🔴 CRÍTICO~~ | ~~Aprovar 3 primeiros contactos: Fresmart, ACE Audit, Multipessoal~~ | ✅ Enviados 25 Mai via Resend |
| 3 | ~~🟠 ALTA~~ | ~~Aprovar follow-ups: 9 leads em silêncio~~ | ✅ 5 de 9 enviados — restantes bloqueados (canal) |
| 4 | 🟠 ALTA | Aprovar post LinkedIn caso Vamos Longe + resolver Buffer API | ⏳ Post em chat aguarda decisão |
| 5 | 🟠 ALTA | **NOVO** Aprovar email EDACO (info@edaco.org) — alternativa ao Instagram bloqueado | ⏳ Aguarda decisão CEO |
| 6 | 🟡 MÉDIA | **NOVO** Activar n8n workflows (4 workflows offline) — ou aguardar deploy FastAPI | ⏳ FastAPI construído, deploy EasyPanel pendente |
| 7 | 🟡 MÉDIA | **NOVO** Confirmar URL LinkedIn perfil Real Express Angola (Director Geral/Comercial) | ⏳ Bloqueador CLOSER |
| 8 | 🟡 MÉDIA | **NOVO** Confirmar URL LinkedIn perfil Adilson Costa (Connectis — Director Comercial) | ⏳ Bloqueador CLOSER |

---

## Infra W22 — estado actualizado 27 Mai

| Item | Estado | Acção |
|------|--------|-------|
| Evolution API — instância `biscaplus` | ✅ Activa | — |
| Resend — `nexus@biscaplus.com` | ✅ Activa | — |
| n8n — 4 webhooks | ❌ Offline (404) | CEO activa manualmente OU aguarda deploy FastAPI |
| Buffer API — LinkedIn Publisher | ❌ HTTP 401 (OIDC token) | CEO confirma endpoint correcto no dashboard Buffer |
| Buffer API — Instagram Publisher | ❌ HTTP 401 (mesmo token) | Mesmo bloqueador que LinkedIn |
| Unipile — LinkedIn DMs | ✅ Activo (validado 26 Mai) | — |
| FastAPI `bmst-api` (Fly.io) | ✅ Produção — bmst-api.fly.dev | — |
| Scheduler `bmst-scheduler` (Fly.io) | ✅ A correr — 08:00 UTC | Volume `schedule_data` com queue.json |

---

## Métricas W22

| Métrica | Meta | Responsável |
|---------|------|-------------|
| Primeiro contacto novos leads | 3 (Fresmart, ACE Audit, Multipessoal) | CLOSER |
| Follow-ups processados | 8-9 leads | CLOSER |
| Mensagem pausa Clínica enviada | Sim | KEEPER |
| Leads Finanças prospectados | 5 | HUNTER |
| Leads Telecomunicações prospectados | 5 | HUNTER |
| Posts W22 publicados | 5/5 | VOICE |
| Webhooks validados (4 canais) | Sim | FORGE |
| Estado financeiro Maio actualizado | Sim | LEDGER |

---

## Delegação por agente — resumo W22

| Agente | Foco W22 | Dependência CEO |
|--------|---------|----------------|
| KEEPER | Encerramento controlado Clínica Vitória (pausa) | Aprovação mensagem |
| CLOSER | 3 novos contactos Seg B + 8-9 follow-ups | Aprovação Telegram |
| HUNTER | Prospecção Finanças (5) + Telecom (5) | Autónomo |
| VOICE | Calendário W22 + estreia LinkedIn | Aprovação posts com clientes |
| SCOUT | Monitorização Genesis.ao + ANGOTIC | Autónomo |
| FORGE | Validar 4 webhooks (aprov, email, LI, IG) | Autónomo |
| LEDGER | Estado financeiro Maio + projecção Junho | Autónomo |
| EDITOR | Revisão de todos os textos antes de envio | Autónomo |

---

---

## Fecho W22 — Sexta-feira 29 Mai 2026

### Sessão de arranque do plano comercial — ATLAS

**Instrução CEO:** "vamos arrancar o plano hoje. tem que se fazer prospecção, envie mensagens aos prospectos"

**Executado:**

| # | Agente | Acção | Estado |
|---|--------|-------|--------|
| 1 | CLOSER | 22 mensagens de primeiro contacto redigidas (FIN ×5, TEL ×4, IMO ×13) | ✅ Rascunhos em `proposals/drafts/` |
| 2 | CLOSER | Batch de aprovação preparado — script `scripts/submeter_aprovacoes_batch.py` | ✅ Pronto a executar |
| 3 | FORGE | FastAPI actualizado com `/webhook/bmst-send-message` (envia WA+email após aprovação CEO) | ✅ Código pronto — deploy pendente |
| 4 | FORGE | RESEND_API_KEY staged para bmst-api (Fly.io) | ✅ Será aplicado no próximo deploy |
| 5 | HUNTER | Pipeline actualizado — 22 leads em estado "em_aprovacao" | ✅ `leads/pipeline.json` actualizado |
| 6 | ATLAS | Scheduler heartbeat fixado (08:00 UTC → email CEO contact@biscaplus.com) | ✅ Activo desde 28 Mai 23:34 UTC |

**Bloqueador actual:** Docker Desktop engine ainda a inicializar → deploy FastAPI pendente.
**Acção CEO:** Quando disponível, iniciar Docker Desktop manualmente e executar: `cd bmst-workspace/api && fly deploy`
**Ou:** Executar directamente `python scripts/submeter_aprovacoes_batch.py` após deploy confirmado.

---

### Métricas W22 — final

| Métrica | Meta | Resultado |
|---------|------|-----------|
| Primeiro contacto novos leads | 3 | 3 ✅ (Fresmart, ACE, Multipessoal) + 22 em aprovação |
| Follow-ups processados | 8-9 | 5/9 ✅ (4 bloqueados por canal) |
| Leads Finanças prospectados | 5 | 5 ✅ (FIN-001 a FIN-005) |
| Leads Telecomunicações prospectados | 5 | 5 ✅ (TEL-001 a TEL-005) |
| Posts W22 publicados | 5 | 1 ✅ + 2 prontos W23 + 1 IG pendente imagem |
| FastAPI bmst-api | Deploy | ✅ Activo desde 27 Mai |
| Scheduler 08:00 UTC | Funcional | ✅ Heartbeat activo desde 28 Mai |

---

## Sessão de trabalho — Sábado 30 Mai 2026

**Instrução CEO:** "atlas vamos trabalhar, movimente a equipa"

### Executado — 30 Mai 2026

| # | Agente | Acção | Estado |
|---|--------|-------|--------|
| 1 | FORGE | Criar volume persistente `bmst_data` (2×1GB, cdg) + montar em `/data/` | ✅ |
| 2 | FORGE | Deploy `bmst-api` com `SESSIONS_FILE=/data/bmst_sessions.json` — sessões persistem entre restarts | ✅ |
| 3 | CLOSER | Batch 24 mensagens (FIN×3, TEL×5, IMO×16) submetidas ao CEO para aprovação | ✅ 24 pendentes |
| 4 | CLOSER | Follow-up B ×4 (Fresmart, ACE Audit, Multipessoal, Connectis) submetidos ao CEO | ✅ 4 pendentes |
| 5 | HUNTER | Prospecção Advocacia — 5 leads (JUR-001 a JUR-005): LCCA (9), CLM Angola (8), Couto Graça (8) | ✅ |
| 6 | HUNTER | Prospecção Contabilidade — 5 leads (CON-001 a CON-005): ATA (9), Nexia (8), Moore (8) | ✅ |
| 7 | LEDGER | Pipeline actualizado: 72 → **82 leads** | ✅ |

**Estado API:** 28 sessões persistidas em `/data/bmst_sessions.json` (volume Fly.io)
**Próxima acção CEO:** Responder APROVAR/REJEITAR às 28 notificações WhatsApp recebidas

---

## Prioridades W23 (1–5 Jun 2026)

### 🔴 CRÍTICO

| # | Agente | Tarefa | Estado inicial |
|---|--------|--------|----------------|
| 1 | CLOSER | CEO aprovar 28 mensagens pendentes — envios automáticos via Evolution API após aprovação | ⏳ CEO |
| 2 | VOICE | Publicar 2 posts W23 prontos: "processos repetitivos" + "custo leads perdidos" | 🔄 Em execução |
| 3 | CLOSER | Redigir primeiros contactos JUR-001 a JUR-005 (Advocacia — novos, ainda "novo") | 🔄 Em execução |

### 🟠 ALTA

| # | Agente | Tarefa | Estado inicial |
|---|--------|--------|----------------|
| 4 | HUNTER | Prospecção Hotelaria Luanda — sector aleatório W23 — 5-8 leads | 🔄 Em execução |
| 5 | CLOSER | Redigir primeiros contactos VIA-001 a VIA-005 (Agências Viagens — prospectadas 01 Jun) | 🔄 Em execução |
| 6 | SCOUT | Análise mercado Hotelaria Angola para apoiar HUNTER | 🔄 Em execução |
| 7 | FORGE | Deploy com SQLite (main.py actualizado) — aguarda Docker ou remote builder disponível | ⏳ pendente |
| 8 | KEEPER | Preparar relatório reactivação Clínica Vitória (Jul 2026) | ⏳ pendente |

### 🟡 MÉDIA

| # | Agente | Tarefa | Estado inicial |
|---|--------|--------|----------------|
| 9 | VOICE | Calendário de conteúdo W23 — 5 posts (LinkedIn 3 + Instagram 2, tema Hotelaria) | 🔄 Em execução |
| 10 | LEDGER | Estado financeiro Junho 2026 — pipeline 87 leads + projecção | 🔄 Em execução |
| 11 | EDITOR | Rever rascunhos CLOSER (JUR ×5 + VIA ×5) antes de submissão CEO | ⏳ aguarda CLOSER |
| 12 | HUNTER | Prospecção Saúde 2 — 5 leads (clínicas privadas, laboratórios) | ⏳ próxima sessão |
| 13 | HUNTER | Prospecção Educação 2 — 5 leads (universidades privadas, colégios) | ⏳ próxima sessão |

---

## Sessão de trabalho — Terça-feira 3 Jun 2026

**Instrução CEO:** "atlas coloca a equipa a trabalhar, todos agentes devem ter uma task a fazer agora. a prospecção está fraca, poucos prospectos. escolhem um sector/nicho aleatório."

**Sector aleatório escolhido:** Hotelaria e Alojamento em Luanda
*Justificação: único sector prioritário do ICP BMST completamente ausente do pipeline. Luanda tem 15+ hotéis 4/5 estrelas com dor clara de automação de reservas e atendimento WhatsApp.*

### Executado — 3 Jun 2026

| # | Agente | Acção | Estado |
|---|--------|-------|--------|
| 1 | ATLAS | 10 tasks criadas e atribuídas a todos os agentes | ✅ |
| 2 | HUNTER | Prospecção Hotelaria Luanda — HOT-001 a HOT-00N | 🔄 A correr |
| 3 | CLOSER | Rascunhos JUR-001 a JUR-005 (5 mensagens Advocacia) | 🔄 A correr |
| 4 | CLOSER | Rascunhos VIA-001 a VIA-005 (5 mensagens Agências Viagens) | 🔄 A correr |
| 5 | VOICE | Calendário W23 + 3 posts novos (tema Hotelaria) | 🔄 A correr |
| 6 | SCOUT | Análise mercado Hotelaria Angola | 🔄 A correr |
| 7 | LEDGER | Estado financeiro Junho 2026 | 🔄 A correr |
| 8 | CON | CON-001 a CON-005 já contactados (2-3 Jun via email) | ✅ Executado em sessão anterior |

**Estado pipeline no arranque desta sessão:**
- 87 leads total (36 novos | 26 contactados | 22 em aprovação | 2 arquivados)
- Sectores: Saúde(5), Educação(5), Logística(27), Comércio(5), Serviços(5), Finanças(5), Telecom(5), Imobiliário(15), Advocacia(5), Contabilidade(5), Viagens(5)
- Receita confirmada: USD 0 — meta Junho: 1 contrato Seg B fechado

**Acções CEO pendentes:**
- 28 mensagens aguardam aprovação desde 28-30 Mai (URGENTE — mais de 5 dias sem resposta)
- 10 novas mensagens (JUR×5 + VIA×5) prontas para aprovação após EDITOR ✅
- 1 email EDACO pendente de aprovação (Instagram bloqueado)
- LinkedIn perfis Real Express + Adilson/Connectis a confirmar para CLOSER

### Resultado da sessão — 3–4 Jun 2026

| # | Agente | Produção | Estado |
|---|--------|----------|--------|
| 1 | HUNTER | 7 leads Hotelaria (HOT-001 a HOT-007, score médio 8.0) | ✅ Pipeline: 87 → 94 leads |
| 2 | SCOUT | Análise mercado hoteleiro Angola (15 hotéis, pain points, tickets, ROI) | ✅ `intelligence/scout-reports/hotelaria-angola-2026-06-03.md` |
| 3 | CLOSER | 10 rascunhos (JUR-001 a JUR-005 + VIA-001 a VIA-005) | ✅ `proposals/drafts/` |
| 4 | EDITOR | Revisão 10 mensagens: 7 aprovadas, 3 rejeitadas e corrigidas | ✅ `editor-review-jur-via-2026-06-03.md` |
| 5 | VOICE | Calendário W23 + 3 posts novos tema Hotelaria | ✅ `content/calendario-w23-2026-06.md` |
| 6 | LEDGER | Estado financeiro Junho 2026 (pipeline 94 leads, projecção) | ✅ `finances/estado-financeiro-2026-06.md` |
| 7 | ATLAS | Plano W23 actualizado, todas tasks atribuídas | ✅ Este ficheiro |

**Pendente (tarefas CEO e equipa):**
- FORGE: deploy SQLite + verificar bmst-api.fly.dev (Task #7)
- KEEPER: relatório reactivação Clínica Vitória (Task #8)
- CEO: aprovar 28+10 = 38 mensagens ⏳ URGENTE

---

*Actualizado: ATLAS — 2026-06-04 (quarta-feira W23)*
*Próxima actualização: ATLAS — W24 | Segunda-feira, 8 Jun 2026*
*Língua: Português europeu (pt-PT)*
