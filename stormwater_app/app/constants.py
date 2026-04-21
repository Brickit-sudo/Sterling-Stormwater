"""
app/constants.py
All domain-specific lookup lists. Edit here to customize for your company's
standard system types and component vocabulary.
"""

# ── Stormwater system types ───────────────────────────────────────────────────
# These appear in the system selector. Add or remove to match your portfolio.

SYSTEM_TYPES = [
    "Bioretention Cell",
    "Catch Basin / Inlet",
    "Constructed Wetland",
    "Dry Swale",
    "Extended Detention Basin",
    "Grass Channel",
    "Green Roof",
    "Infiltration Basin",
    "Infiltration Trench",
    "Level Spreader",
    "Media Filter / Sand Filter",
    "Oil / Water Separator",
    "Permeable Pavement",
    "Proprietary Treatment Device",
    "Retention Pond",
    "Riprap Outfall Protection",
    "Stormwater Wetland",
    "Underdrain Soil Filter",
    "Underground Detention",
    "Vegetated Filter Strip",
    "Wet Pond",
    "Other / Custom",
]

# ── Default system ID prefixes ────────────────────────────────────────────────
# Used to auto-suggest IDs when adding systems.

SYSTEM_ID_PREFIX = {
    "Bioretention Cell": "BR",
    "Catch Basin / Inlet": "CB",
    "Constructed Wetland": "CW",
    "Dry Swale": "DS",
    "Extended Detention Basin": "EDB",
    "Grass Channel": "GC",
    "Green Roof": "GR",
    "Infiltration Basin": "IB",
    "Infiltration Trench": "IT",
    "Level Spreader": "LS",
    "Media Filter / Sand Filter": "MF",
    "Oil / Water Separator": "OWS",
    "Permeable Pavement": "PP",
    "Proprietary Treatment Device": "PTD",
    "Retention Pond": "RP",
    "Riprap Outfall Protection": "RO",
    "Stormwater Wetland": "SW",
    "Underdrain Soil Filter": "USF",
    "Underground Detention": "UD",
    "Vegetated Filter Strip": "VFS",
    "Wet Pond": "WP",
    "Other / Custom": "SYS",
}

# ── Photo component options per system type ───────────────────────────────────
# These drive the "Component" dropdown in the photo caption builder.

COMPONENT_OPTIONS = {
    "Bioretention Cell": [
        "Overall View",
        "Inlet / Curb Cut",
        "Overflow Structure",
        "Underdrain Cleanout",
        "Surface Media",
        "Vegetation",
        "Outlet",
        "Side Slopes",
        "Other",
    ],
    "Underdrain Soil Filter": [
        "Overall View",
        "Inlet Structure",
        "Outlet Structure",
        "Underdrain Cleanout",
        "Surface Media",
        "Filter Media",
        "Overflow",
        "Perimeter Berm",
        "Other",
    ],
    "Catch Basin / Inlet": [
        "Overall View",
        "Grate / Frame",
        "Sump",
        "Outlet Pipe",
        "Sediment Accumulation",
        "Structural Condition",
        "Other",
    ],
    "Wet Pond": [
        "Overall View",
        "Primary Outlet / Riser",
        "Emergency Spillway",
        "Forebay",
        "Main Pool",
        "Inlet",
        "Embankment",
        "Vegetation",
        "Other",
    ],
    "Retention Pond": [
        "Overall View",
        "Primary Outlet",
        "Emergency Spillway",
        "Inlet",
        "Embankment",
        "Vegetation",
        "Other",
    ],
    "Permeable Pavement": [
        "Overall View",
        "Surface Condition",
        "Inlet / Edge",
        "Cleanout",
        "Underdrain",
        "Other",
    ],
    "DEFAULT": [
        "Overall View",
        "Inlet",
        "Outlet",
        "Outlet Structure",
        "Overflow Structure",
        "Structural Condition",
        "Vegetation",
        "Sediment Accumulation",
        "Access",
        "Other",
    ],
}

def get_components_for_system(system_type: str) -> list[str]:
    return COMPONENT_OPTIONS.get(system_type, COMPONENT_OPTIONS["DEFAULT"])


# ── Condition ratings ─────────────────────────────────────────────────────────
CONDITION_RATINGS = ["Good", "Fair", "Poor", "N/A"]

# ── Report types ──────────────────────────────────────────────────────────────
REPORT_TYPES = [
    "Inspection",
    "Maintenance",
    "Inspection and Maintenance",
]

# ── Write-up templates ────────────────────────────────────────────────────────
# Default placeholder text seeded into write-up fields.
# These are intentionally NOT finished sentences — they guide the writer.
# Edit these to match your company's standard language patterns.

