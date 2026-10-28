"""Push LDRankings_top500.csv into the DebateDrills LD Rankings collection.

From this directory:

    export WEBFLOW_API_TOKEN="the DebateDrills site token"
    python push_webflow.py

Fill COLLECTION_ID and FIELD_SLUGS before the first run. An empty value stops
the script before any Webflow item is deleted.

The token needs cms:read and cms:write on DebateDrills Main Site.
CMS → LD Rankings → Settings (gear) → Collection ID.
On each field, the slug is the API name, not the label on screen.
The CSV Name column is written to Webflow's built-in Name field.
"""

import csv
import os
import sys
from pathlib import Path

SEASON_DIR = Path(__file__).resolve().parents[1]
if str(SEASON_DIR) not in sys.path:
    sys.path.insert(0, str(SEASON_DIR))

from webflow_config import item_slug, replace_collection

CSV_PATH = Path(__file__).with_name("LDRankings_top500.csv")

# DebateDrills Main Site → CMS → LD Rankings → Settings → Collection ID.
COLLECTION_ID = "64cae4259ff94cbabafc5890"

# Field slugs. "" skips that column. Name uses Webflow's built-in Name field.
FIELD_SLUGS = {
    "rank": "rank",
    "school": "school",
    "elo": "elo",
}


def _require_config():
    missing = []
    if not COLLECTION_ID.strip():
        missing.append("COLLECTION_ID for the LD Rankings collection")
    for column, slug in FIELD_SLUGS.items():
        if not str(slug).strip():
            missing.append(f"FIELD_SLUGS[{column!r}]")
    if not os.environ.get("WEBFLOW_API_TOKEN", "").strip():
        missing.append("WEBFLOW_API_TOKEN (DebateDrills site token with cms:read and cms:write)")
    if missing:
        print("Set these before pushing. Nothing was deleted.")
        for item in missing:
            print(f"  - {item}")
        sys.exit(1)


def _rows():
    with CSV_PATH.open(newline="") as handle:
        reader = csv.DictReader(handle)
        parsed = []
        for row in reader:
            name = " ".join((row.get("Name") or "").split())[:256] or "Entry"
            rank = int(row["Rank"])
            fields = {}
            if FIELD_SLUGS["rank"]:
                fields[FIELD_SLUGS["rank"]] = rank
            if FIELD_SLUGS["school"]:
                fields[FIELD_SLUGS["school"]] = " ".join((row.get("School") or "").split())
            if FIELD_SLUGS["elo"]:
                fields[FIELD_SLUGS["elo"]] = float(row["Elo"])
            parsed.append({"name": name, "slug": item_slug(name, rank), "fields": fields})
            if len(parsed) == 500:
                break
    if not parsed:
        sys.exit(f"No rows in {CSV_PATH.name}")
    return parsed


def main():
    _require_config()
    rows = _rows()
    print(f"Updating LD Rankings from {CSV_PATH.name}: {len(rows)} rows.", flush=True)
    result = replace_collection(
        os.environ["WEBFLOW_API_TOKEN"].strip(),
        COLLECTION_ID.strip(),
        rows,
    )
    print(
        f"LD rankings published: deleted {result['removed']} existing items, "
        f"then created {result['created']}."
    )


if __name__ == "__main__":
    main()
