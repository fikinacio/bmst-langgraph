# -*- coding: utf-8 -*-
"""
CLOSER — Primeiro contacto SEG-001 a SEG-006
Sector: Seguros — Seguradoras e Resseguradoras Angola
Aprovado pelo CEO: 2026-06-11
"""

import requests
import time
import warnings
warnings.filterwarnings("ignore")

SEND_URL = "https://bmst-api.fly.dev/webhook/bmst-send-message"

mensagens = [
    {
        "session_id": "CLOSER-NOSSA-20260611-160000",
        "decisao": "aprovado",
        "email_destino": "geral@nossaseguros.ao",
        "email_assunto": "Participação de sinistros por WhatsApp — NOSSA Seguros",
        "texto": (
            "Bom dia,\n\n"
            "Os clientes da NOSSA Seguros participam sinistros por WhatsApp ao agente com fotos "
            "e documentos. Sem canal centralizado, não há número de referência automático e o "
            "cliente não sabe se a participação foi recebida.\n\n"
            "Criámos um canal de participação de sinistros que cria caso automaticamente, confirma "
            "recepção com referência e notifica o perito responsável — sem depender do agente.\n\n"
            "15 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
    {
        "session_id": "CLOSER-AAA-20260611-160100",
        "decisao": "aprovado",
        "email_destino": "info@aaaseguros.ao",
        "email_assunto": "Renovação automática de apólices — AAA Seguros",
        "texto": (
            "Bom dia,\n\n"
            "Os agentes da AAA contactam cada cliente individualmente por WhatsApp nas semanas "
            "antes do vencimento da apólice. Com centenas de renovações anuais, o processo é "
            "lento e há risco de perder clientes não contactados a tempo.\n\n"
            "Criámos um sistema de renovação automática — lembrete a 30, 15 e 3 dias do "
            "vencimento, com confirmação de renovação sem intervenção do agente.\n\n"
            "15 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
    {
        "session_id": "CLOSER-Garantia-20260611-160200",
        "decisao": "aprovado",
        "email_destino": "geral@garantia.ao",
        "email_assunto": "Recolha de documentação para apólice empresarial — Garantia Angola",
        "texto": (
            "Bom dia,\n\n"
            "Para emitir uma apólice empresarial, a Garantia precisa recolher listagens de "
            "viaturas, folhas de remunerações e certidões. Esta documentação chega por WhatsApp "
            "ao mediador em formatos variados e frequentemente incompleta, atrasando a emissão.\n\n"
            "Criámos um fluxo de recolha estruturada por WhatsApp que valida a completude e "
            "encaminha automaticamente para a área técnica.\n\n"
            "15 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
    {
        "session_id": "CLOSER-FidelidadeAngola-20260611-160300",
        "decisao": "aprovado",
        "email_destino": "fidelidade@fidelidade.ao",
        "email_assunto": "Canal único de atendimento multi-produto — Fidelidade Angola",
        "texto": (
            "Bom dia,\n\n"
            "Os clientes da Fidelidade Angola com múltiplos produtos — auto, saúde, habitação "
            "— contactam o agente por WhatsApp pessoal para qualquer questão. Sem canal central, "
            "não há visibilidade do portfólio do cliente nem das oportunidades de venda cruzada.\n\n"
            "Criámos um canal corporativo que consolida a comunicação e sinaliza automaticamente "
            "oportunidades de venda cruzada ao agente.\n\n"
            "15 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
    {
        "session_id": "CLOSER-GlobalSeguros-20260611-160400",
        "decisao": "aprovado",
        "email_destino": "info@globalseguros.ao",
        "email_assunto": "Qualificação de leads de seguro auto por WhatsApp — Global Seguros",
        "texto": (
            "Bom dia,\n\n"
            "Potenciais clientes que querem seguro auto contactam a Global Seguros por WhatsApp "
            "a pedir simulações — matrícula, ano do veículo, uso. O agente responde manualmente "
            "a cada pedido, incluindo veículos fora do perfil de risco.\n\n"
            "Criámos um fluxo que qualifica o lead, calcula o prémio indicativo e só encaminha "
            "ao agente os pedidos dentro do perfil de subscrição.\n\n"
            "15 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
    {
        "session_id": "CLOSER-ENSA-20260611-160500",
        "decisao": "aprovado",
        "email_destino": "info@ensa.ao",
        "email_assunto": "Canal único de participação de sinistros — ENSA",
        "texto": (
            "Bom dia,\n\n"
            "A ENSA gere o maior volume de sinistros de Angola, mas o canal de participação é "
            "descentralizado — cada agência recebe por balcão, telefone ou WhatsApp pessoal. "
            "Sem centralização, os tempos de resposta variam e o cliente sem resposta recorre "
            "à reclamação.\n\n"
            "Criámos um canal único de participação por WhatsApp com confirmação automática "
            "e rastreio de estado.\n\n"
            "15 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
]

print(f"CLOSER — Primeiro contacto SEG | {len(mensagens)} emails")
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
        resultados.append({"destino": destino, "status": status})
    except Exception as e:
        print(f"ERRO: {e}")
        resultados.append({"destino": destino, "status": "ERRO"})
    time.sleep(1)

print("\n" + "=" * 60)
ok = sum(1 for r in resultados if r["status"] == "enviado")
print(f"{ok}/{len(mensagens)} enviados com sucesso.")
