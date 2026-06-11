# -*- coding: utf-8 -*-
"""
Envio de mensagens para 10 prospects — sessão cowork externa
9 WhatsApp + 1 Email
Autorizado por Fidel Kussunga (CEO) — 2026-06-11
"""

import requests
import json
import time
import warnings
warnings.filterwarnings("ignore")

EVO_URL = "https://evolution.biscaplus.com/message/sendText/biscaplus"
EVO_KEY = "BE70B339A7A5-4EA9-AF4E-936E314407D5"
SEND_URL = "https://bmst-api.fly.dev/webhook/bmst-send-message"

wa_msgs = [
    {
        "numero": "244923167730",
        "empresa": "Aliva Saúde",
        "decisor": "António Chaves",
        "texto": (
            "Bom dia! 👋 Falo da BMST — Bisca Mais Sistemas e Tecnologias.\n"
            "Vi o trabalho da Aliva Saúde e sei que gerir RH numa rede de saúde com esta dimensão é pesado: "
            "onboarding de clínicos, escalas, assiduidade... muito processo manual.\n"
            "Automatizamos exactamente isso com IA — outras organizações em Angola reduziram o tempo administrativo em +60%.\n"
            "Posso mostrar em 15 minutos como funciona? 🙏\n"
            "— Fidel Kussunga | BMST\n"
            "f.kussunga@biscamaisst.com"
        ),
    },
    {
        "numero": "244923190840",
        "empresa": "Australpharma",
        "decisor": "Emanuel Rebelo",
        "texto": (
            "Bom dia Emanuel! 👋 Falo da BMST — Bisca Mais Sistemas e Tecnologias.\n"
            "Directores comerciais na área farmacêutica enfrentam sempre o mesmo desafio: "
            "gerir centenas de clientes sem um sistema que priorize e qualifique automaticamente os leads certos.\n"
            "Implementamos agentes de IA e automações de pipeline de vendas que fazem esse trabalho "
            "— a equipa foca-se só nos clientes que realmente interessam.\n"
            "Posso mostrar um caso prático em 15 minutos? 🙏\n"
            "— Fidel Kussunga | BMST\n"
            "f.kussunga@biscamaisst.com"
        ),
    },
    {
        "numero": "244947225316",
        "empresa": "Farmaclinic Angola",
        "decisor": "Cristóvão Vieira",
        "texto": (
            "Bom dia! 👋 Falo da BMST — Bisca Mais Sistemas e Tecnologias.\n"
            "A Farmaclinic tem presença em várias localidades — isso significa dados financeiros dispersos, "
            "relatórios tardios e dificuldade de consolidar tudo em tempo real.\n"
            "Implementamos dashboards financeiros com IA que resolvem exactamente isso, sem depender de Excel.\n"
            "Teria 15 minutos para uma conversa? 🙏\n"
            "— Fidel Kussunga | BMST\n"
            "f.kussunga@biscamaisst.com"
        ),
    },
    {
        "numero": "244923167950",
        "empresa": "Clínica Sagrada Esperança",
        "decisor": "Mário Ivanilson",
        "texto": (
            "Bom dia! 👋 Falo da BMST — Bisca Mais Sistemas e Tecnologias.\n"
            "A Clínica Sagrada Esperança é a maior rede de saúde privada de Angola — impressionante. "
            "Com essa escala, sei que os processos administrativos e financeiros são um desafio diário: "
            "conciliações, relatórios por extensão, controlo de custos.\n"
            "Automatizamos esses processos com IA. Posso mostrar como em 15 minutos? 🙏\n"
            "— Fidel Kussunga | BMST\n"
            "f.kussunga@biscamaisst.com"
        ),
    },
    {
        "numero": "244942585016",
        "empresa": "Neomedic Angola",
        "decisor": "Ismail Karolia",
        "texto": (
            "Bom dia Ismail! 👋 Falo da BMST — Bisca Mais Sistemas e Tecnologias.\n"
            "A maior dor que vejo em clínicas privadas em Luanda é esta: "
            "perdem pacientes todos os dias porque o atendimento demora e os agendamentos são manuais.\n"
            "Implementamos chatbots de atendimento que respondem 24h, qualificam o paciente e agendam consultas "
            "— sem sobrecarregar a vossa equipa.\n"
            "Posso mostrar como em 15 minutos? 🙏\n"
            "— Fidel Kussunga | BMST\n"
            "f.kussunga@biscamaisst.com"
        ),
    },
    {
        "numero": "244931251965",
        "empresa": "Grupo Boavida SA",
        "decisor": "Miranda Ganga",
        "texto": (
            "Bom dia Miranda! 👋 Falo da BMST — Bisca Mais Sistemas e Tecnologias.\n"
            "No Grupo Boavida chegam dezenas de leads imobiliários por dia — WhatsApp, site, redes sociais. "
            "Sem um sistema que responda e qualifique automaticamente, perde-se muito potencial para a concorrência.\n"
            "Implementamos chatbots que respondem 24h, qualificam o lead e entregam só os clientes quentes à equipa comercial.\n"
            "Posso mostrar como funciona? 🙏\n"
            "— Fidel Kussunga | BMST\n"
            "f.kussunga@biscamaisst.com"
        ),
    },
    {
        "numero": "244946581308",
        "empresa": "Myimovel",
        "decisor": "Alexandre Pacheco",
        "texto": (
            "Bom dia Alexandre! 👋 Falo da BMST — Bisca Mais Sistemas e Tecnologias.\n"
            "O que estão a construir com a Myimovel é exactamente o tipo de inovação que o mercado angolano precisa. "
            "Para uma startup escalar sem aumentar muito a equipa, a automação é chave: "
            "chatbot de atendimento, qualificação de leads por IA, plataforma web que converte melhor.\n"
            "É exactamente o que fazemos. Posso mostrar como em 15 minutos? 🙏\n"
            "— Fidel Kussunga | BMST\n"
            "f.kussunga@biscamaisst.com"
        ),
    },
    {
        "numero": "244923399234",
        "empresa": "Pimenova Angola",
        "decisor": "João Correia",
        "texto": (
            "Bom dia João! 👋 Falo da BMST — Bisca Mais Sistemas e Tecnologias.\n"
            "As agências que vão liderar o imobiliário angolano nos próximos anos são as que já hoje têm "
            "presença digital forte, atendimento automatizado no WhatsApp e dados para tomar decisões rápidas.\n"
            "Na BMST implementamos exactamente isso: chatbots, automações de pipeline, dashboards e aplicações à medida.\n"
            "Posso mostrar exemplos concretos do que já fizemos em Angola? 🙏\n"
            "— Fidel Kussunga | BMST\n"
            "f.kussunga@biscamaisst.com"
        ),
    },
    {
        "numero": "244934838383",
        "empresa": "Zenki Real Estate",
        "decisor": "Maria Nogueira",
        "texto": (
            "Bom dia Maria! 👋 Falo da BMST — Bisca Mais Sistemas e Tecnologias.\n"
            "A Zenki é referência em avaliação e gestão imobiliária em Angola. "
            "Como COO, sei que muito tempo é perdido em relatórios, gestão de portfólio e análise de mercado manual.\n"
            "Implementamos sistemas de análise com IA e automações de back-office que libertam a equipa "
            "para o que realmente cria valor.\n"
            "Teria 15 minutos? 🙏\n"
            "— Fidel Kussunga | BMST\n"
            "f.kussunga@biscamaisst.com"
        ),
    },
]

