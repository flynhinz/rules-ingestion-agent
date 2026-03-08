"""
main.py
=======
Regulus — Rules Ingestion Agent pipeline runner.

Usage:
    python main.py --pdf input/your_document.pdf

Outputs (written to output/):
    <stem>.json           — schema-validated JSON (CrewRules Ingestion Payload v1)
    <stem>_ambiguity.json — standalone ambiguity log
    <stem>_rules.py       — Python dict representation of each rule (paste into tests)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="regulus",
        description="Regulus — convert a PDF rule document into a CrewRules-compliant JSON payload.",
    )
    p.add_argument("--pdf", required=True, type=Path, help="Input PDF path.")
    p.add_argument("--schema", default="schema.json", type=Path, help="JSON schema path (default: schema.json).")
    p.add_argument("--out", default="output", type=Path, help="Output directory (default: output/).")
    p.add_argument("--top-k", default=5, type=int, help="Max ontology term suggestions per rule (default: 5).")
    return p


def run_pipeline(pdf_path: Path, schema_path: Path, out_dir: Path, top_k: int = 5) -> dict:
    """Execute the full Regulus ingestion pipeline."""
    from agent import pdf_reader, parser, ontology, json_builder

    print(f"[1/5] Reading PDF: {pdf_path.name}")
    pages = pdf_reader.load_pdf(pdf_path)
    doc_meta = pdf_reader.extract_metadata(pdf_path)

    print(f"[2/5] Parsing document ({len(pages)} pages)...")
    parsed_doc = parser.parse_document(pages, source_file=pdf_path.name, doc_metadata=doc_meta)
    rules = parsed_doc.all_rules
    print(f"      Found {len(parsed_doc.sections)} sections, {len(rules)} rules.")

    print(f"[3/5] Loading ontology and matching terms...")
    onto = ontology.load_ontology()
    all_suggestions = [
        ontology.suggest_terms(rule.raw_text, onto, top_k=top_k)
        for rule in rules
    ]

    print(f"[4/5] Building schema-compliant JSON...")
    schema = json_builder.load_schema(schema_path)
    output = json_builder.build_output(parsed_doc, all_suggestions)

    is_valid, errors = json_builder.validate_output(output, schema)
    if not is_valid:
        print(f"[WARN] Schema validation errors ({len(errors)}):")
        for err in errors:
            print(f"       {err}")
    else:
        print(f"      Validation passed.")

    print(f"[5/5] Writing output...")
    stem = pdf_path.stem
    out_path = json_builder.write_output(output, out_dir / f"{stem}.json")
    print(f"      Written: {out_path}")

    # Write standalone ambiguity log
    ambiguity_log = output.get("ambiguityLog", [])
    if ambiguity_log:
        amb_path = json_builder.write_output(
            {"ambiguityLog": ambiguity_log},
            out_dir / f"{stem}_ambiguity.json",
        )
        print(f"      Ambiguity log: {amb_path} ({len(ambiguity_log)} entries)")

    # Write Python representation
    py_path = json_builder.write_python_repr(output, out_dir / f"{stem}_rules.py")
    print(f"      Python repr:  {py_path}")

    return output


def main() -> None:
    args = build_arg_parser().parse_args()

    if not args.pdf.exists():
        print(f"ERROR: PDF not found: {args.pdf}", file=sys.stderr)
        sys.exit(1)

    args.out.mkdir(parents=True, exist_ok=True)

    result = run_pipeline(args.pdf, args.schema, args.out, args.top_k)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
