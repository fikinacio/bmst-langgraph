# CLAUDE_CODE_PROMPTS_COMPLETE.md
# Prompts Completos para Desenvolvimento LangGraph — BMST Angola
# 85-90% do código é gerado pelo Claude Code. Tu validas e aprovas.

---

## COMO USAR ESTE DOCUMENTO

Cada secção é uma sessão de trabalho no Claude Code (terminal).
Antes de cada sessão:
1. `cd bmst-agents` (pasta do projecto)
2. `claude` para iniciar o Claude Code
3. Cola o prompt da sessão
4. Lê o código gerado antes de o executar
5. Não avanças para a sessão seguinte sem a anterior estar funcional

Regra de ouro: se o Claude Code gerar código que não entendes, pede:
"Explica este bloco como se eu fosse um engenheiro C++ a aprender Python"

---
---

## SESSÃO 0 — Onboarding Completo (cola no início de CADA sessão nova)

```
Olá. Vou trabalhar contigo no projecto BMST Agents.

CONTEXTO DO PROJECTO:
Sistema de agentes IA autónomos para a empresa BMST Angola (mercado angolano).
4 agentes principais + 1 agente revisor, orquestrados por n8n, implementados em LangGraph/FastAPI.

AGENTES:
- PROSPECTOR: corre no Cowork/Claude for Desktop às 08h00, pesquisa leads no Google, escreve no Google Sheets
- HUNTER: corre às 09h00, lê o Google Sheet, gera mensagens WhatsApp personalizadas, envia via Evolution API
- REVISOR: nó dentro do HUNTER e CLOSER — revê qualquer texto antes de chegar ao cliente, detecta padrões de IA, garante que soa como Fidel Kussunga (pessoa real)
- CLOSER: converte leads em clientes, gera propostas PDF, requer aprovação humana (interrupt)
- DELIVERY: gere projectos activos, actualizações 2x/semana
- LEDGER: facturação em AOA, lembretes de pagamento

STACK TÉCNICO:
- LangGraph 0.2+ (grafos de agentes, interrupt para human-in-the-loop)
- FastAPI 0.115+ (expõe cada agente como endpoint HTTP)
- Claude API via anthropic SDK (Haiku para classificação, Sonnet para escrita)
- Supabase (PostgreSQL + pgvector para memória e histórico)
- Redis (deduplicação de mensagens WA, sessões)
- Google Sheets API (leitura/escrita de leads pelo HUNTER)
- Evolution API (envio/recepção WhatsApp)
- Telegram Bot API (notificações e aprovações do fundador)
- Gotenberg (geração de PDFs de propostas)
- Langfuse (observabilidade e traces)
- Docker + EasyPanel (deploy)
- pytest (testes com mocks do LLM)

REGRAS DE NEGÓCIO CRÍTICAS:
- Segmento A → arquivo automático, NUNCA contactar
- Segmento B → pipeline normal
- Segmento C → aprovação do fundador antes de qualquer contacto
- Preço mínimo: 180.000 AOA
- Pagamento 50% antes de qualquer trabalho
- Nenhuma mensagem ao cliente sem passar pelo REVISOR
- Nenhuma proposta sem interrupt + aprovação do fundador
- Nunca mencionar: IA, algoritmo, chatbot, bot, machine learning nos textos ao cliente

PERSONA FIDEL:
Todos os textos ao cliente saem como "Fidel Kussunga" (pessoa real, fundador).
Nunca como "agente BMST" ou "assistente virtual".

MEU BACKGROUND:
- Experiência sólida em C++ (embedded systems, máquinas de estados)
- Python básico/intermédio
- Confortável com git, Docker, APIs
- Leio e entendo código mas não sou Python expert

ESTRUTURA DE FICHEIROS JÁ DEFINIDA:
bmst-agents/
├── agents/
│   ├── hunter/   (state.py, nodes.py, graph.py, prompts.py)
│   ├── closer/
│   ├── revisor/  (NOVO — nó partilhado)
│   ├── delivery/
│   └── ledger/
├── core/
│   ├── llm.py
│   ├── memory.py
│   ├── redis_client.py
│   ├── sheets_client.py  (NOVO — Google Sheets)
│   ├── evolution_client.py  (NOVO — WhatsApp)
│   ├── telegram_client.py  (NOVO — notificações)
│   └── alerts.py
├── api/
│   ├── main.py
│   ├── models.py
│   └── dependencies.py
├── tests/
└── [Dockerfile, docker-compose, requirements, .env.example]

Confirma que entendeste e aguarda as minhas instruções.
```

---
---

## SESSÃO 1 — Estrutura do Projecto e Dependências

