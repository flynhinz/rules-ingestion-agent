"""
test_ontology.py
================
Unit tests for agent.ontology.

Run with: pytest tests/test_ontology.py
"""

import pytest
from agent.ontology import OntologyTerm, TermSuggestion


class TestLoadOntology:
    def test_returns_dict(self):
        """load_ontology should return a dict of OntologyTerm."""
        pytest.skip("implementation pending")


class TestSuggestTerms:
    def test_returns_list(self):
        """suggest_terms should return a list."""
        pytest.skip("implementation pending")

    def test_top_k_limit(self):
        """suggest_terms should return at most top_k results."""
        pytest.skip("implementation pending")

    def test_sorted_by_confidence(self):
        """Results should be sorted highest confidence first."""
        pytest.skip("implementation pending")


class TestFlagUnmatched:
    def test_returns_list_of_strings(self):
        """flag_unmatched should return a list of strings."""
        pytest.skip("implementation pending")
