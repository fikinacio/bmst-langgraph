# -*- coding: utf-8 -*-
"""
CLOSER — Follow-up B FAB-001 e FAB-002.
Enviar a 12 Jun 2026 (qui) se sem resposta ao primeiro contacto de 6 Jun.
Accao autonoma (CLAUDE.md) — sem aprovacao CEO necessaria.
"""

import requests
import time
import warnings
warnings.filterwarnings("ignore")

SEND_URL = "https://bmst-api.fly.dev/webhook/bmst-send-message"

mensagens = [

    # -----------------------------------------------------------------------
    # FAB-001 Novagest — score 9
    # Ângulo novo: custo real de um contrato Oil&Gas não renovado
    # Um cliente que não recebe resposta a tempo não reclama — não renova.
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-Novagest-20260612-FAB001-FUB",
        "decisao": "aprovado",
        "email_destino": "novagest@novagest.co.ao",
        "email_assunto": "Re: Encomendas corporativas Oil&Gas — gestão automatizada para a Novagest",
        "texto": (
            "Bom dia,\n\n"
            "Escrevi na semana passada sobre automação de encomendas na Novagest. "
            "Acrescento um ângulo que raramente aparece nas análises de catering: "
            "a razão mais comum de não renovação de um contrato de alimentação colectiva "
            "não é o preço — é a acumulação de pequenas falhas de comunicação ao longo "
            "do contrato.\n\n"
            "O cliente corporativo não liga para reclamar. Aguarda o fim do contrato "
            "e adjudica ao concorrente. Quando a Novagest percebe, o contrato já foi "
            "para outra empresa.\n\n"
            "Um sistema de gestão de encomendas com confirmação automática e histórico "
            "de cada pedido por cliente cria exactamente o registo que prova ao cliente "
            "que cada pedido foi tratado — e que elimina a acumulação silenciosa de "
            "insatisfação.\n\n"
            "Vale 20 minutos de conversa esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # FAB-002 Pizzaria Capricciosa — score 8
    # Ângulo novo: o cliente angolano já compara com apps de delivery
    # Plataformas respondem em 30 segundos — quando a Capricciosa demora
    # mais, o app de delivery ganha o pedido.
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-Capricciosa-20260612-FAB002-FUB",
        "decisao": "aprovado",
        "email_destino": "admcapricciosa@gmail.com",
        "email_assunto": "Re: Um número único para as 4 Capricciosias — gestão central de encomendas",
        "texto": (
            "Bom dia,\n\n"
            "Escrevi na semana passada sobre gestão de encomendas na Capricciosa. "
            "Um dado do mercado angolano que vale considerar: plataformas como a Tupuca+ "
            "confirmam pedidos em menos de 30 segundos. O cliente que envia mensagem "
            "para a Capricciosa e não recebe resposta imediata sabe que tem alternativas "
            "a um clique de distância.\n\n"
            "A Capricciosa tem um produto superior — pizzaria própria, ingredientes "
            "frescos, reputação de 20 anos em Luanda. O problema não é o produto, "
            "é o tempo de resposta.\n\n"
            "Com um número único e confirmação automática, a Capricciosa responde "
            "ao mesmo ritmo das plataformas — sem ceder a margem à comissão do delivery.\n\n"
            "Poderia reservar 20 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
]

# ---------------------------------------------------------------------------
# Execução — correr a 12 Jun 2026
# ---------------------------------------------------------------------------

print(f"CLOSER — Follow-up B FAB | {len(mensagens)} emails")
print("Enviar a: 12 Jun 2026 (qui) — sem resposta desde 6 Jun")
print("=" * 60)

for i, msg in enumerate(mensagens, 1):
    destino = msg["email_destino"]
    print(f"[{i:02d}/02] {destino}...", end=" ", flush=True)
    try:
        r = requests.post(SEND_URL, json=msg, timeout=30, verify=False)
        status = r.json().get("status", f"? HTTP{r.status_code}")
        print(status)
    except Exception as e:
        print(f"ERRO: {e}")
    time.sleep(1)

print("\n" + "=" * 60)
print("Follow-ups B FAB concluidos.")
