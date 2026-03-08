"""
Regulus / parser.py
===================
Segments raw extracted text into structured rules, sections, and metadata.
Tuned for aviation crew rules documents (numbered clauses, obligation keywords).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data models (schema-agnostic intermediate representation)
# ---------------------------------------------------------------------------

@dataclass
class RuleRecord:
    """Intermediate representation of a single extracted rule."""
    rule_id: str
    title: str
    raw_text: str
    page_number: int
    section: str
    reference_code: str = ""          # human-readable e.g. "52.1(a)"
    metadata: dict[str, Any] = field(default_factory=dict)
    references: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


@dataclass
class SectionRecord:
    """Intermediate representation of a document section."""
    section_id: str
    title: str
    page_number: int
    rules: list[RuleRecord] = field(default_factory=list)


@dataclass
class ScenarioRecord:
    """A single test scenario parsed from the document's Scenarios section."""
    name: str
    description: str
    input_data: dict[str, Any]
    expected_outcome: dict[str, Any]


@dataclass
class ParsedDocument:
    """Top-level result returned by parse_document()."""
    source_file: str
    doc_metadata: dict[str, Any]
    sections: list[SectionRecord] = field(default_factory=list)
    scenarios: list[ScenarioRecord] = field(default_factory=list)

    @property
    def all_rules(self) -> list[RuleRecord]:
        return [rule for section in self.sections for rule in section.rules]


# ---------------------------------------------------------------------------
# Internal patterns
# ---------------------------------------------------------------------------

# Matches top-level section headings like "52 Duty Hours" or "52.1 Rest Periods"
_SECTION_HEADING = re.compile(
    r'^(\d{1,3}(?:\.\d{1,3}){0,2})\s{1,4}([A-Z][^\n]{3,80})$',
    re.MULTILINE,
)

# Matches sub-clauses like "(1)", "(a)", "(i)"
_SUBCLAUSE = re.compile(r'^\s*\((\d+|[a-z]|[ivxlcdm]+)\)\s+(.+)', re.MULTILINE)

# Obligation keywords that signal a rule statement
_OBLIGATION = re.compile(
    r'\b(must not|must|shall not|shall|may not|may|should not|should|will not|will|are not|is required to|is prohibited from|is mandatory)\b',
    re.IGNORECASE,
)

# Numeric limit patterns: "52 hours", "168-hour", "52 duty hours", "10.5 hours"
# Optional qualifier word handles "52 duty hours", "168 consecutive hours", etc.
# Negative lookbehind on 4-digit blocks (HHmm clock times like "1730 hours") — these
# are time-of-day references, not durations, and must not be captured as limits.
_NUMERIC_LIMIT = re.compile(
    r'(?<!\d)(?!(?:0[0-9]|1[0-9]|2[0-3])[0-5]\d\b)(\d+(?:\.\d+)?)\s*[-\u2013]?\s*(?:duty\s+|flight\s+|consecutive\s+|calendar\s+)?(hours?|minutes?|days?|weeks?)',
    re.IGNORECASE,
)

# Rolling window patterns: "in any 168-hour period", "within 28 consecutive days"
_ROLLING_WINDOW = re.compile(
    r'(?:in any|within|per|in a)\s+(\d+(?:\.\d+)?)\s*[-\u2013]?\s*(?:consecutive\s+)?(hours?|days?|weeks?)\s*(?:period|window)?',
    re.IGNORECASE,
)

# Primary limit patterns — obligation + value in the same phrase
# Handles: "not more than 52 hours", "not be rostered for more than 52 duty hours",
#          "not intentionally exceed 52 hours", "maximum duty: 52 hours"
_PRIMARY_LIMIT = re.compile(
    r'(?:not (?:be )?(?:\w+ ){0,3}(?:more than|exceed(?:ed)?)|maximum(?:\s+\w+)?:?\s*)'
    r'(\d+(?:\.\d+)?)\s*[-\u2013]?\s*(?:duty\s+|flight\s+|consecutive\s+|calendar\s+)?(hours?|minutes?|days?|weeks?)',
    re.IGNORECASE,
)

# Cross-references to other rules/sections
_XREF = re.compile(r'\b(?:clause|section|rule|paragraph|sub-rule)\s+([\d.]+(?:\([a-z\d]+\))*)', re.IGNORECASE)

# Scenario section heading: "7.0 Rule Example (Scenarios)" or "11.0 Rule Examples (Scenarios)"
_SCENARIO_SECTION_HEADING = re.compile(
    r'^\d{1,2}\.0\s+Rule\s+Examples?\s*(?:\(Scenarios?\))?\s*$',
    re.MULTILINE | re.IGNORECASE,
)

