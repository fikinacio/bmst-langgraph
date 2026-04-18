"""
Alertas críticos — escalação automática para o fundador
"""
from core.telegram_client import TelegramClient


_telegram = TelegramClient()


def alerta_critico(mensagem: str) -> None:
    """Alerta de alta prioridade — usado para erros de sistema e bloqueios."""
    _telegram.send_message(f"🔴 ALERTA CRÍTICO\n\n{mensagem}")


def alerta_pagamento_atraso(empresa: str, valor: int, dias: int) -> None:
    _telegram.send_message(
        f"💰 PAGAMENTO EM ATRASO\n\n"
        f"Empresa: {empresa}\n"
        f"Valor: {valor:,} AOA\n"
        f"Dias em atraso: {dias}"
    )


def alerta_lead_seg_c(empresa: str, notas: str) -> None:
    _telegram.send_message(
        f"⚠️ LEAD SEG C — APROVAÇÃO NECESSÁRIA\n\n"
        f"Empresa: {empresa}\n"
        f"Notas: {notas[:300]}"
    )


def alerta_cliente_sem_resposta(empresa: str, servico: str, dias: int) -> None:
    _telegram.send_message(
        f"📵 CLIENTE SEM RESPOSTA\n\n"
        f"Empresa: {empresa}\n"
        f"Projecto: {servico}\n"
        f"Dias sem resposta: {dias}"
    )


def alerta_erro_sistema(agente: str, erro: str) -> None:
    _telegram.send_message(
        f"🛑 ERRO DE SISTEMA\n\n"
        f"Agente: {agente}\n"
        f"Erro: {erro[:500]}"
    )