```
Cria a estrutura completa do projecto bmst-agents.

PASSO 1: Cria o ficheiro requirements.txt com estas versões exactas:
langgraph>=0.2.0
langchain-anthropic>=0.2.0
anthropic>=0.34.0
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.8.0
pydantic-settings>=2.4.0
supabase>=2.7.0
redis>=5.0.0
langfuse>=2.0.0
google-auth>=2.28.0
google-auth-httplib2>=0.2.0
google-api-python-client>=2.120.0
httpx>=0.27.0
python-dotenv>=1.0.0
pytest>=8.3.0
pytest-asyncio>=0.23.0
pytest-mock>=3.14.0

PASSO 2: Cria o .env.example com TODAS as variáveis necessárias,
organizadas por secção, com comentários:

# === LLM ===
ANTHROPIC_API_KEY=sk-ant-...

# === Supabase ===
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJ...

# === Redis ===
REDIS_URL=redis://localhost:6379

# === Google Sheets ===
GOOGLE_SHEET_ID=1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms
GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}

# === Evolution API (WhatsApp) ===
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=tua-chave-aqui
EVOLUTION_INSTANCE=bmst_angola

# === Telegram ===
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=123456789

# === Gotenberg (PDFs) ===
GOTENBERG_URL=http://localhost:3001

# === Langfuse ===
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# === API Security ===
API_KEY=gera-uma-chave-aleatoria-aqui

# === App ===
APP_ENV=development
LOG_LEVEL=INFO

PASSO 3: Cria todos os ficheiros Python como esqueletos com apenas:
- Import statements necessários
- Comentário de uma linha a descrever o propósito do ficheiro
- Funções vazias com type hints e docstrings de uma linha
NÃO implementes a lógica ainda.

PASSO 4: Cria o .gitignore adequado para Python + dotenv.

Começa pelo requirements.txt e .env.example, mostra-me, e aguarda confirmação
antes de criar os esqueletos Python.
```

---
---

## SESSÃO 2 — Core: LLM, Supabase, Redis

```
Implementa os módulos core. Começa pelo core/llm.py, mostra-me, aguarda
confirmação, depois faz o seguinte.

FICHEIRO 1: core/llm.py

Implementa:
- Dois clientes Anthropic configurados:
  llm_haiku = claude-haiku-4-5-20251001 (classificação, triagem, revisão básica)
  llm_sonnet = claude-sonnet-4-6 (geração de mensagens ao cliente, propostas)

- Função principal:
  async def create_message(
      system: str,
      user: str,
      model: Literal["haiku", "sonnet"] = "haiku",
      max_tokens: int = 1024,
      agent_name: str = "unknown",
      node_name: str = "unknown"
  ) -> str

  A função deve:
  1. Fazer a chamada ao Claude API
  2. Fazer retry exponencial em caso de rate limit ou timeout (máx 3 tentativas, backoff: 2s, 4s, 8s)
  3. Em caso de erro final: lançar excepção com mensagem clara
  4. Logar: agente, nó, modelo, tokens usados, latência (logging.info)
  5. Se LANGFUSE_PUBLIC_KEY estiver configurado: criar trace Langfuse

- Função helper para JSON structured output:
  async def create_json_message(
      system: str,
      user: str,
      schema: type[BaseModel],
      model: Literal["haiku", "sonnet"] = "haiku",
      **kwargs
  ) -> BaseModel

  Adiciona ao system: "Responde APENAS com JSON válido. Sem texto antes ou depois.
  Sem backticks. Sem markdown. Apenas o JSON."
  Faz parse com Pydantic. Se falhar: retenta uma vez com instrução mais explícita.
  Se falhar de novo: lança ValueError com o output raw para debugging.

FICHEIRO 2: core/memory.py

Implementa cliente Supabase com estas funções:
- get_lead(phone: str) -> dict | None
- upsert_lead(lead_data: dict) -> dict
- update_lead_state(phone: str, estado: str, agente: str) -> bool
- save_message(phone: str, role: str, content: str, agente: str) -> bool
- get_conversation_history(phone: str, limit: int = 10) -> list[dict]
- save_revisao(lead_id: str, texto_original: str, texto_final: str, status: str, notas: str) -> bool

Cada função: trata exceções, faz log, devolve valor seguro em caso de erro.

FICHEIRO 3: core/redis_client.py

Implementa:
- get_session / set_session / delete_session (com TTL padrão 3600s)
- is_duplicate(phone: str, message_hash: str) -> bool
  Usa hashlib.md5 da mensagem. TTL de 86400s (24h).
- mark_sent(phone: str, message_hash: str) -> bool
- get_hunter_lock() -> bool  # previne execuções simultâneas do HUNTER
- release_hunter_lock() -> None

Usa prefix de chaves: "bmst:session:", "bmst:msg:", "bmst:lock:"

Mostra-me cada ficheiro antes de avançar para o seguinte.
```

---
---

## SESSÃO 3 — Core: Sheets, Evolution, Telegram

