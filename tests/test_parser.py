"""
test_parser.py
==============
Unit tests for agent.parser.

Run with: pytest tests/test_parser.py
"""

import pytest
from agent.parser import ParsedDocument, RuleRecord, SectionRecord


class TestParseDocument:
    def test_returns_parsed_document(self):
        """parse_document should return a ParsedDocument instance."""
        pytest.skip("implementation pending")

    def test_all_rules_flat(self):
        """ParsedDocument.all_rules should flatten rules across sections."""
        doc = ParsedDocument(source_file="test.pdf", doc_metadata={})
        section = SectionRecord(section_id="1", title="Section 1", page_number=1)
        rule = RuleRecord(rule_id="1.1", title="Rule", raw_text="text", page_number=1, section="1")
        section.rules.append(rule)
        doc.sections.append(section)
        assert doc.all_rules == [rule]


class TestDetectSections:
    def test_returns_list(self):
        """detect_sections should return a list."""
        pytest.skip("implementation pending")


class TestExtractRules:
    def test_returns_list_of_rule_records(self):
        """extract_rules should return RuleRecord instances."""
        pytest.skip("implementation pending")