def get_default_findings(system_type: str, system_id: str, condition: str) -> str:
    return (
        f"The {system_type} ({system_id}) was inspected and found to be in {condition.lower()} "
        f"condition at the time of inspection. "
        f"\n\n[Describe observed conditions: inlet, outlet, media, vegetation, structural elements, "
        f"sediment accumulation, erosion, clogging, or other notable features.]"
    )

def get_default_recommendations(system_type: str, system_id: str) -> str:
    return (
        f"[List recommended corrective actions, if any, for {system_id}. "
        f"If no action is required, note that the system is operating as designed and "
        f"routine maintenance should continue per the approved O&M Plan.]"
    )

def get_default_maintenance(system_type: str, system_id: str) -> str:
    return (
        f"[Describe maintenance activities performed at {system_id}. "
        f"Include: debris removal, sediment removal, vegetation management, "
        f"inlet/outlet clearing, structural repairs, and any other work completed.]"
    )

def get_default_post_service(system_type: str, system_id: str) -> str:
    return (
        f"Following maintenance, the {system_type} ({system_id}) was found to be in "
        f"[Good / Fair / Poor] condition. "
        f"[Note any outstanding items or follow-up work required.]"
    )

# ── Navigation steps ──────────────────────────────────────────────────────────
NAV_STEPS = [
    ("setup",    "1. Report Setup"),
    ("systems",  "2. Systems & Photos"),
    ("writeups", "3. Write-Ups"),
    ("export",   "4. Preview & Export"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# PHOTOSHEET MODE CONSTANTS
# Derived from real Sterling Stormwater report examples.
# ═══════════════════════════════════════════════════════════════════════════════

# ── System types — ordered by stormwater flow convention ─────────────────────
# This order drives "Auto-Sort": site context → typical structures →
# treatment systems → drainage → outfall.
PS_SYSTEM_TYPES = [
    # Site context (always first)
    "Site Signage",
    "Building Frontage",
    "Site Frontage",
    "General Location",
    # Typical pretreatment / collection structures
    "Typical Catch Basin",
    "Typical Catch Basin With Insert",
    "Typical Field Inlet",
    "Typical Drain Manhole",
    "Typical Roof Drip Strip",
    "Roof Drip Edge Filter",
    "Filter Drip Strip",
    # Named treatment systems (user will add numbered variants, e.g. "USF 1")
    "Underdrained Soil Filter (USF)",
    "Subsurface Underdrained Sand Filter (SUSF)",
    "Stormwater Facility",
    "Subsurface Storage System (SS)",
    "Underground Detention System (UGDS)",
    "High Capacity First Defense",
    "Bioretention Basin",
    "Rain Garden",
    "Infiltration Cell",
    "Infiltration Trench",
    "Gravel Infiltration Trench",
    "Isolator Row",
    "Permeable Pavement",
    "Porous Pavement",
    # Conveyance / drainage
    "Grassy Drainage Channel",
    "Drainage Channel",
    "Drainage Ditch",
    # Ponds / large systems
    "Stormwater Pond",
    "Wet Pond",
    "Retention Pond",
    # Outfall (always last)
    "Outfall Area",
    "Typical Outfall Area",
    "Miscellaneous",
]

# Priority index for auto-sort (lower index = appears earlier)
PS_SYSTEM_ORDER = {name: i for i, name in enumerate(PS_SYSTEM_TYPES)}

# ── View types ────────────────────────────────────────────────────────────────
# Matches real Sterling caption vocabulary exactly.
PS_VIEW_TYPES = [
    "Overall View",
    "Surface View",
    "Inside View",
    "Location View",
    "General Location",
    "View Of ___",            # requires component
    "View Inside ___",        # requires component
    "View N Of ___",          # requires view number + component
    "Location Of ___",        # requires component
    "Example N",              # requires example number
    "Typical Section - Example N",   # requires example number
    "After Maintenance",
    "Custom",                 # user types full view text
]

# Within-system view priority for auto-sort (lower = shown earlier in sequence)
PS_VIEW_PRIORITY = {
    "General Location":              0,
    "Overall View":                  1,
    "Location View":                 2,
    "Surface View":                  3,
    "View Of Surface":               4,
    "View Of Inlet Area":            5,
    "View Of Inlet Pipe":            5,
    "View Of Primary Inlet":         5,
    "View Of Secondary Inlet":       5,
    "View Inside Inlet Pipe":        6,
    "View Of Pretreatment Strip":    7,
    "View Of Embankment":            8,
    "View Of Inspection Port":       9,
    "View Inside Inspection Port":   10,
    "View Into Isolator Row":        10,
    "View Inside Infiltration Row":  10,
    "View Of Overflow Structure":    11,
    "View Inside Overflow Structure": 12,
    "View Of Emergency Spillway":    13,
    "View Of Emergency Overflow":    13,
    "View Of Underdrain Outlet Pipe": 14,
    "View Of Outlet":                15,
    "View Of Outfall":               16,
    "After Maintenance":             17,
}

# ── Component options (for "View Of ___" / "View Inside ___" etc.) ───────────
PS_COMPONENTS = [
    # Inlet components
    "Inlet Area",
    "Inlet Pipe",
    "Inlet Pipes",
    "Primary Inlet",
    "Primary Inlets",
    "Secondary Inlet",
    "Inlet Structure",
    "Riprap Inlet",
    "Pretreatment Strip",
    # Overflow / spillway
    "Overflow Structure",
    "Emergency Spillway",
    "Emergency Overflow",
    "Emergency Overflow Riprap",
    # Outlet / underdrain
    "Outlet Pipe",
    "Underdrain Pipe",
    "Underdrain Outlet Pipe",
    "Underdrain",
    "Outfall",
    # Control structures
    "Outlet Control Structure (OCS)",
    "Inlet Control Structure (ICS)",
    "OCS",
    "ICS",
    # OCS sub-components
    "OCS - Upstream Side",
    "OCS - Downstream Side",
    "OCS - Flow Control Orifice",
    "ICS - Access Manholes",
    # Surface / embankment
    "Surface",
    "Embankment",
    "Gravel Infiltration Bench",
    # Inspection
    "Inspection Port",
    "Typical Inspection Port",
    "Access Manhole",
    # Internal views
    "Isolator Row",
    "Infiltration Row",
    "Flow Control Orifice",
    # Upstream / downstream sides
    "Upstream Side",
    "Downstream Side",
]

# ── Severity modifiers — first row of field-notes quick-buttons ───────────────
# Clicking one appends the word to field notes as a leading modifier.
PS_SEVERITY_TAGS = [
    "Minimal",
    "Light",
    "Moderate",
    "Heavy",
    "Significant",
    "Excessive",
]

# ── Issue tags — second row of field-notes quick-buttons ─────────────────────
# Concise phrases; rendered 4-per-row.  Clicking appends to field notes.
PS_ISSUE_TAGS = [
    '>4" Sediment',
    'Sheen on Water',
    'Partially Obstructed',
    'Fully Obstructed',
    'Erosion Present',
    'Excess Vegetation',
    'Standing Water',
    'Debris Present',
    'Structural Damage',
    'Detached Hood',
    'Missing Hardware',
    'Animal Burrow',
]

# ── System name prefixes — auto-suggested when a system type is chosen ────────
# Key = PS_SYSTEM_TYPES entry.  Value = prefix pre-filled in the "System Name"
# text input so the user only has to append the number (e.g. "USF-" → "USF-1").
PS_SYS_PREFIX: dict[str, str] = {
    "Underdrained Soil Filter (USF)":              "USF-",
    "Subsurface Underdrained Sand Filter (SUSF)":  "SUSF-",
    "Stormwater Facility":                          "SF-",
    "Subsurface Storage System (SS)":               "SS-",
    "Underground Detention System (UGDS)":          "UGDS-",
    "High Capacity First Defense":                  "HCFD-",
    "Bioretention Basin":                           "BR-",
    "Rain Garden":                                  "RG-",
    "Infiltration Cell":                            "IC-",
    "Infiltration Trench":                          "IT-",
    "Gravel Infiltration Trench":                   "GIT-",
    "Isolator Row":                                 "IR-",
    "Typical Catch Basin":                          "CB-",
    "Typical Catch Basin With Insert":              "CB-",
    "Typical Field Inlet":                          "FI-",
    "Typical Drain Manhole":                        "DM-",
    "Stormwater Pond":                              "SP-",
    "Wet Pond":                                     "WP-",
    "Retention Pond":                               "RP-",
    "Outfall Area":                                 "OA-",
    "Typical Outfall Area":                         "OA-",
    "Grassy Drainage Channel":                      "GDC-",
    "Drainage Channel":                             "DC-",
    "Drainage Ditch":                               "DD-",
}

# ── Photosheet layout configs ─────────────────────────────────────────────────
# Notation: user-facing "3x2" means 3 rows × 2 cols (matches real Sterling 2-col format).
PS_LAYOUTS = {
    "3x2":  {"cols": 2, "rows": 3, "per_page": 6,
              "label": "3×2  —  6 per page  (Sterling Standard)"},
    "3x3":  {"cols": 3, "rows": 3, "per_page": 9,
              "label": "3×3  —  9 per page"},
    "2x2":  {"cols": 2, "rows": 2, "per_page": 4,
              "label": "2×2  —  4 per page  (larger photos)"},
    "full": {"cols": 1, "rows": 1, "per_page": 1,
              "label": "Full Page  —  1 per page"},
}
