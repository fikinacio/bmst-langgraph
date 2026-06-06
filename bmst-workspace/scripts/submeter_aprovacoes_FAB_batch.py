# -*- coding: utf-8 -*-
"""
CLOSER — primeiros contactos FAB-001 a FAB-003.
Submete 3 aprovações ao CEO via webhook.

FAB-004 Global Catering Angola — BLOQUEADO: canal LinkedIn (Unipile expirado)
FAB-005 Red-M — BLOQUEADO: sem email/WA verificado (tel+Instagram apenas)
"""

import requests
import time
import unicodedata
import warnings
warnings.filterwarnings("ignore")

APROVACAO_URL = "https://bmst-api.fly.dev/webhook/bmst-aprovacao"
SEND_URL      = "https://bmst-api.fly.dev/webhook/bmst-send-message"


def ascii_clean(texto):
    nfkd = unicodedata.normalize("NFKD", texto)
    s = "".join(c for c in nfkd if not unicodedata.combining(c))
    return s.replace("—", "-").replace("–", "-").replace("“", '"').replace("”", '"')


aprovacoes = [

    # -----------------------------------------------------------------------
    # FAB-001 Novagest Serviços e Gestão S.A. — score 9 — Email
    # ISO 9001, 20+ anos, clientes Oil&Gas. Decisora: Raquel Fernandes.
    # Ângulo: cada comercial recebe pedidos no seu canal pessoal — quando
    # está em campo, as encomendas corporativas ficam sem resposta.
    # -----------------------------------------------------------------------
    {
        "tipo": "mensagem",
        "agente": "CLOSER",
        "titulo": ascii_clean("FAB-001 Novagest - primeiro contacto email"),
        "cliente": ascii_clean("Novagest Servicos e Gestao S.A."),
        "valor": "AOA 1.440.000 - 2.880.000",
        "resumo": ascii_clean(
            "Email de primeiro contacto para a Novagest (catering corporativo ISO 9001, "
            "clientes Oil&Gas, hospitais e escolas). Angulo: pedidos de ementa e "
            "confirmacoes de volume chegam a cada comercial individualmente — quando "
            "esta em campo, as mensagens ficam sem resposta."
        ),
        "texto_completo": ascii_clean(
            "Bom dia,\n\n"
            "A Novagest gere contratos de alimentação colectiva para clientes Oil&Gas, "
            "hospitais e escolas — um portefólio exigente, com pedidos de ementa, "
            "alterações de última hora e confirmações de volume que chegam por telefone "
            "e email a cada comercial individualmente.\n\n"
            "Quando o comercial está em campo ou numa reunião, essas mensagens ficam "
            "sem resposta. O cliente corporativo espera — ou procura outro fornecedor.\n\n"
            "Na Bisca+, desenvolvemos agentes de gestão de encomendas para empresas de "
            "catering: o cliente corporativo envia o pedido por WhatsApp, recebe "
            "confirmação automática com data, menu e volume, e o comercial é notificado "
            "apenas dos pedidos que exigem atenção humana — alterações fora do padrão, "
            "novos contratos, situações especiais.\n\n"
            "A equipa comercial concentra-se no que gera receita: novas contas e renovações.\n\n"
            "Poderia reservar 20 minutos para mostrar como funciona concretamente?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
        "texto_publicar": (
            "Bom dia,\n\n"
            "A Novagest gere contratos de alimentação colectiva para clientes Oil&Gas, "
            "hospitais e escolas — um portefólio exigente, com pedidos de ementa, "
            "alterações de última hora e confirmações de volume que chegam por telefone "
            "e email a cada comercial individualmente.\n\n"
            "Quando o comercial está em campo ou numa reunião, essas mensagens ficam "
            "sem resposta. O cliente corporativo espera — ou procura outro fornecedor.\n\n"
            "Na Bisca+, desenvolvemos agentes de gestão de encomendas para empresas de "
            "catering: o cliente corporativo envia o pedido por WhatsApp, recebe "
            "confirmação automática com data, menu e volume, e o comercial é notificado "
            "apenas dos pedidos que exigem atenção humana — alterações fora do padrão, "
            "novos contratos, situações especiais.\n\n"
            "A equipa comercial concentra-se no que gera receita: novas contas e renovações.\n\n"
            "Poderia reservar 20 minutos para mostrar como funciona concretamente?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
        "email_destino":   "novagest@novagest.co.ao",
        "email_assunto":   ascii_clean("Encomendas corporativas Oil&Gas - gestao automatizada para a Novagest"),
        "whatsapp_destino": "",
        "callback_url":    SEND_URL,
        "session_id":      "CLOSER-Novagest-20260606-FAB001",
    },

    # -----------------------------------------------------------------------
    # FAB-002 Pizzaria Capricciosa — score 8 — Email
    # 4 localizações Luanda. Email admin verificado. WA verificado (Maianga).
    # Ângulo: múltiplos números WA por loja sem número único nem visibilidade
    # central — pedidos perdidos são invisíveis.
    # -----------------------------------------------------------------------
    {
        "tipo": "mensagem",
        "agente": "CLOSER",
        "titulo": ascii_clean("FAB-002 Capricciosa - primeiro contacto email"),
        "cliente": ascii_clean("Pizzaria Capricciosa"),
        "valor": "AOA 960.000 - 1.920.000",
        "resumo": ascii_clean(
            "Email de primeiro contacto para a Capricciosa (cadeia 4 localizacoes Luanda). "
            "Angulo: pedidos de delivery chegam a numeros WA distintos por loja, sem "
            "redirecciona mento automatico — pedidos perdidos sao invisiveis sem registo central."
        ),
        "texto_completo": ascii_clean(
            "Bom dia,\n\n"
            "A Pizzaria Capricciosa opera em 4 localizações em Luanda — e os pedidos de "
            "delivery chegam por WhatsApp a números distintos por loja. Quando a linha da "
            "Maianga está ocupada, não há redireccionamento automático. O cliente espera, "
            "ou procura outro número.\n\n"
            "Sem visibilidade central, não há forma de saber quantos pedidos foram "
            "perdidos nesse intervalo.\n\n"
            "Na Bisca+, implementamos gestão de encomendas com número único: o cliente "
            "envia para um número central, o sistema identifica a loja mais próxima, "
            "confirma o tempo de entrega automaticamente e encaminha para a equipa certa "
            "— sem depender do WhatsApp pessoal de nenhum colaborador.\n\n"
            "A capacidade de atendimento cresce sem crescer a equipa.\n\n"
            "Poderia reservar 20 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
        "texto_publicar": (
            "Bom dia,\n\n"
            "A Pizzaria Capricciosa opera em 4 localizações em Luanda — e os pedidos de "
            "delivery chegam por WhatsApp a números distintos por loja. Quando a linha da "
            "Maianga está ocupada, não há redireccionamento automático. O cliente espera, "
            "ou procura outro número.\n\n"
            "Sem visibilidade central, não há forma de saber quantos pedidos foram "
            "perdidos nesse intervalo.\n\n"
            "Na Bisca+, implementamos gestão de encomendas com número único: o cliente "
            "envia para um número central, o sistema identifica a loja mais próxima, "
            "confirma o tempo de entrega automaticamente e encaminha para a equipa certa "
            "— sem depender do WhatsApp pessoal de nenhum colaborador.\n\n"
            "A capacidade de atendimento cresce sem crescer a equipa.\n\n"
            "Poderia reservar 20 minutos esta semana?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
        "email_destino":   "admcapricciosa@gmail.com",
        "email_assunto":   ascii_clean("Um numero unico para as 4 Capricciosias - gestao central de encomendas"),
        "whatsapp_destino": "",
        "callback_url":    SEND_URL,
        "session_id":      "CLOSER-Capricciosa-20260606-FAB002",
    },

    # -----------------------------------------------------------------------
    # FAB-003 Tupuca, LDA (Tupuca+) — score 8 — WhatsApp
    # 120+ restaurantes parceiros, crescimento 5%/mês. CEO: Erickson Mvezi.
    # Ângulo diferente: não é atendimento a clientes finais — é automação de
    # onboarding e suporte a parceiros para escalar sem crescer a equipa.
    # -----------------------------------------------------------------------
    {
        "tipo": "mensagem",
        "agente": "CLOSER",
        "titulo": ascii_clean("FAB-003 Tupuca+ - primeiro contacto WhatsApp"),
        "cliente": ascii_clean("Tupuca, LDA (Tupuca+)"),
        "valor": "AOA 1.440.000 - 2.880.000",
        "resumo": ascii_clean(
            "WhatsApp de primeiro contacto para a Tupuca+ (plataforma delivery, 120+ "
            "restaurantes parceiros, CEO Erickson Mvezi). Angulo: onboarding e suporte "
            "a parceiros por telefone e email nao escala — automatizamos o fluxo para "
            "que a Tupuca chegue a 200+ parceiros com a mesma equipa."
        ),
        "texto_completo": ascii_clean(
            "Bom dia! Sou o Fidel da Bisca+ — automatizamos processos operacionais "
            "para plataformas de delivery em Angola.\n\n"
            "A Tupuca tem 120+ restaurantes parceiros e cresce 5%/mês. A partir de "
            "certa escala, o onboarding e o suporte por telefone e email bloqueiam a "
            "expansão — a equipa de operações gasta tempo a gerir o que existe em vez "
            "de crescer.\n\n"
            "Na Bisca+, automatizamos o fluxo de onboarding de novos parceiros e o "
            "suporte de nível 1 via WhatsApp: documentação, configuração de menu, "
            "formação e relatórios — sem intervenção manual. A Tupuca pode chegar a "
            "200+ parceiros com a mesma equipa que tem hoje.\n\n"
            "Vale 20 minutos de conversa com o Erickson Mvezi?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
        "texto_publicar": (
            "Bom dia! Sou o Fidel da Bisca+ — automatizamos processos operacionais "
            "para plataformas de delivery em Angola.\n\n"
            "A Tupuca tem 120+ restaurantes parceiros e cresce 5%/mês. A partir de "
            "certa escala, o onboarding e o suporte por telefone e email bloqueiam a "
            "expansão — a equipa de operações gasta tempo a gerir o que existe em vez "
            "de crescer.\n\n"
            "Na Bisca+, automatizamos o fluxo de onboarding de novos parceiros e o "
            "suporte de nível 1 via WhatsApp: documentação, configuração de menu, "
            "formação e relatórios — sem intervenção manual. A Tupuca pode chegar a "
            "200+ parceiros com a mesma equipa que tem hoje.\n\n"
            "Vale 20 minutos de conversa com o Erickson Mvezi?\n\n"
            "Fidel Kussunga | Bisca+\n"
            "contact@biscaplus.com | +244 956 873 126"
        ),
        "whatsapp_destino": "244944909797",
        "email_destino":    "",
        "email_assunto":    "",
        "callback_url":     SEND_URL,
        "session_id":       "CLOSER-Tupuca-20260606-FAB003",
    },
]

# ---------------------------------------------------------------------------
# BLOQUEADOS
# FAB-004 Global Catering Angola — canal: LinkedIn (Unipile expirado)
#   Acção: renovar chave em app.unipile.com → actualizar .env.example + Fly.io
# FAB-005 Red-M, LDA — canal: tel +244 222 717 085 / Instagram @redm.lda
#   Acção: contacto manual por telefone ou DM Instagram (sem canal automatizado)
# ---------------------------------------------------------------------------

print(f"CLOSER — aprovacoes FAB | {len(aprovacoes)}/5 (FAB-004 e FAB-005 bloqueados)")
print("=" * 60)

for i, payload in enumerate(aprovacoes, 1):
    sid     = payload["session_id"]
    cliente = payload["cliente"]
    canal   = "email" if payload.get("email_destino") else "WhatsApp"
    destino = payload.get("email_destino") or payload.get("whatsapp_destino")
    print(f"[{i:02d}/03] {cliente} — {canal} {destino}...", end=" ", flush=True)
    try:
        r = requests.post(APROVACAO_URL, json=payload, timeout=30, verify=False)
        resultado = r.json()
        status = resultado.get("status", f"? HTTP{r.status_code}")
        print(status)
    except Exception as e:
        print(f"ERRO: {e}")
    time.sleep(1)

print("\n" + "=" * 60)
print("3 aprovacoes FAB submetidas. CEO notificado via WhatsApp.")
print("FAB-004: aguarda renovacao Unipile | FAB-005: contacto manual")
