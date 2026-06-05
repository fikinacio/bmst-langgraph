# -*- coding: utf-8 -*-
"""
CLOSER — Submissão batch aprovações HOT-001 a HOT-007 (Hotelaria Luanda).
Envia cada mensagem ao CEO via webhook FastAPI para aprovação.
Após aprovação: email enviado automaticamente via callback_url.
"""

import json
import time
import ssl
import urllib.request
import urllib.error
from datetime import datetime

FASTAPI_BASE = "https://bmst-api.fly.dev"
CALLBACK_URL = f"{FASTAPI_BASE}/webhook/bmst-send-message"
TS = datetime.now().strftime("%Y%m%d-%H%M%S")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def ascii_clean(texto: str) -> str:
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'ä': 'a',
        'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
        'í': 'i', 'ì': 'i', 'î': 'i', 'ï': 'i',
        'ó': 'o', 'ò': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o',
        'ú': 'u', 'ù': 'u', 'û': 'u', 'ü': 'u',
        'ç': 'c', 'ñ': 'n',
        'Á': 'A', 'À': 'A', 'Ã': 'A', 'Â': 'A',
        'É': 'E', 'È': 'E', 'Ê': 'E',
        'Í': 'I', 'Ì': 'I', 'Î': 'I',
        'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Õ': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
        'Ç': 'C', 'Ñ': 'N',
    }
    for orig, rep in replacements.items():
        texto = texto.replace(orig, rep)
    return texto


