# Como Criar e Instalar o Skill `bmst-angola-prospector`

## O que é um Skill no Cowork / Claude for Desktop

Um skill é um ficheiro `SKILL.md` que dás ao Claude para ele saber exactamente
como executar uma tarefa repetitiva. É como uma instrução permanente que o Claude
lê antes de agir — sem precisares de explicar tudo de novo em cada sessão.

O skill `bmst-angola-prospector` diz ao Claude:
- Que dia é hoje → que sector pesquisar
- Como encontrar as empresas (web search)
- Como analisar oportunidades de automação
- Como preencher o Google Sheet
- Como escrever o relatório para o Telegram

---

## Passo a Passo — Criar o Skill

### Opção A — Via Claude.ai (Projects) ← MAIS SIMPLES

1. Vai a **claude.ai → Projects → BMST Angola — Agentes IA**
2. Em **"Project Knowledge"**, faz upload do ficheiro `SKILL.md` desta pasta
3. Renomeia para `SKILL_bmst-angola-prospector.md` (para ficar identificável)
4. O skill fica disponível para todas as conversas dentro deste projecto

**Limitação:** Este método funciona bem para conversas manuais no projecto.
Para execução automática agendada precisas da Opção B.

---

### Opção B — Via Claude for Desktop (Cowork) ← PARA AUTOMAÇÃO

O Cowork lê skills de uma pasta no teu computador.

**No macOS:**
```bash
# Cria a pasta do skill
mkdir -p ~/Library/Application\ Support/Claude/skills/bmst-angola-prospector

# Copia o SKILL.md para lá
cp SKILL.md ~/Library/Application\ Support/Claude/skills/bmst-angola-prospector/SKILL.md
```

**No Windows:**
```powershell
# Cria a pasta do skill
mkdir "$env:APPDATA\Claude\skills\bmst-angola-prospector"

# Copia o SKILL.md
copy SKILL.md "$env:APPDATA\Claude\skills\bmst-angola-prospector\SKILL.md"
```

**Verifica que o skill está a ser lido:**
Abre o Cowork e escreve:
```
Usa o skill bmst-angola-prospector e diz-me que sector é o de hoje.
```
Se responder com o sector correcto para o dia da semana, está instalado.

---

### Opção C — Via n8n (execução automática)

Para execuções automáticas às 08h00, o n8n chama o Claude API directamente
com o conteúdo do SKILL.md no system prompt.

**Workflow n8n — Schedule → Claude API → Google Sheets → Telegram:**

```
Trigger: Cron (0 8 * * 1-5) — 08h00 UTC+1, seg a sex

Nó 1: Code — Determina o sector do dia
const dias = {
  1: "Saúde privada",      // Segunda
  2: "Hotelaria e Restauração",  // Terça
  3: "Retalho e Distribuição",   // Quarta
  4: "Seguros, Microfinança e Imobiliário",  // Quinta
  5: "Logística, Educação e Serviços"  // Sexta
};
const diaSemana = new Date().getDay();
return { sector: dias[diaSemana] };

Nó 2: HTTP Request → Claude API
System: [conteúdo completo do SKILL.md]
User: "Executa a sessão de prospecção de hoje. Sector: {{$json.sector}}.
       Data: {{$today}}. Sheet ID: {{$env.SHEET_ID}}"

Nó 3: Google Sheets → Insere leads (n8n processa resposta do Claude)

Nó 4: Telegram → Envia relatório ao fundador
```

**Variáveis de ambiente necessárias no n8n:**
```
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_SHEET_ID=[ID do teu Google Sheet]
TELEGRAM_BOT_TOKEN=[token do bot]
TELEGRAM_CHAT_ID=[teu chat ID]
```

---

## Como Activar o MCP do Google Sheets no Cowork

Para o Cowork escrever directamente no Google Sheet precisas do MCP do Google:

1. Vai a **claude.ai → Settings → Integrations (ou Connectors)**
2. Liga o **Google Sheets** (ou Google Drive)
3. Autoriza o acesso à tua conta Google
4. O Sheet `leads_angola` passa a ser acessível directamente pelo Claude

**Ou via MCP local no Claude for Desktop:**
```json
// Em ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "google-sheets": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-google-sheets"],
      "env": {
        "GOOGLE_SERVICE_ACCOUNT_KEY": "/caminho/para/service-account.json"
      }
    }
  }
}
```

---

## Testar o Skill Manualmente

Antes de activar o agendamento automático, testa manualmente:

```
Executa o skill bmst-angola-prospector.
Sector de hoje: Saúde privada.
Pesquisa 5 clínicas privadas em Luanda (teste — não inserires no sheet ainda).
Mostra-me o output que produzirias para cada empresa.
```

Verifica:
- [ ] O sector está correcto para o dia
- [ ] As empresas encontradas são Seg B (não lojas de bairro)
- [ ] O `pain_point` é específico (não genérico)
- [ ] O `notas_abordagem` tem evidência concreta
- [ ] Nenhum campo usa "IA", "algoritmo", "machine learning"
- [ ] O WhatsApp está no formato correcto (+244...)
- [ ] O relatório de sessão está no formato do Telegram

---

## Estrutura Final de Ficheiros do Skill

```
bmst-angola-prospector/
└── SKILL.md    ← este ficheiro é tudo o que precisas
```

Um skill é sempre apenas um `SKILL.md`. Não há mais ficheiros necessários.
Toda a lógica está nas instruções do SKILL.md.

---

## Ficheiro Google Sheet — Como Criar

1. Vai a **sheets.google.com** → Criar nova folha
2. Renomeia a aba para `leads_angola`
3. Na linha 1, cria os cabeçalhos (colunas A a W):

```
id | data_registo | empresa | sector | segmento | responsavel | cargo |
whatsapp | email | website | instagram | localizacao | nr_funcionarios |
servico_bmst | pain_point | valor_est_aoa | notas_abordagem | notas |
oportunidade | fonte | estado_hunter | data_hunter | resposta
```

4. Partilha o sheet com o email da tua Service Account do Google Cloud
   (ou deixa público com permissão de edição se for só para uso interno)
5. Copia o Sheet ID do URL:
   `https://docs.google.com/spreadsheets/d/[ESTE_É_O_ID]/edit`
6. Guarda o ID nas variáveis de ambiente do n8n como `GOOGLE_SHEET_ID`
