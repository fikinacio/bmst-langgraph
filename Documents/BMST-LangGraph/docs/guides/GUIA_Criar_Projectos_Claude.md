# Guia: Como Criar os Projectos no Claude.ai
## Passo a Passo Completo

---

## PROJECTO 1: BMST Angola

### Passo 1: Criar o Projecto
1. Vai a **claude.ai**
2. No menu lateral esquerdo, clica em **"Projects"**
3. Clica em **"New Project"**
4. Nome: `BMST Angola — Agentes IA`
5. Descrição: `Arquitectura operacional de agentes IA para aquisição de clientes e entrega de serviços no mercado angolano. BMST — Bisca Mais Sistemas e Tecnologias.`
6. Clica em **"Create Project"**

---

### Passo 2: Adicionar os Ficheiros de Conhecimento

Dentro do projecto, vai a **"Project Knowledge"** e faz upload dos seguintes ficheiros pela ordem indicada:

| # | Ficheiro | Função |
|---|---|---|
| 1 | `PRD_Angola_BMST_v2.pdf` | Documento mestre do projecto |
| 2 | `KB_01_Empresa_BMST.md` | Perfil da empresa, serviços, posicionamento |
| 3 | `KB_02_Mercado_Segmentos_Precos.md` | Segmentos A/B/C, preços em AOA, regras de negócio |
| 4 | `KB_03_Templates_WhatsApp.md` | Templates de mensagens por agente |
| 5 | `AGENT_HUNTER_SystemPrompt.md` | System prompt do agente HUNTER |
| 6 | `AGENT_CLOSER_SystemPrompt.md` | System prompt do agente CLOSER |
| 7 | `AGENT_DELIVERY_LEDGER_SystemPrompt.md` | System prompts dos agentes DELIVERY e LEDGER |
| 8 | `ARCHITECTURE_n8n_LangGraph.md` | Arquitectura técnica completa: n8n + LangGraph + FastAPI |

---

### Passo 3: Configurar as Instruções do Projecto

Em **"Project Instructions"**, cola este texto:

```
Sou o fundador e CEO da BMST — Bisca Mais Sistemas e Tecnologias (Angola).
Este projecto contém a arquitectura completa do sistema de agentes IA da empresa.

Contexto permanente:
- Mercado: Angola (foco principal), Luanda
- Stack técnico: n8n (orquestração) + LangGraph/FastAPI (agentes) + Evolution API (WhatsApp) + Claude API + Supabase + Redis
- Deploy dos agentes: EasyPanel VPS (mesmo servidor que o n8n)
- Budget infra: ~$200/mês
- Canal com clientes: WhatsApp (Evolution API)
- Canal interno com fundador: Telegram Bot
- Moeda: AOA (1 USD = 918 AOA)
- Segmentos alvo: B e C APENAS — Segmento A nunca é contactado
- Preço mínimo por projecto: 180.000 AOA
- Agentes: HUNTER, CLOSER, DELIVERY, LEDGER
- Cada agente é um grafo LangGraph exposto como endpoint FastAPI
- O n8n chama os agentes via HTTP POST (igual a qualquer outra API)

Quando me ajudas neste projecto:
- Usa sempre português europeu (pt-PT)
- Respeita as regras de negócio dos ficheiros KB
- Para mensagens ao cliente: usa o tom dos templates do KB_03, nunca menciones termos como IA, algoritmo, n8n ou LangGraph
- Para código Python: segue a estrutura de ficheiros e padrões do ARCHITECTURE_n8n_LangGraph.md
- Para workflows n8n: os agentes são chamados via HTTP POST para os endpoints FastAPI, não via Dify
- Aprovações de proposta requerem sempre interrupt() no LangGraph + confirmação via Telegram
- Pagamento 50% antes de qualquer trabalho começa — regra inviolável
```

---

### Como Testar o Projecto Angola

Depois de fazer o upload dos ficheiros e guardar as instruções, testa com este prompt:

```
Analisa esta empresa para prospecção:
Nome: Hotel Presidente
Sector: Hotelaria
Localização: Luanda
Director: Carlos Mendes
```

O Claude deve devolver dois blocos separados: MENSAGEM_CLIENTE (texto limpo para WhatsApp) e NOTA_INTERNA (para Telegram), separados por `---`. Se sim, o projecto está configurado correctamente.

---

## PROJECTO 2: Consultoria Suíça

### Passo 1: Criar o Projecto
1. Clica em **"New Project"**
2. Nome: `Consultoria Suíça — Fidel Kussunga`
3. Descrição: `Actividade de consultoria independente em IA e automatização para fiduciaires e PME da Suisse romande (Vaud, Genève, Fribourg).`
4. Clica em **"Create Project"**

---

### Passo 2: Adicionar os Ficheiros de Conhecimento

| # | Ficheiro | Função |
|---|---|---|
| 1 | `PRD_Suisse_Consultant_v2.pdf` | Documento mestre |
| 2 | `KB_01_Profil_Consultant.md` | Perfil profissional, expertise, ferramentas |
| 3 | `KB_02_Marche_Tarifs_Conformite.md` | Mercado, tarifas CHF, conformidade LPD |
| 4 | `KB_03_Templates_Emails.md` | Templates de email em francês por situação |
| 5 | `AGENTS_SystemPrompts_Suisse.md` | System prompts dos agentes PROSPECT, PROPOSAL, DELIVERY, ADMIN |