```
Implementa os três clientes de integração externa.

FICHEIRO 1: core/sheets_client.py

Google Sheets API via service account. Implementa:

- Inicialização com GOOGLE_SERVICE_ACCOUNT_JSON do .env
  (o JSON está em base64 ou como string — trata ambos os casos)

- async def get_pending_leads(sheet_id: str) -> list[dict]
  Lê aba "leads_angola", filtra onde estado_hunter == "pendente"
  Exclui automaticamente linhas com segmento == "A"
  Devolve lista de dicts com keys iguais aos nomes das colunas do cabeçalho
  (linha 1 do sheet é sempre o cabeçalho)
  Máximo 20 leads por chamada

- async def update_lead_status(
      sheet_id: str,
      row_index: int,  # índice real na sheet (1-based, linha 1 = cabeçalho)
      status: str,
      date: str | None = None
  ) -> bool
  Actualiza colunas U (estado_hunter) e V (data_hunter)

- async def mark_lead_response(sheet_id: str, row_index: int, response: str) -> bool
  Actualiza coluna W (resposta)

- async def get_lead_by_whatsapp(sheet_id: str, phone: str) -> dict | None
  Procura lead pelo número WhatsApp — usado quando resposta chega

- async def check_duplicate(sheet_id: str, empresa: str, phone: str) -> bool
  Verifica se empresa ou phone já existem no sheet

IMPORTANTE: A Google Sheets API é síncrona. Envolve as chamadas em
asyncio.to_thread() para não bloquear o event loop.

FICHEIRO 2: core/evolution_client.py

Evolution API para WhatsApp. Implementa:

- async def send_text_message(phone: str, text: str) -> dict
  POST /message/sendText/{instance}
  Normaliza o número: remove espaços, garante formato +244XXXXXXXXX

- async def send_document(phone: str, document_url: str, filename: str, caption: str = "") -> dict
  POST /message/sendMedia/{instance} com type "document"
  Usado para envio de propostas PDF

- async def get_message_status(message_id: str) -> str
  GET para verificar se mensagem foi entregue/lida
  Devolve: "sent" | "delivered" | "read" | "failed"

Trata erros HTTP com retry (máx 2 tentativas). Faz log de cada envio.

FICHEIRO 3: core/telegram_client.py

Telegram Bot API. Implementa:

- async def send_message(text: str, parse_mode: str = "HTML") -> dict
  Usa TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID do .env

- async def send_approval_request(
      mensagem_cliente: str,
      contexto: dict,  # empresa, segmento, canal, agente
      revisao_notas: str
  ) -> str  # devolve o message_id do Telegram para o Wait Node

  Formata a mensagem com o template de aprovação do REVISOR.
  Adiciona inline keyboard: [✅ Aprovar] [✏️ Editar] [❌ Rejeitar]

- async def send_alert(title: str, body: str, urgency: str = "média") -> dict
  Para alertas de erros, custos, timeouts

- async def send_daily_report(report: dict) -> dict
  Formata e envia o relatório diário do HUNTER

Todos os textos Telegram usam HTML (não Markdown — mais estável na API).
```

---
---

## SESSÃO 4 — Agente REVISOR (nó partilhado)

```
Implementa o agente REVISOR como módulo reutilizável.
Este não é um grafo autónomo — é um conjunto de nós que o HUNTER e o CLOSER
incluem no seu grafo antes de qualquer envio ao cliente.

FICHEIRO 1: agents/revisor/state.py

Define RevisorState como TypedDict:
- texto_original: str
- texto_corrigido: str | None
- status: Literal["pendente","aprovado","corrigido","escalado","rejeitado"]
- problemas_encontrados: list[str]  # lista de problemas detectados
- auto_correcoes: list[str]  # lista de correcções feitas automaticamente
- qualidade_estimada: Literal["alta","media","baixa"]
- aprovacao_fundador: bool | None
- motivo_escalonamento: str | None

FICHEIRO 2: agents/revisor/prompts.py

Define estas constantes:

CHECKLIST_AVALIACAO_PROMPT:
System prompt que instrui o LLM a avaliar o texto contra:

TERMOS_PROIBIDOS = [
  "inteligência artificial", "IA", "A.I.", "algoritmo", "machine learning",
  "deep learning", "LLM", "chatbot", "n8n", "Dify", "Evolution API", "bot",
  "automatizado" (quando técnico)
]

FRASES_BANIDAS = [
  "Espero que este email o encontre bem",
  "Peço desculpa por este contacto não solicitado",
  "Como especialista em",
  "Venho por este meio",
  "No seguimento de",
  "É com prazer que",
  "Seria um prazer poder",
  "Não hesite em contactar-me",
  "Fico à disposição para qualquer esclarecimento adicional",
  "Aguardo o seu retorno",
  "Não hesite em"
]

SINAIS_IA = [
  Frases demasiado longas e perfeitas sem variação
  Estrutura em 3 parágrafos simétricos
  Ausência de referência específica à empresa
  Começo com "Espero" ou "Venho"
  Nenhuma frase curta (menos de 8 palavras) no texto inteiro
]

O LLM deve devolver JSON com schema RevisorAvaliacaoSchema.

AUTO_CORRECAO_PROMPT:
System prompt para reescrita automática de problemas menores.
Instrução clara: manter o significado, manter a personalização,
remover apenas o que viola as regras, soar como Fidel Kussunga.

FICHEIRO 3: agents/revisor/nodes.py

Implementa:

async def avaliar_texto(state: RevisorState) -> RevisorState:
  """Avalia o texto contra o checklist. Identifica problemas e classifica gravidade."""
  # chama create_json_message com CHECKLIST_AVALIACAO_PROMPT
  # preenche problemas_encontrados e qualidade_estimada

async def auto_corrigir(state: RevisorState) -> RevisorState:
  """Auto-corrige problemas menores (termos proibidos, frases banidas)."""
  # Chama create_message com AUTO_CORRECAO_PROMPT + texto_original + lista de problemas
  # Preenche texto_corrigido e auto_correcoes
  # Se não consegue corrigir (problema estrutural): define status = "escalado"

async def verificar_personalizacao(state: RevisorState) -> RevisorState:
  """Verifica se a mensagem tem referência específica à empresa."""
  # Avaliação simples: conta referências específicas vs genéricas
  # Se genérica: status = "escalado", motivo = "sem_personalizacao"

async def preparar_aprovacao(state: RevisorState) -> RevisorState:
  """Prepara o pedido de aprovação para o fundador via Telegram."""
  # Formata a mensagem Telegram com o template de aprovação do REVISOR
  # Chama telegram_client.send_approval_request()
  # Guarda o message_id para rastreamento

FICHEIRO 4: agents/revisor/graph.py

Monta o sub-grafo REVISOR:

avaliar_texto → [router]
  → se problemas menores: auto_corrigir → verificar_personalizacao → preparar_aprovacao → interrupt
  → se problemas estruturais: preparar_aprovacao (com flag escalonamento) → interrupt
  → se sem problemas: verificar_personalizacao → preparar_aprovacao → interrupt

NOTA: O interrupt() aqui aguarda a resposta do fundador via Telegram.
O n8n retoma o grafo quando o fundador responde com o callback do Telegram.

Explica-me como o interrupt funciona no LangGraph antes de implementar o grafo.
```

