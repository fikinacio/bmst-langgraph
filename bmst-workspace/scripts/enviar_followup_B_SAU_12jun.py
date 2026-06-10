# -*- coding: utf-8 -*-
"""
CLOSER — Follow-up B SAU-001 e SAU-006 (WhatsApp)
Accao autonoma (CLAUDE.md) — sem aprovacao CEO necessaria.
Executar: 12 Jun 2026 se sem resposta ao primeiro contacto de 10 Jun.
"""

import json, ssl, urllib.request, urllib.error, time, datetime, warnings
warnings.filterwarnings("ignore")

EVOLUTION_URL = "https://evolution.biscaplus.com/message/sendText/biscaplus"
EVOLUTION_KEY = "BE70B339A7A5-4EA9-AF4E-936E314407D5"

NOW = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

WA_MESSAGES = [

    # -----------------------------------------------------------------------
    # SAU-001 Clinica Sagrada Esperanca — WA +244929070787
    # Angulo novo: oncologia em 18 provincias — o paciente em quimio que nao
    # consegue confirmar a proxima sessao esta a usar o numero errado.
    # -----------------------------------------------------------------------
    {
        "id": "SAU-001",
        "empresa": "Clinica Sagrada Esperanca",
        "session_id": f"CLOSER-CSE-FUB-{NOW}",
        "numero": "244929070787",
        "texto": (
            "Da Bisca+. Escrevi há dois dias sobre o número central de "
            "marcações para a Sagrada Esperança. Um ângulo adicional: a CSE "
            "é a única rede com oncologia em 18 províncias — um paciente em "
            "quimio que não consegue confirmar a próxima sessão via WhatsApp "
            "está a ligar para o número errado. Este problema tem solução "
            "directa. Vale 15 minutos?"
        ),
    },

    # -----------------------------------------------------------------------
    # SAU-006 Clinica Katondo — WA +244923168644
    # Angulo novo: Talatona tem concentracao elevada de expatriados que
    # trabalham de dia e enviam mensagens a noite/fim de semana. A clinica
    # que responde primeiro tem a marcacao.
    # -----------------------------------------------------------------------
    {
        "id": "SAU-006",
        "empresa": "Clinica General Katondo",
        "session_id": f"CLOSER-Katondo-FUB-{NOW}",
        "numero": "244923168644",
        "texto": (
            "Da Bisca+. Escrevi há dois dias sobre respostas automáticas "
            "fora do horário da Katondo. Uma observação do mercado: a "
            "Talatona tem uma concentração elevada de expatriados e "
            "profissionais que trabalham durante o dia — as marcações chegam "
            "à noite e ao fim de semana. A clínica que responde primeiro tem "
            "a marcação. Vale 15 minutos esta semana?"
        ),
    },
]


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


if __name__ == "__main__":
    total = len(WA_MESSAGES)
    print(f"CLOSER — Follow-up B SAU WA | {total} mensagens | {NOW}")
    print("Enviar a: 12 Jun 2026 — sem resposta desde 10 Jun (48h)")
    print("=" * 60)

    resultados = []
    for i, msg in enumerate(WA_MESSAGES, 1):
        print(
            f"[{i:02d}/{total}] {msg['id']:8} {msg['empresa'][:30]:30} WA ...",
            end=" ", flush=True,
        )
        ok, info = send_whatsapp(msg["numero"], msg["texto"])
        print("OK" if ok else "FAIL")
        if ok:
            print(f"         msg_id: {info}")
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
