#!/usr/bin/env python3
"""
BMST Agents — Script de simulação completo

Percorre o pipeline inteiro com um lead fictício:
  1. HUNTER  → batch (tenta ler leads do Sheet e enviar WA)
  2. CLOSER  → diagnose (inicia conversa de diagnóstico)
  3. CLOSER  → webhook x3 (simula respostas do prospect ao diagnóstico)
  4. DELIVERY → start (onboarding do projeto)
  5. DELIVERY → update: actualizar (progresso a meio de semana)
  6. DELIVERY → update: solicitar_aprovacao (cliente aprova fase)
  7. DELIVERY → webhook (cliente responde SIM)
  8. LEDGER  → invoice adiantamento (50%)
  9. LEDGER  → check-payments (verifica se pagou — vai estar pendente)
  10. LEDGER  → invoice saldo (50% final)
  11. DELIVERY → update: encerrar (entrega final)

Uso:
    python scripts/simulate.py --api-key SEU_BMST_API_KEY
    # ou define BMST_API_KEY no ambiente
"""
from __future__ import annotations

import argparse
import os
import sys
import time

try:
    import httpx
except ImportError:
    print("ERROR: httpx não instalado. Corre: pip install httpx")
    sys.exit(1)

BASE_URL = os.environ.get("BMST_BASE_URL", "https://agents.biscaplus.com")

# ── Lead de teste ─────────────────────────────────────────────────────────────
LEAD = {
    "phone":       "+244923000001",
    "empresa":     "Clínica Bem-Estar",
    "sector":      "saude",
    "segmento":    "B",
    "responsavel": "Dr. Santos",
}
PROJECT_ID = "proj-2026-001"
VALOR_AOA  = 250_000


# ── Helpers ───────────────────────────────────────────────────────────────────

def step(title: str) -> None:
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print('─'*60)


def call(
    client: httpx.Client,
    method: str,
    path: str,
    payload: dict | None = None,
    *,
    expect_status: int = 200,
) -> dict:
    url = f"{BASE_URL}{path}"
    r = client.request(method, url, json=payload)
    status_ok = "✅" if r.status_code == expect_status else "⚠️ "
    print(f"{status_ok} {method} {path}  →  HTTP {r.status_code}")
    try:
        data = r.json()
        print(f"   {data}")
        return data
    except Exception:
        print(f"   (resposta não-JSON) {r.text[:200]}")
        return {}


def pause(seconds: int = 3) -> None:
    for i in range(seconds, 0, -1):
        print(f"   aguarda {i}s...", end="\r")
        time.sleep(1)
    print("   " + " "*20)


# ── Simulação ─────────────────────────────────────────────────────────────────

