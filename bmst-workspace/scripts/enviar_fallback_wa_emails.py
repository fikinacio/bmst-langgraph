# -*- coding: utf-8 -*-
"""
Fallback email para os 4 WA que falharam (numero nao no WhatsApp):
FIN-001 Fortaleza Seguros, IMO-008 Terra Imobiliaria,
IMO-011 My House Angola, IMO-014 Capicua.
"""

import requests
import time

SEND_URL = "https://bmst-api.fly.dev/webhook/bmst-send-message"

fallbacks = [
    {
        "session_id": "CLOSER-FortalezaSeguros-20260604-FALLBACK",
        "decisao": "aprovado",
        "email_destino": "info@fortalezaseguros.ao",
        "email_assunto": "Atendimento automatizado para 110.000 clientes — Fortaleza Seguros",
        "texto": (
            "Bom dia,\n\n"
            "A Fortaleza Seguros atende mais de 110 mil clientes em Angola, com linha dedicada 24/7 "
            "para sinistros e renovacoes. Com esse volume, a equipa responde manualmente a centenas "
            "de pedidos por dia — muitos dos quais sao rotineiros e poderiam ter resposta imediata.\n\n"
            "Na Bisca+, ajudamos seguradoras angolanas a automatizar exactamente esse atendimento: "
            "o cliente envia o pedido de renovacao ou abertura de sinistro pelo WhatsApp, recebe "
            "confirmacao em segundos e o processo arranca sem intervencao humana na triagem inicial.\n\n"
            "Posso mostrar como isto funciona especificamente para o sector seguros em 20 minutos. "
            "Quando e que lhe conve?\n\n"
            "Fidel Kussunga\n"
            "Bisca Mais Sistemas e Tecnologias\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },
    {
        "session_id": "CLOSER-TerraImobiliaria-20260604-FALLBACK",
        "decisao": "aprovado",
        "email_destino": "atendimento@terraimobiliaria.co.ao",
        "email_assunto": "Resposta automatica a pedidos de T3 em Talatona — Terra Imobiliaria",
        "texto": (
            "Bom dia,\n\n"
            "A Terra Imobiliaria opera em Talatona — uma zona com alta rotatividade de arrendamentos, "
            "especialmente de expatriados e tecnicos de empresa. Com esse perfil de cliente, os pedidos "
            "de informacao chegam por WhatsApp a qualquer hora, incluindo ao fim de semana quando a "
            "equipa nao esta disponivel.\n\n"
            "Na Bisca+, automatizamos o atendimento de imobiliarias nesta zona: o cliente envia "
            "'tem T3 disponivel em Talatona?', recebe ficha tecnica e fotos em segundos, e agenda "
            "visita directamente — mesmo as 22h de sabado.\n\n"
            "Clientes nossos em Talatona reduziram o tempo de resposta de horas para segundos sem "
            "aumentar a equipa.\n\n"
            "20 minutos para mostrar como funciona?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },
    {
        "session_id": "CLOSER-MyHouseAngola-20260604-FALLBACK",
        "decisao": "aprovado",
        "email_destino": "info@myhouseangola.com",
        "email_assunto": "Quem responde quando esta em visita? — My House Angola",
        "texto": (
            "Bom dia,\n\n"
            "A My House Angola esta em Talatona — uma zona muito competitiva. Quando esta em visita "
            "com um cliente, quem responde as mensagens que chegam pelo WhatsApp?\n\n"
            "Na Bisca+, ajudamos agencias de dimensao media a nunca perder um lead por falta de "
            "disponibilidade: o sistema responde automaticamente fora de horario, apresenta os "
            "imoveis disponiveis e agenda a visita para quando estiver livre.\n\n"
            "O lead fica garantido. O agente foca-se em fechar.\n\n"
            "20 minutos para mostrar como funciona?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },
    {
        "session_id": "CLOSER-Capicua-20260604-FALLBACK",
        "decisao": "aprovado",
        "email_destino": "geral@capicua-ao.com",
        "email_assunto": "Um assistente que nunca vai a visitas — Capicua Imobiliaria",
        "texto": (
            "Bom dia,\n\n"
            "Numa agencia onde e a mesma pessoa a atender, visitar, negociar e fechar — quando esta "
            "em visita, nao ha ninguem a responder as mensagens que chegam. Cada mensagem sem "
            "resposta e um lead que foi procurar noutro lado.\n\n"
            "Na Bisca+, resolvemos exactamente este problema: o sistema responde automaticamente "
            "as perguntas sobre imoveis disponiveis, envia fotos e precos, e agenda a visita para "
            "quando estiver disponivel.\n\n"
            "E como ter um assistente que nunca vai a visitas nem tira ferias.\n\n"
            "20 minutos para mostrar como funciona?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
    },
]

for msg in fallbacks:
    destino = msg["email_destino"]
    print(f"Enviando fallback email {msg['session_id']} -> {destino}")
    try:
        r = requests.post(SEND_URL, json=msg, timeout=30, verify=False)
        resultado = r.json()
        status = resultado.get("status", f"? HTTP{r.status_code}")
        print(f"  {status}")
    except Exception as e:
        print(f"  ERRO: {e}")
    time.sleep(1)

print("\nFallbacks concluidos.")
