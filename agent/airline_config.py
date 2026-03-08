"""
Regulus / airline_config.py
===========================
Per-airline parsing configuration.

Each airline entry defines:
  - iata_code       : IATA two-letter code
  - name            : Full airline name
  - jurisdiction    : Regulatory jurisdiction (IATA region or national authority code)
  - contract_pattern: Regex matching contract/schedule names in this airline's PDFs
  - crew_groups     : Known crew position terms used in this airline's documents
  - section_format  : Description of the section numbering convention (informational)
  - duty_types      : Recognised duty type labels (Domestic, International, etc.)
  - notes           : Any parser hints specific to this airline's format

To add a new airline, append a config dict to AIRLINE_CONFIGS and update
AIRLINE_REGISTRY which is keyed by IATA code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class AirlineConfig:
    iata_code: str                          # "NZ"
    name: str                               # "Air New Zealand"
    jurisdiction: str                       # "NZCAA" / "EASA" / "FAA" etc.
    contract_pattern: re.Pattern            # compiled regex
    crew_groups: list[str]                  # terms that map to crew positions
    duty_types: list[str]                   # Domestic, International, Ground, Positioning
    section_format: str = ""               # human note about numbering style
    notes: list[str] = field(default_factory=list)

# ---------------------------------------------------------------------------
# Airline definitions
# ---------------------------------------------------------------------------

_AIRLINE_CONFIGS: list[dict] = [
    {
        "iata_code": "NZ",
        "name": "Air New Zealand",
        "jurisdiction": "NZCAA",
        # NZ collective agreements use "ETU Schedule NNN" and "AMEA"
        "contract_pattern": re.compile(
            r'\b(?:ETU\s+Schedule\s+\d+|AMEA|NZ\s+Schedule\s+\d+)\b',
            re.IGNORECASE,
        ),
        "crew_groups": [
            "Flight Attendants",
            "Cabin Crew",
            "Flight Deck",
            "Pilots",
            "Captain",
            "First Officer",
            "Purser",
            "Senior Flight Attendant",
            "SFA",
        ],
        "duty_types": [
            "Domestic",
            "International",
            "Ground",
            "Positioning",
            "Transtasman",
        ],
        "section_format": "Decimal-numbered sections (e.g. 52.1, 52.2) with sub-clauses (a), (b), (i)",
        "notes": [
            "Collective agreement PDFs may repeat section headings in a sidebar — parser uses longest content occurrence.",
            "Contract references follow pattern 'ETU Schedule NNN' or 'AMEA'.",
        ],
    },
    # --- Template for next airline ---
    # {
    #     "iata_code": "QF",
    #     "name": "Qantas Airways",
    #     "jurisdiction": "CASA",
    #     "contract_pattern": re.compile(r'\b(?:EBA\s+\d+|Qantas\s+Agreement)\b', re.IGNORECASE),
    #     "crew_groups": ["Cabin Crew", "Pilots", "Flight Deck"],
    #     "duty_types": ["Domestic", "International", "Positioning"],
    #     "section_format": "EBA clause numbering (e.g. Clause 12.3)",
    # },
]

# Build lookup registry keyed by IATA code (uppercase)
AIRLINE_REGISTRY: dict[str, AirlineConfig] = {
    cfg["iata_code"].upper(): AirlineConfig(**cfg)
    for cfg in _AIRLINE_CONFIGS
}

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def get_airline(iata_code: str) -> AirlineConfig | None:
    """Return AirlineConfig for the given IATA code, or None if unknown."""
    return AIRLINE_REGISTRY.get(iata_code.upper())


def list_airlines() -> list[str]:
    """Return list of registered IATA codes."""
    return sorted(AIRLINE_REGISTRY.keys())


def build_contract_pattern(iata_code: str) -> re.Pattern:
    """Return the contract regex for an airline, or a generic fallback."""
    cfg = get_airline(iata_code)
    if cfg:
        return cfg.contract_pattern
    # Generic fallback: any XX Schedule NNN or Agreement
    return re.compile(
        r'\b(?:[A-Z]{2,6}\s+Schedule\s+\d+|AMEA|EBA\s+\d+)\b',
        re.IGNORECASE,
    )
