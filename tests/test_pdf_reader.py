"""
test_pdf_reader.py
==================
Unit tests for agent.pdf_reader.

All tests use a small fixture PDF stored at tests/fixtures/sample.pdf.
Run with: pytest tests/test_pdf_reader.py
"""

import pytest
from pathlib import Path

# Fixture path — add a real test PDF here before running tests
FIXTURE_PDF = Path(__file__).parent / "fixtures" / "sample.pdf"


class TestLoadPdf:
    def test_returns_list(self):
        """load_pdf should return a non-empty list."""
        pytest.skip("implementation pending")

    def test_page_record_keys(self):
        """Each page record must contain required keys."""
        pytest.skip("implementation pending")

    def test_invalid_path_raises(self):
        """load_pdf should raise FileNotFoundError for missing files."""
        pytest.skip("implementation pending")


class TestIterPages:
    def test_yields_same_count_as_load(self):
        """iter_pages should yield the same number of pages as load_pdf."""
        pytest.skip("implementation pending")


class TestExtractMetadata:
    def test_returns_dict(self):
        """extract_metadata should return a dict with at least page_count."""
        pytest.skip("implementation pending")
