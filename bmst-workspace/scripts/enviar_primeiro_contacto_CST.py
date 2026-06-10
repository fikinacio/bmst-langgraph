# -*- coding: utf-8 -*-
"""
CLOSER — Primeiro contacto CST-001, CST-002, CST-003, CST-005
Sector: Construção e Grandes Obras
Aprovado pelo CEO: 2026-06-11
"""

import requests
import time
import warnings
warnings.filterwarnings("ignore")

SEND_URL = "https://bmst-api.fly.dev/webhook/bmst-send-message"

mensagens = [

    # -----------------------------------------------------------------------
    # CST-001 Mota-Engil Angola — score 8
    # Dor: coordenação multi-obra via grupos WA, pedido de material para grupo errado
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-MotaEngil-20260610-120000",
        "decisao": "aprovado",
        "email_destino": "angola@mota-engil.com",
        "email_assunto": "Coordenação de obras em múltiplas províncias — Mota-Engil Angola",
        "texto": (
            "Bom dia,\n\n"
            "A Mota-Engil gere obras em 18 províncias com grupos WhatsApp por projecto "
            "para trabalhadores, materiais e subcontratados. Um pedido de material enviado "
            "para o grupo errado pode parar uma obra no dia seguinte.\n\n"
            "Criámos uma forma de centralizar pedidos e actualizações de obra num canal "
            "estruturado, sem substituir o WhatsApp que já usam.\n\n"
            "15 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126 | biscaplus.com"
        ),
    },

    # -----------------------------------------------------------------------
    # CST-002 Teixeira Duarte Angola (TDA) — score 8
    # Dor: gestão de não-conformidades em habitação social sem workflow estruturado
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-TDA-20260610-120100",
        "decisao": "aprovado",
        "email_destino": "geral@tdangola.co.ao",
        "email_assunto": "Gestão de não-conformidades em obra — TDA Angola",
        "texto": (
            "Bom dia,\n\n"
            "A TDA Angola coordena dezenas de subcontratados especializados em projectos "
            "de habitação social de grande escala. Quando surge uma não-conformidade "
            "— defeito de acabamento, falha de instalação —, o ciclo de reporte e "
            "rectificação por WhatsApp pode levar semanas sem registo estruturado.\n\n"
            "Criámos uma forma de registar, notificar e rastrear não-conformidades "
            "automaticamente por obra.\n\n"
            "15 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126 | biscaplus.com"
        ),
    },

    # -----------------------------------------------------------------------
    # CST-003 Conduril Angola — score 7
    # Dor: coordenação logística de frentes rodoviárias móveis a centenas de km
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-Conduril-20260610-120200",
        "decisao": "aprovado",
        "email_destino": "conduril@conduril.pt",
        "email_assunto": "Coordenação logística de obras rodoviárias — Conduril Angola",
        "texto": (
            "Bom dia,\n\n"
            "A Conduril Angola constrói estradas em corredores de centenas de quilómetros. "
            "Um encarregado numa frente de obra a 300km de Luanda coordena a chegada de "
            "betuminoso e máquinas por WhatsApp — o atraso desconhecido de uma entrega "
            "bloqueia toda a frente.\n\n"
            "Criámos um sistema de rastreio de entregas por WA: alertas de ETA, "
            "confirmação de chegada, zero espera surpresa.\n\n"
            "15 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126 | biscaplus.com"
        ),
    },

    # -----------------------------------------------------------------------
    # CST-005 Tecnovia Angola — score 7
    # Dor: ocorrências rodoviárias chegam via WA sem triagem, duplicadas ou perdidas
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-Tecnovia-20260610-120400",
        "decisao": "aprovado",
        "email_destino": "geral@tecnovia.pt",
        "email_assunto": "Gestão de ocorrências de manutenção rodoviária — Tecnovia Angola",
        "texto": (
            "Bom dia,\n\n"
            "A Tecnovia Angola recebe ocorrências de manutenção rodoviária — buracos, "
            "erosão de bermas, sinalização danificada — via WhatsApp de fiscais, "
            "autarquias e do INEA. Sem triagem estruturada, as ocorrências chegam a "
            "vários números, são duplicadas ou perdem-se.\n\n"
            "Criámos uma forma de receber, classificar e atribuir automaticamente "
            "cada ocorrência à equipa mais próxima.\n\n"
            "15 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126 | biscaplus.com"
        ),
    },
]

print(f"CLOSER — Primeiro contacto CST | {len(mensagens)} emails")
print("Aprovado pelo CEO: 2026-06-11")
print("=" * 60)

resultados = []
for i, msg in enumerate(mensagens, 1):
    destino = msg["email_destino"]
    session = msg["session_id"].split("-")[1]
    print(f"[{i:02d}/{len(mensagens)}] {destino}...", end=" ", flush=True)
    try:
        r = requests.post(SEND_URL, json=msg, timeout=30, verify=False)
        status = r.json().get("status", f"? HTTP{r.status_code}")
        print(status)
        resultados.append({"id": msg["session_id"], "status": status})
    except Exception as e:
        print(f"ERRO: {e}")
        resultados.append({"id": msg["session_id"], "status": "ERRO"})
    time.sleep(1)

print("\n" + "=" * 60)
ok = sum(1 for r in resultados if r["status"] == "enviado")
print(f"{ok}/{len(mensagens)} enviados com sucesso.")
print("CST-004 Zagope Angola — LinkedIn DM pendente (requer Unipile).")
print("CST-006 Soares da Costa — lead condicional, verificar operação Angola antes de contactar.")