def submit(lead: dict) -> dict:
    payload = {
        "tipo": "mensagem",
        "agente": "CLOSER",
        "titulo": f"Primeiro contacto {lead['empresa']}",
        "cliente": lead['empresa'],
        "valor": lead.get('valor', ''),
        "resumo": ascii_clean(lead['resumo']),
        "texto_completo": ascii_clean(lead['corpo']),
        "texto_publicar": lead['corpo'],
        "whatsapp_destino": lead.get('whatsapp_destino', ''),
        "email_destino": lead.get('email_destino', ''),
        "email_assunto": lead.get('email_assunto', ''),
        "callback_url": CALLBACK_URL,
        "session_id": lead['session_id'],
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{FASTAPI_BASE}/webhook/bmst-aprovacao",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# HOT-001 Epic Sana Luanda — score 9
# ---------------------------------------------------------------------------
leads = [
    {
        "empresa": "Epic Sana Luanda",
        "session_id": f"CLOSER-EpicSanaLuanda-{TS}-HOT001",
        "email_destino": "epic.luanda@sanahotels.com",
        "email_assunto": "Atendimento automatizado para 344 quartos — Epic Sana Luanda",
        "valor": "AOA 1.920.000–3.840.000",
        "resumo": "Primeiro contacto email — automatizar FAQ pre e pos-estadia (check-in, room service, confirmacoes) para 344 quartos.",
        "corpo": (
            "Bom dia,\n\n"
            "Um hotel de 344 quartos na Ilha de Luanda recebe centenas de mensagens por dia "
            "sobre check-in, serviços, transferes de aeroporto e pedidos de room service. "
            "A recepção responde manualmente às mesmas perguntas enquanto gere chegadas simultâneas.\n\n"
            "Na Bisca+, automatizamos o atendimento digital de hotéis de grande escala: o hóspede "
            "envia a questão pelo WhatsApp, recebe resposta imediata com a informação correcta, "
            "e os pedidos que exigem atenção humana são encaminhados directamente ao departamento "
            "certo — sem passar pela recepção.\n\n"
            "A recepção concentra-se no que não se automatiza: a experiência presencial de um "
            "hotel cinco estrelas.\n\n"
            "Poderia reservar 20 minutos esta semana para uma demonstração concreta?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # HOT-002 Pullman Luanda — score 9
    # -----------------------------------------------------------------------
    {
        "empresa": "Pullman Luanda",
        "session_id": f"CLOSER-PullmanLuanda-{TS}-HOT002",
        "email_destino": "H8845@accor.com",
        "email_assunto": "Gestão automática de pedidos corporativos Oil&Gas — Pullman Luanda",
        "valor": "AOA 1.920.000–3.840.000",
        "resumo": "Primeiro contacto email — unificar gestao pedidos corporativos (Oil&Gas, embaixadas) com notificacoes proactivas.",
        "corpo": (
            "Bom dia,\n\n"
            "O Pullman Luanda tem uma carteira de clientes corporativos exigente — executivos de "
            "Oil&Gas e embaixadas que enviam pedidos de reserva e alteração por múltiplos canais, "
            "sem priorização automática. Um pedido de última hora de um cliente de alto valor fica "
            "na mesma fila que um pedido de informação genérica.\n\n"
            "Na Bisca+, desenvolvemos soluções para hotéis com este perfil de cliente: gestão "
            "unificada de canais com triagem automática por prioridade, notificações proactivas "
            "de check-in e estado de quarto, e alertas de upgrade disponível — exactamente o nível "
            "de serviço que os padrões AccorHotels exigem, adaptado às especificidades do mercado "
            "angolano.\n\n"
            "O que as plataformas globais do grupo não cobrem, nós cobrimos localmente.\n\n"
            "20 minutos para mostrar como funciona concretamente?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # HOT-003 Talatona Convention Hotel — score 8
    # -----------------------------------------------------------------------
    {
        "empresa": "Talatona Convention Hotel",
        "session_id": f"CLOSER-TalatonaConvention-{TS}-HOT003",
        "email_destino": "reservas@talatona.com",
        "email_assunto": "Coordenar 5 eventos simultâneos sem aumentar a equipa — Talatona Convention",
        "valor": "AOA 1.440.000–2.880.000",
        "resumo": "Primeiro contacto email — automatizar coordenacao MICE (confirmacoes salas, catering, AV, follow-up orcamentos).",
        "corpo": (
            "Bom dia,\n\n"
            "Um hotel de convenções com 12 salas de conferência em Luanda Sul é o destino natural "
            "para eventos corporativos de 50 a 200 participantes. O problema surge quando há vários "
            "eventos em paralelo: cada organizador envia dezenas de mensagens sobre confirmação de "
            "sala, catering, equipamento AV e alojamento de grupo — e a equipa de eventos passa "
            "mais tempo a coordenar do que a vender.\n\n"
            "Na Bisca+, automatizamos a coordenação de eventos MICE: o organizador recebe "
            "confirmações automáticas de cada item da checklist, os orçamentos sem resposta recebem "
            "follow-up automático ao fim de 48 horas, e o estado de cada evento é visível numa "
            "única dashboard — sem emails em falta.\n\n"
            "A capacidade de gerir mais eventos em simultâneo sem aumentar a equipa "
            "é mensurável desde o primeiro mês.\n\n"
            "Poderia reservar 20 minutos com o Director de Eventos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # HOT-004 Baía Hotel Luanda — score 8
    # -----------------------------------------------------------------------
    {
        "empresa": "Baía Hotel Luanda",
        "session_id": f"CLOSER-BaiaHotelLuanda-{TS}-HOT004",
        "email_destino": "reservas@baiahotel.co.ao",
        "email_assunto": "Cada reserva directa poupa USD 18–22 em comissão — Baía Hotel",
        "valor": "AOA 960.000–1.920.000",
        "resumo": "Primeiro contacto email — agente reservas directas WhatsApp para eliminar comissao Booking.com (15-18%).",
        "corpo": (
            "Bom dia,\n\n"
            "Com uma tarifa média de USD 120/noite e uma localização icónica na Marginal, o Baía "
            "Hotel tem um argumento forte para atrair reservas directas. O problema é que quando "
            "um hóspede envia mensagem pelo WhatsApp fora do horário de trabalho, não recebe "
            "resposta imediata — e reserva pelo Booking.com, que cobra 15 a 18% de comissão.\n\n"
            "Na Bisca+, implementamos um agente de reservas directas via WhatsApp: o hóspede "
            "pergunta a disponibilidade, recebe confirmação em segundos, e conclui a reserva sem "
            "intermediário — às 22h de sexta-feira tanto quanto às 10h de segunda-feira.\n\n"
            "Com apenas 20 reservas directas mensais via WhatsApp, o sistema paga-se em menos "
            "de seis meses.\n\n"
            "Poderia reservar 20 minutos esta semana para mostrar como funciona?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # HOT-005 Tropicana Hotel Luanda — score 8
    # -----------------------------------------------------------------------
    {
        "empresa": "Tropicana Hotel Luanda",
        "session_id": f"CLOSER-TropicanaHotel-{TS}-HOT005",
        "email_destino": "info@tropicanahotel.co.ao",
        "email_assunto": "Um número único para todas as reservas WhatsApp — Tropicana Hotel",
        "valor": "AOA 960.000–1.920.000",
        "resumo": "Primeiro contacto email — centralizar reservas WhatsApp (actualmente em multiplos numeros pessoais colaboradores).",
        "corpo": (
            "Bom dia,\n\n"
            "No Tropicana Hotel, como na maioria dos hotéis de gestão angolana, as reservas chegam "
            "pelo WhatsApp pessoal de vários colaboradores. O resultado é previsível: ninguém tem "
            "visibilidade de todas as reservas ao mesmo tempo, há duplicações, e quando o "
            "colaborador está indisponível, o cliente não recebe resposta.\n\n"
            "Na Bisca+, resolvemos exactamente este problema: um único número WhatsApp Business "
            "com confirmação automática de disponibilidade, registo centralizado de reservas e "
            "notificação à equipa correcta — sem depender do WhatsApp pessoal de nenhum "
            "colaborador.\n\n"
            "A operação de reservas fica profissional e escalável. O cliente recebe sempre "
            "resposta, mesmo quando a equipa está ocupada.\n\n"
            "20 minutos para mostrar como funciona concretamente?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # HOT-006 Maison Luanda Apart-Hotel — score 8
    # -----------------------------------------------------------------------
    {
        "empresa": "Maison Luanda Apart-Hotel",
        "session_id": f"CLOSER-MaisonLuanda-{TS}-HOT006",
        "email_destino": "reservas@maisonluanda.com",
        "email_assunto": "O inquilino reporta a avaria às 23h — quem responde? — Maison Luanda",
        "valor": "AOA 960.000–1.920.000",
        "resumo": "Primeiro contacto email — automatizar gestao pedidos manutencao expatriados (estadias longas, alta exigencia).",
        "corpo": (
            "Bom dia,\n\n"
            "Num apart-hotel com expatriados e executivos em estadia mensal ou anual, a dor não "
            "está nas reservas — está na manutenção. O inquilino reporta uma avaria às 23h pelo "
            "WhatsApp. A mensagem fica sem resposta até à manhã seguinte. O inquilino sente que "
            "não há serviço. O risco de rescisão de um contrato de AOA 200.000/mês cresce.\n\n"
            "Na Bisca+, automatizamos a gestão de pedidos de manutenção para apart-hotéis: o "
            "inquilino envia o pedido, recebe confirmação imediata com prazo de resolução, o "
            "técnico correcto recebe notificação, e o inquilino é avisado quando o problema "
            "está resolvido — sem nenhuma intervenção manual no fluxo.\n\n"
            "Menos churn. Mais satisfação. A mesma equipa a gerir mais inquilinos.\n\n"
            "20 minutos para mostrar como funciona?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # HOT-007 Hotel Presidente Luanda — score 7
    # -----------------------------------------------------------------------
    {
        "empresa": "Hotel Presidente Luanda",
        "session_id": f"CLOSER-HotelPresidente-{TS}-HOT007",
        "email_destino": "reservas@hotelpresidente.co.ao",
        "email_assunto": "Os concorrentes confirmam reservas em 2 minutos — Hotel Presidente",
        "valor": "AOA 960.000–1.920.000",
        "resumo": "Primeiro contacto email — lançar WhatsApp Business reservas directas (hotel sem canal WA activo, perde vs concorrentes).",
        "corpo": (
            "Bom dia,\n\n"
            "O Hotel Presidente tem 246 quartos em Luanda central e uma reputação de décadas. "
            "O problema é que quando um cliente quer reservar e envia mensagem pelo WhatsApp, "
            "não encontra número activo — e reserva num hotel concorrente que responde em dois "
            "minutos.\n\n"
            "Na Bisca+, lançamos canais de reserva directa via WhatsApp Business para hotéis: "
            "o cliente envia a data e o tipo de quarto, recebe disponibilidade e preço em "
            "segundos, e conclui a reserva sem sair do WhatsApp. Nenhuma comissão ao "
            "Booking.com. Nenhuma reserva perdida por falta de resposta.\n\n"
            "Num mercado onde a velocidade de resposta define a escolha, o WhatsApp é o canal "
            "que os clientes angolanos preferem.\n\n"
            "Poderia reservar 20 minutos esta semana para uma demonstração?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },
]

# ---------------------------------------------------------------------------
# Execução
# ---------------------------------------------------------------------------

print(f"CLOSER — HOT-001 a HOT-007 | {len(leads)} mensagens a submeter para aprovação CEO")
print("=" * 70)

resultados = []
erros = []

for i, lead in enumerate(leads, 1):
    empresa = lead['empresa']
    canal = "WA" if lead.get('whatsapp_destino') else "Email"
    print(f"[{i:02d}/07] {empresa} ({canal})...", end=" ", flush=True)
    try:
        res = submit(lead)
        status = res.get("status", "?")
        sid = lead['session_id'][-14:]
        print(f"OK — {status} [{sid}]")
        resultados.append({"empresa": empresa, "session_id": lead["session_id"], "status": status})
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        print(f"ERRO {e.code}: {body}")
        erros.append({"empresa": empresa, "erro": f"HTTP {e.code}: {body}"})
    except Exception as ex:
        print(f"EXCEPCAO: {ex}")
        erros.append({"empresa": empresa, "erro": str(ex)})
    time.sleep(3)

print("\n" + "=" * 70)
print(f"Submetidos com sucesso: {len(resultados)}")
print(f"Erros: {len(erros)}")
if erros:
    print("Erros detalhados:")
    for e in erros:
        print(f"  - {e['empresa']}: {e['erro']}")
print("\nAguarda aprovação CEO via WhatsApp +41795748225.")
