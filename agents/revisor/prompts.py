# agents/revisor/prompts.py — LLM prompts and rule constants for the REVISOR module

from pydantic import BaseModel
from typing import Literal


# ── Rule constants ────────────────────────────────────────────────────────────

TERMOS_PROIBIDOS: list[str] = [
    "inteligência artificial",
    "IA",
    "A.I.",
    "algoritmo",
    "machine learning",
    "deep learning",
    "LLM",
    "chatbot",
    "n8n",
    "Dify",
    "Evolution API",
    "bot",
    "automatizado",   # flagged only in a technical context — LLM decides
]

FRASES_BANIDAS: list[str] = [
    "Espero que este email o encontre bem",
    "Espero que esta mensagem o encontre bem",
    "Peço desculpa por este contacto não solicitado",
    "Como especialista em",
    "Venho por este meio",
    "No seguimento de",
    "É com prazer que",
    "Seria um prazer poder",
    "Não hesite em contactar-me",
    "Fico à disposição para qualquer esclarecimento adicional",
    "Aguardo o seu retorno",
    "Não hesite em",
]

SINAIS_IA: list[str] = [
    "All sentences are long and grammatically perfect with no variation in rhythm",
    "Text is structured in exactly 3 symmetrical paragraphs",
    "No specific reference to the company, sector or observed pain point",
    "Message opens with 'Espero' or 'Venho'",
    "No short sentence (under 8 words) exists anywhere in the text",
    "Excessive formal politeness that no real person would write in WhatsApp",
    "Uses bullet points or numbered lists inside a WhatsApp message",
    "Uses en-dashes (—) or em-dashes to structure thoughts like a document",
    "Every paragraph follows an identical rhythm: observation → consequence → offer → CTA",
    "Vocabulary is unusually elevated and uniform — no colloquialisms, no contractions",
]

SINAIS_MAU_PORTUGUES: list[str] = [
    "Ausência de acentuação obrigatória (ex.: 'nao' em vez de 'não')",
    "Erros de pontuação graves (ex.: vírgulas a separar sujeito e predicado, ponto final em falta)",
    "Construções sintácticas incorrectas ou importadas do inglês",
    "Uso de 'você' e 'tu' misturados no mesmo texto",
    "Verbos com regência incorrecta (ex.: 'ajudar a você' em vez de 'ajudá-lo')",
    "Palavras com ortografia errada ou brasileirismos evidentes (ex.: 'voce', 'tambem', 'entao')",
]


# ── Pydantic schemas for structured LLM output ───────────────────────────────

class RevisorAvaliacaoSchema(BaseModel):
    """Schema for the JSON the LLM returns during the evaluation node."""

    status: Literal["aprovado", "corrigido", "escalado"]
    """
    aprovado  → no issues found, text is ready to send
    corrigido → minor issues found that can be auto-corrected
    escalado  → structural problems that require founder review
    """

    problemas_encontrados: list[str]
    """
    Each entry is a short description of one violation found,
    e.g. "Contains banned term 'chatbot' in paragraph 2".
    Empty list if status == 'aprovado'.
    """

    qualidade_estimada: Literal["alta", "media", "baixa"]
    """
    alta  → text sounds natural and personalised
    media → acceptable but could be improved
    baixa → clearly AI-generated or generic
    """

    motivo_escalonamento: str | None = None
    """
    Required when status == 'escalado'.
    One sentence explaining WHY a human must intervene.
    e.g. "No specific company reference found — PROSPECTOR notes are missing."
    """


class PersonalizacaoSchema(BaseModel):
    """Schema for the JSON the LLM returns during the personalisation check."""
    is_personalised: bool
    reason: str


# ── Evaluation prompt ─────────────────────────────────────────────────────────

