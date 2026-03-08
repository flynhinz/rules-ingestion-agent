"""
test_json_builder.py
====================
Unit tests for agent.json_builder.

Run with: pytest tests/test_json_builder.py
"""

import pytest
from agent.json_builder import load_schema, validate_output


class TestLoadSchema:
    def test_returns_dict(self):
        """load_schema should return a dict."""
        pytest.skip("implementation pending — schema.json not yet populated")

    def test_raises_if_missing(self):
        """load_schema should raise FileNotFoundError when schema.json is absent."""
        pytest.skip("implementation pending")


class TestValidateOutput:
    def test_valid_output_passes(self):
        """validate_output should return (True, []) for a fully valid output."""
        pytest.skip("implementation pending")

    def test_missing_required_field_fails(self):
        """validate_output should return errors for missing required fields."""
        pytest.skip("implementation pending")


class TestBuildOutput:
    def test_returns_dict(self):
        """build_output should return a dict."""
        pytest.skip("implementation pending")
