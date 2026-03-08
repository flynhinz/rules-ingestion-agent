"""
Regulus / json_builder.py
=========================
Assembles schema-compliant JSON from a ParsedDocument + ontology suggestions,
then validates against schema.json using jsonschema.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_PATH = Path(__file__).parent.parent / "schema.json"

# ID sanitisation — must match schema pattern ^[a-zA-Z0-9._-]+$
import re
_ID_UNSAFE = re.compile(r'[^a-zA-Z0-9._-]')

# Context extraction patterns (used to build parser notes)
_CONTRACT_PATTERN = re.compile(
    r'(?:ETU\s+Schedule\s+\d+|AMEA|[A-Z]{2,6}\s+Schedule\s+\d+)',
    re.IGNORECASE,
)
_CREW_GROUP_PATTERN = re.compile(
    r'\b(?:Flight\s+Attendants?|Cabin\s+Crew|Flight\s+Deck|Pilots?|Pursers?)\b',
    re.IGNORECASE,
)
_APPLICABILITY_PATTERN = re.compile(
    r'(?:applies?\s+to|applicable\s+to|in\s+respect\s+of|for\s+(?:the\s+purposes?\s+of|all))'
    r'[^.;\n]{5,120}',
    re.IGNORECASE,
)

# Human-readable type labels for reference code construction
_TYPE_LABEL = {
    "duty-limit": "Duty Hours",
    "rest-period": "Rest Hours",
    "flight-time-limit": "Flight Time Hours",
    "day-off": "Days Off",
    "standby": "Standby Hours",
    "cumulative-limit": "Cumulative Hours",
    "positioning": "Positioning Hours",
    "augmented-crew": "Augmented FDP Hours",
}


def _safe_id(text: str) -> str:
    return _ID_UNSAFE.sub('-', text).strip('-') or "rule"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_schema(schema_path: str | Path = SCHEMA_PATH) -> dict:
    """Load schema.json and return as a dict."""
    path = Path(schema_path)
    if not path.exists():
        raise FileNotFoundError(f"schema.json not found at: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def build_output(parsed_doc: Any, all_suggestions: list[list[Any]],
                 airline_cfg: Any | None = None) -> dict:
    """Assemble the output payload from a ParsedDocument and per-rule term suggestions.

    Parameters
    ----------
    parsed_doc : parser.ParsedDocument
    all_suggestions : list[list[TermSuggestion]]
        One inner list per rule, in the same order as parsed_doc.all_rules.
    airline_cfg : airline_config.AirlineConfig | None
        Optional airline context. When provided, embeds IATA code, jurisdiction,
        and airline name into the ruleset and each rule's scope.
    """
    now = datetime.now(timezone.utc).isoformat()
    rules = parsed_doc.all_rules
    suggestions_map = {
        rule.rule_id: suggs
        for rule, suggs in zip(rules, all_suggestions)
    }

    # Assign parsed PDF scenarios to the primary rule (first rule with a limit value,
    # or just the first rule if none have one).
    scenarios = getattr(parsed_doc, "scenarios", [])
    primary_rule_id: str | None = None
    for rule in rules:
        if rule.metadata.get("limit_value") is not None:
            primary_rule_id = rule.rule_id
            break
    if primary_rule_id is None and rules:
        primary_rule_id = rules[0].rule_id

    output: dict[str, Any] = {
        "$schema": "https://crewrules.app/schemas/rule-ingestion/v1",
        "meta": {
            "schemaVersion": "1.0",
            "generatedAt": now,
            "generatedBy": "Regulus v0.1.0",
            "vendorSystem": "manual",
            "description": f"Ingested from {parsed_doc.source_file}",
            **({"airlineIata": airline_cfg.iata_code, "airlineName": airline_cfg.name} if airline_cfg else {}),
        },
        "ruleset": _build_ruleset(parsed_doc, airline_cfg=airline_cfg),
        "rules": [
            _build_rule(
                rule,
                suggestions_map.get(rule.rule_id, []),
                parsed_doc.source_file,
                scenarios=scenarios if rule.rule_id == primary_rule_id else [],
                airline_cfg=airline_cfg,
            )
            for rule in rules
        ],
        "ambiguityLog": _build_ambiguity_log(rules),
    }

    return output


def validate_output(output: dict, schema: dict) -> tuple[bool, list[str]]:
    """Validate output dict against the JSON schema.

    Returns (True, []) on success, or (False, [error_messages]) on failure.
    """
    try:
        import jsonschema
        validator = jsonschema.Draft202012Validator(schema)
        errors = sorted(validator.iter_errors(output), key=lambda e: list(e.path))
        if errors:
            messages = [f"{list(e.path)}: {e.message}" for e in errors]
            return False, messages
        return True, []
    except ImportError:
        return True, ["[WARNING] jsonschema not installed — validation skipped"]


def write_output(output: dict, dest_path: str | Path) -> Path:
    """Write validated output JSON to dest_path."""
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    return dest.resolve()


def write_python_repr(output: dict, dest_path: str | Path) -> Path:
    """Write a Python source file containing each rule as a named dict literal.

    The generated file can be pasted directly into a test module. Each rule is
    assigned to a variable named ``rule_<id>`` (with non-identifier chars replaced
    by underscores). A ``RULES`` list at the bottom collects all of them.

    Parameters
    ----------
    output:
        Validated output dict (from build_output / write_output).
    dest_path:
        Destination ``.py`` file path.

    Returns
    -------
    Path
        Resolved path of the written file.
    """
    import pprint

    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)

    rules: list[dict] = output.get("rules", [])
    ruleset: dict = output.get("ruleset", {})

    lines: list[str] = [
        '"""',
        f'Python representation of rules ingested from: {output.get("meta", {}).get("description", "")}',
        f'Generated by: {output.get("meta", {}).get("generatedBy", "Regulus")}',
        f'Schema version: {output.get("meta", {}).get("schemaVersion", "1.0")}',
        '"""',
        "",
        "# Ruleset metadata",
        f"RULESET = {pprint.pformat(ruleset, indent=4)}",
        "",
    ]

    var_names: list[str] = []
    id_unsafe = re.compile(r"[^a-zA-Z0-9]")

    for rule in rules:
        rule_id = rule.get("id", "unknown")
        var = "rule_" + id_unsafe.sub("_", rule_id)
        var_names.append(var)

        # Build a clean dict with only populated schema fields
        rule_dict: dict = {}
        for field in ("id", "title", "referenceCode", "type", "rawText",
                      "dsl", "scope", "params", "visibility", "provenance",
                      "quarantineMetadata", "assumedTerms", "testCases",
                      "changeNotes", "tags", "lifecycleStatus", "notes", "assumptions"):
            if field in rule and rule[field] is not None:
                val = rule[field]
                # Omit empty lists/dicts
                if isinstance(val, (list, dict)) and not val:
                    continue
                rule_dict[field] = val

        lines.append(f"# Rule {rule_id}: {rule.get('title', '')[:60]}")
        lines.append(f"{var} = {pprint.pformat(rule_dict, indent=4)}")
        lines.append("")

    lines.append(f"RULES = [{', '.join(var_names)}]")
    lines.append("")

    dest.write_text("\n".join(lines), encoding="utf-8")
    return dest.resolve()


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------

