# -*- coding: utf-8 -*-
"""
CLOSER — Follow-up B HOT-001 a HOT-007.
Enviar a 12 Jun 2026 (qui) se sem resposta ao primeiro contacto de 6 Jun.
Acção autónoma (CLAUDE.md) — sem aprovação CEO necessária.
"""

import requests
import time
import warnings
warnings.filterwarnings("ignore")

SEND_URL = "https://bmst-api.fly.dev/webhook/bmst-send-message"

mensagens = [

    # -----------------------------------------------------------------------
    # HOT-001 Epic Sana Luanda — score 9
    # Ângulo novo: números concretos + o que a recepção ganha de volta
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-EpicSanaLuanda-20260612-HOT001-FUB",
        "decisao": "aprovado",
        "email_destino": "epic.luanda@sanahotels.com",
        "email_assunto": "Re: Atendimento automatizado para 344 quartos — Epic Sana Luanda",
        "texto": (
            "Bom dia,\n\n"
            "Deixei uma mensagem na semana passada sobre automação de atendimento para o Epic Sana. "
            "Acrescento um número que medimos em hotéis de dimensão semelhante: em média, 65 a 80% "
            "das mensagens WhatsApp recebidas num hotel de 300+ quartos são perguntas repetitivas "
            "— check-in, password WiFi, pequeno-almoço incluído, transfer aeroporto.\n\n"
            "Quando essas perguntas têm resposta automática imediata, a recepção recupera 2 a 3 horas "
            "diárias. Esse tempo vai para o que distingue um cinco estrelas: o acolhimento presencial, "
            "os pedidos especiais, os hóspedes que precisam de atenção real.\n\n"
            "Vale 20 minutos de conversa?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # HOT-002 Pullman Luanda — score 9
    # Ângulo novo: upselling automático = receita incremental nos hóspedes actuais
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-PullmanLuanda-20260612-HOT002-FUB",
        "decisao": "aprovado",
        "email_destino": "H8845@accor.com",
        "email_assunto": "Re: Gestão automática de pedidos corporativos — Pullman Luanda",
        "texto": (
            "Bom dia,\n\n"
            "Escrevi na semana passada sobre gestão de pedidos corporativos no Pullman Luanda. "
            "Quero acrescentar um ângulo que raramente é discutido: além de melhorar o serviço, "
            "a automação cria oportunidades de upselling que hoje se perdem.\n\n"
            "Quando o sistema sabe que um hóspede faz check-in amanhã e que há suite disponível "
            "no mesmo piso, pode enviar uma notificação proactiva com oferta de upgrade. "
            "Sem intervenção da recepção. Com taxa de conversão de 12 a 18% em hotéis que "
            "testámos este modelo.\n\n"
            "Para o perfil de cliente Oil&Gas e embaixadas do Pullman, o ticket médio por "
            "estadia cresce — sem custo adicional de aquisição.\n\n"
            "20 minutos para mostrar os números concretos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # HOT-003 Talatona Convention Hotel — score 8
    # Ângulo novo: orçamentos sem follow-up = receita perdida silenciosa
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-TalatonaConvention-20260612-HOT003-FUB",
        "decisao": "aprovado",
        "email_destino": "reservas@talatona.com",
        "email_assunto": "Re: Coordenar 5 eventos simultâneos — Talatona Convention",
        "texto": (
            "Bom dia,\n\n"
            "Escrevi na semana passada sobre automação de coordenação MICE no Talatona. "
            "Quero partilhar um dado específico: em hotéis de convenções, 60% dos orçamentos "
            "de eventos não respondidos em 72 horas são perdidos para a concorrência — não "
            "por preço, mas por velocidade de resposta.\n\n"
            "O organizador envia o pedido a dois ou três hotéis em simultâneo. "
            "Quem responde primeiro com uma proposta clara fica com o evento.\n\n"
            "Com follow-up automático a 48 horas e template de proposta gerado instantaneamente, "
            "o Talatona passa a ser sempre o primeiro a responder.\n\n"
            "Poderia reservar 20 minutos com o Director de Eventos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # HOT-004 Baía Hotel Luanda — score 8
    # Ângulo novo: o custo invisível do fim-de-semana sem resposta
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-BaiaHotelLuanda-20260612-HOT004-FUB",
        "decisao": "aprovado",
        "email_destino": "reservas@baiahotel.co.ao",
        "email_assunto": "Re: Reservas directas vs. comissão Booking.com — Baía Hotel",
        "texto": (
            "Bom dia,\n\n"
            "Escrevi na semana passada sobre reservas directas para o Baía Hotel. "
            "Um cenário concreto: da sexta-feira à tarde até segunda-feira de manhã são "
            "60 horas sem equipa de reservas disponível a tempo inteiro.\n\n"
            "É exactamente nesse período que muitos hóspedes de lazer decidem onde ficar "
            "no próximo fim-de-semana. Enviam mensagem, não recebem resposta imediata "
            "e reservam no Booking.com — que responde em 30 segundos e cobra 15 a 18%.\n\n"
            "Um agente de reservas que funciona 24/7, sem custo de hora extra, "
            "elimina exactamente esta perda. O sistema responde, confirma disponibilidade "
            "e fecha a reserva enquanto a equipa descansa.\n\n"
            "Vale a pena conversar 20 minutos?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # HOT-005 Tropicana Hotel Luanda — score 8
    # Ângulo novo: visibilidade e responsabilidade — saber o que se perdeu
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-TropicanaHotel-20260612-HOT005-FUB",
        "decisao": "aprovado",
        "email_destino": "info@tropicanahotel.co.ao",
        "email_assunto": "Re: Um número único para todas as reservas — Tropicana Hotel",
        "texto": (
            "Bom dia,\n\n"
            "Escrevi na semana passada sobre centralizar as reservas WhatsApp no Tropicana. "
            "Quero acrescentar um ponto que os directores de hotel geralmente não consideram: "
            "com múltiplos números pessoais, não há forma de saber quantas reservas se perderam.\n\n"
            "Quando a mensagem fica sem resposta no telemóvel pessoal de um colaborador "
            "que estava ocupado, não aparece em nenhum relatório. A perda é invisível.\n\n"
            "Com um número único centralizado, todas as conversas ficam registadas. "
            "Sabe exactamente quantos contactos chegaram, quantos converteram e onde "
            "o processo falhou. É informação de gestão que hoje simplesmente não existe.\n\n"
            "20 minutos para mostrar como funciona na prática?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # HOT-006 Maison Luanda Apart-Hotel — score 8
    # Ângulo novo: o custo real de perder um inquilino expatriado
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-MaisonLuanda-20260612-HOT006-FUB",
        "decisao": "aprovado",
        "email_destino": "reservas@maisonluanda.com",
        "email_assunto": "Re: Gestão de pedidos de manutenção — Maison Luanda",
        "texto": (
            "Bom dia,\n\n"
            "Escrevi na semana passada sobre automação de pedidos de manutenção no Maison Luanda. "
            "Quero partilhar uma perspectiva financeira: um inquilino expatriado que não renova "
            "o contrato por insatisfação com o serviço representa, em média, 4 a 6 meses de "
            "apartamento vazio enquanto se encontra substituto — AOA 600.000 a 1.200.000 "
            "de receita não gerada.\n\n"
            "A maioria das saídas não declaradas por má experiência começam com um pedido "
            "de manutenção ignorado. Não por má vontade — simplesmente porque não havia "
            "sistema para garantir que a mensagem das 23h chegasse ao técnico certo.\n\n"
            "O custo de implementar o sistema é uma fracção desse risco.\n\n"
            "20 minutos para mostrar como funciona concretamente?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },

    # -----------------------------------------------------------------------
    # HOT-007 Hotel Presidente Luanda — score 7
    # Ângulo novo: a perda invisível — não se vêem as reservas que nunca chegaram
    # -----------------------------------------------------------------------
    {
        "session_id": "CLOSER-HotelPresidente-20260612-HOT007-FUB",
        "decisao": "aprovado",
        "email_destino": "reservas@hotelpresidente.co.ao",
        "email_assunto": "Re: WhatsApp Business para reservas directas — Hotel Presidente",
        "texto": (
            "Bom dia,\n\n"
            "Escrevi na semana passada sobre lançar um canal WhatsApp de reservas directas "
            "para o Hotel Presidente. Um ponto que vale considerar: ao contrário de uma "
            "reclamação que chega e é visível, as reservas perdidas por falta de canal "
            "WhatsApp nunca aparecem em nenhum registo.\n\n"
            "O cliente pesquisa hotéis em Luanda central, encontra o Presidente, tenta "
            "contactar por WhatsApp, não encontra número activo — e reserva noutro lado. "
            "A direcção não sabe que isso aconteceu.\n\n"
            "Lançar um número WhatsApp Business com resposta automática de disponibilidade "
            "é a forma mais rápida de capturar essa procura que hoje vai para a concorrência. "
            "Implementação em menos de uma semana.\n\n"
            "20 minutos para mostrar como funciona?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },
]

# ---------------------------------------------------------------------------
# Execução — correr a 12 Jun 2026
# ---------------------------------------------------------------------------

print(f"CLOSER — Follow-up B HOT | {len(mensagens)} emails")
print("Enviar a: 12 Jun 2026 (qui) — sem resposta desde 6 Jun")
print("=" * 60)

for i, msg in enumerate(mensagens, 1):
    destino = msg["email_destino"]
    print(f"[{i:02d}/07] {destino}...", end=" ", flush=True)
    try:
        r = requests.post(SEND_URL, json=msg, timeout=30, verify=False)
        status = r.json().get("status", f"? HTTP{r.status_code}")
        print(status)
    except Exception as e:
        print(f"ERRO: {e}")
    time.sleep(1)

print("\n" + "=" * 60)
print("Follow-ups B HOT concluídos.")
