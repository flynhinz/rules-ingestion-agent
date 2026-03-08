"""
patch_ontology_db.py
====================
Normalises all ontology_terms rows in Supabase:
  - codes: SCREAMING_SNAKE_CASE
  - categories: lowercase-kebab (no spaces, no capitals)
  - removes leading/trailing whitespace from name/description

Run once:  python scripts/patch_ontology_db.py
"""
import json
import os
import urllib.request
import urllib.error

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://ucteqdaqsintywfjwcoh.supabase.co")
ANON_KEY = os.environ.get(
    "SUPABASE_ANON_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVjdGVxZGFxc2ludHl3Zmp3Y29oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk3MTg1MjksImV4cCI6MjA4NTI5NDUyOX0.zDJgpZfmOr1MQ7uaODRB9C7pI_p8pf2XlK9mPqQtGy4",
)

HEADERS = {
    "apikey": ANON_KEY,
    "Authorization": f"Bearer {ANON_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

# Category normalisation map
CATEGORY_MAP = {
    "Crew": "crew",
    "crew": "crew",
    "Time Tracking": "time-tracking",
    "time tracking": "time-tracking",
    "rest": "rest",
    "duty": "duty",
    "fatigue": "fatigue",
    "leave": "leave",
    "general": "general",
    "flight": "flight",
    "": "general",
}


def normalise_code(raw: str) -> str:
    return raw.strip().upper().replace(" ", "_").replace("-", "_").strip("_")


def normalise_category(raw: str) -> str:
    raw = (raw or "").strip()
    if raw in CATEGORY_MAP:
        return CATEGORY_MAP[raw]
    # Generic: lowercase, spaces to hyphens
    return raw.lower().replace(" ", "-") or "general"


def fetch_all() -> list:
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/ontology_terms?select=id,code,name,category,description,definition_text&order=category,name"
    req = urllib.request.Request(url, headers={**HEADERS, "Prefer": ""})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.load(resp)


def patch_row(row_id: str, payload: dict):
    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/ontology_terms?id=eq.{row_id}"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, method="PATCH", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.status


def main():
    print("Fetching ontology_terms from DB...")
    rows = fetch_all()
    print(f"  Found {len(rows)} rows.")

    patched = 0
    skipped = 0

    for row in rows:
        row_id = row["id"]
        orig_code = row.get("code") or ""
        orig_cat = row.get("category") or ""
        orig_name = (row.get("name") or "").strip()

        norm_code = normalise_code(orig_code)
        norm_cat = normalise_category(orig_cat)

        updates = {}
        if norm_code != orig_code:
            updates["code"] = norm_code
        if norm_cat != orig_cat:
            updates["category"] = norm_cat
        if orig_name != (row.get("name") or ""):
            updates["name"] = orig_name

        if not updates:
            skipped += 1
            continue

        print(f"  Patching [{row_id[:8]}] code={orig_code!r}->{norm_code!r}  cat={orig_cat!r}->{norm_cat!r}")
        try:
            status = patch_row(row_id, updates)
            print(f"    -> HTTP {status}")
            patched += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"    ERROR {e.code}: {body}")
        except Exception as ex:
            print(f"    ERROR: {ex}")

    print(f"\nDone. {patched} rows patched, {skipped} already clean.")


if __name__ == "__main__":
    main()
