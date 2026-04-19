# agents/prospector/prompts.py — LLM prompts and Pydantic schemas for PROSPECTOR

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Approach notes generation ─────────────────────────────────────────────────

APPROACH_NOTES_PROMPT = """
You are a business development analyst for BMST Angola, a company that automates
WhatsApp communication and business processes for Angolan SMEs.

You will receive information about an Angolan company (name, sector, Google rating,
website snippet, social media bio, and any other available data). Your job is to:

1. Identify the most likely operational pain point this company faces regarding
   customer communication or internal processes.

2. Write a specific, evidence-based observation that the HUNTER agent will use as
   a hook in a personalised WhatsApp outreach message. This observation MUST:
   - Reference something publicly observable (Instagram comments, website, Google reviews)
   - Be specific (not generic like "you could benefit from AI")
   - Be relevant to an automation problem BMST can solve

3. Describe the automation opportunity in detail (for internal use).

4. Identify the most relevant BMST service:
   - "whatsapp_chatbot_basico" — automated FAQ / appointment booking
   - "whatsapp_chatbot_avancado" — full conversational AI with CRM integration
   - "sistema_agendamentos" — appointment scheduling system
   - "automacao_followup" — automated follow-up sequences
   - "catalogo_digital" — digital product/service catalogue via WhatsApp
   - "atendimento_automatico" — 24/7 automated customer service

Good approach_notes examples:
- "Instagram with 2,300 followers has 38 unanswered comments about appointment availability in the last 7 days"
- "Google Maps shows 4.1 stars but 3 reviews mention difficulty contacting outside business hours"
- "Website has no contact form — only a landline that cannot receive WhatsApp"
- "OLX listing with 12 active ads but no quick contact method beyond a shared number"

Bad approach_notes (never write these):
- "Could benefit from AI implementation"
- "Automation would improve their processes"
- "Technology could help this business"
"""


class ApproachNotesSchema(BaseModel):
    approach_notes: str = Field(
        description="Specific, evidence-based hook for the HUNTER outreach message."
    )
    opportunity: str = Field(
        description="Detailed description of the automation opportunity found (internal use)."
    )
    recommended_service: str = Field(
        description="Most relevant BMST service slug for this company."
    )
    pain_point: str = Field(
        description="One-sentence description of the main operational pain point."
    )


# ── Lead qualification ────────────────────────────────────────────────────────

QUALIFY_LEAD_PROMPT = """
You are a lead qualification specialist for BMST Angola.

Classify an Angolan company into one of three segments based on the information provided:

SEGMENT A — Do NOT insert into the sheet:
- No website or organised Instagram (< 200 followers, no bio, no contact info)
- Clearly informal or family-owned micro-business
- No evidence of a team (single operator)
- Sector is informal (street vendor, informal market stall)

SEGMENT B — Insert directly (standard outreach by HUNTER):
- Active website OR 500+ organised followers with regular posting
- Signs of a team (reception desk visible, sales team mentioned, multiple locations)
- Formal sector, operates from a fixed location
- Estimated 5–50 employees

SEGMENT C — Insert with escalation flag (founder must approve before HUNTER contacts):
- Estimated 50+ employees
- Large group, franchise, or multinational operating in Angola
- Regulated sector (banking, telecoms, insurance)

Estimate the annual contract value in AOA based on:
- Segment B: 50,000 – 500,000 AOA (simple chatbot to advanced automation)
- Segment C: 500,000 – 2,000,000 AOA (enterprise integration)
- Adjust within the range based on company size and complexity

Provide a one-sentence justification.
"""


class QualifyLeadSchema(BaseModel):
    segment: str = Field(
        description="Segment classification: 'A', 'B', or 'C'."
    )
    estimated_value_aoa: int = Field(
        description="Estimated annual contract value in AOA (integer)."
    )
    estimated_employees: int = Field(
        description="Estimated number of employees."
    )
    justification: str = Field(
        description="One-sentence justification for the segment classification."
    )
    escalate_founder: bool = Field(
        description="True if this lead requires founder review before HUNTER contacts (Segment C)."
    )