---
---

## SESSÃO 5 — Agente HUNTER: State, Nodes, Graph

```
Implementa o agente HUNTER completo com integração Google Sheets e REVISOR.

FICHEIRO 1: agents/hunter/state.py

HunterState TypedDict com:
# Input (do sheet ou webhook WhatsApp)
- lead_id: str | None
- sheet_row_index: int | None
- empresa: str | None
- sector: str | None
- segmento: Literal["A","B","C"] | None
- responsavel: str | None
- whatsapp: str | None
- notas_abordagem: str | None
- oportunidade: str | None
- servico_bmst: str | None
- valor_est_aoa: int | None

# Processamento HUNTER
- qualificado: bool | None
- motivo_rejeicao: str | None
- template_usado: str | None
- mensagem_gerada: str | None
- nota_interna: str | None

# Integração REVISOR (campos do RevisorState embutidos)
- revisao_status: str | None
- revisao_texto_final: str | None
- revisao_notas: str | None
- aprovacao_fundador: bool | None

# Resultado
- mensagem_enviada: bool
- whatsapp_message_id: str | None
- proxima_acao: str | None
- erro: str | None

# Batch (para o modo de execução diária)
- leads_pendentes: list[dict]
- leads_processados: int
- mensagens_enviadas: int

FICHEIRO 2: agents/hunter/prompts.py

Define:

TRIAGEM_PROMPT: instrui o LLM a:
1. Confirmar o segmento (A/B/C) com base nos critérios do KB_02
2. Devolver JSON: { "segmento_confirmado": "B", "qualificado": true, "motivo": "..." }
3. Ser conservador — se houver dúvida, classifica como B e marca para verificação

SELECAO_TEMPLATE_PROMPT: instrui o LLM a:
1. Com base no sector e nas notas_abordagem, seleccionar o template mais adequado
2. Devolver JSON: { "template": "saude", "justificacao": "..." }

GERACAO_MENSAGEM_PROMPT: instrui o LLM a:
1. Gerar a mensagem WhatsApp usando o template seleccionado
2. Incorporar OBRIGATORIAMENTE o gancho do campo notas_abordagem
3. Escrever como Fidel Kussunga (primeira pessoa, tom humano, sem IA)
4. Máx. 5 linhas, 3 parágrafos curtos
5. Terminar com pergunta de baixo compromisso
6. Assinar: "Fidel Kussunga\nBisca+ | biscaplus.com"
7. Devolver dois blocos separados por ---:
   ### MENSAGEM_CLIENTE
   [texto limpo]
   ---
   ### NOTA_INTERNA
   [metadados]

Inclui no prompt 3 exemplos (few-shot) de mensagens bem escritas por sector.
Inclui no prompt 3 exemplos de mensagens MAL escritas com explicação do porquê.

FICHEIRO 3: agents/hunter/nodes.py

Implementa:

async def carregar_leads_sheet(state: HunterState) -> HunterState:
  """Carrega leads pendentes do Google Sheet. Modo batch diário."""
  # Chama sheets_client.get_pending_leads()
  # Preenche state["leads_pendentes"]
  # Se lista vazia: state["proxima_acao"] = "sem_leads_hoje"

async def confirmar_segmento(state: HunterState) -> HunterState:
  """Confirma segmento do lead. Seg A → arquivo. Seg C → verificar flag."""
  # Para Seg A: state["proxima_acao"] = "arquivar"
  # Para Seg C com flag escalar: state["proxima_acao"] = "aguardar_aprovacao_seg_c"
  # Para Seg B: state["proxima_acao"] = "gerar_mensagem"

async def gerar_mensagem_hunter(state: HunterState) -> HunterState:
  """Gera mensagem WhatsApp personalizada usando template + notas_abordagem."""
  # Verifica que notas_abordagem não está vazio
  # Selecciona template com llm_haiku
  # Gera mensagem com llm_sonnet (qualidade de escrita importa aqui)
  # Faz split por "---", extrai MENSAGEM_CLIENTE e NOTA_INTERNA
  # Valida: mensagem < 5 linhas, tem referência específica, sem termos proibidos
  # Se validação falha: state["erro"] = "mensagem_invalida", detalha o problema

async def arquivar_lead(state: HunterState) -> HunterState:
  """Arquiva lead Seg A no sheet e Supabase."""
  # sheets_client.update_lead_status(status="arquivado")
  # memory.update_lead_state(estado="arquivo")

async def notificar_seg_c(state: HunterState) -> HunterState:
  """Notifica fundador sobre lead Seg C e aguarda aprovação."""
  # telegram_client.send_message(mensagem de escalamento Seg C)
  # state["proxima_acao"] = "aguardar_aprovacao_seg_c"

async def enviar_whatsapp(state: HunterState) -> HunterState:
  """Envia mensagem aprovada via Evolution API."""
  # Verifica aprovacao_fundador == True
  # Verifica is_duplicate (Redis) — não reenvia mensagem igual
  # evolution_client.send_text_message()
  # sheets_client.update_lead_status(status="enviado")
  # memory.save_message()
  # Aguarda 90 segundos (time.sleep em thread separada para não bloquear)

async def processar_resposta(state: HunterState) -> HunterState:
  """Processa resposta recebida do prospect. Classifica interesse."""
  # Usa llm_haiku para classificar: INTERESSADO / NEUTRO / NAO_INTERESSADO / SEM_RESPOSTA
  # Actualiza sheet e Supabase
  # Se INTERESSADO: state["proxima_acao"] = "passar_ao_closer"

async def gerar_relatorio_diario(state: HunterState) -> HunterState:
  """Gera e envia relatório diário às 16h30 via Telegram."""

FICHEIRO 4: agents/hunter/graph.py

Monta o StateGraph do HUNTER:

START → carregar_leads_sheet → [router: tem leads?]
  → sem leads: gerar_relatorio_diario → END
  → tem leads: [loop sobre cada lead]
    → confirmar_segmento → [router: segmento?]
      → A: arquivar_lead → [próximo lead ou END]
      → C sem aprovação: notificar_seg_c → [próximo lead]
      → B: gerar_mensagem_hunter → REVISOR_subgraph → [interrupt: aprovação Telegram]
        → aprovado: enviar_whatsapp → [próximo lead ou END]
        → rejeitado: arquivar_lead → [próximo lead]
    → após todos os leads: gerar_relatorio_diario → END

Usa MemorySaver como checkpointer (necessário para interrupt).
Implementa o loop de leads como iteração no state, não como edges paralelos.

Explica-me o design do loop no grafo antes de implementar.
```

