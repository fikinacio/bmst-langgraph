# agents/prospector/tools.py — data acquisition tools for the PROSPECTOR agent

from __future__ import annotations

import asyncio
import logging
import os
import random
import re

import httpx

logger = logging.getLogger(__name__)

# ── HTTP configuration ────────────────────────────────────────────────────────

_TIMEOUT = httpx.Timeout(15.0, connect=5.0)

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) Gecko/20100101 Firefox/124.0",
]

_GOOGLE_PLACES_BASE = "https://maps.googleapis.com/maps/api/place"


def _random_headers() -> dict[str, str]:
    return {
        "User-Agent": random.choice(_USER_AGENTS),
        "Accept-Language": "pt-AO,pt;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }


# ── Angola phone normalisation ────────────────────────────────────────────────

_WA_REGEX = re.compile(
    r"(?:wa\.me/|whatsapp\.com/send\?phone=)[\+]?(244)?(\d{9})",
    re.IGNORECASE,
)
_ANGOLA_PHONE_REGEX = re.compile(
    r"(?:\+244|244)?[\s\-\.]?(9\d{2})[\s\-\.]?(\d{3})[\s\-\.]?(\d{3})"
)


def normalize_angola_phone(raw: str) -> str | None:
    """
    Normalise any Angolan phone string to +244XXXXXXXXX format.

    Handles:
      "923 456 789"     → "+244923456789"
      "244923456789"    → "+244923456789"
      "+244923456789"   → "+244923456789"
      "923456789"       → "+244923456789"
      "wa.me/244923..." → "+244923456789"
    Returns None if the number cannot be recognised.
    """
    if not raw:
        return None

    # Extract from wa.me / whatsapp links
    wa_match = _WA_REGEX.search(raw)
    if wa_match:
        digits = wa_match.group(2)
        return f"+244{digits}"

    # Extract from plain phone patterns
    m = _ANGOLA_PHONE_REGEX.search(raw)
    if m:
        return f"+244{m.group(1)}{m.group(2)}{m.group(3)}"

    return None


def extract_all_phones(text: str) -> list[str]:
    """Return all normalised Angola phone numbers found in text."""
    phones: list[str] = []

    # wa.me links first (highest confidence)
    for wa_match in _WA_REGEX.finditer(text):
        phones.append(f"+244{wa_match.group(2)}")

    # Plain phone patterns
    for m in _ANGOLA_PHONE_REGEX.finditer(text):
        candidate = f"+244{m.group(1)}{m.group(2)}{m.group(3)}"
        if candidate not in phones:
            phones.append(candidate)

    return phones


# ── Google Places API ─────────────────────────────────────────────────────────

async def google_places_search(
    sector: str,
    city: str,
    api_key: str,
    max_results: int = 30,
) -> list[dict]:
    """
    Search Google Places for businesses in the given sector and city.

    Calls Text Search to discover companies, then Place Details for each to get
    phone number and website. Returns a list of enriched company dicts.

    Each result dict contains:
      name, address, phone, website, rating, place_id, types, maps_url
    """
    query   = f"{sector} em {city}, Angola"
    results = await _places_text_search(query, api_key)
    logger.info("google_places_search: %d raw results for '%s'", len(results), query)

    enriched: list[dict] = []
    for place in results[:max_results]:
        place_id = place.get("place_id", "")
        detail   = await _places_details(place_id, api_key) if place_id else {}

        # Rate-limit: respect 10 req/s quota
        await asyncio.sleep(0.15)

        enriched.append({
            "name":      place.get("name", ""),
            "address":   place.get("formatted_address", ""),
            "phone":     detail.get("formatted_phone_number", ""),
            "website":   detail.get("website", ""),
            "maps_url":  detail.get("url", ""),
            "rating":    place.get("rating", 0),
            "place_id":  place_id,
            "types":     place.get("types", []),
        })

    return enriched


async def _places_text_search(query: str, api_key: str) -> list[dict]:
    """Call Google Places Text Search and return raw result list."""
    params = {
        "query":    query,
        "language": "pt",
        "key":      api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{_GOOGLE_PLACES_BASE}/textsearch/json", params=params)
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") not in ("OK", "ZERO_RESULTS"):
                logger.warning("Places Text Search status: %s", data.get("status"))
            return data.get("results", [])
    except Exception as exc:
        logger.error("_places_text_search failed: %s", exc)
        return []


async def _places_details(place_id: str, api_key: str) -> dict:
    """Fetch phone number and website for a single Place ID."""
    params = {
        "place_id": place_id,
        "fields":   "formatted_phone_number,website,url",
        "language": "pt",
        "key":      api_key,
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{_GOOGLE_PLACES_BASE}/details/json", params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", {})
    except Exception as exc:
        logger.error("_places_details failed (place_id=%s): %s", place_id, exc)
        return {}


# ── Website scraping ──────────────────────────────────────────────────────────

async def scrape_website_for_whatsapp(url: str) -> dict:
    """
    Fetch a company website and extract WhatsApp numbers and social media links.

    Returns:
        {
          "phones": ["+244923456789", ...],
          "instagram_url": "https://instagram.com/...",
          "facebook_url":  "https://facebook.com/...",
          "text_snippet":  first 500 chars of visible text
        }
    """
    if not url:
        return {"phones": [], "instagram_url": None, "facebook_url": None, "text_snippet": ""}

    try:
        delay = random.uniform(
            float(os.environ.get("PROSPECTOR_DELAY_MIN", "2")),
            float(os.environ.get("PROSPECTOR_DELAY_MAX", "5")),
        )
        await asyncio.sleep(delay)

        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers=_random_headers(),
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text

        phones        = extract_all_phones(html)
        instagram_url = _extract_social_link(html, "instagram.com")
        facebook_url  = _extract_social_link(html, "facebook.com")
        text_snippet  = re.sub(r"<[^>]+>", " ", html)[:500].strip()

        return {
            "phones":        phones,
            "instagram_url": instagram_url,
            "facebook_url":  facebook_url,
            "text_snippet":  text_snippet,
        }
    except Exception as exc:
        logger.warning("scrape_website_for_whatsapp failed (url=%s): %s", url, exc)
        return {"phones": [], "instagram_url": None, "facebook_url": None, "text_snippet": ""}


def _extract_social_link(html: str, domain: str) -> str | None:
    """Extract the first href pointing to the given social domain from HTML."""
    pattern = re.compile(
        r'href=["\']?(https?://(?:www\.)?' + re.escape(domain) + r'/[^\s"\'<>]+)',
        re.IGNORECASE,
    )
    m = pattern.search(html)
    return m.group(1) if m else None


# ── Instagram bio scraping ────────────────────────────────────────────────────

async def try_instagram_bio(company_name: str) -> dict:
    """
    Attempt to fetch an Instagram business profile by constructing a probable slug.

    Tries the most common slug variants (lowercased, no spaces, with/without dots).
    Returns a dict with any phone numbers or external URLs found in the bio.

    May fail if Instagram blocks the request — callers must handle gracefully.
    """
    slug = _company_to_instagram_slug(company_name)
    if not slug:
        return {"phones": [], "bio": "", "external_url": None}

    url = f"https://www.instagram.com/{slug}/"
    try:
        delay = random.uniform(2.0, 4.0)
        await asyncio.sleep(delay)

        async with httpx.AsyncClient(
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers=_random_headers(),
        ) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                return {"phones": [], "bio": "", "external_url": None}
            resp.raise_for_status()
            html = resp.text

        phones   = extract_all_phones(html)
        bio_text = _extract_instagram_bio(html)

        return {
            "phones":       phones,
            "bio":          bio_text,
            "external_url": None,
            "instagram_url": url if resp.status_code == 200 else None,
        }
    except Exception as exc:
        logger.debug("try_instagram_bio failed (company=%s): %s", company_name, exc)
        return {"phones": [], "bio": "", "external_url": None}


def _company_to_instagram_slug(name: str) -> str:
    """Convert a company name to the most probable Instagram username."""
    slug = name.lower().strip()
    # Remove common legal suffixes
    for suffix in ("lda", "sa", "srl", "angola", "luanda", "- angola", "- luanda"):
        slug = slug.replace(suffix, "")
    slug = re.sub(r"[^a-z0-9]", "", slug)  # keep only alphanumeric
    return slug[:30] if len(slug) >= 3 else ""


def _extract_instagram_bio(html: str) -> str:
    """Extract the bio text from Instagram HTML (best-effort regex)."""
    patterns = [
        r'"biography":"([^"]*)"',
        r'<meta\s+name="description"\s+content="([^"]{10,200})"',
    ]
    for pattern in patterns:
        m = re.search(pattern, html)
        if m:
            return m.group(1)[:300]
    return ""