---

### Passo 3: Configurar as Instruções do Projecto

```
Je suis Fidel Kussunga, consultant indépendant en IA et automatisation basé
à Lausanne, Suisse. Ce projet est distinct de la société BMST Angola.

Contexte permanent:
- Marché: Suisse romande (Vaud, Genève, Fribourg)
- Segments cibles: fiduciaires, PME 10-100 employés, cabinets médicaux, agences immobilières
- TJM de référence: CHF 950 (entrée de marché) à CHF 1'400 (profil senior)
- Projet minimum: CHF 3'000 — en dessous, pas rentable
- Langue de travail client: Français professionnel
- Conformité obligatoire: LPD suisse + RGPD
- Canal de prospection: Email + LinkedIn (jamais WhatsApp)
- Notifications internes: Telegram Bot
- Stack technique: n8n + LangGraph/FastAPI + DocuSeal + InvoiceNinja (CHF)

Quand tu m'aides dans ce projet:
- Utilise le français professionnel pour toutes les communications clients
- Utilise le portugais (pt-PT) pour les notes internes si je le demande
- Respecte les règles tarifaires du KB_02
- Pour les emails: jamais "IA" ou "algorithme" dans le premier contact, utilise "processus automatisés" ou "gain de temps"
- Toujours inclure le bloc opt-out LPD dans les emails de prospection
- Ne jamais générer un email final si [LIEN_CALENDLY], [EMAIL] ou [TÉLÉPHONE] ne sont pas renseignés
- Mentionner la conformité LPD comme avantage concurrentiel face aux solutions cloud américaines
```

---

### Como Testar o Projecto Suíça

Depois de configurar, testa com este prompt:

```
Prépare un email de prospection pour:
Cabinet: Fiduciaire Rochat & Associés
Localisation: Lausanne
Taille: 6 collaborateurs
Décideur: M. Pierre Rochat
```

O email gerado deve ter o nome do decisor, a assinatura sem "IA", o opt-out LPD no final, e sem travessões longos.

---

## PROJECTO 3: BMST Agents (LangGraph/GitHub)

Este projecto cobre o desenvolvimento do sistema de agentes em Python com LangGraph.

### Passo 1: Criar o Projecto
1. Nome: `BMST Agents — LangGraph Dev`
2. Descrição: `Desenvolvimento do sistema de agentes IA em Python com LangGraph, FastAPI e Claude API. Portfólio AI Engineer.`

### Passo 2: Adicionar os Ficheiros

| # | Ficheiro | Função |
|---|---|---|
| 1 | `README.md` | Documentação do projecto (versão GitHub) |
| 2 | `ARCHITECTURE_n8n_LangGraph.md` | Arquitectura técnica de referência |
| 3 | `DEVELOPMENT_GUIDE.md` | Guia de desenvolvimento e sequência de build |
| 4 | `CLAUDE_CODE_PROMPTS.md` | Prompts para as sessões de trabalho com Claude Code |
| 5 | `INFRA_DECISION.md` | Decisão de infraestrutura e deploy |

### Passo 3: Instruções

```
Este projecto cobre o desenvolvimento em Python do sistema BMST Agents.

Contexto:
- Stack: LangGraph 0.2+, FastAPI 0.115+, Anthropic SDK, Supabase, Redis, Langfuse
- Deploy: Docker + EasyPanel (mesmo VPS que o n8n, 4GB RAM)
- Python: 3.12, async/await, Pydantic v2, type hints
- Testes: pytest com mocks do LLM para testes unitários, testes de integração marcados com @pytest.mark.integration
- Portfólio: repositório público no GitHub, documentação em inglês

Quando me ajudas neste projecto:
- Usa português europeu (pt-PT) para notas e discussão
- Usa inglês para código, comentários, docstrings e documentação GitHub
- Segue a estrutura de ficheiros do DEVELOPMENT_GUIDE.md
- Cada agente tem: state.py, nodes.py, graph.py, prompts.py
- Nunca uses travessões longos (—) nos textos de documentação
- Quando gerares código, explica as decisões principais
- Para os prompts do Claude Code, consulta o CLAUDE_CODE_PROMPTS.md
```

---

## Uso Diário: Exemplos por Projecto

### Angola
```
"Preciso de uma mensagem WhatsApp para prospectar uma clínica privada em Luanda
chamada Clínica Sagrada Esperança. O director é o Dr. António Silva."
```

```
"O lead da Imobiliária Atlântico respondeu que tem interesse.
Qual o próximo passo e como abordá-lo?"
```

### Suíça
```
"Prépare un email de prospection pour la fiduciaire Dupont & Associés
à Lausanne. Ils ont 8 collaborateurs selon leur site web."
```

```
"J'ai eu un appel avec PME Martin SA, 25 employés, logistique,
problème principal: suivi manuel des commandes. Prépare un brouillon d'offre."
```

### LangGraph Dev
```
"Estou na Sessão 3 do CLAUDE_CODE_PROMPTS. Abre esse ficheiro
e ajuda-me a implementar o agents/hunter/nodes.py."
```

```
"O teste test_segmento_b está a falhar com este erro: [COLAR ERRO].
Aqui está o código do nó: [COLAR CÓDIGO]. O que está errado?"
```