# Numbered scenario: "Scenario 1: Title" — captures everything until next scenario or end
_NUMBERED_SCENARIO = re.compile(
    r'Scenario\s+(\d+)[:\s]+([^\n]+)\n(.*?)(?=Scenario\s+\d+|\Z)',
    re.DOTALL,
)

# Inline scenario: "Description → outcome" or "Description -> outcome"
_INLINE_SCENARIO = re.compile(
    r'^([^\n→\-][^\n]+?)\s*[→\u2192]>?\s*(.+)$',
    re.MULTILINE,
)

# Outcome signals
_OUTCOME_NO_ALERT = re.compile(r'\bno\s+(?:illegal\s+)?alert\b', re.IGNORECASE)
_OUTCOME_ALERT = re.compile(r'\balert\s+(?:displayed|triggered)\b', re.IGNORECASE)
_OUTCOME_ILLEGAL = re.compile(r'\billegal\b', re.IGNORECASE)

# Sanitise a string to a valid schema ID
_ID_UNSAFE = re.compile(r'[^a-zA-Z0-9._-]')


def _safe_id(text: str) -> str:
    return _ID_UNSAFE.sub('-', text).strip('-')


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_document(pages: list[dict], source_file: str = "", doc_metadata: dict | None = None) -> ParsedDocument:
    """Parse a list of page records into a ParsedDocument.

    Parameters
    ----------
    pages:
        Output of pdf_reader.load_pdf().
    source_file:
        Original filename (used for provenance).
    doc_metadata:
        Output of pdf_reader.extract_metadata() (optional).
    """
    doc = ParsedDocument(
        source_file=source_file,
        doc_metadata=doc_metadata or {},
    )

    sections = detect_sections(pages)

    # If no section headings detected, treat the whole doc as one section
    if not sections:
        full_text = "\n".join(p["raw_text"] for p in pages)
        fallback = SectionRecord(section_id="1", title="Document", page_number=1)
        fallback.rules = extract_rules(fallback, full_text, start_page=1)
        doc.sections = [fallback]
        return doc

    doc.sections = sections
    doc.scenarios = parse_scenarios(pages)
    return doc


def parse_scenarios(pages: list[dict]) -> list[ScenarioRecord]:
    """Extract test scenarios from the document's 'Rule Examples (Scenarios)' section."""
    full_text = "\n".join(p["raw_text"] for p in pages)

    # Find the scenario section — take the last (richest) occurrence
    headings = list(_SCENARIO_SECTION_HEADING.finditer(full_text))
    if not headings:
        return []

    # Use the last match — sidebar repeats the heading without body, body comes last
    section_start = headings[-1].end()
    # Section ends at the next top-level numeric heading or end of text
    next_section = re.search(r'^\d{1,2}\.0\s+[A-Z]', full_text[section_start:], re.MULTILINE)
    section_text = full_text[section_start: section_start + next_section.start()] if next_section else full_text[section_start:]

    scenarios: list[ScenarioRecord] = []

    # Try numbered "Scenario N: Title" format first
    numbered = list(_NUMBERED_SCENARIO.finditer(section_text))
    if numbered:
        for m in numbered:
            name = m.group(2).strip()
            body = m.group(3).strip()
            scenarios.append(_parse_scenario_body(name, body))
        return scenarios

    # Fall back to inline "Description → outcome" format
    inline = list(_INLINE_SCENARIO.finditer(section_text))
    for m in inline:
        description = m.group(1).strip()
        outcome_text = m.group(2).strip()
        outcome = _classify_outcome(outcome_text)
        scenarios.append(ScenarioRecord(
            name=description,
            description=description,
            input_data={"conditions": [description]},
            expected_outcome=outcome,
        ))

    return scenarios


def _parse_scenario_body(name: str, body: str) -> ScenarioRecord:
    """Parse a numbered scenario's body lines into inputData and expectedOutcome."""
    lines = [ln.strip() for ln in body.splitlines() if ln.strip()]

    # Last line that contains an outcome signal is the outcome
    outcome_line = ""
    body_lines: list[str] = []
    for line in lines:
        if _OUTCOME_NO_ALERT.search(line) or _OUTCOME_ALERT.search(line) or _OUTCOME_ILLEGAL.search(line):
            outcome_line = line
        else:
            body_lines.append(line)

    outcome = _classify_outcome(outcome_line or name)

    # Build inputData: "Key = Value" pairs → dict entries; others → conditions list
    input_data: dict[str, Any] = {}
    conditions: list[str] = []
    for line in body_lines:
        if "=" in line:
            key, _, val = line.partition("=")
            # camelCase the key: "Rolling total" → "rollingTotal"
            words = key.strip().split()
            camel = words[0].lower() + "".join(w.capitalize() for w in words[1:])
            input_data[camel] = val.strip()
        else:
            conditions.append(line)
    if conditions:
        input_data["conditions"] = conditions

    return ScenarioRecord(
        name=name,
        description=name,
        input_data=input_data,
        expected_outcome=outcome,
    )


