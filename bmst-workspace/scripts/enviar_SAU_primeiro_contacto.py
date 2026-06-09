# -*- coding: utf-8 -*-
"""
CLOSER — Primeiro contacto SAU-001..006 (Sector Saude Privada, Sessao 15)
Executar APOS aprovacao CEO. 9 Jun 2026.
Accao aprovada (⏳ → ✅) — CEO aprova via webhook bmst-aprovacao.
"""

import json, ssl, time, urllib.request, urllib.error, datetime
import requests, urllib3

urllib3.disable_warnings()

SEND_URL      = "https://bmst-api.fly.dev/webhook/bmst-send-message"
EVOLUTION_URL = "https://evolution.biscaplus.com/message/sendText/biscaplus"
EVOLUTION_KEY = "BE70B339A7A5-4EA9-AF4E-936E314407D5"
RESEND_URL    = "https://api.resend.com/emails"
RESEND_KEY    = "re_GMtRc3sX_HrPf2pYoa9B7tocV2WLGVAYm"
EMAIL_FROM    = "Fidel Kussunga | Bisca+ <f.kussunga@biscamaisst.com>"

NOW = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

# ---------------------------------------------------------------------------
# MENSAGENS EMAIL (SAU-002, SAU-003, SAU-004, SAU-005)
# ---------------------------------------------------------------------------

