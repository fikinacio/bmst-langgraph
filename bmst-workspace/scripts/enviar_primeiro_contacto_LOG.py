# -*- coding: utf-8 -*-
"""
CLOSER — Primeiro contacto LOG-001 a LOG-006
Sector: Distribuição e Logística
Aprovado pelo CEO: 2026-06-11
"""

import requests
import time
import warnings
warnings.filterwarnings("ignore")

SEND_URL = "https://bmst-api.fly.dev/webhook/bmst-send-message"

mensagens = [

    # -----------------------------------------------------------------------
    # LOG-001 Unicargas Angola — score 8
    # Dor: dispatcher coordena 40+ entregas/dia por WA individual, sem registo
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-Unicargas-20260611-100000",
        "decisao": "aprovado",
        "email_destino": "info@unicargas.co.ao",
        "email_assunto": "Coordenação de entregas e confirmações — Unicargas Angola",
        "texto": (
            "Bom dia,\n\n"
            "Com 40 ou mais entregas por dia, o dispatcher da Unicargas coordena condutores "
            "por WhatsApp um a um — 'chegaste?', 'confirmou a descarga?', 'qual o ETA para Malanje?'. "
            "Cada entrega gera várias mensagens sem registo estruturado.\n\n"
            "Criámos uma forma de o condutor confirmar a entrega por WhatsApp com código único, "
            "o cliente assinar digitalmente e o registo ficar automático — sem passar pelo dispatcher.\n\n"
            "15 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126 | biscaplus.com"
        ),
    },

    # -----------------------------------------------------------------------
    # LOG-002 Macon Angola — score 8
    # Dor: encomendas de retalhistas por WA ao representante, confirmação manual de stock
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-Macon-20260611-100100",
        "decisao": "aprovado",
        "email_destino": "geral@macon.co.ao",
        "email_assunto": "Encomendas de retalhistas via WhatsApp — Macon Angola",
        "texto": (
            "Bom dia,\n\n"
            "Retalhistas que trabalham com a Macon enviam as suas encomendas por WhatsApp "
            "ao representante — lista de produtos, quantidades, prazo. O representante valida "
            "stock e confirma manualmente. Com dezenas de retalhistas activos, o volume torna "
            "o processo lento e sujeito a erros.\n\n"
            "Criámos um fluxo de encomenda por WhatsApp que confirma stock e data de entrega "
            "automaticamente, sem intermediário manual.\n\n"
            "15 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126 | biscaplus.com"
        ),
    },

    # -----------------------------------------------------------------------
    # LOG-003 Transnama — score 7
    # Dor: actualizações de fronteira Angola-Namíbia por WA sem registo automático
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-Transnama-20260611-100200",
        "decisao": "aprovado",
        "email_destino": "transnama@transnama.co.ao",
        "email_assunto": "Rastreio de atravessamento de fronteiras — Transnama",
        "texto": (
            "Bom dia,\n\n"
            "Na rota Angola–Namíbia, os condutores da Transnama comunicam o estado de cada "
            "fronteira por WhatsApp — 'estou na fronteira', 'passou', 'retido por falta de "
            "documento'. A equipa em Luanda notifica o cliente manualmente, sem registo "
            "automático de tempos ou ocorrências.\n\n"
            "Criámos uma forma de o condutor enviar actualizações de fronteira por WA que se "
            "registam automaticamente e notificam o cliente em tempo real.\n\n"
            "15 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126 | biscaplus.com"
        ),
    },

    # -----------------------------------------------------------------------
    # LOG-004 DHL Express Angola — score 7
    # Dor: perguntas de tracking chegam por WA pessoal dos agentes, resposta manual
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-DHL-20260611-100300",
        "decisao": "aprovado",
        "email_destino": "customerservice.angola@dhl.com",
        "email_assunto": "Rastreio de envios por WhatsApp — DHL Angola",
        "texto": (
            "Bom dia,\n\n"
            "Uma parte significativa das perguntas ao serviço de cliente da DHL Angola "
            "— 'onde está o meu pacote?', 'há taxas a pagar?', 'quando chega?' — chega "
            "por WhatsApp pessoal aos agentes, fora do sistema de tracking. "
            "A resposta é manual e demorada.\n\n"
            "Criámos um canal WhatsApp central que responde automaticamente com o estado "
            "do envio pelo número de rastreio e encaminha os casos complexos para o agente humano.\n\n"
            "15 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126 | biscaplus.com"
        ),
    },

    # -----------------------------------------------------------------------
    # LOG-005 Grupo Carrinho Logística — score 7
    # Dor: pedidos de reposição entre 65 lojas por WA, gestor como hub de mensagens
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-GrupoCarrinho-20260611-100400",
        "decisao": "aprovado",
        "email_destino": "logistica@grupocarrinho.co.ao",
        "email_assunto": "Transferências de stock entre lojas — Grupo Carrinho",
        "texto": (
            "Bom dia,\n\n"
            "Com 65 lojas em Angola, a equipa de logística do Carrinho recebe pedidos de "
            "reposição urgente por WhatsApp — 'a loja da Viana ficou sem arroz, há stock "
            "no armazém de Luanda Norte?'. Sem sistema centralizado, o gestor de logística "
            "é o hub de todas as mensagens.\n\n"
            "Criámos uma forma de as lojas pedirem transferência de stock por WA de forma "
            "estruturada, com confirmação automática de disponibilidade e ETA de entrega.\n\n"
            "15 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126 | biscaplus.com"
        ),
    },

    # -----------------------------------------------------------------------
    # LOG-006 Pumangol Logística — score 8
    # Dor: confirmações de entrega de combustível por WA, reconciliação manual fim do dia
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-Pumangol-20260611-100500",
        "decisao": "aprovado",
        "email_destino": "info@pumangol.com",
        "email_assunto": "Confirmação de entregas de combustível — Pumangol",
        "texto": (
            "Bom dia,\n\n"
            "Os condutores de cisterna da Pumangol confirmam cada entrega por WhatsApp "
            "— litros descarregados, ponto de entrega, assinatura do cliente. Sem sistema "
            "estruturado, a reconciliação entre o planeado e o entregue é feita manualmente "
            "no fim de cada dia.\n\n"
            "Criámos uma forma de o condutor registar a entrega por WA com os dados "
            "estruturados, actualizando automaticamente o relatório diário de distribuição.\n\n"
            "15 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126 | biscaplus.com"
        ),
    },
]

print(f"CLOSER — Primeiro contacto LOG | {len(mensagens)} emails")
print("Aprovado pelo CEO: 2026-06-11")
print("=" * 60)

resultados = []
for i, msg in enumerate(mensagens, 1):
    destino = msg["email_destino"]
    print(f"[{i:02d}/{len(mensagens)}] {destino}...", end=" ", flush=True)
    try:
        r = requests.post(SEND_URL, json=msg, timeout=30, verify=False)
        status = r.json().get("status", f"? HTTP{r.status_code}")
        print(status)
        resultados.append({"id": msg["session_id"], "destino": destino, "status": status})
    except Exception as e:
        print(f"ERRO: {e}")
        resultados.append({"id": msg["session_id"], "destino": destino, "status": "ERRO"})
    time.sleep(1)

print("\n" + "=" * 60)
ok = sum(1 for r in resultados if r["status"] == "enviado")
print(f"{ok}/{len(mensagens)} enviados com sucesso.")
