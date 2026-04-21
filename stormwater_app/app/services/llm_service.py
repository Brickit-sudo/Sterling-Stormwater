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
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
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
