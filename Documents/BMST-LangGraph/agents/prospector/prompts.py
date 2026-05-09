# agents/prospector/prompts.py

from pydantic import BaseModel
from typing import Literal, Optional

# ── Weekly sector calendar ────────────────────────────────────────────────────

SECTOR_POR_DIA: dict[int, str] = {
    0: "Saúde privada",                       # Segunda
    1: "Hotelaria e Restauração",             # Terça
    2: "Retalho e Distribuição",              # Quarta
    3: "Seguros, Microfinança e Imobiliário", # Quinta
    4: "Logística, Educação e Serviços",      # Sexta
}

# ── Google Places search queries per sector ───────────────────────────────────

QUERIES_POR_SECTOR: dict[str, list[str]] = {
    "Saúde privada": [
        "clínica privada Luanda",
        "hospital privado Luanda Angola",
        "centro médico Luanda",
        "clínica dentária Luanda",
    ],
    "Hotelaria e Restauração": [
        "hotel Luanda Angola",
        "restaurante Luanda Angola",
        "resort Luanda Angola",
    ],
    "Retalho e Distribuição": [
        "supermercado Luanda Angola",
        "distribuidora Luanda Angola",
        "material de construção Luanda",
    ],
    "Seguros, Microfinança e Imobiliário": [
        "seguradora Angola Luanda",
        "imobiliária Luanda Angola",
        "microfinança Angola",
    ],
    "Logística, Educação e Serviços": [
        "transportadora Luanda Angola",
        "escola privada Luanda Angola",
        "universidade privada Angola",
        "escritório advogados Luanda",
    ],
}

# ── Classification schema ─────────────────────────────────────────────────────

class ClassificacaoEmpresaSchema(BaseModel):
    segmento: Literal["A", "B", "C"]
    qualificado: bool
    motivo_exclusao: Optional[str] = None
    pain_point: str
    oportunidade: str
    notas_abordagem: str
    servico_bmst: str
    valor_est_aoa: int
    notas_seg_c: Optional[str] = None


# ── Classification prompt ─────────────────────────────────────────────────────

CLASSIFICACAO_EMPRESA_PROMPT = """És o PROSPECTOR da BMST Angola — Fidel Kussunga a fazer prospecção pessoal.

A BMST oferece automação de comunicação para empresas angolanas:
- Chatbot WhatsApp com catálogo, marcações e resposta a perguntas frequentes
- Automação de respostas a comentários e DMs do Instagram/Facebook
- CRM integrado para gestão de leads e seguimento de clientes
- Relatórios automáticos (vendas, stock, reservas)

CRITÉRIOS DE SEGMENTO:
Seg A (NÃO qualificado — excluir):
  - Sem presença digital organizada (sem website nem Instagram activo)
  - Negócio claramente individual/familiar pequeno
  - Menos de 200 seguidores nas redes sociais
  - Sector informal

Seg B (qualificado — inserir directamente):
  - Website activo OU +500 seguidores organizados
  - Sinais de equipa visível (recepção, equipa de vendas)
  - Opera em sector formal
  - Potencial valor do contrato: 150.000–500.000 AOA/mês

Seg C (qualificado — inserir COM flag escalar_fundador):
  - Mais de 50 funcionários estimados
  - Grande grupo empresarial ou multinacional
  - Sector regulado (banca, telecoms, seguros de grande porte)
  - Potencial valor do contrato: +500.000 AOA/mês

SERVIÇOS BMST (usa o mais relevante para o caso específico):
  - "Chatbot WhatsApp — catálogo e marcações"
  - "Automação de atendimento Instagram/Facebook"
  - "CRM + seguimento de leads WhatsApp"
  - "Relatórios automáticos de vendas/stock"
  - "Sistema completo de atendimento multicanal"

Com base na informação fornecida sobre a empresa, classifica-a e gera as notas para o HUNTER.
O campo notas_abordagem é CRÍTICO — deve conter evidência específica observável (ex: "Instagram com 38
comentários sem resposta sobre preços", "Site só com telefone, sem formulário"). NUNCA genérico.

Responde APENAS com JSON válido:
{
  "segmento": "A/B/C",
  "qualificado": true/false,
  "motivo_exclusao": "string ou null",
  "pain_point": "problema específico da empresa em 1 linha",
  "oportunidade": "descrição detalhada da oportunidade de automação",
  "notas_abordagem": "evidência específica para o HUNTER personalizar a mensagem",
  "servico_bmst": "serviço mais relevante",
  "valor_est_aoa": 250000,
  "notas_seg_c": "escalar_fundador: sim" ou null
}
"""
