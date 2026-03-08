"""
Regulus / pdf_reader.py
=======================
Extracts raw text and structural metadata from a PDF file using pdfplumber.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator


def load_pdf(pdf_path: str | Path) -> list[dict]:
    """Open a PDF and return a list of page records.

    Returns
    -------
    list[dict]  — one dict per page:
        page_number (int)
        raw_text    (str)
        lines       (list[str])   non-empty lines only
        bbox_hints  (list[dict])  reserved for future layout cues
    """
    import pdfplumber

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            lines = [ln for ln in text.splitlines() if ln.strip()]
            pages.append({
                "page_number": i,
                "raw_text": text,
                "lines": lines,
                "bbox_hints": [],
            })
    return pages


def iter_pages(pdf_path: str | Path) -> Iterator[dict]:
    """Lazily yield page records (memory-friendly for large PDFs)."""
    for page in load_pdf(pdf_path):
        yield page


def extract_metadata(pdf_path: str | Path) -> dict:
    """Extract document-level metadata from the PDF.

    Returns
    -------
    dict — title, author, subject, creator, creation_date,
           page_count, file_size_bytes
    """
    import pdfplumber

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    with pdfplumber.open(pdf_path) as pdf:
        meta = pdf.metadata or {}
        return {
            "title": meta.get("Title", ""),
            "author": meta.get("Author", ""),
            "subject": meta.get("Subject", ""),
            "creator": meta.get("Creator", ""),
            "creation_date": str(meta.get("CreationDate", "")),
            "page_count": len(pdf.pages),
            "file_size_bytes": pdf_path.stat().st_size,
        }