---
---

## SESSÃO 6 — FastAPI e Endpoints

```
Implementa a camada FastAPI que expõe todos os agentes como endpoints HTTP.

FICHEIRO 1: api/models.py

Define os Pydantic models para todos os endpoints:

HunterBatchRequest:
  sheet_id: str
  max_leads: int = 20

HunterWebhookRequest (para resposta de WhatsApp):
  phone: str
  message: str
  message_id: str
  timestamp: int

TelegramCallbackRequest (para aprovações do Telegram):
  callback_query_id: str
  message_id: int
  data: Literal["aprovar","editar","rejeitar"]
  thread_id: str  # identifica qual grafo retomar

CloserDiagnoseRequest:
  phone: str
  empresa: str
  mensagem: str
  historico: list[dict] = []

CloserProposeRequest:
  phone: str
  empresa: str
  diagnostico: dict

BatchResponse:
  leads_processados: int
  mensagens_enviadas: int
  erros: list[str]
  tempo_execucao_segundos: float

FICHEIRO 2: api/dependencies.py

Implementa verificação de API key:
async def verify_api_key(x_api_key: str = Header(...)) -> str:
  if x_api_key != settings.API_KEY:
    raise HTTPException(status_code=401, detail="Invalid API key")
  return x_api_key

FICHEIRO 3: api/main.py

Implementa a FastAPI app com estes endpoints:

GET /health
  Verifica conectividade: Supabase, Redis, Evolution API, Google Sheets
  Devolve status de cada serviço

GET /metrics
  Agrega métricas do Supabase:
  - total leads por segmento
  - mensagens enviadas hoje / esta semana
  - taxa de resposta
  - taxa de conversão (leads → propostas → clientes)
  - custos estimados de API (tokens usados × preço por token)

POST /hunter/batch (protected)
  Chama carregar_leads_sheet + loop HUNTER
  Background task (não bloqueia o n8n)
  Devolve BatchResponse imediatamente, processa em background

POST /hunter/webhook (não protegido — chamado pela Evolution API)
  Recebe mensagens WhatsApp recebidas
  Identifica o lead no sheet pelo número
  Chama processar_resposta

POST /telegram/callback (não protegido — chamado pelo Telegram)
  Recebe callbacks dos botões inline de aprovação
  Retoma o grafo correcto via thread_id
  Usa LangGraph MemorySaver para continuar o interrupt

POST /closer/diagnose (protected)
POST /closer/propose (protected)
POST /delivery/start (protected)
POST /delivery/update (protected)
POST /ledger/invoice (protected)
POST /ledger/check-payments (protected)

NOTA SOBRE /telegram/callback:
Este endpoint é crítico. O Telegram chama este endpoint quando o fundador
clica num botão de aprovação. O endpoint deve:
1. Identificar qual thread LangGraph está em interrupt (pelo thread_id no callback data)
2. Injectar a decisão no state
3. Retomar o grafo
Explica-me como implementar isto com o MemorySaver do LangGraph antes de começar.
```

