"""
Regulus / dsl_generator.py
==========================
Emits rule syntax in a domain-specific language (DSL).

Responsibilities:
- Convert a RuleRecord's structured metadata into a DSL expression.
- Support an extensible DSL grammar (defined below as a stub).
- Validate DSL output for syntactic correctness before writing.
- Write DSL files to output/ alongside JSON output.

Stub DSL Grammar (to be formalised with the user's schema):
------------------------------------------------------------
  rule <ID> "<TITLE>" {
      scope:      <SCOPE>
      obligation: <must | shall | may | must_not>
      subject:    <SUBJECT>
      condition:  <CONDITION>
      action:     <ACTION>
      effective:  <DATE>
      refs:       [<RULE_ID>, ...]
  }
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def rule_to_dsl(rule: Any) -> str:
    """Convert a single RuleRecord to a DSL string.

    Parameters
    ----------
    rule:
        A parser.RuleRecord instance with populated metadata.

    Returns
    -------
    str
        A DSL expression representing the rule.
    """
    raise NotImplementedError("rule_to_dsl: implementation pending")


def document_to_dsl(parsed_doc: Any) -> str:
    """Convert an entire ParsedDocument to a DSL file string.

    Parameters
    ----------
    parsed_doc:
        A parser.ParsedDocument instance.

    Returns
    -------
    str
        Full DSL file content (all rules concatenated with section headers).
    """
    raise NotImplementedError("document_to_dsl: implementation pending")


def validate_dsl(dsl_text: str) -> tuple[bool, list[str]]:
    """Check a DSL string for syntactic correctness.

    Parameters
    ----------
    dsl_text:
        Raw DSL string to validate.

    Returns
    -------
    tuple[bool, list[str]]
        (is_valid, list_of_syntax_errors)
    """
    raise NotImplementedError("validate_dsl: implementation pending")
