# -*- coding: utf-8 -*-
"""
Envia convite LinkedIn a Rui Serrano Nogueira (Director, Atlântida WTA)
para VIA-002 — via Unipile API.
"""

import requests
import json

UNIPILE_BASE = "https://api21.unipile.com:15124/api/v1"
UNIPILE_KEY = "rJmhogjf.bl7pQPHfS7YIx9ESf/eu5YLPJ0cfrgBqy5AxSbld6DE="
ACCOUNT_ID = "4BuyU1K_SLyP8Tp28Jwn9Q"

HEADERS = {
    "X-API-KEY": UNIPILE_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# Perfil LinkedIn do decisor
LINKEDIN_IDENTIFIER = "rui-serrano-nogueira-04289724"

# Mensagem < 300 chars (limite LinkedIn connection note)
MESSAGE = (
    "Bom dia Rui! A Atlantida WTA gere viagens de executivos ha 35 anos em Angola. "
    "Automatizamos confirmacoes de voo, check-in e alertas para clientes corporativos "
    "— a equipa trata so o que importa. Faz sentido falarmos esta semana? "
    "— Fidel, Bisca+ | +244 956 873 126"
)

print(f"Mensagem ({len(MESSAGE)} chars): {MESSAGE}\n")

# Passo 1: obter o provider_id via endpoint de perfil LinkedIn
print("Passo 1: a obter perfil LinkedIn...")
try:
    r = requests.get(
        f"{UNIPILE_BASE}/linkedin/users/{ACCOUNT_ID}/profile",
        headers=HEADERS,
        params={"public_identifier": LINKEDIN_IDENTIFIER},
        verify=False,
        timeout=30,
    )
    print(f"  HTTP {r.status_code}")
    print(f"  Resposta: {r.text[:500]}")
    if r.status_code == 200:
        data = r.json()
        provider_id = data.get("provider_id") or data.get("id") or data.get("entity_urn")
        print(f"  provider_id: {provider_id}")
    else:
        provider_id = None
except Exception as e:
    print(f"  ERRO: {e}")
    provider_id = None

# Passo 2: se não encontrou via profile endpoint, tentar search
if not provider_id:
    print("\nPasso 1b: a tentar search LinkedIn...")
    try:
        r2 = requests.get(
            f"{UNIPILE_BASE}/linkedin/users/{ACCOUNT_ID}/search",
            headers=HEADERS,
            params={"q": "Rui Serrano Nogueira Atlantida Angola", "limit": 3},
            verify=False,
            timeout=30,
        )
        print(f"  HTTP {r2.status_code}")
        print(f"  Resposta: {r2.text[:800]}")
        if r2.status_code == 200:
            data2 = r2.json()
            items = data2.get("items") or data2.get("results") or []
            if items:
                first = items[0]
                provider_id = first.get("provider_id") or first.get("id")
                print(f"  provider_id (search): {provider_id}")
    except Exception as e:
        print(f"  ERRO: {e}")

# Passo 3: enviar convite
if provider_id:
    print(f"\nPasso 2: a enviar convite LinkedIn a provider_id={provider_id}...")
    payload = {
        "provider_id": provider_id,
        "account_id": ACCOUNT_ID,
        "message": MESSAGE,
    }
    try:
        r3 = requests.post(
            f"{UNIPILE_BASE}/users/invite",
            headers=HEADERS,
            json=payload,
            verify=False,
            timeout=30,
        )
        print(f"  HTTP {r3.status_code}")
        print(f"  Resposta: {r3.text[:500]}")
        if r3.status_code in (200, 201):
            print("  CONVITE ENVIADO COM SUCESSO")
        else:
            print("  FALHOU — ver resposta acima")
    except Exception as e:
        print(f"  ERRO: {e}")
else:
    print("\nNao foi possivel obter o provider_id. A tentar envio directo com public_identifier...")
    # Alguns SDKs Unipile aceitam o public_identifier directamente
    payload_alt = {
        "provider_id": LINKEDIN_IDENTIFIER,
        "account_id": ACCOUNT_ID,
        "message": MESSAGE,
    }
    try:
        r4 = requests.post(
            f"{UNIPILE_BASE}/users/invite",
            headers=HEADERS,
            json=payload_alt,
            verify=False,
            timeout=30,
        )
        print(f"  HTTP {r4.status_code}")
        print(f"  Resposta: {r4.text[:500]}")
    except Exception as e:
        print(f"  ERRO: {e}")