---
---

## SESSÃO 7 — Agente CLOSER com Interrupt

```
Implementa o agente CLOSER. É o agente mais complexo porque usa interrupt()
em dois pontos: aprovação de proposta + eventuais edições do fundador.

FICHEIRO 1: agents/closer/state.py

CloserState TypedDict:
# Input do HUNTER
- phone: str
- empresa: str
- sector: str
- segmento: str
- responsavel: str
- historico_conversa: list[dict]

# Diagnóstico
- perguntas_feitas: list[str]
- respostas_cliente: list[str]
- diagnostico_completo: bool
- problema_identificado: str | None
- servico_recomendado: str | None

# Proposta
- rascunho_proposta: dict | None
  # campos: cliente, decisor, problema, solucao, entregaveis, prazo, valor_aoa,
  #         condicoes_pagamento, validade_dias, notas_fundador
- proposta_aprovada: bool | None
- edicoes_fundador: str | None
- pdf_url: str | None
- proposta_enviada: bool

# Follow-up
- followup_dia: int  # 0, 3, 7, 14
- proxima_acao: str | None
- erro: str | None

FICHEIRO 2: agents/closer/nodes.py

Implementa:

async def iniciar_diagnostico(state: CloserState) -> CloserState:
  """Envia primeira pergunta de diagnóstico ao prospect."""
  # P1: "Quantas mensagens/chamadas recebem por dia em média?"
  # (usando llm_sonnet para linguagem natural e adequada)
  # Passa pelo REVISOR antes de enviar

async def processar_resposta_diagnostico(state: CloserState) -> CloserState:
  """Processa resposta do prospect e decide próxima pergunta ou avança."""
  # Usa llm_haiku para extrair informação da resposta
  # Se 3 perguntas feitas: diagnostico_completo = True

async def seleccionar_solucao(state: CloserState) -> CloserState:
  """Com base no diagnóstico, selecciona o serviço mais adequado."""
  # Tabela de mapeamento: problema → serviço → preço indicativo

async def apresentar_solucao_verbal(state: CloserState) -> CloserState:
  """Apresenta solução verbalmente via WhatsApp antes de enviar PDF."""
  # "Com base no que partilhou, a solução que faz mais sentido é..."
  # Passa pelo REVISOR

async def gerar_rascunho_proposta(state: CloserState) -> CloserState:
  """Gera rascunho JSON da proposta para aprovação do fundador."""
  # Usa llm_sonnet para gerar todos os campos do rascunho
  # Formata mensagem Telegram com rascunho + botões [Aprovar/Editar/Rejeitar]
  # → interrupt() aqui ← O grafo para e aguarda o Telegram callback

async def incorporar_edicoes_fundador(state: CloserState) -> CloserState:
  """Se fundador editou, incorpora as edições e gera nova versão."""

async def gerar_pdf_proposta(state: CloserState) -> CloserState:
  """Gera PDF via Gotenberg a partir do rascunho aprovado."""
  # POST para GOTENBERG_URL com HTML da proposta
  # Guarda URL do PDF no state

async def enviar_proposta_cliente(state: CloserState) -> CloserState:
  """Envia proposta (texto + PDF) ao cliente via WhatsApp."""
  # Envia mensagem de cobertura (Template 7) pelo REVISOR
  # Envia PDF via evolution_client.send_document()

async def processar_resposta_proposta(state: CloserState) -> CloserState:
  """Classifica resposta do cliente à proposta."""
  # ACEITE / OBJECAO_PRECO / OBJECAO_PRAZO / PRECISA_PENSAR / RECUSA

async def gerir_objecao(state: CloserState) -> CloserState:
  """Responde a objeções com as estratégias definidas no system prompt."""
  # Nunca baixa preço — reduz âmbito
  # Sempre pelo REVISOR

FICHEIRO 3: agents/closer/graph.py

Grafo com dois interrupt():
1. Após gerar_rascunho_proposta → aprovação da proposta
2. Após apresentar_solucao_verbal → (opcional) aprovação do ângulo de abordagem

```