def _build_ruleset(parsed_doc: Any, airline_cfg: Any | None = None) -> dict:
    meta = parsed_doc.doc_metadata
    title = meta.get("title", "") or parsed_doc.source_file

    # Jurisdiction: airline config wins; fall back to filename heuristic
    if airline_cfg:
        jurisdiction = airline_cfg.jurisdiction
    else:
        jurisdiction = meta.get("jurisdiction", "UNKNOWN")
        for known in ["EASA", "FAA", "CASA", "CAA", "DGCA", "NZCAA"]:
            if known.lower() in (parsed_doc.source_file + title).lower():
                jurisdiction = known
                break

    ruleset: dict[str, Any] = {
        "id": _safe_id(parsed_doc.source_file.replace(".pdf", "")),
        "name": title or parsed_doc.source_file,
        "jurisdiction": jurisdiction,
    }
    if airline_cfg:
        ruleset["airlineIata"] = airline_cfg.iata_code
        ruleset["airlineName"] = airline_cfg.name

    return ruleset


def _build_rule(rule: Any, suggestions: list[Any], source_file: str,
                scenarios: list[Any] | None = None, airline_cfg: Any | None = None) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    meta = rule.metadata

    dsl = _build_dsl(rule, meta)
    params = _build_params(dsl)
    provenance = _build_provenance(rule, source_file, now)
    assumed_terms = _build_assumed_terms(suggestions)
    test_cases = _build_test_cases_from_scenarios(scenarios) if scenarios else []

    # Human-readable rule name: "Max 52 Duty Hours in 168 Hours"
    human_ref = _build_human_reference_code(meta, dsl, rule.reference_code or _safe_id(rule.rule_id))

    # Context notes: contracts, crew groups, applicability clauses
    notes = _extract_context_notes(rule, airline_cfg=airline_cfg)
    # Section reference preserved as provenance note
    if rule.reference_code and rule.reference_code != human_ref:
        notes.insert(0, f"Section reference: {rule.reference_code}")
    if rule.references:
        notes.append(f"Cross-references: {', '.join(rule.references)}")

    # Scope: jurisdiction + airline context
    scope: dict[str, Any] = {}
    if airline_cfg:
        scope["airlineIata"] = airline_cfg.iata_code
        scope["airlineName"] = airline_cfg.name
        scope["jurisdiction"] = airline_cfg.jurisdiction

    rule_obj: dict[str, Any] = {
        "id": _safe_id(rule.rule_id),
        "referenceCode": human_ref,
        "type": meta.get("rule_type", "duty-limit"),
        "title": human_ref,
        "rawText": rule.raw_text,
        "dsl": dsl,
        "params": params,
        "scope": scope,
        "provenance": provenance,
    }

    if test_cases:
        rule_obj["testCases"] = test_cases

    if notes:
        rule_obj["notes"] = notes

    if assumed_terms:
        rule_obj["assumedTerms"] = assumed_terms

    if rule.flags:
        rule_obj["tags"] = rule.flags
        rule_obj["quarantineMetadata"] = _build_quarantine(rule, now)
        rule_obj["lifecycleStatus"] = "quarantine"
    else:
        rule_obj["lifecycleStatus"] = "draft"

    return rule_obj


