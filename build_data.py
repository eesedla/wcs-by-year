#!/usr/bin/env python3
"""
Regenerate the `DATA` array in index.html from the WCS violations CSV.

Each dated WCS case is classified into one or more of five sub-categories by
matching phrases in "Charge & Discipline Decision" (the narrative field) —
a case can land in more than one category (e.g. failed to activate AND failed
to upload), same dedup-per-case logic as the other CPD charts:

  activate   failed to place/keep in event mode, failed to activate,
             deactivated, WCS not carried on person, turned WCS off
  maintain   returned to / failed to keep in buffering mode
  upload     failed to upload/tag footage, ETM slot, dash camera video
  safeguard  "Failed to Safeguard Equipment" charge tag, or lost/damaged
             equipment language
  generic    none of the above matched — WCS Violation charge with no
             specific reason given in the narrative

CASE_OVERRIDES below hand-corrects individual case IDs where the automated
read of the narrative doesn't match the intended category — add to it as
cases get manually reviewed (see "Link to original report" per case).

KNOWN GAPS (as of this script's creation): the automated classifier under-
counts "safeguard" in most years relative to the hand-built chart it
replaced — e.g. 2022 has only 3 cases with textual safeguard/damage signal
in this CSV's narrative fields, but the original chart showed 9. That
signal likely lived in the original hearing PDFs (see "Link to original
report"), not in this CSV. Needs manual review; not yet resolved.

Setup:
  - Put the WCS CSV next to this file (or edit CSV_PATH).

Run:
  python3 build_data.py
"""

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

HERE       = Path(__file__).parent
INDEX_HTML = HERE / "index.html"
CSV_PATH   = HERE / "Divisional Notice Discipline Cases-Body Camera Violations.csv"

CATS = ["activate", "maintain", "upload", "safeguard", "generic"]

# case ID -> explicit set of categories, overriding the text classifier.
# Populate as ambiguous/irresolvable cases get manually reviewed.
CASE_OVERRIDES = {}

ID_PAT = re.compile(r"^\s*(\d{2})-\d+")

def year_of(row):
    """Year for a case: Hearing Date, else Effective date of termination,
    else the YY- prefix of the report ID (e.g. 17-126 -> 2017)."""
    for col in ("Hearing Date", "Effective date of termination"):
        m = re.search(r"(20\d\d)", (row.get(col) or "").strip())
        if m:
            return int(m.group(1))
    p = ID_PAT.match(row.get("Link to original report") or "")
    return 2000 + int(p.group(1)) if p else None

def classify(row):
    case_id = row.get("ID")
    if case_id in CASE_OVERRIDES:
        return set(CASE_OVERRIDES[case_id])

    txt = row.get("Charge & Discipline Decision") or ""
    charges = [c.strip().lower() for c in (row.get("Charges") or "").split(",") if c.strip()]
    low = re.sub(r"\s+", " ", txt.lower())  # collapse embedded newlines/double-spaces

    cats = set()
    if re.search(
        r"(failed to (place|keep)|instructed .*(turn off|deactivat)).{0,80}?event mode"
        r"|failed to activate|reactivat|de-?activat|failed to wear (and activate)?"
        r"|removed wcs|(on (his|her|their) person)"
        r"|turn(ed)? .{0,40}off|turned? off.{0,40}wcs", low):
        cats.add("activate")
    if re.search(r"buffering", low):
        cats.add("maintain")
    if re.search(r"upload|tag footage|enter (all )?(captured )?video|dash camera|etm slot|evidence transfer manager", low):
        cats.add("upload")
    if "failed to safeguard equipment" in charges or re.search(
        r"safeguard|lost or damaged|damaged (the )?(wcs|equipment|camera)", low):
        cats.add("safeguard")
    if not cats:
        cats.add("generic")
    return cats

YEAR_MIN, YEAR_MAX = 2017, 2025

year_counts = defaultdict(lambda: defaultdict(int))
year_total  = defaultdict(int)

with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        year = year_of(row)
        if year is None or not (YEAR_MIN <= year <= YEAR_MAX):
            continue
        year_total[year] += 1
        for cat in classify(row):
            year_counts[year][cat] += 1

years_out = []
for y in sorted(year_total):
    entry = {"year": y, "total": year_total[y]}
    entry.update({c: year_counts[y][c] for c in CATS})
    years_out.append(entry)

# ── Write back into index.html ───────────────────────────────────────────────

raw = INDEX_HTML.read_text(encoding="utf-8")
entries = ",\n".join(
    "  { year: %d, total: %d, activate: %d, maintain: %d, upload: %d, safeguard: %d, generic: %d }"
    % (d["year"], d["total"], d["activate"], d["maintain"], d["upload"], d["safeguard"], d["generic"])
    for d in years_out
)
data_js = f"const DATA = [\n{entries},\n];"

new_raw, n = re.subn(r"const DATA = \[.*?\];", data_js, raw, count=1, flags=re.DOTALL)
if n == 0:
    raise RuntimeError("Could not find 'const DATA = [...];' in index.html")
INDEX_HTML.write_text(new_raw, encoding="utf-8")

total = sum(year_total.values())
print(f"Updated {INDEX_HTML.name} — {total} dated WCS cases across {len(years_out)} years.")
for d in years_out:
    print(f"  {d['year']}: total={d['total']}  activate={d['activate']} maintain={d['maintain']} "
          f"upload={d['upload']} safeguard={d['safeguard']} generic={d['generic']}")
