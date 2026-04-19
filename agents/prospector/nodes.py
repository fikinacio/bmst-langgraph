# agents/prospector/nodes.py — PROSPECTOR node implementations

from __future__ import annotations

import datetime
import logging
import os

from agents.prospector.state import ProspectorState
from agents.prospector.prompts import (
    APPROACH_NOTES_PROMPT,
    QUALIFY_LEAD_PROMPT,
    ApproachNotesSchema,
    QualifyLeadSchema,
)
from agents.prospector.tools import (
    google_places_search,
    scrape_website_for_whatsapp,
    try_instagram_bio,
    normalize_angola_phone,
)
from core.llm import create_json_message
from core import sheets_client, telegram_client

logger = logging.getLogger(__name__)

_AGENT = "prospector"

# ── Sector calendar ───────────────────────────────────────────────────────────
# Even ISO weeks → primary calendar; odd ISO weeks → alternate calendar

_SECTOR_CALENDAR = {
    0: "saúde",            # Monday    — clinics, hospitals, pharmacies
    1: "hotelaria",        # Tuesday   — hotels, restaurants, cafés
    2: "retalho",          # Wednesday — supermarkets, distributors
    3: "seguros",          # Thursday  — insurance, microfinance, real estate
    4: "educacao",         # Friday    — private schools, training centres
}

_SECTOR_CALENDAR_ALT = {
    0: "imobiliario",
    1: "logistica",
    2: "servicos_profissionais",
    3: "saúde",
    4: "retalho",
}

# Human-readable sector labels for Telegram report
_SECTOR_LABELS: dict[str, str] = {
    "saúde":                   "Saúde",
    "hotelaria":               "Hotelaria & Restauração",
    "retalho":                 "Retalho & Distribuição",
    "seguros":                 "Seguros & Imobiliário",
    "educacao":                "Educação & Serviços",
    "imobiliario":             "Imobiliário",
    "logistica":               "Logística",
    "servicos_profissionais":  "Serviços Profissionais",
}


# ── Node 1: initialize_session ────────────────────────────────────────────────

async def initialize_session(state: ProspectorState) -> dict:
    """
    Determine the sector for today based on the day-of-week calendar,
    set the run date, and reset all batch counters.
    """
    today     = datetime.date.today()
    weekday   = today.weekday()         # 0=Monday … 4=Friday
    iso_week  = today.isocalendar().week

    calendar  = _SECTOR_CALENDAR if iso_week % 2 == 0 else _SECTOR_CALENDAR_ALT
    sector    = state.get("sector") or calendar.get(weekday, "saúde")
    city      = state.get("city") or os.environ.get("PROSPECTOR_CIDADE", "Luanda")
    max_co    = state.get("max_companies") or int(os.environ.get("PROSPECTOR_MAX_EMPRESAS", "30"))

    logger.info(
        "prospector.initialize_session: date=%s weekday=%d sector=%s city=%s max=%d",
        today, weekday, sector, city, max_co,
    )

    return {
        "sector":          sector,
        "city":            city,
        "run_date":        today.isoformat(),
        "max_companies":   max_co,
        "raw_companies":   [],
        "current_company": None,
        "current_index":   0,
        "whatsapp_found":  None,
        "instagram_url":   None,
        "facebook_url":    None,
        "website_url":     None,
        "scraped_content": None,
        "approach_notes":  None,
        "opportunity":     None,
        "recommended_service": None,
        "segment":             None,
        "estimated_value_aoa": None,
        "qualified":           None,
        "leads_written":       0,
        "leads_skipped":       0,
        "errors":              [],
        "next_action":         None,
        "error":               None,
    }


# ── Node 2: discover_companies ────────────────────────────────────────────────

async def discover_companies(state: ProspectorState) -> dict:
    """
    Call Google Places Text Search + Details to discover companies in the
    target sector and city.
    """
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY", "")
    if not api_key:
        logger.error("prospector.discover_companies: GOOGLE_PLACES_API_KEY not set")
        return {
            "raw_companies": [],
            "next_action":   "no_results",
            "errors":        state.get("errors", []) + ["GOOGLE_PLACES_API_KEY not configured"],
        }

    sector = state["sector"]
    city   = state["city"]
    logger.info("prospector.discover_companies: searching '%s' in '%s'", sector, city)

    companies = await google_places_search(
        sector=sector,
        city=city,
        api_key=api_key,
        max_results=state.get("max_companies", 30),
    )

    logger.info("prospector.discover_companies: %d companies found", len(companies))
    next_action = "no_results" if not companies else "process"
    return {"raw_companies": companies, "next_action": next_action}


# ── Node 3: prepare_current_company ──────────────────────────────────────────

