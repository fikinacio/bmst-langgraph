# agents/prospector/state.py

from typing import Optional
from typing_extensions import TypedDict


class ProspectorState(TypedDict):
    # Input
    sector: str           # Sector to search (empty = auto-detect from day of week)
    city: str             # City (default: Luanda)
    max_companies: int    # Maximum leads to insert per run

    # Internal
    sector_do_dia: str    # Resolved sector for today
    companies_raw: list   # Raw results from Google Places API
    leads_qualificados: list  # Leads that passed classification (Seg B/C)

    # Output
    leads_escritos: int   # Leads successfully written to Google Sheet
    leads_ignorados: int  # Leads skipped (Seg A, no WhatsApp, duplicates)
    seg_c_pendentes: list # Seg C companies that need founder approval
    erro: Optional[str]   # Error message if pipeline failed
