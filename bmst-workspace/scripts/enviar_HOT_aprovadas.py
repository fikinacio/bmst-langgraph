# -*- coding: utf-8 -*-
"""
Envia 7 emails HOT-001 a HOT-007 aprovados pelo CEO (2026-06-06).
"""

import requests
import time
import warnings
warnings.filterwarnings("ignore")

SEND_URL = "https://bmst-api.fly.dev/webhook/bmst-send-message"

mensagens = [
    {
        "session_id": "CLOSER-EpicSanaLuanda-20260606-HOT001",
        "decisao": "aprovado",
        "email_destino": "epic.luanda@sanahotels.com",
        "email_assunto": "Atendimento automatizado para 344 quartos — Epic Sana Luanda",
        "texto": (
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
    {
        "session_id": "CLOSER-PullmanLuanda-20260606-HOT002",
        "decisao": "aprovado",
        "email_destino": "H8845@accor.com",
        "email_assunto": "Gestão automática de pedidos corporativos Oil&Gas — Pullman Luanda",
        "texto": (
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
    {
        "session_id": "CLOSER-TalatonaConvention-20260606-HOT003",
        "decisao": "aprovado",
        "email_destino": "reservas@talatona.com",
        "email_assunto": "Coordenar 5 eventos simultâneos sem aumentar a equipa — Talatona Convention",
        "texto": (
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
    {
        "session_id": "CLOSER-BaiaHotelLuanda-20260606-HOT004",
        "decisao": "aprovado",
        "email_destino": "reservas@baiahotel.co.ao",
        "email_assunto": "Cada reserva directa poupa USD 18–22 em comissão — Baía Hotel",
        "texto": (
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
    {
        "session_id": "CLOSER-TropicanaHotel-20260606-HOT005",
        "decisao": "aprovado",
        "email_destino": "info@tropicanahotel.co.ao",
        "email_assunto": "Um número único para todas as reservas WhatsApp — Tropicana Hotel",
        "texto": (
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
    {
        "session_id": "CLOSER-MaisonLuanda-20260606-HOT006",
        "decisao": "aprovado",
        "email_destino": "reservas@maisonluanda.com",
        "email_assunto": "O inquilino reporta a avaria às 23h — quem responde? — Maison Luanda",
        "texto": (
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
    {
        "session_id": "CLOSER-HotelPresidente-20260606-HOT007",
        "decisao": "aprovado",
        "email_destino": "reservas@hotelpresidente.co.ao",
        "email_assunto": "Os concorrentes confirmam reservas em 2 minutos — Hotel Presidente",
        "texto": (
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

print(f"A enviar {len(mensagens)} emails HOT aprovados...")
print("=" * 60)

for i, msg in enumerate(mensagens, 1):
    destino = msg["email_destino"]
    sid = msg["session_id"]
    print(f"[{i:02d}/07] {destino}...", end=" ", flush=True)
    try:
        r = requests.post(SEND_URL, json=msg, timeout=30, verify=False)
        resultado = r.json()
        status = resultado.get("status", f"? HTTP{r.status_code}")
        print(f"{status}")
    except Exception as e:
        print(f"ERRO: {e}")
    time.sleep(1)

print("\n" + "=" * 60)
print("Envio concluído.")