async def prepare_current_company(state: ProspectorState) -> dict:
    """
    Copy the company at current_index into current_company and reset enrichment fields.
    Sets next_action = 'batch_complete' when all companies are processed or the
    leads_written cap has been reached.
    """
    companies = state.get("raw_companies", [])
    idx       = state.get("current_index", 0)
    written   = state.get("leads_written", 0)
    max_co    = state.get("max_companies", 30)

    if idx >= len(companies) or written >= max_co:
        logger.info(
            "prospector.prepare_current_company: batch complete (idx=%d total=%d written=%d)",
            idx, len(companies), written,
        )
        return {"next_action": "batch_complete"}

    company = companies[idx]
    logger.info(
        "prospector.prepare_current_company: [%d/%d] %s",
        idx + 1, len(companies), company.get("name", "?"),
    )

    return {
        "current_company": company,
        "next_action":     "continue",
        # Reset enrichment fields for each new company
        "whatsapp_found":      None,
        "instagram_url":       None,
        "facebook_url":        None,
        "website_url":         company.get("website", None),
        "scraped_content":     None,
        "approach_notes":      None,
        "opportunity":         None,
        "recommended_service": None,
        "segment":             None,
        "estimated_value_aoa": None,
        "qualified":           None,
    }


# ── Node 4: check_duplicate_company ──────────────────────────────────────────

async def check_duplicate_company(state: ProspectorState) -> dict:
    """
    Check whether the current company already exists in the Google Sheet
    (by name or by WhatsApp number). Sets next_action = 'duplicate' if found.
    """
    company   = state.get("current_company") or {}
    sheet_id  = os.environ.get("GOOGLE_SHEETS_ID", "")
    name      = company.get("name", "")
    phone     = company.get("phone", "")

    if not sheet_id:
        logger.warning("prospector.check_duplicate_company: GOOGLE_SHEETS_ID not set — skipping check")
        return {"next_action": "continue"}

    is_dup = await sheets_client.check_duplicate(sheet_id, empresa=name, phone=phone)
    if is_dup:
        logger.info("prospector.check_duplicate_company: DUPLICATE — %s", name)
        return {
            "leads_skipped": state.get("leads_skipped", 0) + 1,
            "next_action":   "duplicate",
        }

    return {"next_action": "continue"}


# ── Node 5: enrich_social_media ───────────────────────────────────────────────

async def enrich_social_media(state: ProspectorState) -> dict:
    """
    Try to find the company's WhatsApp number via Instagram bio scraping.
    Supplements the phone number from Google Places.
    """
    company = state.get("current_company") or {}
    name    = company.get("name", "")

    logger.info("prospector.enrich_social_media: trying Instagram for '%s'", name)
    ig_data = await try_instagram_bio(name)

    instagram_url = ig_data.get("instagram_url") or state.get("instagram_url")
    phones        = ig_data.get("phones", [])

    # Combine scraped bio with any existing content
    bio_snippet = ig_data.get("bio", "")
    existing    = state.get("scraped_content") or ""
    combined    = f"{existing}\nInstagram bio: {bio_snippet}".strip() if bio_snippet else existing

    result: dict = {
        "instagram_url":   instagram_url,
        "scraped_content": combined,
    }

    if phones:
        result["whatsapp_found"] = phones[0]
        logger.info(
            "prospector.enrich_social_media: found WA via Instagram for '%s': %s",
            name, phones[0],
        )

    return result


# ── Node 6: scrape_company_website ────────────────────────────────────────────

async def scrape_company_website(state: ProspectorState) -> dict:
    """
    Scrape the company website (from Google Places) for WhatsApp links,
    social media profiles, and extractable contact info.
    """
    website = state.get("website_url") or (state.get("current_company") or {}).get("website", "")
    if not website:
        return {}

    logger.info("prospector.scrape_company_website: scraping '%s'", website)
    data = await scrape_website_for_whatsapp(website)

    result: dict = {}

    phones = data.get("phones", [])
    if phones and not state.get("whatsapp_found"):
        result["whatsapp_found"] = phones[0]

    if data.get("instagram_url") and not state.get("instagram_url"):
        result["instagram_url"] = data["instagram_url"]

    if data.get("facebook_url") and not state.get("facebook_url"):
        result["facebook_url"] = data["facebook_url"]

    snippet  = data.get("text_snippet", "")
    existing = state.get("scraped_content") or ""
    if snippet:
        result["scraped_content"] = f"{existing}\nWebsite: {snippet}".strip()

    return result


# ── Node 7: normalize_contact ─────────────────────────────────────────────────

