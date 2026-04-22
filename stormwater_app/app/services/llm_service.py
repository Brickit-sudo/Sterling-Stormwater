"""
app/services/llm_service.py
Claude API integration for AI-assisted write-up generation.

Usage:
  1. Copy .env.example to .env and set ANTHROPIC_API_KEY.
  2. Call generate_writeup() from the write-ups page.
  3. Check api_key_configured() before showing the AI Draft button.

Model: claude-haiku-4-5 (fast, low-cost, well-suited for structured report text)
Prompt caching: system prompt is marked ephemeral — cached across calls in a session.
"""

import os
from pathlib import Path

# Load .env on first import (no-op if already loaded or package not present)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env", override=True)
except ImportError:
    pass

_client = None

_SYSTEM_PROMPT = """\
You are a licensed stormwater compliance specialist writing formal inspection \
and maintenance reports for a professional environmental services firm. \
Your reports are delivered to municipal clients and property owners under \
MS4 permit requirements and local stormwater ordinances.

Writing style rules:
- Third-person, formal technical prose
- Passive voice for observations ("standing water was observed", "sediment accumulation was noted")
- Active voice for recommendations ("the outlet structure should be cleared", "vegetation should be removed")
- Concise — findings: 2–4 sentences; recommendations: 1–3 bullet-style sentences
- Do not speculate beyond observed conditions
- Do not use the word "significant" without quantifying it
- Reference the O&M Plan or permit schedule where relevant
- Replace all bracketed placeholders in your output — never leave [text] in the result

Output only the requested field text. No headers, labels, or extra commentary."""


def api_key_configured() -> bool:
    """Return True if ANTHROPIC_API_KEY is set in the environment."""
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())


def get_client():
    """Return the shared Anthropic client, creating it on first call."""
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.Anthropic()   # reads ANTHROPIC_API_KEY from env
    return _client


def generate_writeup(
    system_type: str,
    system_id: str,
    condition: str,
    notes: str,
    report_type: str,
    field: str,
    site_name: str = "",
    inspection_date: str = "",
) -> str:
    """
    Generate a single write-up field using Claude.

    Args:
        system_type:     e.g. "Underdrain Soil Filter"
        system_id:       e.g. "USF-1"
        condition:       "Good" | "Fair" | "Poor" | "N/A"
        notes:           Raw field technician notes
        report_type:     "Inspection" | "Maintenance" | "Inspection and Maintenance"
        field:           "findings" | "recommendations" | "maintenance_performed" | "post_service_condition"
        site_name:       Optional — adds site context to the prompt
        inspection_date: Optional — used for temporal references

    Returns:
        Generated text string, or raises on API error.
    """
    import anthropic

    field_definitions = {
        "findings": (
            "What was observed during the inspection. Objective, past tense. "
            "Describe the system's physical condition: inlet, outlet, media, vegetation, "
            "sediment accumulation, structural integrity, and any deficiencies noted."
        ),
        "recommendations": (
            "What corrective actions are needed, if any. Prioritized, actionable sentences. "
            "If no action is required, state that the system is operating as designed and "
            "routine maintenance should continue per the O&M Plan."
        ),
        "maintenance_performed": (
            "Work completed during this service visit. Past tense, specific. "
            "Include: debris removal, sediment removal, vegetation management, "
            "inlet/outlet clearing, structural repairs, and any other work completed."
        ),
        "post_service_condition": (
            "The system's condition after maintenance was completed. Objective. "
            "Note any outstanding items or follow-up work required."
        ),
    }

    field_def = field_definitions.get(field, f"The '{field}' section of the report.")

    user_content = f"""Site: {site_name or 'Not specified'}
Inspection / Service Date: {inspection_date or 'Not specified'}
BMP Type: {system_type}
System ID: {system_id}
Observed Condition Rating: {condition}
Report Type: {report_type}

Field Technician Notes:
{notes.strip() if notes.strip() else '(No notes provided — base the draft on the condition rating and system type.)'}

Generate the "{field}" field.
Definition: {field_def}

Write only the {field} text. No labels or headers."""

    client = get_client()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},   # cached across calls in same session
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )

    return response.content[0].text.strip()


def generate_summary(
    systems: list[dict],
    report_type: str,
    site_name: str = "",
    inspection_date: str = "",
) -> str:
    """
    Generate the overall site summary paragraph from a list of system conditions.

    Args:
        systems: List of dicts with keys: system_type, system_id, condition, notes
    """
    if not systems:
        return ""

    system_lines = "\n".join(
        f"  - {s.get('display_name') or s.get('system_type','')} ({s.get('system_id','')}): "
        f"{s.get('condition','N/A')} — {s.get('notes','') or 'no notes'}"
        for s in systems
    )

    user_content = f"""Site: {site_name or 'Not specified'}
Inspection / Service Date: {inspection_date or 'Not specified'}
Report Type: {report_type}

Systems inspected:
{system_lines}

Generate a concise overall summary paragraph (3–5 sentences) for the cover page. \
This paragraph introduces the scope of work and summarizes the overall site condition. \
Do not repeat individual system details — those appear in dedicated sections below."""

    client = get_client()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    )

    return response.content[0].text.strip()


