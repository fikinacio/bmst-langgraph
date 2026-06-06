# -*- coding: utf-8 -*-
"""
Envia 3 primeiros contactos FAB-001 a FAB-003 aprovados pelo CEO (2026-06-06).
"""

import requests
import time
import warnings
warnings.filterwarnings("ignore")

SEND_URL = "https://bmst-api.fly.dev/webhook/bmst-send-message"

mensagens = [

    # -----------------------------------------------------------------------
    # FAB-001 Novagest — score 9 — Email
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-Novagest-20260606-FAB001",
        "decisao": "aprovado",
        "email_destino": "novagest@novagest.co.ao",
        "email_assunto": "Encomendas corporativas Oil&Gas — gestão automatizada para a Novagest",
        "texto": (
            "Bom dia,\n\n"
            "A Novagest gere contratos de alimentação colectiva para clientes Oil&Gas, "
            "hospitais e escolas — um portefólio exigente, com pedidos de ementa, "
            "alterações de última hora e confirmações de volume que chegam por telefone "
            "e email a cada comercial individualmente.\n\n"
            "Quando o comercial está em campo ou numa reunião, essas mensagens ficam "
            "sem resposta. O cliente corporativo espera — ou procura outro fornecedor.\n\n"
            "Na Bisca+, desenvolvemos agentes de gestão de encomendas para empresas de "
            "catering: o cliente corporativo envia o pedido por WhatsApp, recebe "
            "confirmação automática com data, menu e volume, e o comercial é notificado "
            "apenas dos pedidos que exigem atenção humana — alterações fora do padrão, "
            "novos contratos, situações especiais.\n\n"
            "A equipa comercial concentra-se no que gera receita: novas contas e renovações.\n\n"
            "Poderia reservar 20 minutos para mostrar como funciona concretamente?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # FAB-002 Pizzaria Capricciosa — score 8 — Email
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-Capricciosa-20260606-FAB002",
        "decisao": "aprovado",
        "email_destino": "admcapricciosa@gmail.com",
        "email_assunto": "Um número único para as 4 Capricciosias — gestão central de encomendas",
        "texto": (
            "Bom dia,\n\n"
            "A Pizzaria Capricciosa opera em 4 localizações em Luanda — e os pedidos de "
            "delivery chegam por WhatsApp a números distintos por loja. Quando a linha da "
            "Maianga está ocupada, não há redireccionamento automático. O cliente espera, "
            "ou procura outro número.\n\n"
            "Sem visibilidade central, não há forma de saber quantos pedidos foram "
            "perdidos nesse intervalo.\n\n"
            "Na Bisca+, implementamos gestão de encomendas com número único: o cliente "
            "envia para um número central, o sistema identifica a loja mais próxima, "
            "confirma o tempo de entrega automaticamente e encaminha para a equipa certa "
            "— sem depender do WhatsApp pessoal de nenhum colaborador.\n\n"
            "A capacidade de atendimento cresce sem crescer a equipa.\n\n"
            "Poderia reservar 20 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # FAB-003 Tupuca+ — score 8 — WhatsApp
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-Tupuca-20260606-FAB003",
        "decisao": "aprovado",
        "whatsapp_destino": "244944909797",
        "texto": (
            "Bom dia! Sou o Fidel da Bisca+ — automatizamos processos operacionais "
            "para plataformas de delivery em Angola.\n\n"
            "A Tupuca tem 120+ restaurantes parceiros e cresce 5%/mês. A partir de "
            "certa escala, o onboarding e o suporte por telefone e email bloqueiam a "
            "expansão — a equipa de operações gasta tempo a gerir o que existe em vez "
            "de crescer.\n\n"
            "Na Bisca+, automatizamos o fluxo de onboarding de novos parceiros e o "
            "suporte de nível 1 via WhatsApp: documentação, configuração de menu, "
            "formação e relatórios — sem intervenção manual. A Tupuca pode chegar a "
            "200+ parceiros com a mesma equipa que tem hoje.\n\n"
            "Vale 20 minutos de conversa com o Erickson Mvezi?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },
]

print(f"A enviar {len(mensagens)} contactos FAB aprovados...")
print("=" * 60)

for i, msg in enumerate(mensagens, 1):
    destino = msg.get("email_destino") or msg.get("whatsapp_destino")
    canal = "email" if msg.get("email_destino") else "WA"
    print(f"[{i:02d}/03] [{canal}] {destino}...", end=" ", flush=True)
    try:
        r = requests.post(SEND_URL, json=msg, timeout=30, verify=False)
        resultado = r.json()
        status = resultado.get("status", f"? HTTP{r.status_code}")
        print(status)
    except Exception as e:
        print(f"ERRO: {e}")
    time.sleep(1)

print("\n" + "=" * 60)
print("Envio FAB concluído.")
