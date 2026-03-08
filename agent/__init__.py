"""
Regulus — Rules Ingestion Agent
================================
Modular pipeline for ingesting aviation crew rule documents (PDF) and producing:
  - Structured JSON (validated against the CrewRules Ingestion Payload v1 schema)
  - Plain-English summaries
  - Ontology term suggestions
  - Ambiguity logs
  - DSL rule syntax

Modules
-------
pdf_reader      : Extract raw text and page structure from a PDF.
parser          : Segment text into rules, sections, and metadata.
ontology        : Map rule content to ontology terms.
json_builder    : Assemble and validate output JSON against schema.json.
summarizer      : Generate plain-English summaries of rules.
dsl_generator   : Emit rule syntax in a domain-specific language (DSL).
ambiguity_logger: Record and report ambiguous or unclear rule content.
"""

__version__ = "0.1.0"
__agent_name__ = "Regulus"
