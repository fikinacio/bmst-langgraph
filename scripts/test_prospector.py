#!/usr/bin/env python3
"""scripts/test_prospector.py — validates each layer of the PROSPECTOR pipeline."""
from __future__ import annotations

import asyncio
import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.prospector.tools import (
    google_places_search,
    scrape_website_for_whatsapp,
    try_instagram_bio,
)


async def test_places(api_key: str) -> tuple[bool, list[dict]]:
    print("[1/3] Google Places API — a pesquisar 'saúde' em Luanda...")
    try:
        results = await google_places_search(
            sector="saúde",
            city="Luanda",
            api_key=api_key,
            max_results=3,
        )
    except Exception as exc:
        print(f"  ✗ FALHOU: {exc}")
        return False, []

    if not results:
        print("  ✗ FALHOU: nenhum resultado retornado — verificar GOOGLE_PLACES_API_KEY e billing")
        return False, []

    for r in results:
        print(f"  • {r['name']}")
        print(f"    morada:  {r['address']}")
        print(f"    tel:     {r['phone'] or '(sem telefone no Places)'}")
        print(f"    website: {r['website'] or '(sem website)'}")
        print(f"    rating:  {r['rating']}")

    print(f"  ✓ OK — {len(results)} empresa(s) encontrada(s)\n")
    return True, results


async def test_scraper(url: str) -> bool:
    print(f"[2/3] Website Scraper — a fazer scrape de {url} ...")
    try:
        result = await scrape_website_for_whatsapp(url)
    except Exception as exc:
        print(f"  ✗ FALHOU: {exc}")
        return False

    phones = result.get("phones", [])
    insta  = result.get("instagram_url")
    fb     = result.get("facebook_url")
    snip   = (result.get("text_snippet") or "")[:120]

    print(f"  • WhatsApp(s) encontrado(s): {phones if phones else '(nenhum)'}")
    print(f"  • Instagram: {insta or '(não encontrado)'}")
    print(f"  • Facebook:  {fb or '(não encontrado)'}")
    print(f"  • Snippet:   {snip}...")

    if phones:
        print(f"  ✓ OK — WhatsApp: {phones[0]}\n")
    else:
        print("  ⚠ OK — sem WhatsApp directo (normal para muitos sites angolanos)\n")
    return True


async def test_instagram(company_name: str) -> bool:
    print(f"[3/3] Instagram Scraper — a pesquisar perfil para '{company_name}' ...")
    try:
        result = await try_instagram_bio(company_name)
    except Exception as exc:
        print(f"  ✗ FALHOU: {exc}")
        return False

    phones = result.get("phones", [])
    bio    = result.get("bio", "")

    print(f"  • Bio:    {bio[:120] if bio else '(não encontrado)'}")
    print(f"  • Phones: {phones if phones else '(nenhum)'}")

    if bio:
        print(f"  ✓ OK — perfil encontrado\n")
    else:
        print("  ⚠ OK — perfil Instagram não encontrado (normal — muitas PME angolanas não têm)\n")
    return True


async def main() -> None:
    print("=" * 60)
    print("PROSPECTOR — Validação de Pipeline")
    print("=" * 60)
    print()

    api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        print("ERRO: GOOGLE_PLACES_API_KEY não está definido no ambiente.")
        print("  Execute: export GOOGLE_PLACES_API_KEY=<chave>")
        sys.exit(1)

    places_ok, companies = await test_places(api_key)

    # Use first result's website for scraper test; fallback to a known URL
    test_url = ""
    company_name = "Clínica Katondo"
    if places_ok and companies:
        test_url     = companies[0].get("website", "")
        company_name = companies[0].get("name", company_name)

    if not test_url:
        test_url = "https://clinicakatondo.ao"
        print(f"  (nenhum website no 1º resultado — a usar fallback: {test_url})\n")

    await test_scraper(test_url)
    await test_instagram(company_name)

    print("=" * 60)
    print("Validação concluída. Se todos os testes passaram, corre:")
    print()
    print('  curl -X POST https://<VPS>/prospector/run \\')
    print('    -H "X-Api-Key: $BMST_API_KEY" \\')
    print('    -H "Content-Type: application/json" \\')
    print("    -d '{\"sector\": \"saude\", \"city\": \"Luanda\", \"max_companies\": 3}'")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