---
---

## SESSÃO 8 — DELIVERY e LEDGER

```
Implementa DELIVERY e LEDGER seguindo o mesmo padrão.

DELIVERY:
State: projecto_id, empresa, servico, fase_atual, data_inicio,
       data_entrega_prevista, itens_concluidos (list), itens_pendentes (list),
       aguarda_aprovacao_fase (bool), mensagem_actualizacao (str | None),
       feedback_cliente (str | None)

Nós:
- iniciar_projecto: cria workspace Notion via API, envia mensagem de onboarding
  (Template 10) PELO REVISOR
- gerar_actualizacao: cria relatório de progresso (Template 11) PELO REVISOR
  Executa 2x/semana: segunda e quinta-feira às 10h00
- solicitar_aprovacao_fase: interrupt() — aguarda aprovação do cliente
- registar_feedback: processa feedback e guarda no Supabase
- encerrar_projecto: envia relatório final + activa LEDGER para saldo + pede
  avaliação ao cliente

LEDGER:
State: projecto_id, empresa, tipo_factura (adiantamento/saldo/retainer),
       valor_aoa, estado_pagamento, data_emissao, data_vencimento,
       dias_atraso (int), mensagem_lembrete (str | None)

Nós:
- emitir_factura_adiantamento: cria factura no InvoiceNinja, envia Template 13 PELO REVISOR
- emitir_factura_saldo: confirma com DELIVERY que projecto está pronto, emite saldo
- verificar_pagamentos: corre diariamente às 09h30, consulta InvoiceNinja API
- gerar_lembrete_pagamento: selecciona template (D+3, D+7, D+14) baseado em dias_atraso
  D+3: Template 14 (amigável) | D+7: Template 15 (profissional) | D+14: Template 16 (firme)
  Todos PELO REVISOR + aprovação fundador (D+14 especialmente)
- alertar_fundador_divida: se dias_atraso > 21: alerta crítico Telegram, pausa serviços
- gerar_relatorio_mensal: agrega dados do mês, envia ao fundador no dia 1 às 08h00

Para ambos: segue exactamente a mesma estrutura de ficheiros.
Adiciona os endpoints em api/main.py.
```

---
---

## SESSÃO 9 — Testes

```
Implementa testes para todos os agentes.

ESTRATÉGIA DE TESTES:

1. TESTES UNITÁRIOS (sem LLM real):
   - Testam cada nó individualmente
   - Mockam create_message com respostas predefinidas
   - Testam as transições de estado
   - Correm em < 5 segundos
   - Marcados com @pytest.mark.unit (default)

2. TESTES DE INTEGRAÇÃO (com LLM real):
   - Testam o grafo completo
   - Chamam o Claude API real (custam tokens)
   - Verificam que as regras de negócio são respeitadas no output
   - Marcados com @pytest.mark.integration

Implementa estes testes:

tests/test_hunter.py:
- test_seg_a_arquivado_automaticamente
  Dado um lead Seg A, verifica que proxima_acao == "arquivar"
  e que nenhuma mensagem é gerada

- test_seg_b_gera_mensagem
  Dado um lead Seg B com notas_abordagem preenchidas,
  verifica que mensagem_gerada não é None e tem < 5 linhas

- test_mensagem_sem_termos_proibidos (integration)
  Dado um lead real, verifica que a mensagem gerada não contém
  nenhum dos termos proibidos da lista do REVISOR

- test_seg_c_sem_aprovacao_nao_envia
  Dado Seg C sem flag de aprovação, verifica que não chega a enviar

- test_notas_abordagem_vazio_nao_envia
  Dado lead com notas_abordagem vazio, verifica proxima_acao != "gerar_mensagem"

tests/test_revisor.py:
- test_detecta_termo_proibido_ia
  Dado texto com "inteligência artificial", verifica que status != "aprovado"

- test_detecta_frase_banida
  Dado texto com "Espero que este email o encontre bem", verifica que é corrigido

- test_aprovado_texto_correcto
  Dado texto bem escrito (sem problemas), verifica status == "aprovado"

- test_auto_corrige_chatbot
  Dado texto com "chatbot", verifica que texto_corrigido substitui por "assistente"

tests/test_closer.py:
- test_proposta_nao_enviada_sem_aprovacao
  Verifica que o grafo para em interrupt antes de enviar proposta

- test_valor_minimo_180000_aoa
  Dado diagnóstico que levaria a proposta < 180.000 AOA,
  verifica que CLOSER oferece serviço mais reduzido ou recusa

Usa pytest-mock para mockar create_message. Mostra-me o padrão de mock primeiro.
```

