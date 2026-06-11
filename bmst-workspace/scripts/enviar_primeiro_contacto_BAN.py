# -*- coding: utf-8 -*-
"""
CLOSER — Primeiro contacto BAN-001 a BAN-006
Sector: Banca e Microfinanças
Aprovado pelo CEO: 2026-06-11
"""

import requests
import time
import warnings
warnings.filterwarnings("ignore")

SEND_URL = "https://bmst-api.fly.dev/webhook/bmst-send-message"

mensagens = [
    {
        "session_id": "CLOSER-BAI-20260611-150000",
        "decisao": "aprovado",
        "email_destino": "geral@bancobai.ao",
        "email_assunto": "Canais de atendimento ao cliente — BAI",
        "texto": (
            "Bom dia,\n\n"
            "As agências do BAI recebem diariamente um volume considerável de mensagens "
            "no WhatsApp pessoal dos gestores — saldos, bloqueio de cartões, pedidos de crédito. "
            "Sem canal centralizado, cada agência responde de forma diferente e o gestor perde "
            "tempo em perguntas repetitivas.\n\n"
            "Criámos um canal de atendimento central que responde automaticamente às questões "
            "frequentes, encaminha reclamações e qualifica pedidos de crédito antes de chegarem "
            "ao gestor.\n\n"
            "15 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
    {
        "session_id": "CLOSER-BFA-20260611-150100",
        "decisao": "aprovado",
        "email_destino": "info@bfa.ao",
        "email_assunto": "Instrução de crédito PME — recolha de documentação estruturada",
        "texto": (
            "Bom dia,\n\n"
            "As PME que pedem financiamento ao BFA enviam a documentação — certidão fiscal, "
            "balanço, registo comercial — por WhatsApp ao gestor de conta. Sem fluxo estruturado, "
            "documentos perdem-se, ficam incompletos e o ciclo de instrução de crédito "
            "atrasa semanas.\n\n"
            "Criámos um sistema que guia o cliente pela submissão de documentos passo a passo, "
            "valida a completude do dossier e só encaminha ao analista quando tudo está reunido.\n\n"
            "15 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
    {
        "session_id": "CLOSER-Yetu-20260611-150200",
        "decisao": "aprovado",
        "email_destino": "info@yetu.ao",
        "email_assunto": "Reduzir o abandono no onboarding digital — Yetu",
        "texto": (
            "Bom dia,\n\n"
            "Muitos utilizadores que começam o onboarding do Yetu abandonam a meio da submissão "
            "de documentos — BI, comprovativo de morada, selfie — porque o processo não é "
            "guiado de forma clara.\n\n"
            "Criámos um fluxo de onboarding por WhatsApp que acompanha o utilizador passo a passo, "
            "valida automaticamente a qualidade dos documentos e só escala para revisão humana "
            "quando necessário. A taxa de activação de contas aumenta sem aumentar a equipa "
            "de suporte.\n\n"
            "15 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
    {
        "session_id": "CLOSER-Kixicredito-20260611-150300",
        "decisao": "aprovado",
        "email_destino": "info@kixicredito.ao",
        "email_assunto": "Reporte de cobrança de agentes de campo — Kixicrédito",
        "texto": (
            "Bom dia,\n\n"
            "Os agentes de campo do Kixicrédito reportam as cobranças do dia por WhatsApp ao "
            "supervisor — lista de clientes, valores, fotos de recibos. Sem sistema estruturado, "
            "a reconciliação da carteira é feita manualmente no escritório central, processo "
            "demorado e sujeito a erros.\n\n"
            "Criámos uma forma de o agente reportar cobranças por WA de forma estruturada, "
            "com cruzamento automático com a carteira e relatório diário de zona gerado "
            "sem intervenção manual.\n\n"
            "15 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
    {
        "session_id": "CLOSER-BIC-20260611-150400",
        "decisao": "aprovado",
        "email_destino": "bic@bancobic.ao",
        "email_assunto": "Pré-qualificação de crédito pessoal por WhatsApp — Banco BIC",
        "texto": (
            "Bom dia,\n\n"
            "Os clientes que pretendem um crédito pessoal no BIC chegam por WhatsApp com as "
            "mesmas perguntas — quanto posso pedir, quais os documentos, qual a prestação. "
            "O gestor responde a cada um individualmente, incluindo os que não têm condições "
            "de crédito.\n\n"
            "Criámos um sistema de pré-qualificação por WhatsApp que avalia o perfil do cliente "
            "e só encaminha ao gestor os pedidos que cumprem os critérios de elegibilidade.\n\n"
            "15 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
    {
        "session_id": "CLOSER-BNI-20260611-150500",
        "decisao": "aprovado",
        "email_destino": "info@bni.ao",
        "email_assunto": "Registo e rastreio de instruções de clientes empresariais — BNI",
        "texto": (
            "Bom dia,\n\n"
            "Os clientes empresariais do BNI enviam instruções de pagamento e pedidos de "
            "trade finance por WhatsApp ao gestor de conta. Sem acuse de recepção automático "
            "e registo de timestamp, surgem disputas sobre o que foi enviado e quando.\n\n"
            "Criámos um canal de comunicação corporativa por WhatsApp que acusa recepção de "
            "cada instrução, regista o trilho de auditoria e notifica o back-office para "
            "processamento — argumento de conformidade com as exigências de rastreabilidade "
            "do BNA.\n\n"
            "15 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
]

print(f"CLOSER — Primeiro contacto BAN | {len(mensagens)} emails")
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