async def normalize_contact(state: ProspectorState) -> dict:
    """
    Determine the best WhatsApp number for this company.

    Priority order:
      1. Explicitly found WhatsApp link (wa.me/)
      2. Instagram/website extracted phone
      3. Google Places phone if it starts with 9 (Angola mobile → valid WhatsApp)

    Sets next_action = 'no_contact' if no valid number can be found.
    """
    company    = state.get("current_company") or {}
    wa_current = state.get("whatsapp_found")

    # Already have a normalised WhatsApp number
    if wa_current and wa_current.startswith("+244"):
        return {"whatsapp_found": wa_current, "next_action": "continue"}

    # Try to normalise whatever we have
    candidates = [
        wa_current,
        company.get("phone", ""),
    ]
    for raw in candidates:
        if not raw:
            continue
        normalised = normalize_angola_phone(raw)
        if normalised:
            logger.info(
                "prospector.normalize_contact: normalised '%s' → %s for %s",
                raw, normalised, company.get("name", ""),
            )
            return {"whatsapp_found": normalised, "next_action": "continue"}

    # Fallback: Google Places phone as probable WhatsApp (Angolan mobile)
    places_phone = company.get("phone", "").replace(" ", "").replace("-", "")
    if places_phone and places_phone.startswith("9") and len(places_phone) == 9:
        wa = f"+244{places_phone}"
        logger.info(
            "prospector.normalize_contact: using Places phone fallback for %s: %s",
            company.get("name", ""), wa,
        )
        return {"whatsapp_found": wa, "next_action": "continue"}

    logger.info(
        "prospector.normalize_contact: no contact found for '%s' — skipping",
        company.get("name", ""),
    )
    return {
        "whatsapp_found": None,
        "leads_skipped":  state.get("leads_skipped", 0) + 1,
        "next_action":    "no_contact",
    }


# ── Node 8: generate_approach_notes ──────────────────────────────────────────

async def generate_approach_notes(state: ProspectorState) -> dict:
    """
    Use Claude Haiku to analyse the company's digital presence and generate:
    - approach_notes: specific hook for HUNTER outreach messages
    - opportunity: detailed automation opportunity for internal use
    - recommended_service: most relevant BMST service
    - pain_point: one-sentence problem description
    """
    company = state.get("current_company") or {}
    name    = company.get("name", "")

    context_parts = [
        f"Company: {name}",
        f"Sector: {state.get('sector', '')}",
        f"City: {company.get('address', state.get('city', 'Luanda'))}",
        f"Google rating: {company.get('rating', 'N/A')}",
        f"Website: {company.get('website', 'None')}",
    ]
    if state.get("instagram_url"):
        context_parts.append(f"Instagram: {state['instagram_url']}")
    if state.get("facebook_url"):
        context_parts.append(f"Facebook: {state['facebook_url']}")
    if state.get("scraped_content"):
        context_parts.append(f"Scraped content excerpt: {state['scraped_content'][:400]}")

    context = "\n".join(context_parts)

    result = await create_json_message(
        system=APPROACH_NOTES_PROMPT,
        user=f"Analyse this Angolan company and generate approach notes:\n\n{context}",
        schema=ApproachNotesSchema,
        model="haiku",
        agent_name=_AGENT,
        node_name="generate_approach_notes",
    )

    logger.info(
        "prospector.generate_approach_notes: service=%s for '%s'",
        result.recommended_service, name,
    )

    return {
        "approach_notes":      result.approach_notes,
        "opportunity":         result.opportunity,
        "recommended_service": result.recommended_service,
    }


# ── Node 9: qualify_lead ──────────────────────────────────────────────────────

async def qualify_lead(state: ProspectorState) -> dict:
    """
    Use Claude Haiku to classify the lead into segment A / B / C and estimate
    the annual contract value.

    Segment A leads are discarded (not written to the sheet).
    """
    company = state.get("current_company") or {}
    name    = company.get("name", "")

    context = (
        f"Company: {name}\n"
        f"Sector: {state.get('sector', '')}\n"
        f"Website: {'yes' if company.get('website') else 'no'}\n"
        f"Instagram: {'yes' if state.get('instagram_url') else 'no'}\n"
        f"Google rating: {company.get('rating', 'N/A')}\n"
        f"Pain point: {state.get('approach_notes', '')}\n"
        f"Address: {company.get('address', '')}"
    )

    result = await create_json_message(
        system=QUALIFY_LEAD_PROMPT,
        user=f"Qualify this Angolan lead:\n\n{context}",
        schema=QualifyLeadSchema,
        model="haiku",
        agent_name=_AGENT,
        node_name="qualify_lead",
    )

    logger.info(
        "prospector.qualify_lead: segment=%s value=%s AOA for '%s'",
        result.segment, result.estimated_value_aoa, name,
    )

    next_action = "segment_a" if result.segment == "A" else "qualified"
    if result.segment == "A":
        return {
            "segment":             "A",
            "qualified":           False,
            "leads_skipped":       state.get("leads_skipped", 0) + 1,
            "next_action":         next_action,
        }

    return {
        "segment":             result.segment,
        "estimated_value_aoa": result.estimated_value_aoa,
        "qualified":           True,
        "next_action":         next_action,
    }


