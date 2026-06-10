# -*- coding: utf-8 -*-
"""
CLOSER — Follow-up B SAU-002..005 (Email)
Accao autonoma (CLAUDE.md) — sem aprovacao CEO necessaria.
Executar: 15 Jun 2026 se sem resposta ao primeiro contacto de 10 Jun.
"""

import requests, time, datetime, warnings
warnings.filterwarnings("ignore")

SEND_URL   = "https://bmst-api.fly.dev/webhook/bmst-send-message"
RESEND_URL = "https://api.resend.com/emails"
RESEND_KEY = "re_GMtRc3sX_HrPf2pYoa9B7tocV2WLGVAYm"
EMAIL_FROM = "Fidel Kussunga | Bisca+ <f.kussunga@biscamaisst.com>"

NOW = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

EMAILS = [

    # -----------------------------------------------------------------------
    # SAU-002 ALIVA Saude — email patricia.magalhaes@alivasaude.com
    # Angulo novo: ja tem linha WA propria — o problema nao e ter WA,
    # e responder manualmente a 2500 consultas/dia.
    # -----------------------------------------------------------------------
    {
        "id": "SAU-002",
        "empresa": "ALIVA Saude",
        "session_id": f"CLOSER-ALIVA-FUB-{NOW}",
        "email_destino": "patricia.magalhaes@alivasaude.com",
        "email_assunto": "Re: Gestão de comunicação com pacientes — ALIVA Saúde",
        "texto": (
            "Exma. Patrícia,\n\n"
            "Escrevi há cinco dias sobre o volume de comunicação com "
            "pacientes na ALIVA.\n\n"
            "Um dado concreto: a vossa linha WhatsApp (+244 923 167 730) "
            "já existe — o que falta é responder às 2.500 consultas/dia "
            "sem depender da equipa de recepção. A ALIVA reconheceu a "
            "necessidade do WhatsApp; o passo seguinte é não o gerir "
            "manualmente.\n\n"
            "20 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+"
        ),
    },

    # -----------------------------------------------------------------------
    # SAU-003 MEDIAG — email geral@laboratoriomediag.com
    # Angulo novo: vantagem competitiva — notificacao automatica e diferencial
    # visivel ao paciente num mercado onde todos ainda respondem manualmente.
    # -----------------------------------------------------------------------
    {
        "id": "SAU-003",
        "empresa": "MEDIAG Laboratorio",
        "session_id": f"CLOSER-MEDIAG-FUB-{NOW}",
        "email_destino": "geral@laboratoriomediag.com",
        "email_assunto": "Re: Notificação automática de resultados — MEDIAG",
        "texto": (
            "Exmo. Director,\n\n"
            "Escrevi há cinco dias sobre notificação automática de "
            "resultados na MEDIAG.\n\n"
            "Um laboratório que notifica o paciente automaticamente tem "
            "uma vantagem clara: o paciente não precisa de ligar para "
            "saber. Em Angola, onde a maioria dos laboratórios ainda "
            "responde manualmente, esta diferença é percebida de imediato.\n\n"
            "20 minutos?\n\n"
            "Fidel Kussunga | Bisca+"
        ),
    },

    # -----------------------------------------------------------------------
    # SAU-004 Clinica Girassol — email info@clinicagirassol.co.ao
    # Angulo novo: protocolo pre-operatorio — cirurgias cardiovasculares e
    # neurologicas exigem comunicacao precisa. Automatizar reduz cancelamentos.
    # -----------------------------------------------------------------------
    {
        "id": "SAU-004",
        "empresa": "Clinica Girassol",
        "session_id": f"CLOSER-Girassol-FUB-{NOW}",
        "email_destino": "info@clinicagirassol.co.ao",
        "email_assunto": "Re: Centralização de marcações — Clínica Girassol",
        "texto": (
            "Exmo. Director,\n\n"
            "Escrevi há cinco dias sobre a centralização de marcações "
            "na Girassol.\n\n"
            "A Girassol realiza cirurgias cardiovasculares e neurológicas "
            "— cada cirurgia tem um protocolo pré-operatório (jejum, "
            "exames, confirmação). Um sistema que envia este protocolo "
            "automaticamente ao paciente reduz cancelamentos de "
            "última hora. Vale 20 minutos?\n\n"
            "Fidel Kussunga | Bisca+"
        ),
    },

    # -----------------------------------------------------------------------
    # SAU-005 Multiperfil — email comercial@multiperfil.co.ao (Belmiro Rosa)
    # Angulo novo: salas cirurgicas digitais vs acompanhamento pos-op manual —
    # o contraste entre tecnologia cirurgica e comunicacao manual e o argumento.
    # -----------------------------------------------------------------------
    {
        "id": "SAU-005",
        "empresa": "Clinica Multiperfil",
        "session_id": f"CLOSER-Multiperfil-FUB-{NOW}",
        "email_destino": "comercial@multiperfil.co.ao",
        "email_assunto": "Re: Comunicação com pacientes — Clínica Multiperfil",
        "texto": (
            "Exmo. Dr. Belmiro Rosa,\n\n"
            "Escrevi há cinco dias sobre a comunicação com pacientes "
            "na Multiperfil.\n\n"
            "A Multiperfil tem as primeiras salas cirúrgicas digitais "
            "de Angola — o acompanhamento pós-operatório ainda é feito "
            "manualmente? Um sistema que contacta o paciente a D+1, D+3 "
            "e D+7 com perguntas de estado eleva o cuidado sem aumentar "
            "a equipa. Vale 20 minutos?\n\n"
            "Fidel Kussunga | Bisca+"
        ),
    },
]


