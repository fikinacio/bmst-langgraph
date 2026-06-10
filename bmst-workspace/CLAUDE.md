# BMST — Bisca Mais Sistemas e Tecnologias

## Identidade da empresa
- **Nome completo:** Bisca Mais Sistemas e Tecnologias — Prestação de Serviços (SU), LDA
- **NIF:** 5002731479 | **Matrícula:** 37901-25/251015
- **Sede:** Luanda, Angola (Alvalade, Maianga)
- **Operação:** Lausanne, Suíça
- **Website:** www.biscaplus.com
- **Email geral:** info@biscamaisst.com
- **Email comercial:** sales@biscamaisst.com
- **Email CEO:** f.kussunga@biscamaisst.com
- **Telefone:** +244 956 873 126 | +41 79 574 8225

## Regras de uso de email
- **info@biscamaisst.com** — contacto geral, dúvidas, informações institucionais, facturas
- **sales@biscamaisst.com** — remetente Resend para outreach comercial (CLOSER, KEEPER), propostas, follow-ups
- **f.kussunga@biscamaisst.com** — email pessoal do CEO; usar SEMPRE que se redigir mensagem em nome de Fidel Kussunga

## CEO
- **Nome:** Fidel Inácio Kussunga
- **Cargo:** CEO & Fundador
- **Formação:** MSc Engenharia Electrónica Industrial e de Computadores
- **Localização:** Lausanne, Suíça

## Serviços
1. Inteligência Artificial e Análise de Dados
2. Automação de Processos Empresariais (n8n, Dify, LangGraph, LangChain)
3. Agentes de IA conversacionais (WhatsApp, web, email)
4. RAG — análise e extracção de conhecimento de documentos
5. Desenvolvimento de Software (web, mobile, sistemas embebidos)
6. Cibersegurança Avançada
7. Sistemas Embebidos e IoT
8. Transformação Digital Integrada

## Regras invioláveis
- **50% de pagamento antecipado** em TODOS os contratos. Sem excepção.
- Propostas comerciais requerem aprovação do CEO antes de envio — marcar com ⏳
- Mensagens directas a clientes requerem aprovação do CEO — marcar com ⏳
- Acções autónomas dos agentes — marcar com ✅

## Segmentos alvo Angola (Fase 1)
- **Segmento B:** PMEs médias — orçamento AOA 960.000–3.840.000/projecto
- **Segmento C:** PMEs pequenas — orçamento AOA 240.000–960.000/projecto
- Sectores prioritários: Saúde, Educação, Logística, Comércio, Sector público, Finanças e Seguros, Telecomunicações, Contabilidade, Advocacia e Serviços Jurídicos
- Canal principal: WhatsApp > LinkedIn > Email > Presencial

## Stack técnica
LangGraph, LangChain, n8n, Dify, RAG, Evolution API, Supabase, Redis, Gotenberg, WhatsApp Business API

## Língua
Português europeu (pt-PT) em TODOS os documentos e comunicações. Acentos obrigatórios. Pontuação correcta.

---

## Sistema de aprovação — WhatsApp via FastAPI

Todas as acções que requerem aprovação do CEO (⏳) são submetidas via webhook FastAPI, que envia notificação WhatsApp ao CEO (+41795748225). Os agentes nunca usam o canal nativo do Claude Code para aprovações — usam exclusivamente os webhooks abaixo.

**API BMST:** `https://bmst-api.fly.dev` (deploy Fly.io — activo desde 2026-05-27)
**Fallback n8n:** `https://n8n.biscaplus.com/webhook/bmst-aprovacao` (workflows offline — não usar até reactivação)

---

### Webhook de validação (aprovação CEO)
**URL:** `https://bmst-api.fly.dev/webhook/bmst-aprovacao`
**Método:** POST
**Content-Type:** application/json

### Payload obrigatório
```json
{
  "tipo": "mensagem|proposta|contrato|factura|linkedin_post",
  "agente": "NOME_DO_AGENTE",
  "titulo": "Descricao curta da accao",
  "cliente": "Nome do cliente ou BMST se post institucional",
  "valor": "AOA [X] ou vazio se nao aplicavel",
  "resumo": "Resumo em 1-2 frases do que esta a ser aprovado",
  "texto_completo": "Texto integral da mensagem, proposta ou post sem acentos",
  "conteudo_html": "HTML formatado (obrigatorio se tipo=proposta)",
  "whatsapp_destino": "244XXXXXXXXX ou vazio se nao aplicavel",
  "callback_url": "URL para onde o n8n envia a decisao do CEO",
  "session_id": "AGENTE-CLIENTE-YYYYMMDD-HHMMSS"
}
```

### Resposta do webhook de aprovação ao agente (via callback_url)
```json
{
  "session_id": "...",
  "decisao": "aprovado|editado|rejeitado",
  "whatsapp_destino": "...",
  "texto": "texto aprovado ou editado pelo CEO"
}
```

---

### Webhook de publicação LinkedIn
**URL:** `https://n8n.biscaplus.com/webhook/bmst-linkedin-publish`
**Método:** POST
**Content-Type:** application/json

Usado pelo VOICE para publicar posts na página Bisca+ no LinkedIn via Buffer.

### Payload
```json
{
  "texto": "Texto completo do post em pt-PT com acentos",
  "session_id": "VOICE-BMST-YYYYMMDD-HHMMSS",
  "publicar_agora": true
}
```