# ── Node 10: write_lead_to_sheet ──────────────────────────────────────────────

async def write_lead_to_sheet(state: ProspectorState) -> dict:
    """
    Append the fully enriched and qualified lead to the Google Sheet
    (leads_angola tab) with estado_hunter = "pendente".
    """
    company   = state.get("current_company") or {}
    sheet_id  = os.environ.get("GOOGLE_SHEETS_ID", "")

    if not sheet_id:
        logger.error("prospector.write_lead_to_sheet: GOOGLE_SHEETS_ID not set")
        return {
            "errors":      state.get("errors", []) + ["GOOGLE_SHEETS_ID not configured"],
            "next_action": "advance",
        }

    notes = ""
    if state.get("segment") == "C":
        notes = "escalar_fundador: sim"

    lead_row = {
        "empresa":         company.get("name", ""),
        "sector":          state.get("sector", ""),
        "segmento":        state.get("segment", "B"),
        "responsavel":     "A confirmar",
        "cargo":           "",
        "whatsapp":        state.get("whatsapp_found", ""),
        "email":           "",
        "website":         company.get("website", ""),
        "instagram":       state.get("instagram_url", ""),
        "localizacao":     company.get("address", ""),
        "nr_funcionarios": 0,
        "servico_bmst":    state.get("recommended_service", ""),
        "pain_point":      state.get("approach_notes", ""),
        "valor_est_aoa":   state.get("estimated_value_aoa", 0),
        "notas_abordagem": state.get("approach_notes", ""),
        "notas":           notes,
        "oportunidade":    state.get("opportunity", ""),
        "fonte":           "google_places",
        "estado_hunter":   "pendente",
    }

    try:
        await sheets_client.append_lead(sheet_id, lead_row)
        written = state.get("leads_written", 0) + 1
        logger.info(
            "prospector.write_lead_to_sheet: wrote lead #%d — '%s' (seg %s)",
            written, company.get("name", ""), state.get("segment"),
        )
        return {"leads_written": written, "next_action": "advance"}
    except Exception as exc:
        logger.error("prospector.write_lead_to_sheet failed for '%s': %s", company.get("name"), exc)
        errors = state.get("errors", []) + [f"Sheet write failed: {company.get('name')}: {exc}"]
        return {"errors": errors, "next_action": "advance"}


# ── Node 11: advance_to_next_company ─────────────────────────────────────────

async def advance_to_next_company(state: ProspectorState) -> dict:
    """
    Increment the current_index pointer. If more companies remain and the
    leads_written cap has not been reached, loops back to prepare_current_company.
    Otherwise transitions to generate_session_report.
    """
    new_index = state.get("current_index", 0) + 1
    total     = len(state.get("raw_companies", []))
    written   = state.get("leads_written", 0)
    max_co    = state.get("max_companies", 30)

    if new_index < total and written < max_co:
        next_action = "continue"
    else:
        next_action = "done"

    logger.debug(
        "prospector.advance_to_next_company: index=%d/%d written=%d next=%s",
        new_index, total, written, next_action,
    )
    return {"current_index": new_index, "next_action": next_action}


# ── Node 12: generate_session_report ─────────────────────────────────────────

async def generate_session_report(state: ProspectorState) -> dict:
    """
    Send a session summary to the founder via Telegram and log final stats.
    """
    sector_label = _SECTOR_LABELS.get(state.get("sector", ""), state.get("sector", ""))
    run_date     = state.get("run_date", "")
    written      = state.get("leads_written", 0)
    skipped      = state.get("leads_skipped", 0)
    errors       = state.get("errors", [])
    total        = len(state.get("raw_companies", []))

    logger.info(
        "prospector.generate_session_report: date=%s sector=%s written=%d skipped=%d errors=%d",
        run_date, sector_label, written, skipped, len(errors),
    )

    # Build Telegram message
    lines = [
        f"🔍 <b>PROSPECTOR — {run_date} | {sector_label}</b>",
        "",
        f"📊 Google Places: {total} companies found",
        f"✅ Leads written to sheet: <b>{written}</b>",
        f"⏭️ Skipped (duplicates / no WhatsApp): {skipped}",
    ]

    if errors:
        lines.append(f"❌ Errors: {len(errors)}")

    lines += [
        "",
        "⏰ HUNTER processes at 09:00.",
    ]

    message = "\n".join(lines)

    try:
        await telegram_client.send_message(message)
    except Exception as exc:
        logger.error("prospector.generate_session_report: Telegram send failed: %s", exc)

    return {}
