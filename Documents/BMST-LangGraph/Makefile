# BMST Agents — comandos de produção
#
# Uso:
#   make up        — arranca todos os serviços em background
#   make down      — para e remove containers
#   make restart   — restart sem perder dados (Redis persistente)
#   make logs      — segue os logs em tempo real
#   make status    — mostra containers e health
#   make test      — corre a suite de testes local
#   make hunter    — dispara um batch HUNTER manualmente
#   make health    — chama o endpoint /health

include .env

COMPOSE = docker compose
API_URL  = http://localhost:8000

.PHONY: up down restart logs status test hunter health shell rebuild

# ── Ciclo de vida ──────────────────────────────────────────────────────────────

up:
	@echo "→ A criar rede bmst-net (ignora se já existe)..."
	docker network create bmst-net 2>/dev/null || true
	@echo "→ A arrancar serviços..."
	$(COMPOSE) up -d --build
	@echo "→ Serviços a correr. A aguardar health check..."
	@sleep 5
	@$(MAKE) health

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart bmst-agents

rebuild:
	$(COMPOSE) up -d --build --force-recreate bmst-agents

# ── Observabilidade ────────────────────────────────────────────────────────────

logs:
	$(COMPOSE) logs -f bmst-agents

logs-all:
	$(COMPOSE) logs -f

status:
	$(COMPOSE) ps
	@echo ""
	@$(MAKE) health

health:
	@curl -s $(API_URL)/health | python3 -m json.tool || echo "API não responde"

# ── Operações manuais ──────────────────────────────────────────────────────────

hunter:
	@echo "→ A disparar HUNTER batch (max 20 leads)..."
	curl -s -X POST $(API_URL)/hunter/batch \
	  -H "Content-Type: application/json" \
	  -H "X-Api-Key: $(BMST_API_KEY)" \
	  -d '{"max_leads": 20}' | python3 -m json.tool

hunter-dry:
	@echo "→ HUNTER batch (max 1 lead — modo teste)..."
	curl -s -X POST $(API_URL)/hunter/batch \
	  -H "Content-Type: application/json" \
	  -H "X-Api-Key: $(BMST_API_KEY)" \
	  -d '{"max_leads": 1}' | python3 -m json.tool

metrics:
	curl -s $(API_URL)/metrics \
	  -H "X-Api-Key: $(BMST_API_KEY)" | python3 -m json.tool

shell:
	$(COMPOSE) exec bmst-agents bash

# ── Testes ─────────────────────────────────────────────────────────────────────

test:
	python3 -m pytest tests/ -v --no-header

test-watch:
	python3 -m pytest tests/ -v --no-header -f
