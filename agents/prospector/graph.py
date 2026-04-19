# agents/prospector/graph.py — PROSPECTOR StateGraph

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, START, END

from agents.prospector.state import ProspectorState
from agents.prospector.nodes import (
    initialize_session,
    discover_companies,
    prepare_current_company,
    check_duplicate_company,
    enrich_social_media,
    scrape_company_website,
    normalize_contact,
    generate_approach_notes,
    qualify_lead,
    write_lead_to_sheet,
    advance_to_next_company,
    generate_session_report,
)


# ── Routing functions ─────────────────────────────────────────────────────────

def _route_after_discovery(state: ProspectorState) -> str:
    return "generate_session_report" if state.get("next_action") == "no_results" else "prepare_current_company"


def _route_after_prepare(state: ProspectorState) -> str:
    return "generate_session_report" if state.get("next_action") == "batch_complete" else "check_duplicate_company"


def _route_after_duplicate_check(state: ProspectorState) -> str:
    return "advance_to_next_company" if state.get("next_action") == "duplicate" else "enrich_social_media"


def _route_after_normalize(state: ProspectorState) -> str:
    return "advance_to_next_company" if state.get("next_action") == "no_contact" else "generate_approach_notes"


def _route_after_qualify(state: ProspectorState) -> str:
    return "advance_to_next_company" if state.get("next_action") == "segment_a" else "write_lead_to_sheet"


def _route_after_advance(state: ProspectorState) -> str:
    return "prepare_current_company" if state.get("next_action") == "continue" else "generate_session_report"


# ── Graph factory ─────────────────────────────────────────────────────────────

def get_prospector_graph(checkpointer: Any = None) -> Any:
    """
    Build and compile the PROSPECTOR StateGraph.

    The PROSPECTOR runs fully autonomously — no interrupt() calls.
    The checkpointer is accepted for API consistency but is rarely needed
    since sessions complete in a single run.

    Graph flow:
      START
        → initialize_session
        → discover_companies
        → [route] prepare_current_company | generate_session_report
        → [route] check_duplicate_company | advance_to_next_company
        → enrich_social_media
        → scrape_company_website
        → normalize_contact
        → [route] generate_approach_notes | advance_to_next_company
        → qualify_lead
        → [route] write_lead_to_sheet | advance_to_next_company
        → advance_to_next_company
        → [route] prepare_current_company (loop) | generate_session_report
        → END
    """
    g = StateGraph(ProspectorState)

    # ── Nodes ────────────────────────────────────────────────────────────────
    g.add_node("initialize_session",       initialize_session)
    g.add_node("discover_companies",       discover_companies)
    g.add_node("prepare_current_company",  prepare_current_company)
    g.add_node("check_duplicate_company",  check_duplicate_company)
    g.add_node("enrich_social_media",      enrich_social_media)
    g.add_node("scrape_company_website",   scrape_company_website)
    g.add_node("normalize_contact",        normalize_contact)
    g.add_node("generate_approach_notes",  generate_approach_notes)
    g.add_node("qualify_lead",             qualify_lead)
    g.add_node("write_lead_to_sheet",      write_lead_to_sheet)
    g.add_node("advance_to_next_company",  advance_to_next_company)
    g.add_node("generate_session_report",  generate_session_report)

    # ── Edges ────────────────────────────────────────────────────────────────
    g.add_edge(START, "initialize_session")
    g.add_edge("initialize_session", "discover_companies")

    g.add_conditional_edges("discover_companies", _route_after_discovery, {
        "prepare_current_company": "prepare_current_company",
        "generate_session_report": "generate_session_report",
    })

    g.add_conditional_edges("prepare_current_company", _route_after_prepare, {
        "check_duplicate_company": "check_duplicate_company",
        "generate_session_report": "generate_session_report",
    })

    g.add_conditional_edges("check_duplicate_company", _route_after_duplicate_check, {
        "enrich_social_media":    "enrich_social_media",
        "advance_to_next_company": "advance_to_next_company",
    })

    g.add_edge("enrich_social_media", "scrape_company_website")
    g.add_edge("scrape_company_website", "normalize_contact")

    g.add_conditional_edges("normalize_contact", _route_after_normalize, {
        "generate_approach_notes":  "generate_approach_notes",
        "advance_to_next_company":  "advance_to_next_company",
    })

    g.add_edge("generate_approach_notes", "qualify_lead")

    g.add_conditional_edges("qualify_lead", _route_after_qualify, {
        "write_lead_to_sheet":      "write_lead_to_sheet",
        "advance_to_next_company":  "advance_to_next_company",
    })

    g.add_edge("write_lead_to_sheet", "advance_to_next_company")

    g.add_conditional_edges("advance_to_next_company", _route_after_advance, {
        "prepare_current_company":  "prepare_current_company",
        "generate_session_report":  "generate_session_report",
    })

    g.add_edge("generate_session_report", END)

    return g.compile(checkpointer=checkpointer)
