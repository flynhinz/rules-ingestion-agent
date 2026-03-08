"""
Regulus / ontology.py
=====================
Maps extracted rule content to ontology terms using a built-in starter
vocabulary for aviation crew rules. Extensible via ontology_terms.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Built-in starter vocabulary — aviation crew rules domain
_BUILTIN_TERMS: list[dict] = [
    {
        "code": "DUTY_HOURS_MAX",
        "name": "Maximum Duty Hours",
        "category": "duty-limits",
        "dataType": "duration",
        "unit": "hours",
        "description": "The maximum number of hours a crew member may be on duty.",
        "aliases": ["duty limit", "maximum duty", "duty hours limit", "duty period limit"],
    },
    {
        "code": "DUTY_HOURS_168H",
        "name": "Duty Hours in 168-Hour Period",
        "category": "duty-limits",
        "dataType": "duration",
        "unit": "hours",
        "description": "Maximum cumulative duty hours in any 168-hour (7-day) rolling window.",
        "aliases": ["168 hours", "168-hour period", "7 day period", "weekly duty limit"],
    },
    {
        "code": "REST_PERIOD_MIN",
        "name": "Minimum Rest Period",
        "category": "rest",
        "dataType": "duration",
        "unit": "hours",
        "description": "Minimum rest a crew member must receive before a duty period.",
        "aliases": ["minimum rest", "rest period", "pre-duty rest", "rest before duty"],
    },
    {
        "code": "FDP_MAX",
        "name": "Maximum Flight Duty Period",
        "category": "duty-limits",
        "dataType": "duration",
        "unit": "hours",
        "description": "Maximum length of a flight duty period.",
        "aliases": ["fdp", "flight duty period", "maximum fdp", "fdp limit"],
    },
    {
        "code": "CUMULATIVE_FLIGHT_TIME_28D",
        "name": "Cumulative Flight Time in 28 Days",
        "category": "flight-time",
        "dataType": "duration",
        "unit": "hours",
        "description": "Maximum total flight time in any 28-day rolling window.",
        "aliases": ["28 days", "28-day period", "cumulative flight time"],
    },
    {
        "code": "CUMULATIVE_FLIGHT_TIME_365D",
        "name": "Cumulative Flight Time in 365 Days",
        "category": "flight-time",
        "dataType": "duration",
        "unit": "hours",
        "description": "Maximum total flight time in any 365-day (calendar year) window.",
        "aliases": ["365 days", "annual flight time", "yearly limit", "calendar year"],
    },
    {
        "code": "DAY_OFF_MIN",
        "name": "Minimum Days Off",
        "category": "day-off",
        "dataType": "number",
        "unit": "days",
        "description": "Minimum number of days off required in a given period.",
        "aliases": ["days off", "day off", "free days", "days free from duty"],
    },
    {
        "code": "STANDBY_DUTY",
        "name": "Standby Duty",
        "category": "duty-limits",
        "dataType": "string",
        "unit": None,
        "description": "A period during which a crew member must be available to report for duty.",
        "aliases": ["standby", "on call", "airport standby", "home standby", "reserve"],
    },
    {
        "code": "SPLIT_DUTY",
        "name": "Split Duty",
        "category": "duty-limits",
        "dataType": "string",
        "unit": None,
        "description": "A duty period separated by a rest break that does not qualify as a full rest period.",
        "aliases": ["split duty", "split fdp", "duty split"],
    },
    {
        "code": "POSITIONING",
        "name": "Positioning",
        "category": "duty-limits",
        "dataType": "string",
        "unit": None,
        "description": "Travel by a crew member as a passenger for operational purposes.",
        "aliases": ["positioning", "deadhead", "ferry", "repositioning"],
    },
    {
        "code": "AUGMENTED_CREW",
        "name": "Augmented Crew",
        "category": "augmented-crew",
        "dataType": "string",
        "unit": None,
        "description": "A flight crew with additional members allowing in-flight relief.",
        "aliases": ["augmented", "augmented crew", "extra pilot", "reinforced crew"],
    },
    {
        "code": "LAYOVER_REST",
        "name": "Layover Rest",
        "category": "rest",
        "dataType": "duration",
        "unit": "hours",
        "description": "Rest period taken away from home base between duty periods.",
        "aliases": ["layover", "away from base rest", "hotel rest", "layover rest"],
    },
    {
        "code": "ACCLIMATIZATION",
        "name": "Acclimatization",
        "category": "acclimatization",
        "dataType": "string",
        "unit": None,
        "description": "The process of adjusting to a new time zone after crossing multiple time zones.",
        "aliases": ["acclimatization", "acclimatisation", "time zone", "circadian"],
    },
    {
        "code": "MEAL_BREAK",
        "name": "Meal Break",
        "category": "duty-limits",
        "dataType": "duration",
        "unit": "minutes",
        "description": "A break in duty provided for meals.",
        "aliases": ["meal break", "meal period", "food break"],
    },
    {
        "code": "DISRUPTED_DUTY",
        "name": "Disrupted Duty",
        "category": "duty-limits",
        "dataType": "string",
        "unit": None,
        "description": "A duty period significantly altered from the planned schedule.",
        "aliases": ["disrupted duty", "disrupted", "irregular operations", "irops"],
    },
]


@dataclass
class OntologyTerm:
    """A single term in the domain ontology (mirrors schema OntologyTerm)."""
    code: str
    name: str
    category: str
    dataType: str = "string"
    unit: str | None = None
    description: str = ""
    aliases: list[str] = field(default_factory=list)


@dataclass
class TermSuggestion:
    """A suggested ontology match for a span of rule text."""
    term: OntologyTerm
    matched_text: str
    confidence: float        # 0.0 – 1.0
    source: str              # "keyword" | "manual"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_ontology(ontology_path: str | Path | None = None) -> dict[str, OntologyTerm]:
    """Load ontology terms.

    Starts with the built-in vocabulary. If ontology_path points to a JSON file
    of the same shape, those terms are merged in (overriding built-ins by code).

    Returns
    -------
    dict[str, OntologyTerm]  — code -> OntologyTerm
    """
    registry: dict[str, OntologyTerm] = {
        t["code"]: OntologyTerm(**{k: v for k, v in t.items()})
        for t in _BUILTIN_TERMS
    }

    if ontology_path:
        path = Path(ontology_path)
        if path.exists():
            with path.open(encoding="utf-8") as f:
                extra = json.load(f)
            for t in extra:
                registry[t["code"]] = OntologyTerm(**{k: v for k, v in t.items()})

    return registry


def suggest_terms(
    text: str,
    ontology: dict[str, OntologyTerm],
    top_k: int = 5,
) -> list[TermSuggestion]:
    """Suggest the top-k ontology terms for a piece of rule text.

    Uses keyword/alias matching. Returns results sorted by confidence desc.
    """
    text_lower = text.lower()
    scored: list[tuple[float, str, OntologyTerm]] = []

    for term in ontology.values():
        best_score = 0.0
        best_match = ""

        candidates = [term.name.lower()] + [a.lower() for a in term.aliases]
        for phrase in candidates:
            if phrase in text_lower:
                # Longer phrase match = higher confidence
                score = min(0.95, 0.5 + len(phrase) / 60)
                if score > best_score:
                    best_score = score
                    best_match = phrase

        if best_score > 0:
            scored.append((best_score, best_match, term))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        TermSuggestion(term=t, matched_text=m, confidence=s, source="keyword")
        for s, m, t in scored[:top_k]
    ]


def flag_unmatched(
    text: str,
    suggestions: list[TermSuggestion],
    confidence_threshold: float = 0.5,
) -> list[str]:
    """Return numeric/domain phrases in text with no high-confidence match."""
    import re
    matched_phrases = {s.matched_text for s in suggestions if s.confidence >= confidence_threshold}

    # Extract candidate domain phrases: things that look like limits or durations
    candidates = re.findall(r'\b\d+(?:\.\d+)?\s*(?:hours?|minutes?|days?|weeks?)\b', text, re.IGNORECASE)
    return [c for c in candidates if c.lower() not in matched_phrases]