resultados = []

print("=" * 60)
print("COWORK PROSPECTS — 9 WhatsApp + 1 Email")
print("=" * 60)

for m in wa_msgs:
    payload = {"number": m["numero"], "text": m["texto"]}
    try:
        r = requests.post(
            EVO_URL,
            headers={"apikey": EVO_KEY, "Content-Type": "application/json"},
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            timeout=15,
            verify=False,
        )
        if r.status_code in (200, 201):
            mid = r.json().get("key", {}).get("id", "?")
            print(f"  WA OK   +{m['numero']} — {m['empresa']} ({m['decisor']}) | {mid}")
            resultados.append({"empresa": m["empresa"], "canal": "WA", "status": "OK", "mid": mid})
        else:
            err = r.json().get("response", {}).get("message", [r.text[:50]])
            print(f"  WA ERR  +{m['numero']} — {m['empresa']} | {err}")
            resultados.append({"empresa": m["empresa"], "canal": "WA", "status": "ERRO", "mid": ""})
    except Exception as e:
        print(f"  WA EXC  +{m['numero']} — {m['empresa']} | {e}")
        resultados.append({"empresa": m["empresa"], "canal": "WA", "status": "ERRO", "mid": ""})
    time.sleep(1)

# Email — Teixeira Duarte RE
email_msg = {
    "session_id": "CLOSER-TeixeiraDuarteRE-20260611-130000",
    "decisao": "aprovado",
    "email_destino": "info@tdimobiliaria.pt",
    "email_assunto": "Teixeira Duarte Angola — sistemas inteligentes para gestão de projectos imobiliários",
    "texto": (
        "Olá Erick,\n\n"
        "A Teixeira Duarte Real Estate Angola tem uma escala e reputação que exige ferramentas à altura. "
        "Coordenação de equipas, fases de projecto, reporting para administração "
        "— processos que na maioria das empresas ainda dependem de email e Excel.\n\n"
        "Na BMST desenvolvemos aplicações web e sistemas inteligentes que centralizam toda a gestão "
        "de projecto e automatizam o reporting para a administração.\n\n"
        "Posso mostrar-lhe casos concretos aplicados ao sector imobiliário?\n\n"
        "Cumprimentos,\n"
        "Fidel Kussunga | BMST — Bisca Mais Sistemas e Tecnologias\n"
        "f.kussunga@biscamaisst.com"
    ),
}
try:
    r = requests.post(SEND_URL, json=email_msg, timeout=30, verify=False)
    status = r.json().get("status", f"HTTP{r.status_code}")
    print(f"  EMAIL {status.upper()}  info@tdimobiliaria.pt — Teixeira Duarte RE (Erick Ienke)")
    resultados.append({"empresa": "Teixeira Duarte RE", "canal": "email", "status": status, "mid": ""})
except Exception as e:
    print(f"  EMAIL ERR  info@tdimobiliaria.pt | {e}")
    resultados.append({"empresa": "Teixeira Duarte RE", "canal": "email", "status": "ERRO", "mid": ""})

print()
print("=" * 60)
ok = sum(1 for r in resultados if r["status"] in ("OK", "enviado"))
print(f"RESULTADO FINAL: {ok}/{len(resultados)} enviados com sucesso")
erros = [r for r in resultados if r["status"] not in ("OK", "enviado")]
if erros:
    print(f"Erros ({len(erros)}):")
    for e in erros:
        print(f"  - {e['empresa']} ({e['canal']})")
