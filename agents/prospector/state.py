# agents/prospector/state.py

from __future__ import annotations

from typing import TypedDict


class ProspectorState(TypedDict):
    # ── Session configuration ─────────────────────────────────────────────────
    sector:         str          # business sector for this session (from day calendar)
    city:           str          # target city — "Luanda" by default
    run_date:       str          # ISO date of the prospecting session
    max_companies:  int          # session cap (HUNTER processes at most 20 leads/day)

    # ── Discovery pipeline ────────────────────────────────────────────────────
    raw_companies:      list[dict]   # raw results from Google Places
    current_company:    dict | None  # company being enriched right now
    current_index:      int          # pointer into raw_companies

    # ── Enrichment ────────────────────────────────────────────────────────────
    whatsapp_found:      str | None
    instagram_url:       str | None
    facebook_url:        str | None
    website_url:         str | None
    scraped_content:     str | None  # raw text extracted from website / social profiles
    approach_notes:      str | None  # LLM-generated hook for HUNTER messages
    opportunity:         str | None  # detailed automation opportunity found
    recommended_service: str | None  # most relevant BMST service for this company

    # ── Qualification ─────────────────────────────────────────────────────────
    segment:             str | None  # "A" (discard) | "B" (standard) | "C" (escalate)
    estimated_value_aoa: int | None
    qualified:           bool | None

    # ── Batch control ─────────────────────────────────────────────────────────
    leads_written:  int
    leads_skipped:  int          # duplicates or no WhatsApp found
    errors:         list[str]

    # ── Routing ───────────────────────────────────────────────────────────────
    next_action: str | None
    error:       str | None
