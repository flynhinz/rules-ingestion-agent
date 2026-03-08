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
    p.add_argument("--airline", default=None, type=str,
                   help="Airline IATA code (e.g. NZ, QF). Enables airline-specific parsing rules.")
    p.add_argument("--schema", default="schema.json", type=Path, help="JSON schema path (default: schema.json).")
    p.add_argument("--out", default="output", type=Path, help="Output directory (default: output/).")
    p.add_argument("--top-k", default=5, type=int, help="Max ontology term suggestions per rule (default: 5).")
    return p


def run_pipeline(pdf_path: Path, schema_path: Path, out_dir: Path,
                 top_k: int = 5, airline_code: str | None = None) -> dict:
    """Execute the full Regulus ingestion pipeline."""
    import os
    from agent import pdf_reader, parser, ontology, json_builder, airline_config

    # Resolve airline context
    airline_cfg = None
    if airline_code:
        airline_cfg = airline_config.get_airline(airline_code.upper())
        if airline_cfg:
            print(f"      Airline context: {airline_cfg.name} ({airline_cfg.iata_code}) — {airline_cfg.jurisdiction}")
        else:
            print(f"[WARN] Unknown airline IATA code '{airline_code}' — proceeding without airline context.")

    print(f"[1/5] Reading PDF: {pdf_path.name}")
    pages = pdf_reader.load_pdf(pdf_path)
    doc_meta = pdf_reader.extract_metadata(pdf_path)
    if airline_cfg:
        doc_meta.setdefault("airline_iata", airline_cfg.iata_code)
        doc_meta.setdefault("airline_name", airline_cfg.name)
        doc_meta.setdefault("jurisdiction", airline_cfg.jurisdiction)

    print(f"[2/5] Parsing document ({len(pages)} pages)...")
    parsed_doc = parser.parse_document(pages, source_file=pdf_path.name, doc_metadata=doc_meta)
    rules = parsed_doc.all_rules
    print(f"      Found {len(parsed_doc.sections)} sections, {len(rules)} rules, {len(parsed_doc.scenarios)} scenarios.")

    print(f"[3/5] Loading ontology and matching terms...")
    onto = ontology.load_ontology(
        ontology_path=Path(__file__).parent / "ontology_terms.json",
        supabase_url=os.environ.get("SUPABASE_URL", "https://ucteqdaqsintywfjwcoh.supabase.co"),
        anon_key=os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVjdGVxZGFxc2ludHl3Zmp3Y29oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk3MTg1MjksImV4cCI6MjA4NTI5NDUyOX0.zDJgpZfmOr1MQ7uaODRB9C7pI_p8pf2XlK9mPqQtGy4"),
    )
    all_suggestions = [
        ontology.suggest_terms(rule.raw_text, onto, top_k=top_k)
        for rule in rules
    ]

    print(f"[4/5] Building schema-compliant JSON...")
    schema = json_builder.load_schema(schema_path)
    output = json_builder.build_output(parsed_doc, all_suggestions, airline_cfg=airline_cfg)

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

    result = run_pipeline(args.pdf, args.schema, args.out, args.top_k,
                          airline_code=args.airline)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