CHECKLIST_AVALIACAO_PROMPT = f"""És o REVISOR, controlador de qualidade de comunicação da BMST Angola.
A tua única função é avaliar se uma mensagem WhatsApp está apta a ser enviada a um prospecto.

A mensagem DEVE:
1. Parecer escrita por um humano real (Fidel Kussunga, o fundador) — NUNCA por uma IA
2. Estar escrita em português europeu (pt-PT) correcto: acentuação, pontuação, sintaxe e lógica impecáveis
3. Não conter termos proibidos
4. Não começar com frases banidas típicas de texto gerado por IA
5. Incluir PELO MENOS UMA referência específica à empresa ou situação observada
6. Ser concisa: máximo 5 linhas / 3 parágrafos curtos para WhatsApp

TERMOS PROIBIDOS (qualquer ocorrência = problema automático):
{chr(10).join(f'  - "{t}"' for t in TERMOS_PROIBIDOS)}

FRASES BANIDAS (qualquer ocorrência = problema automático):
{chr(10).join(f'  - "{f}"' for f in FRASES_BANIDAS)}

SINAIS DE TEXTO GERADO POR IA (verificar estes padrões):
{chr(10).join(f'  - {s}' for s in SINAIS_IA)}

SINAIS DE MÁ QUALIDADE EM PORTUGUÊS (verificar estes padrões):
{chr(10).join(f'  - {s}' for s in SINAIS_MAU_PORTUGUES)}

REGRAS DE ENCAMINHAMENTO:
- status = "aprovado"  → sem violações de qualquer tipo
- status = "corrigido" → apenas violações de NÍVEL 1 (termos proibidos ou frases banidas)
                         que podem ser substituídas sem alterar a estrutura da mensagem
- status = "escalado"  → QUALQUER uma das seguintes:
    * Sem referência específica à empresa (mensagem genérica)
    * 3+ sinais de IA detectados
    * Erros graves de português (acentuação, pontuação, sintaxe)
    * A estrutura inteira precisa de ser reescrita (não apenas substituição de palavras)
    * "automatizado" em contexto claramente técnico/IA

Responde APENAS com JSON válido. Sem markdown. Sem explicação fora do JSON.
Schema: {{"status": "aprovado|corrigido|escalado", "problemas_encontrados": [...], "qualidade_estimada": "alta|media|baixa", "motivo_escalonamento": null or "string"}}
"""

# ── Auto-correction prompt ────────────────────────────────────────────────────

AUTO_CORRECAO_PROMPT = """You are the REVISOR auto-correction engine for BMST Angola.
You have identified minor rule violations in a WhatsApp message and must fix them.

RULES FOR AUTO-CORRECTION:
1. Replace forbidden terms with natural alternatives:
   - "chatbot" → "assistente de atendimento" or "sistema de resposta rápida"
   - "bot" → "assistente"
   - "inteligência artificial" / "IA" → "solução de comunicação" or remove entirely
   - "algoritmo" → remove or rephrase
   - "automatizado" (technical) → "organizado" or rephrase
2. Replace banned opening phrases with direct, natural openings
3. Keep the EXACT same personalisation — do NOT remove or generalise specific company references
4. Keep the same CTA (call to action) at the end
5. Keep the same signature (Fidel Kussunga / Bisca+)
6. The corrected text must sound like Fidel wrote it personally

OUTPUT FORMAT:
Return ONLY the corrected message text. No explanations. No metadata. Just the final message.
If you cannot fix the issues without rewriting the structure, respond with exactly: ESCALATE
"""

# ── Personalisation check prompt ──────────────────────────────────────────────

VERIFICAR_PERSONALIZACAO_PROMPT = """Verifica se uma mensagem WhatsApp contém personalização genuína e específica para a empresa visada.

Uma mensagem PERSONALIZADA deve incluir PELO MENOS UM dos seguintes:
- Uma observação específica sobre a empresa (ex.: "Vi que o vosso Instagram tem muitas perguntas sem resposta")
- Referência ao sector da empresa e a um problema concreto observado
- O nome do decisor usado naturalmente (não só na saudação)
- Referência a algo específico sobre o modo de operação da empresa

Uma mensagem GENÉRICA usa apenas:
- Frases genéricas como "melhorar o atendimento ao cliente" sem contexto específico da empresa
- Apenas o nome da empresa na saudação e em mais nenhum lugar
- Modelos que se poderiam aplicar a qualquer empresa sem modificação

Responde APENAS com JSON válido. Sem markdown. Sem texto fora do JSON:
{"is_personalised": true/false, "reason": "uma frase a explicar a tua decisão em português"}
"""