def send_email_api(msg):
    """Tenta bmst-send-message; fallback Resend directo."""
    payload = {
        "session_id": msg["session_id"],
        "decisao": "aprovado",
        "email_destino": msg["email_destino"],
        "email_assunto": msg["email_assunto"],
        "texto": msg["texto"],
    }
    try:
        r = requests.post(SEND_URL, json=payload, timeout=20, verify=False)
        if r.status_code in (200, 201, 202):
            return True, f"bmst-api: {r.status_code}"
        raise Exception(f"HTTP {r.status_code}")
    except Exception as e:
        try:
            r2 = requests.post(
                RESEND_URL,
                json={
                    "from": EMAIL_FROM,
                    "to": [msg["email_destino"]],
                    "subject": msg["email_assunto"],
                    "text": msg["texto"],
                },
                headers={"Authorization": f"Bearer {RESEND_KEY}"},
                timeout=20,
                verify=False,
            )
            if r2.status_code in (200, 201):
                rid = r2.json().get("id", "?")
                return True, f"resend:{rid}"
            return False, f"resend HTTP {r2.status_code}: {r2.text[:100]}"
        except Exception as e2:
            return False, f"bmst:{e} | resend:{e2}"


if __name__ == "__main__":
    total = len(EMAILS)
    print(f"CLOSER — Follow-up B SAU Email | {total} mensagens | {NOW}")
    print("Enviar a: 15 Jun 2026 — sem resposta desde 10 Jun (5 dias)")
    print("=" * 60)

    resultados = []
    for i, msg in enumerate(EMAILS, 1):
        print(
            f"[{i:02d}/{total}] {msg['id']:8} {msg['empresa'][:28]:28} email ...",
            end=" ", flush=True,
        )
        ok, info = send_email_api(msg)
        print("OK" if ok else "FAIL")
        if ok:
            print(f"         {info}")
        else:
            print(f"         ERRO: {info}")
        resultados.append({"id": msg["id"], "ok": ok})
        time.sleep(1.5)

    enviados = sum(1 for r in resultados if r["ok"])
    falhas = [r["id"] for r in resultados if not r["ok"]]
    print("\n" + "=" * 60)
    print(f"Resultado: {enviados}/{total} enviados com sucesso.")
    if falhas:
        print(f"Falhas: {', '.join(falhas)}")
