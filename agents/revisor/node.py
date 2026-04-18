"""
Nó REVISOR — partilhado por HUNTER, CLOSER e DELIVERY
Não tem graph próprio; é invocado directamente pelos outros agentes.
"""
from typing import Literal
from core.llm import get_llm_fast
from agents.revisor.prompts import (
    SYSTEM_PROMPT,
    TERMOS_PROIBIDOS,
    ABERTURAS_BANIDAS,
    OUTPUT_APROVADO,
    OUTPUT_CORRIGIDO,
    OUTPUT_ESCALADO,
    TELEGRAM_APROVACAO_TEMPLATE,
)


def revisor_avaliar(
    texto: str,
    empresa: str,
    segmento: Literal["A", "B", "C"],
    canal: Literal["WhatsApp", "Email"],
    agente: Literal["HUNTER", "CLOSER", "DELIVERY"],
) -> dict:
    """
    Avalia o texto e devolve um dict com:
    - status: "aprovado" | "corrigido" | "escalado"
    - texto_final: texto a enviar ao cliente
    - aprovado: bool
    - notas: str
    - mensagem_telegram: str (para enviar ao fundador)
    - texto_sugerido: str (apenas quando escalado)
    """
    llm = get_llm_fast()

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"Contexto:\n"
        f"- Empresa: {empresa}\n"
        f"- Segmento: {segmento}\n"
        f"- Canal: {canal}\n"
        f"- Agente origem: {agente}\n\n"
        f"Texto a avaliar:\n{texto}\n\n"
        f"Termos proibidos a verificar: {', '.join(TERMOS_PROIBIDOS)}\n"
        f"Aberturas banidas: {ABERTURAS_BANIDAS[:5]}\n\n"
        f"Avalia o texto e responde em JSON com campos:\n"
        f"  status ('aprovado'|'corrigido'|'escalado'),\n"
        f"  texto_final (texto corrigido ou original),\n"
        f"  problemas_encontrados (lista),\n"
        f"  qualidade ('Alta'|'Média'|'Baixa'),\n"
        f"  motivo_escalamento (se aplicável),\n"
        f"  texto_sugerido (se escalado)"
    )

    response = llm.invoke(prompt)
    # TODO: parsear JSON do response

    # Placeholder — substituir por parse real do JSON do LLM
    resultado_raw = {
        "status": "aprovado",
        "texto_final": texto,
        "problemas_encontrados": [],
        "qualidade": "Alta",
        "motivo_escalamento": None,
        "texto_sugerido": None,
    }

    status = resultado_raw["status"]
    texto_final = resultado_raw["texto_final"]
    problemas = resultado_raw["problemas_encontrados"]
    qualidade = resultado_raw["qualidade"]

    revisoes = ", ".join(problemas) if problemas else "nenhuma"

    mensagem_telegram = TELEGRAM_APROVACAO_TEMPLATE.format(
        empresa=empresa,
        segmento=segmento,
        canal=canal,
        agente=agente,
        texto_final=texto_final,
        revisoes=revisoes,
        qualidade=qualidade,
    )

    return {
        "status": status,
        "texto_final": texto_final,
        "aprovado": status in ("aprovado", "corrigido"),
        "notas": revisoes,
        "mensagem_telegram": mensagem_telegram,
        "texto_sugerido": resultado_raw.get("texto_sugerido"),
    }