def _call_claude_json(prompt: str) -> dict:
    """Call Claude and parse JSON response. Returns dict or {} on failure."""
    import json, re
    try:
        client = get_client()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        # Extract JSON even if wrapped in markdown code fences
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group()) if match else {}
    except Exception:
        return {}


def classify_document(text: str) -> str:
    """Classify a document as: inspection_report | maintenance_report | invoice | proposal | other."""
    snippet = text[:800]
    prompt = f"""Classify this stormwater document. Return ONLY one of these exact strings:
inspection_report
maintenance_report
invoice
proposal
other

Document text:
{snippet}

Classification:"""
    try:
        client = get_client()
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
        )
        result = msg.content[0].text.strip().lower()
        for t in ("inspection_report", "maintenance_report", "invoice", "proposal"):
            if t in result:
                return t
        return "other"
    except Exception:
        return "other"


def extract_inspection_fields(text: str) -> dict:
    """Extract structured fields from a stormwater inspection report PDF text."""
    prompt = f"""Extract fields from this stormwater inspection report. Return valid JSON only, no markdown.

Fields to extract:
- site_name: the site name (e.g. "Southern Maine Health Care")
- site_address: full address
- client: client/owner name if mentioned
- inspection_date: date inspection was performed (YYYY-MM-DD if possible, else as written)
- inspector: who performed inspection ("STERLING Stormwater Maintenance Services, LLC" or individual name)
- report_type: "Inspection" or "Inspection and Maintenance"
- overall_condition: overall site condition if stated (Good/Fair/Poor or narrative)
- findings_summary: 2-3 sentence summary of key findings
- recommendations_summary: 2-3 sentence summary of key recommendations
- bmp_types: comma-separated list of BMP/system types mentioned (e.g. "catch basins, bioretention, StormFilter")
- num_pages: number of pages in report if stated

Document text:
{text[:3000]}

JSON:"""
    return _call_claude_json(prompt)


def extract_maintenance_fields(text: str) -> dict:
    """Extract structured fields from a stormwater maintenance report PDF text."""
    prompt = f"""Extract fields from this stormwater maintenance report. Return valid JSON only, no markdown.

Fields to extract:
- site_name: the site name
- site_address: full address/location
- service_date: date maintenance was performed (YYYY-MM-DD if possible)
- inspector: company/person who performed service
- systems_maintained: comma-separated list of systems that were serviced
- systems_not_completed: comma-separated list of systems where work could NOT be completed and why
- maintenance_summary: 2-3 sentence summary of work performed
- next_service_date: next recommended service date if mentioned
- num_pages: number of pages if stated

Document text:
{text[:3000]}

JSON:"""
    return _call_claude_json(prompt)


def extract_invoice_fields(text: str) -> dict:
    """Extract structured fields from a Sterling Stormwater invoice PDF."""
    prompt = f"""Extract fields from this stormwater services invoice. Return valid JSON only, no markdown.

Fields to extract:
- site_name: site name
- site_address: site address
- client_name: who the invoice is billed to
- invoice_number: invoice number/ID
- invoice_date: invoice date (YYYY-MM-DD if possible)
- status: payment status (e.g. "Not Paid", "Paid")
- line_items: list of objects with "description" and "amount" (dollar amount as string)
- subtotal: subtotal amount
- total: total amount
- balance_due: balance due

Document text:
{text[:2000]}

JSON:"""
    return _call_claude_json(prompt)


def extract_proposal_fields(text: str) -> dict:
    """Extract structured fields from a Sterling Stormwater proposal PDF."""
    prompt = f"""Extract fields from this stormwater compliance proposal. Return valid JSON only, no markdown.

Fields to extract:
- site_name: site name
- site_address: location/address
- quote_number: quote or proposal number
- quote_date: date of proposal (YYYY-MM-DD if possible)
- contract_term: contract term (e.g. "5 Years", "Annual")
- annual_total: total annual cost as string
- services: comma-separated list of services proposed
- notes: key notes or special conditions

Document text:
{text[:2000]}

JSON:"""
    return _call_claude_json(prompt)


def extract_document_fields(text: str, doc_type: str) -> dict:
    """Dispatcher — extract fields based on document type."""
    if doc_type == "inspection_report":
        return extract_inspection_fields(text)
    elif doc_type == "maintenance_report":
        return extract_maintenance_fields(text)
    elif doc_type == "invoice":
        return extract_invoice_fields(text)
    elif doc_type == "proposal":
        return extract_proposal_fields(text)
    return {}