def _classify_outcome(text: str) -> dict[str, Any]:
    """Map outcome text to a structured expectedOutcome dict."""
    t = text.lower()
    # "no illegal alert" — compliant but with conditions applied (allowances etc.)
    if "no illegal alert" in t:
        return {
            "compliant": True,
            "message": text,
            "severity": "warning",
        }
    # "no alert" — fully compliant
    if _OUTCOME_NO_ALERT.search(text):
        return {
            "compliant": True,
            "message": text,
            "severity": "info",
        }
    # "alert displayed / triggered" — violation
    if _OUTCOME_ALERT.search(text) or "illegal" in t:
        return {
            "compliant": False,
            "message": text,
            "severity": "violation",
        }
    # Ambiguous — treat as warning for human review
    return {
        "compliant": True,
        "message": text,
        "severity": "warning",
    }


def detect_sections(pages: list[dict]) -> list[SectionRecord]:
    """Identify section boundaries from page text and return SectionRecords."""
    full_text = "\n".join(p["raw_text"] for p in pages)
    page_starts = {}
    offset = 0
    for p in pages:
        page_starts[offset] = p["page_number"]
        offset += len(p["raw_text"]) + 1  # +1 for the \n join

    # Collect all candidate sections (section_id -> best candidate by text length)
    # Confluence PDFs repeat headings in a sidebar with no body — we keep the
    # occurrence with the most content between its heading and the next heading.
    candidates: dict[str, dict] = {}
    matches = list(_SECTION_HEADING.finditer(full_text))

    for i, m in enumerate(matches):
        sec_id = m.group(1)
        sec_title = m.group(2).strip()

        pos = m.start()
        page_num = 1
        for start_pos, pg in sorted(page_starts.items()):
            if start_pos <= pos:
                page_num = pg

        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        section_text = full_text[m.start():end_pos]

        existing = candidates.get(sec_id)
        if existing is None or len(section_text) > len(existing["text"]):
            candidates[sec_id] = {
                "sec_id": sec_id,
                "title": sec_title,
                "page_num": page_num,
                "text": section_text,
            }

    # Preserve document order using first-seen position of each section_id
    order = []
    seen: set[str] = set()
    for m in matches:
        sec_id = m.group(1)
        if sec_id not in seen:
            seen.add(sec_id)
            order.append(sec_id)

    sections: list[SectionRecord] = []
    for sec_id in order:
        c = candidates[sec_id]
        section = SectionRecord(
            section_id=c["sec_id"],
            title=c["title"],
            page_number=c["page_num"],
        )
        section.rules = extract_rules(section, c["text"], start_page=c["page_num"])
        sections.append(section)

    return sections


def extract_rules(section: SectionRecord, raw_text: str, start_page: int = 1) -> list[RuleRecord]:
    """Extract individual rule records from a section's raw text."""
    rules: list[RuleRecord] = []

    # Split on sub-clause markers first
    sub_matches = list(_SUBCLAUSE.finditer(raw_text))

    if sub_matches:
        for j, sm in enumerate(sub_matches):
            clause_label = sm.group(1)
            end = sub_matches[j + 1].start() if j + 1 < len(sub_matches) else len(raw_text)
            clause_text = raw_text[sm.start():end].strip()

            if not _OBLIGATION.search(clause_text) and len(clause_text) < 20:
                continue  # skip non-rule lines

            rule_id = _safe_id(f"{section.section_id}.{clause_label}")
            ref_code = f"{section.section_id}({clause_label})"
            title = _derive_title(clause_text, section.title)
            meta = extract_rule_metadata(clause_text)
            refs = _extract_references(clause_text)
            flags = _detect_flags(clause_text)

            rules.append(RuleRecord(
                rule_id=rule_id,
                title=title,
                raw_text=clause_text,
                page_number=start_page,
                section=section.section_id,
                reference_code=ref_code,
                metadata=meta,
                references=refs,
                flags=flags,
            ))
    else:
        # No sub-clauses — treat the whole section text as one rule if it has
        # obligation language OR a numeric limit (e.g. "Maximum duty: 52 hours")
        stripped = raw_text.strip()
        has_obligation = _OBLIGATION.search(stripped)
        has_limit = _NUMERIC_LIMIT.search(stripped)
        if (has_obligation or has_limit) and len(stripped) >= 10:
            rule_id = _safe_id(section.section_id)
            meta = extract_rule_metadata(stripped)
            rules.append(RuleRecord(
                rule_id=rule_id,
                title=section.title,
                raw_text=stripped,
                page_number=start_page,
                section=section.section_id,
                reference_code=section.section_id,
                metadata=meta,
                references=_extract_references(stripped),
                flags=_detect_flags(stripped),
            ))

    return rules