def _build_dsl(rule: Any, meta: dict) -> dict:
    dsl: dict[str, Any] = {"ruleType": meta.get("rule_type", "duty-limit")}

    limit_value = meta.get("limit_value")
    limit_unit = meta.get("limit_unit")
    condition_type = meta.get("condition_type")

    if limit_value is not None and condition_type:
        dsl["condition"] = {
            "type": condition_type,
            "field": _field_for_rule_type(dsl["ruleType"]),
            "value": limit_value,
            "unit": limit_unit or "hours",
        }

    rolling = meta.get("rolling_window")
    if rolling:
        dsl["rollingWindow"] = {
            "duration": rolling["duration"],
            "unit": rolling["unit"],
            "alignment": rolling.get("alignment", "homeBase"),
        }

    return dsl


def _field_for_rule_type(rule_type: str) -> str:
    return {
        "duty-limit": "dutyHours",
        "rest-period": "restHours",
        "flight-time-limit": "flightTimeHours",
        "day-off": "daysOff",
        "standby": "standbyHours",
        "cumulative-limit": "cumulativeHours",
        "positioning": "positioningHours",
        "augmented-crew": "augmentedFdpHours",
    }.get(rule_type, "dutyHours")


def _build_provenance(rule: Any, source_file: str, now: str) -> dict:
    return {
        "sourceFile": source_file,
        "extractedBy": "Regulus v0.1.0",
        "extractedAt": now,
        "pageReference": f"p.{rule.page_number}",
        "confidence": "medium" if not rule.flags else "low",
    }


def _build_assumed_terms(suggestions: list[Any]) -> list[dict]:
    terms = []
    for s in suggestions:
        t = s.term
        confidence = "high" if s.confidence >= 0.8 else ("medium" if s.confidence >= 0.5 else "low")
        terms.append({
            "code": t.code,
            "name": t.name,
            "category": t.category,
            "dataType": t.dataType,
            "unit": t.unit,
            "description": t.description,
            "aliases": t.aliases,
            "confidence": confidence,
        })
    return terms


def _build_quarantine(rule: Any, now: str) -> dict:
    ambiguities = []
    for flag in rule.flags:
        if flag == "VAGUE_LANGUAGE":
            ambiguities.append({
                "field": "rawText",
                "issue": "Rule contains vague language (e.g. 'reasonable', 'appropriate'). Numeric threshold unclear.",
                "suggestion": "Identify the specific numeric value or condition intended.",
            })
        elif flag == "NO_NUMERIC_LIMIT":
            ambiguities.append({
                "field": "dsl.condition.value",
                "issue": "No numeric limit detected in rule text. DSL condition value is unknown.",
                "suggestion": "Verify whether a numeric threshold applies and populate dsl.condition.value.",
            })

    checklist = [
        "Verify extracted rawText matches source document",
        "Confirm dsl.ruleType is correctly classified",
        "Resolve flagged ambiguities before promotion",
    ]

    return {
        "stagedAt": now,
        "reviewerChecklist": checklist,
        "ambiguities": ambiguities,
        "priority": "high" if ambiguities else "medium",
    }