### Resposta
```json
{
  "status": "publicado|erro",
  "post_id": "ID do post no Buffer",
  "session_id": "..."
}
```

---

### Webhook de publicação Instagram
**URL:** `https://n8n.biscaplus.com/webhook/bmst-instagram-publish`
**Método:** POST
**Content-Type:** application/json

Usado pelo VOICE para publicar posts no Instagram @biscaplus via Buffer. Posts de feed requerem imagem obrigatória (`imagem_url`).

### Payload
```json
{
  "texto": "Legenda do post em pt-PT com acentos e hashtags",
  "imagem_url": "https://URL-da-imagem.jpg",
  "session_id": "VOICE-BMST-YYYYMMDD-HHMMSS",
  "publicar_agora": true
}
```

### Resposta
```json
{
  "status": "publicado|erro",
  "post_id": "ID do post no Buffer",
  "session_id": "..."
}
```

---

### Webhook de envio de email
**URL:** `https://n8n.biscaplus.com/webhook/bmst-email-send`
**Método:** POST
**Content-Type:** application/json

Usado pelo CLOSER e KEEPER para enviar emails a clientes após aprovação do CEO. Aceita texto com acentos pt-PT completos (sem conversão ASCII). Credencial n8n: **BMST Resend** (smtp.resend.com, porta 465 SSL, remetente: sales@biscamaisst.com).

### Payload
```json
{
  "para": "email@destino.com",
  "assunto": "Assunto do email em pt-PT",
  "corpo": "Corpo completo do email em pt-PT com acentos",
  "session_id": "CLOSER-Cliente-YYYYMMDD-HHMMSS"
}
```

### Resposta
```json
{
  "status": "enviado|erro",
  "session_id": "..."
}
```

---

### Envio WhatsApp (mensagens a clientes)
A mensagem aprovada é enviada automaticamente pela instância **biscaplus** do Evolution API a partir do número **+244 956 873 126**. O campo `whatsapp_destino` indica apenas o número do cliente que recebe.

---

### Encoding do payload de aprovação
Todos os campos de texto enviados no payload JSON devem usar ASCII puro — sem acentos, sem cedilhas, sem caracteres especiais portugueses. Substituições obrigatórias:
- ã→a, ç→c, é→e, ê→e, á→a, ó→o, ô→o, â→a, í→i, õ→o, ú→u
- Exemplo correcto: "marcacao" em vez de "marcação", "clinica" em vez de "clínica"
- Esta regra aplica-se APENAS ao payload do webhook de aprovação. Os webhooks LinkedIn Publisher, Instagram Publisher e Email Sender aceitam texto com acentos normais.

### Formato do whatsapp_destino
Número sem +, sem espaços, sem traços.
- Angola: 244936931299
- Suíça: 41795748225

---

### Fluxo de aprovação — mensagens e propostas
1. Agente prepara a acção
2. Agente envia payload ao webhook de aprovação
3. CEO recebe notificação Telegram com texto completo + PDF (se proposta)
4. CEO responde: Aprovar / Aprovar com Edições / Rejeitar
5. n8n envia decisão ao agente via callback_url
6. Agente executa a acção (envia WhatsApp, publica post, etc.)

### Fluxo VOICE — posts LinkedIn
**Posts autónomos (✅ — publicação directa sem aprovação):**
1. VOICE gera o post
2. VOICE envia directamente ao webhook LinkedIn Publisher
3. Post publicado na página Bisca+

**Posts que requerem aprovação (⏳):**
1. VOICE gera o post
2. VOICE envia ao webhook de aprovação com `tipo: linkedin_post`
3. CEO aprova/edita no Telegram
4. VOICE recebe decisão via callback_url
5. Se aprovado/editado → VOICE envia ao webhook LinkedIn Publisher
6. Post publicado na página Bisca+

---

### Quando pedir aprovação (⏳)
- CLOSER: mensagem de primeiro contacto WhatsApp
- CLOSER: proposta final para enviar ao cliente
- CLOSER: qualquer desconto acima de 10% em contratos > AOA 1.200.000
- KEEPER: update semanal ao cliente
- LEDGER: emissão de factura
- FORGE: proposta técnica final
- VOICE: posts que mencionam clientes, resultados concretos ou casos de uso reais
- VOICE: posts de posicionamento institucional ou comparação com concorrentes
- EDITOR: qualquer texto com score IA > 65% ou risco reputacional elevado

### Acções autónomas (✅ — sem aprovação necessária)
- HUNTER: pesquisa e qualificação de leads
- HUNTER: gravação de leads no ficheiro JSON
- CLOSER: rascunho interno de proposta
- CLOSER: follow-up após 48h sem resposta
- FORGE: validação técnica interna
- KEEPER: actualização interna de status de projecto
- LEDGER: actualização do estado financeiro interno
- VOICE: posts de educação genérica sobre IA (sem mencionar clientes ou resultados)
- VOICE: calendário de conteúdo semanal
- VOICE: posts de dicas de automação genéricas
- EDITOR: revisão e correcção de textos internos (score IA ≤ 65%, sem erros graves)

---

### Formato do session_id
Sempre único por acção: `[AGENTE]-[CLIENTE ou BMST]-[YYYYMMDD]-[HHMMSS]`
- Exemplo mensagem: `CLOSER-MDClinic-20260426-143022`
- Exemplo post: `VOICE-BMST-20260506-090000`