def main(api_key: str) -> None:
    headers = {
        "X-Api-Key":    api_key,
        "Content-Type": "application/json",
    }

    print(f"\n{'='*60}")
    print("  BMST Agents — Simulação completa do pipeline")
    print(f"  Base URL: {BASE_URL}")
    print(f"  Lead:     {LEAD['empresa']} ({LEAD['phone']})")
    print(f"{'='*60}")

    with httpx.Client(headers=headers, timeout=30) as client:

        # ── 0. Health check ───────────────────────────────────────────────────
        step("0 ▸ Health check")
        call(client, "GET", "/health")

        # ── 1. HUNTER batch ───────────────────────────────────────────────────
        step("1 ▸ HUNTER — batch (lê leads do Google Sheet e envia WA)")
        print("   → O HUNTER vai tentar ler o Sheet e enviar mensagens.")
        print("   → Se o Sheet estiver vazio ou WA falhar, aparece nos logs do EasyPanel.")
        call(
            client, "POST", "/hunter/batch",
            {"max_leads": 3},
            expect_status=202,
        )
        pause(2)

        # ── 2. CLOSER — iniciar diagnóstico ───────────────────────────────────
        step("2 ▸ CLOSER — diagnose (lead interessado entra no pipeline)")
        print("   → O CLOSER envia a 1ª pergunta de diagnóstico via WA.")
        print("   → O grafo pausa (interrupt) a aguardar resposta do prospect.")
        call(
            client, "POST", "/closer/diagnose",
            {
                "phone":       LEAD["phone"],
                "empresa":     LEAD["empresa"],
                "sector":      LEAD["sector"],
                "segmento":    LEAD["segmento"],
                "responsavel": LEAD["responsavel"],
                "historico": [
                    {
                        "role":    "assistant",
                        "content": (
                            "Bom dia Dr. Santos! Vi que a Clínica Bem-Estar tem bastante "
                            "actividade no Instagram mas os comentários ficam sem resposta. "
                            "Teria 10 minutos esta semana?"
                        ),
                    },
                    {
                        "role":    "user",
                        "content": "Sim, pode dizer. Que solução tem em mente?",
                    },
                ],
            },
            expect_status=202,
        )
        pause(4)

        # ── 3. CLOSER — respostas do prospect (diagnóstico) ───────────────────
        step("3a ▸ CLOSER webhook — resposta ao diagnóstico P1")
        print("   Prospect responde: recebe umas 60 mensagens/dia pelo WA")
        call(
            client, "POST", "/closer/webhook",
            {
                "phone":      LEAD["phone"],
                "message":    "Recebemos umas 60 mensagens por dia no WhatsApp, é impossível responder a tudo.",
                "message_id": "msg-sim-001",
                "timestamp":  int(time.time()),
            },
        )
        pause(4)

        step("3b ▸ CLOSER webhook — resposta ao diagnóstico P2")
        print("   Prospect responde: equipa de 2 pessoas na recepção")
        call(
            client, "POST", "/closer/webhook",
            {
                "phone":      LEAD["phone"],
                "message":    "Temos 2 pessoas na recepção. A maior parte das mensagens são para marcar consultas ou pedir preços.",
                "message_id": "msg-sim-002",
                "timestamp":  int(time.time()),
            },
        )
        pause(4)

        step("3c ▸ CLOSER webhook — resposta ao diagnóstico P3 (diagnóstico completo)")
        print("   Prospect responde: orçamento e urgência")
        call(
            client, "POST", "/closer/webhook",
            {
                "phone":      LEAD["phone"],
                "message":    "Estamos a perder clientes por falta de resposta. Podemos investir até 300 mil AOA se o retorno justificar.",
                "message_id": "msg-sim-003",
                "timestamp":  int(time.time()),
            },
        )
        pause(4)

        # ── 4. CLOSER webhook — prospect aceita a apresentação verbal ─────────
        step("4 ▸ CLOSER webhook — prospect aceita a proposta verbal")
        print("   Depois da apresentação verbal (aprovada pelo founder no Telegram),")
        print("   o prospect responde positivamente.")
        print("   NOTA: o founder precisa de ter aprovado no Telegram antes deste passo.")
        call(
            client, "POST", "/closer/webhook",
            {
                "phone":      LEAD["phone"],
                "message":    "Sim, faz sentido. Pode enviar a proposta formal.",
                "message_id": "msg-sim-004",
                "timestamp":  int(time.time()),
            },
        )
        pause(4)

        # ── 5. CLOSER webhook — prospect aceita a proposta formal ─────────────
        step("5 ▸ CLOSER webhook — prospect aceita a proposta formal (FECHADO)")
        print("   O prospect responde ao PDF da proposta com aceitação.")
        call(
            client, "POST", "/closer/webhook",
            {
                "phone":      LEAD["phone"],
                "message":    "Aceito. Quando podemos começar? Vou transferir o adiantamento hoje.",
                "message_id": "msg-sim-005",
                "timestamp":  int(time.time()),
            },
        )
        pause(3)

        # ── 6. LEDGER — factura de adiantamento (50%) ─────────────────────────
        step("6 ▸ LEDGER — emitir factura de adiantamento (50% = 125.000 AOA)")
        print("   → Cria factura no InvoiceNinja.")
        print("   → Gera mensagem WA com dados de pagamento.")
        print("   → Envia para aprovação no Telegram antes de enviar ao cliente.")
        call(
            client, "POST", "/ledger/invoice",
            {
                "projecto_id": PROJECT_ID,
                "empresa":     LEAD["empresa"],
                "phone":       LEAD["phone"],
                "responsavel": LEAD["responsavel"],
                "tipo_factura": "adiantamento",
                "valor_aoa":   VALOR_AOA // 2,
                "servico":     "Chatbot WhatsApp básico",
            },
            expect_status=202,
        )
        pause(3)

        # ── 7. DELIVERY — iniciar projeto ─────────────────────────────────────
        step("7 ▸ DELIVERY — start (adiantamento confirmado, projeto começa)")
        print("   → Cria página no Notion.")
        print("   → Gera mensagem de boas-vindas ao novo cliente.")
        print("   → Envia para revisão do Telegram antes de enviar ao cliente.")
        call(
            client, "POST", "/delivery/start",
            {
                "projecto_id":          PROJECT_ID,
                "empresa":              LEAD["empresa"],
                "servico":              "Chatbot WhatsApp básico",
                "phone":                LEAD["phone"],
                "responsavel":          LEAD["responsavel"],
                "segmento":             LEAD["segmento"],
                "data_entrega_prevista": "2026-05-16",
            },
            expect_status=202,
        )
        pause(4)

        # ── 8. DELIVERY — actualização de progresso ───────────────────────────
        step("8 ▸ DELIVERY — actualização de progresso (D+3)")
        print("   → Gera mensagem de progresso 2x/semana.")
        print("   → Passa pelo Revisor e aprovação Telegram.")
        call(
            client, "POST", "/delivery/update",
            {
                "projecto_id":    PROJECT_ID,
                "proxima_acao":   "actualizar",
                "itens_concluidos": [
                    "Análise de requisitos concluída",
                    "Fluxo de marcações desenhado e aprovado",
                ],
                "itens_pendentes": [
                    "Desenvolvimento do chatbot (em curso)",
                    "Integração com agenda da clínica",
                ],
            },
            expect_status=202,
        )
        pause(3)

        # ── 9. DELIVERY — solicitar aprovação de fase ─────────────────────────
        step("9 ▸ DELIVERY — solicitar aprovação de fase (desenvolvimento → revisão)")
        print("   → Envia mensagem ao cliente a pedir aprovação para avançar.")
        call(
            client, "POST", "/delivery/update",
            {
                "projecto_id":    PROJECT_ID,
                "proxima_acao":   "solicitar_aprovacao",
                "itens_concluidos": [
                    "Chatbot desenvolvido e testado internamente",
                    "Integração WhatsApp activa",
                    "Fluxo de marcações automáticas a funcionar",
                ],
                "itens_pendentes": [
                    "Revisão com o cliente",
                    "Ajustes finais",
                ],
            },
            expect_status=202,
        )
        pause(3)

        # ── 10. DELIVERY webhook — cliente aprova a fase ──────────────────────
        step("10 ▸ DELIVERY webhook — cliente aprova a fase de revisão")
        print("   → Simula cliente a responder SIM à aprovação de fase.")
        call(
            client, "POST", "/delivery/webhook",
            {
                "thread_id": f"delivery-{PROJECT_ID}",
                "phone":     LEAD["phone"],
                "aprovado":  True,
            },
        )
        pause(3)

        # ── 11. LEDGER — verificar pagamento do adiantamento ──────────────────
        step("11 ▸ LEDGER — verificar pagamento do adiantamento")
        print("   → Consulta InvoiceNinja. Provavelmente 'pendente' neste momento.")
        print("   → Se estiver em atraso, enviaria lembrete D+3/D+7/D+14.")
        call(
            client, "POST", "/ledger/check-payments",
            {
                "projecto_id":     PROJECT_ID,
                "invoice_ninja_id": "",
            },
            expect_status=202,
        )
        pause(3)

        # ── 12. LEDGER — factura saldo final (50%) ────────────────────────────
        step("12 ▸ LEDGER — emitir factura saldo final (50% = 125.000 AOA)")
        print("   → Emite segunda factura antes da entrega final.")
        call(
            client, "POST", "/ledger/invoice",
            {
                "projecto_id":  PROJECT_ID,
                "empresa":      LEAD["empresa"],
                "phone":        LEAD["phone"],
                "responsavel":  LEAD["responsavel"],
                "tipo_factura": "saldo",
                "valor_aoa":    VALOR_AOA // 2,
                "servico":      "Chatbot WhatsApp básico — saldo final",
            },
            expect_status=202,
        )
        pause(3)

        # ── 13. DELIVERY — encerrar projeto ───────────────────────────────────
        step("13 ▸ DELIVERY — encerrar projeto (entrega final)")
        print("   → ATENÇÃO: este passo vai BLOQUEAR se o LEDGER ainda não confirmou")
        print("     pagamento_final_confirmado=True. Isso é o comportamento correcto.")
        print("   → Em produção, o LEDGER actualiza o estado quando a factura é paga.")
        call(
            client, "POST", "/delivery/update",
            {
                "projecto_id":    PROJECT_ID,
                "proxima_acao":   "encerrar",
                "itens_concluidos": [
                    "Chatbot WhatsApp básico entregue",
                    "Integração com agenda activa",
                    "Equipa da Clínica formada",
                    "Documentação entregue",
                ],
                "itens_pendentes": [],
            },
            expect_status=202,
        )
        pause(3)

        # ── 14. Métricas finais ───────────────────────────────────────────────
        step("14 ▸ Métricas do sistema")
        call(client, "GET", "/metrics")

    print(f"\n{'='*60}")
    print("  Simulação concluída.")
    print("  Abre os logs do EasyPanel para ver toda a actividade:")
    print("  EasyPanel → bmst-agents → Logs")
    print(f"{'='*60}\n")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BMST pipeline simulation")
    parser.add_argument(
        "--api-key",
        default=os.environ.get("BMST_API_KEY", ""),
        help="BMST internal API key (X-Api-Key header)",
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("BMST_BASE_URL", "https://agents.biscaplus.com"),
        help="Base URL of the deployed API",
    )
    args = parser.parse_args()

    if not args.api_key:
        print("ERROR: API key em falta.")
        print("  Usa: python scripts/simulate.py --api-key TUA_CHAVE")
        print("  Ou define: export BMST_API_KEY=TUA_CHAVE")
        sys.exit(1)

    BASE_URL = args.base_url
    main(args.api_key)
