"""
Regulus / ambiguity_logger.py
=============================
Records, categorises, and reports ambiguous or unclear rule content.

Responsibilities:
- Accept ambiguity flags raised by parser, ontology, or json_builder.
- Categorise flags: VAGUE_LANGUAGE | MISSING_FIELD | CONFLICTING_RULE |
                    ONTOLOGY_GAP | SCHEMA_MISMATCH | UNPARSEABLE_TEXT
- Accumulate flags across the pipeline run in a session log.
- Write a structured ambiguity report to output/ambiguity_log.json.
- Provide a plain-text summary of ambiguities for human review.

Ambiguity entries are included in the final JSON output under 'ambiguities'.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class AmbiguityCategory(str, Enum):
    VAGUE_LANGUAGE    = "VAGUE_LANGUAGE"      # e.g. "reasonable", "appropriate"
    MISSING_FIELD     = "MISSING_FIELD"        # required schema field not found
    CONFLICTING_RULE  = "CONFLICTING_RULE"     # two rules contradict each other
    ONTOLOGY_GAP      = "ONTOLOGY_GAP"         # no ontology term matched
    SCHEMA_MISMATCH   = "SCHEMA_MISMATCH"      # extracted value doesn't fit schema type
    UNPARSEABLE_TEXT  = "UNPARSEABLE_TEXT"     # text block could not be structured


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class AmbiguityEntry:
    """A single ambiguity record."""
    rule_id: str | None
    category: AmbiguityCategory
    description: str
    excerpt: str                    # the offending text snippet
    page_number: int | None = None
    suggestions: list[str] = field(default_factory=list)  # human-readable hints


@dataclass
class AmbiguityLog:
    """Accumulated ambiguity entries for one pipeline run."""
    source_file: str
    entries: list[AmbiguityEntry] = field(default_factory=list)

    def add(self, entry: AmbiguityEntry) -> None:
        """Append a new ambiguity entry."""
        self.entries.append(entry)

    @property
    def count(self) -> int:
        return len(self.entries)

    def by_category(self, category: AmbiguityCategory) -> list[AmbiguityEntry]:
        return [e for e in self.entries if e.category == category]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def new_log(source_file: str) -> AmbiguityLog:
    """Create a fresh AmbiguityLog for a pipeline run.

    Parameters
    ----------
    source_file:
        Name of the PDF being processed.

    Returns
    -------
    AmbiguityLog
    """
    return AmbiguityLog(source_file=source_file)


def flag(
    log: AmbiguityLog,
    category: AmbiguityCategory,
    description: str,
    excerpt: str,
    rule_id: str | None = None,
    page_number: int | None = None,
    suggestions: list[str] | None = None,
) -> None:
    """Append a new ambiguity entry to the log.

    This is the primary interface used by other modules to raise flags.
    """
    log.add(AmbiguityEntry(
        rule_id=rule_id,
        category=category,
        description=description,
        excerpt=excerpt,
        page_number=page_number,
        suggestions=suggestions or [],
    ))


def write_log(log: AmbiguityLog, dest_path: str | Path) -> Path:
    """Serialise the AmbiguityLog to a JSON file.

    Parameters
    ----------
    log:
        The accumulated log from a pipeline run.
    dest_path:
        Destination path (inside output/).

    Returns
    -------
    Path
        Resolved path of the written file.
    """
    raise NotImplementedError("write_log: implementation pending")


def plain_text_report(log: AmbiguityLog) -> str:
    """Return a human-readable summary of all ambiguity entries.

    Parameters
    ----------
    log:
        The accumulated log.

    Returns
    -------
    str
        Formatted plain-text report.
    """
    raise NotImplementedError("plain_text_report: implementation pending")