EMAILS = [

    # --- SAU-002 ALIVA Saude — email corporativo Patricia Magalhaes ----------
    {
        "id": "SAU-002",
        "empresa": "ALIVA Saude",
        "session_id": f"CLOSER-ALIVA-{NOW}",
        "email_destino": "patricia.magalhaes@alivasaude.com",
        "email_assunto": "Gestão de comunicação com pacientes — ALIVA Saúde",
        "texto": (
            "Exma. Patrícia,\n\n"
            "A ALIVA realizou 900.000 consultas em 2025. Para cada consulta há "
            "uma mensagem: marcação, confirmação, resultado, follow-up. São "
            "dezenas de milhares de mensagens por mês respondidas pela equipa.\n\n"
            "Desenvolvemos um sistema que trata este volume de comunicação de "
            "forma estruturada, sem sobrecarregar a recepção. Vale 20 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },

    # --- SAU-003 MEDIAG — email geral ----------------------------------------
    {
        "id": "SAU-003",
        "empresa": "MEDIAG Laboratorio",
        "session_id": f"CLOSER-MEDIAG-{NOW}",
        "email_destino": "geral@laboratoriomediag.com",
        "email_assunto": "Notificação automática de resultados — MEDIAG",
        "texto": (
            "Exmo. Director,\n\n"
            "A MEDIAG é a maior rede de laboratórios em Angola. Cada análise "
            "concluída gera a mesma mensagem do paciente: 'os meus resultados "
            "já estão?' — centenas por dia, respondidas manualmente.\n\n"
            "Desenvolvemos um sistema que notifica o paciente automaticamente "
            "quando os resultados ficam prontos, sem ocupar a recepção. "
            "Vale 20 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },

    # --- SAU-004 Clinica Girassol — email info@ -------------------------------
    {
        "id": "SAU-004",
        "empresa": "Clinica Girassol",
        "session_id": f"CLOSER-Girassol-{NOW}",
        "email_destino": "info@clinicagirassol.co.ao",
        "email_assunto": "Centralização de marcações — Clínica Girassol",
        "texto": (
            "Exmo. Director,\n\n"
            "A Clínica Girassol tem cardiologia, neurologia e ortopedia — "
            "especialidades com marcações complexas que passam por WhatsApp "
            "e telefone sem sistema centralizado. Um paciente que quer "
            "remarcar uma consulta de neurologia não sabe para onde ligar.\n\n"
            "Desenvolvemos um sistema que centraliza marcações por WhatsApp "
            "com agenda em tempo real por especialidade. Vale 20 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },

    # --- SAU-005 Multiperfil — email comercial (Belmiro Rosa) ----------------
    {
        "id": "SAU-005",
        "empresa": "Clinica Multiperfil",
        "session_id": f"CLOSER-Multiperfil-{NOW}",
        "email_destino": "comercial@multiperfil.co.ao",
        "email_assunto": "Comunicação com pacientes — Clínica Multiperfil",
        "texto": (
            "Exmo. Dr. Belmiro Rosa,\n\n"
            "A Multiperfil tem 1.000+ colaboradores e dezenas de especialidades "
            "— centenas de mensagens de pacientes por dia: marcações, "
            "resultados, acompanhamento pós-operatório. Respondidas "
            "manualmente pela equipa clínica.\n\n"
            "Desenvolvemos um sistema que trata esse volume sem sobrecarregar "
            "a equipa. Vale 20 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "f.kussunga@biscamaisst.com | +244 956 873 126"
        ),
    },
]

# ---------------------------------------------------------------------------
# MENSAGENS WHATSAPP (SAU-001, SAU-006) — Evolution API directo
# ---------------------------------------------------------------------------

WA_MESSAGES = [

    # --- SAU-001 Clinica Sagrada Esperanca — WA +244929070787 ----------------
    {
        "id": "SAU-001",
        "empresa": "Clinica Sagrada Esperanca",
        "session_id": f"CLOSER-CSE-{NOW}",
        "numero": "244929070787",
        "texto": (
            "Bom dia, sou o Fidel da Bisca+. A Sagrada Esperança tem unidades "
            "em 18 províncias — cada paciente que tenta marcar consulta em "
            "Benguela via WhatsApp está a marcar para o número errado ou sem "
            "resposta. Um sistema central de marcações via WhatsApp resolve "
            "esta fragmentação. Vale 20 minutos de conversa?"
        ),
    },

    # --- SAU-006 Clinica General Katondo — WA +244923168644 ------------------
    {
        "id": "SAU-006",
        "empresa": "Clinica General Katondo",
        "session_id": f"CLOSER-Katondo-{NOW}",
        "numero": "244923168644",
        "texto": (
            "Bom dia, sou o Fidel da Bisca+. A Clínica Katondo usa WhatsApp "
            "para marcação de consultas — a equipa responde manualmente a cada "
            "pedido, incluindo à noite quando não há recepcionista. "
            "Desenvolvemos um sistema que responde automaticamente fora do "
            "horário e confirma a marcação sem intervenção da equipa. "
            "Vale 15 minutos de conversa?"
        ),
    },
]


# ---------------------------------------------------------------------------
# FUNCOES DE ENVIO
# ---------------------------------------------------------------------------

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


def send_whatsapp(numero, texto):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    data = json.dumps(
        {"number": numero, "text": texto}, ensure_ascii=False
    ).encode("utf-8")
    req = urllib.request.Request(
        EVOLUTION_URL,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "apikey": EVOLUTION_KEY,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
            r = json.loads(resp.read().decode("utf-8"))
            return True, r.get("key", {}).get("id", "ok")
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        return False, f"HTTP {e.code}: {body}"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# EXECUCAO
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    total = len(EMAILS) + len(WA_MESSAGES)
    print(f"CLOSER — Primeiro contacto SAU | {total} mensagens | {NOW}")
    print("Sector: Saude Privada — Clinicas e Laboratorios (Sessao 15)")
    print("=" * 68)

    resultados = []
    idx = 1

    for msg in EMAILS:
        print(
            f"[{idx:02d}/{total}] {msg['id']:8} {msg['empresa'][:30]:30} email ...",
            end=" ", flush=True,
        )
        ok, info = send_email_api(msg)
        print("OK" if ok else "FAIL")
        if ok:
            print(f"         {info}")
        else:
            print(f"         ERRO: {info}")
        resultados.append({"id": msg["id"], "ok": ok, "canal": "email"})
        idx += 1
        time.sleep(1.5)

    for msg in WA_MESSAGES:
        print(
            f"[{idx:02d}/{total}] {msg['id']:8} {msg['empresa'][:30]:30} WA   ...",
            end=" ", flush=True,
        )
        ok, info = send_whatsapp(msg["numero"], msg["texto"])
        print("OK" if ok else "FAIL")
        if ok:
            print(f"         msg_id: {info}")
        else:
            print(f"         ERRO: {info}")
        resultados.append({"id": msg["id"], "ok": ok, "canal": "whatsapp"})
        idx += 1
        time.sleep(1.5)

    enviados = sum(1 for r in resultados if r["ok"])
    falhas = [r["id"] for r in resultados if not r["ok"]]

    print("\n" + "=" * 68)
    print(f"Resultado: {enviados}/{total} enviados com sucesso.")
    if falhas:
        print(f"Falhas: {', '.join(falhas)}")