def extract_rule_metadata(rule_text: str) -> dict[str, Any]:
    """Extract structured metadata from a raw rule string."""
    meta: dict[str, Any] = {}

    # Obligation type
    obl_match = _OBLIGATION.search(rule_text)
    if obl_match:
        meta["obligation_type"] = obl_match.group(1).lower()

    # Primary limit: prefer obligation-bound value (e.g. "not more than 52 hours")
    # over first numeric match, to avoid catching rolling-window values first.
    primary_match = _PRIMARY_LIMIT.search(rule_text) or _NUMERIC_LIMIT.search(rule_text)
    if primary_match:
        meta["limit_value"] = float(primary_match.group(1))
        meta["limit_unit"] = _normalise_unit(primary_match.group(2))

    # Rolling window
    window_match = _ROLLING_WINDOW.search(rule_text)
    if window_match:
        meta["rolling_window"] = {
            "duration": float(window_match.group(1)),
            "unit": _normalise_unit(window_match.group(2)),
            "alignment": "homeBase",
        }

    # Rule type inference
    meta["rule_type"] = _infer_rule_type(rule_text)

    # Condition type
    t_lower = rule_text.lower()
    if any(kw in t_lower for kw in ("must not", "shall not", "may not", "will not", "not exceed", "not more than")):
        meta["condition_type"] = "maximum"
    elif any(kw in t_lower for kw in ("must", "shall", "will", "is mandatory", "is required")):
        meta["condition_type"] = "minimum"
    elif "may" in t_lower:
        meta["condition_type"] = "conditional"
    else:
        meta["condition_type"] = None

    return meta


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _infer_rule_type(text: str) -> str:
    t = text.lower()
    # Check specific duty/flight types before generic "rest" — rest clauses often
    # appear as remedies inside duty-limit rules and should not override the type.
    if "flight duty" in t or "fdp" in t:
        return "flight-time-limit"
    if "flight time" in t or "flying time" in t:
        return "flight-time-limit"
    # "day off" as a standalone rule type — exclude if "duty" is the primary subject
    if ("day off" in t or "days off" in t or "day(s) off" in t) and "duty" not in t:
        return "day-off"
    if "augmented" in t:
        return "augmented-crew"
    if "cumulative" in t:
        return "cumulative-limit"
    # Check "duty" before positioning/standby/rest — those terms often appear as
    # subcategories or remedies inside duty-limit rules and must not override the type.
    if "duty" in t:
        return "duty-limit"
    if "standby" in t:
        return "standby"
    if "positioning" in t:
        return "positioning"
    if "rest" in t:
        return "rest-period"
    return "duty-limit"


def _normalise_unit(raw: str) -> str:
    r = raw.lower().rstrip("s")
    return {"hour": "hours", "minute": "minutes", "day": "days", "week": "weeks"}.get(r, r + "s")


def _derive_title(text: str, section_title: str) -> str:
    """Generate a short title from the first sentence of the clause."""
    first_sentence = re.split(r'[.;]', text)[0].strip()
    if len(first_sentence) <= 120:
        return first_sentence[:120]
    return section_title


def _extract_references(text: str) -> list[str]:
    return list(dict.fromkeys(m.group(1) for m in _XREF.finditer(text)))


def _detect_flags(text: str) -> list[str]:
    flags = []
    vague = re.compile(r'\b(reasonable|appropriate|adequate|sufficient|as necessary|practicable)\b', re.IGNORECASE)
    if vague.search(text):
        flags.append("VAGUE_LANGUAGE")
    if not _NUMERIC_LIMIT.search(text) and _OBLIGATION.search(text):
        flags.append("NO_NUMERIC_LIMIT")
    return flags