---
---

## SESSÃO 10 — Docker e Deploy

```
Prepara o projecto para deploy no EasyPanel.

FICHEIRO 1: Dockerfile
- Base: python:3.12-slim
- Instala dependências de sistema necessárias (libpq para psycopg2 se necessário)
- Copia requirements.txt e instala dependências
- Copia código
- Expõe porta 8000
- CMD: uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 1
  (1 worker — o LangGraph MemorySaver não é thread-safe com múltiplos workers)

FICHEIRO 2: docker-compose.yml (para desenvolvimento local)
Serviços:
- bmst-agents: a nossa FastAPI app
- redis: redis:7-alpine
- gotenberg: gotenberg/gotenberg:8
NÃO inclui Supabase, n8n, Evolution API (já correm noutros containers/servidores)

FICHEIRO 3: .github/workflows/test.yml (CI básico)
- Trigger: push para main e pull_request
- Jobs:
  - lint: ruff check
  - test: pytest -m "not integration" (sem LLM real na CI)

Verifica que o Dockerfile faz build sem erros localmente antes de terminar.
Faz: docker build -t bmst-agents . e mostra-me o output.
```

---
---

## PROMPTS DE DEBUGGING (usar quando algo falha)

### Nó devolve formato errado:
```
O nó [NOME_DO_NÓ] está a devolver um output no formato errado.

State antes do nó:
[COLAR STATE]

Output actual:
[COLAR OUTPUT]

Output esperado:
[DESCREVER]

Identifica a causa. Corrige sem alterar a assinatura da função.
Explica a causa antes de propores a solução.
```

### LLM não respeita formato:
```
O LLM não está a respeitar o formato MENSAGEM_CLIENTE / --- / NOTA_INTERNA.

System prompt actual:
[COLAR PROMPT]

Exemplos de output incorrecto:
[COLAR 2-3 EXEMPLOS]

Reescreve o prompt. Considera: few-shot examples com outputs correctos,
XML tags como alternativa ao separador ---, instrução de auto-verificação
no final ("antes de responder, verifica que o teu output tem exactamente dois blocos").
```

### REVISOR não detecta problema óbvio:
```
O REVISOR aprovou este texto mas deveria ter rejeitado/corrigido:
[COLAR TEXTO]

Problema que não detectou: [DESCRIÇÃO]

Melhora o CHECKLIST_AVALIACAO_PROMPT para detectar este padrão.
Adiciona um exemplo negativo específico ao prompt.
```

### Google Sheets não lê correctamente:
```
sheets_client.get_pending_leads() está a devolver dados errados.

Sheet ID: [ID]
Output actual: [COLAR]
Output esperado: [DESCREVER]

Aqui está o código da função: [COLAR]

Diagnostica. Verifica: mapeamento das colunas (A=col1, B=col2?),
filtro do campo estado_hunter, tratamento de células vazias.
```

### Interrupt não retoma:
```
O grafo LangGraph não está a retomar após o interrupt.

Thread ID usado: [ID]
Callback do Telegram recebido: [COLAR]
Estado actual do MemorySaver: [COLAR se acessível]

Aqui está o endpoint /telegram/callback: [COLAR]
Aqui está o graph.py relevante: [COLAR]

Diagnostica o problema de retoma do interrupt.
```

---
---

## CHECKLIST DE VALIDAÇÃO POR SESSÃO

Antes de passar à sessão seguinte, verifica:

### Sessão 1:
- [ ] `pip install -r requirements.txt` sem erros
- [ ] Todos os esqueletos importam sem erros (`python -c "from agents.hunter.state import HunterState"`)

### Sessão 2:
- [ ] `from core.llm import create_message` importa
- [ ] `await create_message("system", "user")` devolve string
- [ ] Supabase conecta (health check manual)

### Sessão 3:
- [ ] `get_pending_leads()` lê o sheet correctamente (testa com sheet de teste)
- [ ] `send_text_message()` envia WA de teste (para o teu próprio número)
- [ ] `telegram_client.send_message("teste")` chega ao Telegram

### Sessão 4 (REVISOR):
- [ ] Texto com "inteligência artificial" → status != "aprovado"
- [ ] Texto com "Espero que este email" → auto-corrigido
- [ ] Texto limpo → aprovado

### Sessão 5 (HUNTER):
- [ ] Lead Seg A → arquivado sem mensagem
- [ ] Lead Seg B com notas_abordagem → mensagem gerada
- [ ] Mensagem gerada não tem termos proibidos
- [ ] interrupt funciona: grafo para e aguarda Telegram

### Sessão 6 (API):
- [ ] `uvicorn api.main:app` arranca sem erros
- [ ] GET /health → 200 com status de todos os serviços
- [ ] POST /hunter/batch com API key correcta → 202 Accepted
- [ ] POST /hunter/batch sem API key → 401

### Sessão 9 (Testes):
- [ ] `pytest -m "not integration"` → 100% pass
- [ ] `pytest -m integration` → passa (requer ANTHROPIC_API_KEY)
