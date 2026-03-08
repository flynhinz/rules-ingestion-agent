"""
Regulus / summarizer.py
=======================
Generates plain-English summaries of extracted rules and sections.

Responsibilities:
- Produce a one-sentence summary for each RuleRecord.
- Produce a paragraph-level summary for each SectionRecord.
- Produce a document-level executive summary.
- Support two modes:
    "template"  : Fast, deterministic; uses rule metadata fields.
    "llm"       : Calls an LLM API for richer natural-language output
                  (requires API key; disabled by default).

Summaries are stored in the output JSON under the 'summaries' key.
"""

from __future__ import annotations

from typing import Any, Literal

SummaryMode = Literal["template", "llm"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def summarize_rule(rule: Any, mode: SummaryMode = "template") -> str:
    """Generate a plain-English summary for a single RuleRecord.

    Parameters
    ----------
    rule:
        A parser.RuleRecord instance.
    mode:
        "template" uses field substitution; "llm" calls an external model.

    Returns
    -------
    str
        One-sentence summary of the rule.
    """
    raise NotImplementedError("summarize_rule: implementation pending")


def summarize_section(section: Any, mode: SummaryMode = "template") -> str:
    """Generate a paragraph-level summary for a SectionRecord.

    Parameters
    ----------
    section:
        A parser.SectionRecord instance.
    mode:
        Summary generation strategy.

    Returns
    -------
    str
        Short paragraph (2-4 sentences) describing the section's rules.
    """
    raise NotImplementedError("summarize_section: implementation pending")


def summarize_document(parsed_doc: Any, mode: SummaryMode = "template") -> str:
    """Generate an executive summary for the full ParsedDocument.

    Parameters
    ----------
    parsed_doc:
        A parser.ParsedDocument instance.
    mode:
        Summary generation strategy.

    Returns
    -------
    str
        Executive summary suitable for a cover page or report header.
    """
    raise NotImplementedError("summarize_document: implementation pending")