def _build_params(dsl: dict) -> dict[str, Any]:
    """Build a structured params dict from DSL condition and rolling window values."""
    params: dict[str, Any] = {}
    condition = dsl.get("condition")
    if condition:
        value = condition.get("value")
        unit = condition.get("unit", "hours")
        cond_type = condition.get("type")
        field = condition.get("field", "dutyHours")
        if value is not None and cond_type:
            prefix = "max" if cond_type == "maximum" else "min"
            key = f"{prefix}{field[0].upper()}{field[1:]}"
            params[key] = value
            params[f"{key}Unit"] = unit

    rolling = dsl.get("rollingWindow")
    if rolling:
        params["rollingWindowDuration"] = rolling.get("duration")
        params["rollingWindowUnit"] = rolling.get("unit")
        params["rollingWindowAlignment"] = rolling.get("alignment", "homeBase")

    return params


def _build_test_cases_from_scenarios(scenarios: list[Any]) -> list[dict]:
    """Convert parsed ScenarioRecords into schema-compliant TestCase dicts."""
    return [
        {
            "name": s.name,
            "description": s.description,
            "inputData": s.input_data,
            "expectedOutcome": s.expected_outcome,
        }
        for s in scenarios
    ]


def _build_human_reference_code(meta: dict, dsl: dict, fallback: str) -> str:
    """Derive a human-readable rule name from DSL condition + rolling window.

    Examples:
        "Max 52 Duty Hours in 168 Hours"
        "Min 12 Rest Hours"
        "Max 100 Flight Time Hours in 28 Days"
    """
    condition = dsl.get("condition", {})
    rolling = dsl.get("rollingWindow", {})
    rule_type = dsl.get("ruleType", "")

    value = condition.get("value")
    cond_type = condition.get("type")

    if value is None or cond_type is None:
        return fallback

    prefix = "Max" if cond_type == "maximum" else "Min"
    type_label = _TYPE_LABEL.get(rule_type, "Hours")

    # Format value cleanly: drop .0 for whole numbers
    v_str = str(int(value)) if isinstance(value, float) and value == int(value) else str(value)
    name = f"{prefix} {v_str} {type_label}"

    if rolling and rolling.get("duration"):
        w_dur = rolling["duration"]
        w_unit = rolling.get("unit", "hours").capitalize()
        w_str = str(int(w_dur)) if isinstance(w_dur, float) and w_dur == int(w_dur) else str(w_dur)
        name += f" in {w_str} {w_unit}"

    return name


def _extract_context_notes(rule: Any, airline_cfg: Any | None = None) -> list[str]:
    """Extract applicability context from rule text and return as notes.

    Covers:
    - Contract/schedule references  (e.g. "ETU Schedule 400, ETU Schedule 500")
    - Crew group mentions           (e.g. "Flight Attendants", "Cabin Crew")
    - Applicability clauses         (e.g. "applies to augmented crew operations")

    When airline_cfg is provided its contract_pattern is used instead of the
    generic fallback, giving airline-specific contract detection.
    """
    text = rule.raw_text
    notes: list[str] = []

    contract_re = airline_cfg.contract_pattern if airline_cfg else _CONTRACT_PATTERN
    contracts = list(dict.fromkeys(m.group(0).strip() for m in contract_re.finditer(text)))
    if contracts:
        notes.append(f"Applies to contracts: {', '.join(contracts)}")

    # Crew group pattern: use airline-specific list when available
    if airline_cfg and airline_cfg.crew_groups:
        crew_re = re.compile(
            r'\b(?:' + '|'.join(re.escape(g) for g in airline_cfg.crew_groups) + r')\b',
            re.IGNORECASE,
        )
    else:
        crew_re = _CREW_GROUP_PATTERN
    crew_groups = list(dict.fromkeys(m.group(0).strip() for m in crew_re.finditer(text)))
    if crew_groups:
        notes.append(f"Crew group(s): {', '.join(crew_groups)}")

    # Add applicability clauses that aren't already covered by contract/crew notes above
    already_covered = {c.lower() for c in contracts} | {g.lower() for g in crew_groups}
    for m in _APPLICABILITY_PATTERN.finditer(text):
        clause = m.group(0).strip().rstrip(".,;")
        clause_lower = clause.lower()
        if not any(covered in clause_lower for covered in already_covered):
            notes.append(clause[:200])

    return notes


def _build_ambiguity_log(rules: list[Any]) -> list[dict]:
    log = []
    for rule in rules:
        for i, flag in enumerate(rule.flags):
            log.append({
                "id": f"{rule.rule_id}-flag-{i}",
                "summary": f"Rule {rule.rule_id}: {flag}",
                "ruleId": rule.rule_id,
                "flag": flag,
            })
    return log
