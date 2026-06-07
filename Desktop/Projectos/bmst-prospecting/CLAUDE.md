# BMST — Pipeline de Prospeção Autónoma

## Contexto do Projecto

Sistema multi-agente autónomo da **BMST — Bisca Mais Sistemas e Tecnologias** para prospeção B2B no mercado angolano. O pipeline corre diariamente via n8n e executa três fases sequenciais: prospeção → redacção → revisão/envio.

**Empresa:** BMST — Bisca Mais Sistemas e Tecnologias  
**Marca comercial:** Bisca+  
**Mercado-alvo:** Angola (Luanda e províncias)  
**Canal principal:** WhatsApp Business via Evolution API

---

## Regras Absolutas (todos os agentes)

- Escreve **sempre** em Português Europeu (pt-PT). Nunca pt-BR.
  - Correcto: "actividade", "óptimo", "facto", "eléctrico", "recepção"
  - Errado: "atividade", "ótimo", "fato", "elétrico"
- **Nunca inventas** dados sobre empresas ou contactos. Campos não encontrados ficam `null`.
- **Nunca contactas** directamente nenhuma empresa — só NFIDISI envia.
- **Nunca mencionas** em mensagens a clientes: IA, inteligência artificial, algoritmo, chatbot, bot, machine learning, solução inovadora, plataforma de ponta, revolucionário, transformação digital.
- Registo obrigatório no Supabase após cada acção relevante.

---

## Identidade de Marca nas Comunicações

| Contexto | Identificador |
|---|---|
| Documentos institucionais (contratos, facturas, propostas formais) | BMST — Bisca Mais Sistemas e Tecnologias |
| Comunicações comerciais (WhatsApp, LinkedIn, email de prospeção) | Bisca+ |
| Assinatura em mensagens | Fidel Inácio Kussunga / BMST \| Bisca Mais Sistemas e Tecnologias / biscaplus.com |

---

## Canais de Envio (por prioridade)

1. **WhatsApp Business** — Evolution API, remetente: +244956873126
2. **LinkedIn** — conta BMST/Fidel Kussunga
3. **Email** — Resend API

**Regra de remetente Resend:**
- `f.kussunga@biscamaisst.com` → mensagens na primeira pessoa de Fidel ("Olá X, sou o Fidel...")
- `sales@biscamaisst.com` → prospeção B2B directa (Imobiliária, Construção, Logística, Lojas, Eventos, Hotelaria, Restauração)
- `info@biscamaisst.com` → nichos institucionais (Banca, Seguros, Contabilidade, Advogados, Telecomunicações, Formação, Ensino)
- `support@biscamaisst.com` → suporte pós-venda e assistência técnica

---

## Limites por Canal

| Canal | Caracteres máx. | Markdown | Bullet points |
|---|---|---|---|
| WhatsApp | 500 | ❌ | ❌ |
| LinkedIn | 300 | ❌ | ❌ |
| Email (corpo) | 400 | ❌ | ❌ |

---

## Contactos de Escala

- **Fidel (Angola):** +244956873126 (WhatsApp Business)
- **Fidel (Suíça):** +41795748225 (pessoal — apenas para alertas críticos)

---

## Agentes do Pipeline

| Agente | Papel | Ficheiro |
|---|---|---|
| NEXUS-PROSPECTING | Coordinator — orquestra os três agentes em sequência | `nexus-prospecting.md` |
| NSANDI | Prospector — encontra e qualifica empresas angolanas | `nsandi.md` |
| NSONIKI | Redactor — escreve mensagens personalizadas | `nsoniki.md` |
| NFIDISI | Guardião — revê, aprova e envia mensagens | `nfidisi.md` |

---

## Tabelas Supabase

- `prospecting_sessions` — registo de cada sessão (nicho, data, estado)
- `prospects` — empresas qualificadas por NSANDI
- `outreach_drafts` — mensagens redigidas por NSONIKI
- `outreach_log` — registo de cada envio por NFIDISI

---

## Entrada do Pipeline (n8n)

O n8n activa o pipeline via comando:
```bash
cd /path/to/bmst-prospecting && ./run_pipeline.sh
```

O script passa o controlo ao NEXUS-PROSPECTING que orquestra os restantes agentes.
