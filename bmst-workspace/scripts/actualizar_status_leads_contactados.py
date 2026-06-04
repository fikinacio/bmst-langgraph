# -*- coding: utf-8 -*-
"""
Actualiza status dos leads contactados em 3-4 Jun 2026 para 'contactado'.
"""

import json
import os

BASE = r"C:\Users\User\bmst-workspace\leads"

actualizacoes = {
    "advocacia-luanda-2026-05-30.json": {
        "JUR-001": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "lcca@lcca.ao"},
        "JUR-002": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "info@clm-angola.com"},
        "JUR-003": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "geral@coutograca.ao", "nota": "WA +244923394577 retornou 400 — fallback email"},
        "JUR-004": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "angola@mirandaassociados.com"},
        "JUR-005": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "geral@advocaciaenegocios.ao", "nota": "WA +244912372100 retornou 400 — fallback email"},
    },
    "viagens-luanda-2026-06-01.json": {
        "VIA-001": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "info@charmetours.com"},
        "VIA-002": {"status": "em_curso", "data_contacto": "2026-06-04", "nota": "WA +244941367711 retornou 400. Sem email publico. Pendente LinkedIn."},
        "VIA-003": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "reservas@valtours-ao.com"},
        "VIA-004": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "reservas@flyluanda.co.ao"},
        "VIA-005": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "whatsapp", "whatsapp_usado": "244936544358"},
    },
    "financas-luanda-2026-05-19.json": {
        "FIN-001": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "info@fortalezaseguros.ao", "nota": "WA +244924744544 retornou 400 — fallback email"},
        "FIN-002": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "amilcar.trindade@interisk-angola.com"},
        "FIN-003": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "info@zillian.co.ao"},
        "FIN-004": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "geral@multicredito.co.ao"},
        "FIN-005": {"status": "contactado", "data_contacto": "2026-06-01", "canal_contacto": "linkedin", "nota": "WA +244927094314 retornou 400. Contactado via LinkedIn — visualizou mensagem, sem resposta."},
    },
    "telecomunicacoes-luanda-2026-05-26.json": {
        "TEL-001": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "whatsapp", "whatsapp_usado": "244940415313"},
        "TEL-002": {"status": "contactado", "data_contacto": "2026-05-31", "canal_contacto": "linkedin", "nota": "WA +244944888988 retornou 400. Contactado via LinkedIn."},
        "TEL-003": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "nuno.ventura@connectis.co.ao"},
        "TEL-004": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "geral@advanlink.co.ao"},
        "TEL-005": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "suporte@uwf.ao"},
    },
    "imobiliario-luanda-2026-05-12.json": {
        "IMO-001": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "geral@imogesba.ao"},
        "IMO-002": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "info@koraangola.com"},
        "IMO-003": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "geral@predilel.ao"},
        "IMO-004": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "contacto@luandarealestate.com"},
        "IMO-005": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "angola@century21.com"},
    },
    "imobiliario-luanda-2026-05-27.json": {
        "IMO-006": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "geral@square.co.ao"},
        "IMO-007": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "info@primeproperties.ao"},
        "IMO-008": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "atendimento@terraimobiliaria.co.ao", "nota": "WA +244995724624 retornou 400 — fallback email"},
        "IMO-009": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "geral@imotrust.co.ao"},
        "IMO-010": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "angola@remax-multitrust.co.ao"},
        "IMO-011": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "info@myhouseangola.com", "nota": "WA +244918884077 retornou 400 — fallback email"},
        "IMO-012": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "info@abacusangola.com"},
        "IMO-013": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "geral@equilatero.ao"},
        "IMO-014": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "geral@capicua-ao.com", "nota": "WA +244940983472 retornou 400 — fallback email (email estimado)"},
        "IMO-015": {"status": "contactado", "data_contacto": "2026-06-04", "canal_contacto": "email", "email_usado": "info@casaesolucoesafrica.com"},
    },
}

def actualizar_leads(ficheiro, actualizacoes_ficheiro):
    path = os.path.join(BASE, ficheiro)
    with open(path, "r", encoding="utf-8") as f:
        dados = json.load(f)

    # Encontrar lista de leads
    leads_key = None
    if isinstance(dados, list):
        leads = dados
    elif "leads" in dados:
        leads = dados["leads"]
        leads_key = "leads"
    else:
        print(f"  Formato desconhecido: {ficheiro}")
        return 0

    actualizados = 0
    for lead in leads:
        lead_id = lead.get("id")
        if lead_id in actualizacoes_ficheiro:
            updates = actualizacoes_ficheiro[lead_id]
            for key, val in updates.items():
                lead[key] = val
            actualizados += 1

    with open(path, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)

    return actualizados

total = 0
for ficheiro, acts in actualizacoes.items():
    n = actualizar_leads(ficheiro, acts)
    print(f"{ficheiro}: {n} leads actualizados")
    total += n

print(f"\nTotal: {total} leads actualizados para 'contactado'")
