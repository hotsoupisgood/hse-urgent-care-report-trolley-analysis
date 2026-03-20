#!/usr/bin/env python3
"""
Compare hospital names between the scraped HSE facility list (hospital_names.csv)
and the TrolleyGAR site. Uses multiple validation steps to produce a final mapping.

Validation strategy:
  1. Scrape live TrolleyGAR names and cross-check against config.py HOSPITAL_TO_REGION
  2. Expand abbreviations (MRH, UH, CHI) and strip suffixes (Emergency Department, etc.)
  3. Try exact match on normalised+stripped forms, then substring containment
  4. Fall back to SequenceMatcher, but require shared location word to avoid false positives
  5. Separate results into: confirmed matches, TrolleyGAR-only, CSV-only
"""

import csv
import os
import re
import sys
import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher

CSV_PATH = os.path.join(os.path.dirname(__file__), "hospital_names.csv")
TROLLEYGAR_URL = "https://uec.hse.ie/uec/TGAR.php"

# Add parent dir so we can import config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "daily_ingestion"))
from config import HOSPITAL_TO_REGION

# Abbreviation expansions used on TrolleyGAR
ABBREVIATIONS = {
    "mrh": "midland regional hospital",
    "uh": "university hospital",
    "chi": "childrens health ireland",
}

# Suffixes the CSV appends that TrolleyGAR omits
SUFFIXES = [
    "emergency department",
    "early pregnancy assessment unit",
    "maternity emergency service",
    "maternity emergency",
    "injury unit",
    "rapid injury clinic",
]

# Generic words to ignore when extracting location identifiers
GENERIC = {
    "hospital", "university", "general", "regional", "county",
    "emergency", "department", "injury", "unit", "maternity",
    "service", "early", "pregnancy", "assessment", "midland",
    "national", "infirmary", "childrens", "health", "ireland",
    "orthopaedic", "radiation", "oncology", "network", "rapid",
    "clinic", "care", "primary", "centre", "the", "at", "in",
    "of", "and", "a", "st", "our", "ladys", "lady",
    "mater", "misericordiae", "south", "west", "north", "east",
    "mid",
}


def load_csv_hospitals():
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        return [row["facility_name"] for row in csv.DictReader(f)]


def scrape_trolleygar_hospitals():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    resp = requests.get(TROLLEYGAR_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    table = soup.find("table")
    if not table:
        raise RuntimeError("No table found on TrolleyGAR page")

    hospitals = []
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) != 14:
            continue
        name_cell = cells[1]
        if int(name_cell.get("colspan", 1)) < 8:
            continue
        name = name_cell.get_text(strip=True)
        if name:
            hospitals.append(name)
    return hospitals


# --- text helpers ---

def normalise(name):
    """Lowercase, remove apostrophes/dots, collapse whitespace."""
    name = name.lower()
    name = re.sub(r"[''.]", "", name)
    return " ".join(name.split())


def expand(name):
    """Normalise + expand known abbreviations."""
    n = normalise(name)
    for abbr, full in ABBREVIATIONS.items():
        n = re.sub(rf"\b{abbr}\b", full, n)
    return n


def strip(name):
    """Normalise + remove facility-type suffixes."""
    n = normalise(name)
    for suffix in SUFFIXES:
        if n.endswith(suffix):
            n = n[: -len(suffix)].strip()
    return n


def location_words(name):
    """Extract identifying location words (not generic hospital terms)."""
    words = set(expand(name).split())
    return {w for w in words if w not in GENERIC and len(w) > 2}


# --- matching ---

def match_score(tgar, csv_name):
    """
    Score how well a TrolleyGAR name matches a CSV name.
    Returns (score, method) where method explains why.
    """
    nt, nc = normalise(tgar), normalise(csv_name)

    # 1) Exact after normalisation
    if nt == nc:
        return 1.0, "exact"

    # 2) One is substring of the other
    if nt in nc or nc in nt:
        return 0.95, "substring"

    # 3) Expand abbreviations, then substring
    et, ec = expand(tgar), expand(csv_name)
    if et in ec or ec in et:
        return 0.93, "expanded-substring"

    # 4) Strip suffixes from both, compare
    st, sc = strip(tgar), strip(csv_name)
    est, esc = expand(st), expand(sc)
    if est == esc:
        return 0.90, "stripped-exact"
    if est in esc or esc in est:
        return 0.88, "stripped-substring"

    # 5) Sequence similarity on stripped+expanded, but require location overlap
    loc_t = location_words(tgar)
    loc_c = location_words(csv_name)
    seq = SequenceMatcher(None, est, esc).ratio()

    if loc_t and loc_c and not (loc_t & loc_c):
        # No shared location word — almost certainly different hospitals
        return seq * 0.2, "no-location-overlap"

    return seq, "sequence"


def find_best_csv_match(tgar_name, csv_names):
    """Return (csv_name, score, method) or (None, best_score, method)."""
    best, best_score, best_method = None, 0.0, ""
    for csv_name in csv_names:
        score, method = match_score(tgar_name, csv_name)
        if score > best_score:
            best, best_score, best_method = csv_name, score, method
    return best, best_score, best_method


def main():
    csv_hospitals = load_csv_hospitals()
    tgar_hospitals = scrape_trolleygar_hospitals()
    config_hospitals = set(HOSPITAL_TO_REGION.keys())

    # ── Step 1: Validate live scrape against config.py ──────────────────
    print("=" * 70)
    print("STEP 1: Cross-check live TrolleyGAR vs config.py HOSPITAL_TO_REGION")
    print("=" * 70)

    tgar_set = set(tgar_hospitals)
    in_both = config_hospitals & tgar_set
    only_config = config_hospitals - tgar_set
    only_live = tgar_set - config_hospitals

    print(f"  config.py hospitals:  {len(config_hospitals)}")
    print(f"  Live TrolleyGAR:      {len(tgar_hospitals)}")
    print(f"  Match:                {len(in_both)}")
    if only_config:
        print(f"  Only in config.py ({len(only_config)}):")
        for h in sorted(only_config):
            print(f"    - {h}")
    if only_live:
        print(f"  Only on live site ({len(only_live)}):")
        for h in sorted(only_live):
            print(f"    - {h}")
    if not only_config and not only_live:
        print("  config.py and live site are in sync")

    # ── Step 2: Match TrolleyGAR names against CSV ─────────────────────
    print()
    print("=" * 70)
    print("STEP 2: Fuzzy-match TrolleyGAR names to CSV facility list")
    print("=" * 70)

    THRESHOLD = 0.80
    matched = []       # (tgar, csv, score, method)
    unmatched = []     # (tgar, best_score, method)
    used_csv = set()

    for tgar in sorted(tgar_hospitals):
        csv_name, score, method = find_best_csv_match(tgar, csv_hospitals)
        if score >= THRESHOLD and csv_name not in used_csv:
            matched.append((tgar, csv_name, score, method))
            used_csv.add(csv_name)
        else:
            unmatched.append((tgar, score, method))

    print(f"\n  Matched:   {len(matched)}/{len(tgar_hospitals)}")
    print(f"  Unmatched: {len(unmatched)}/{len(tgar_hospitals)}")

    for tgar, csv_name, score, method in matched:
        print(f"\n  TGAR:  {tgar}")
        print(f"  CSV:   {csv_name}")
        print(f"         [{score:.0%} via {method}]")

    # ── Step 3: Validate matches with location-word check ──────────────
    print()
    print("=" * 70)
    print("STEP 3: Validate — do matched pairs share a location word?")
    print("=" * 70)

    confirmed = []
    suspect = []

    for tgar, csv_name, score, method in matched:
        lt = location_words(tgar)
        lc = location_words(csv_name)
        shared = lt & lc
        if shared or method in ("exact", "substring", "expanded-substring"):
            confirmed.append((tgar, csv_name, score, method, shared))
        else:
            suspect.append((tgar, csv_name, score, method, lt, lc))

    if suspect:
        print(f"\n  SUSPECT ({len(suspect)}) — matched on score but no shared location:")
        for tgar, csv_name, score, method, lt, lc in suspect:
            print(f"    TGAR: {tgar}  (locations: {lt or '{}'})")
            print(f"    CSV:  {csv_name}  (locations: {lc or '{}'})")
            print()
        # Move suspects to unmatched
        for tgar, csv_name, score, method, lt, lc in suspect:
            unmatched.append((tgar, score, method))
            used_csv.discard(csv_name)
    else:
        print("  All matches share a location word — no suspects.")

    print(f"\n  Confirmed: {len(confirmed)}")

    # ── Step 4: Final mapping ──────────────────────────────────────────
    print()
    print("=" * 70)
    print("STEP 4: Final results")
    print("=" * 70)

    tgar_only = sorted(set(t for t, _, _ in unmatched))
    csv_only = sorted(set(h for h in csv_hospitals if h not in used_csv))

    print(f"\n  OVERLAP ({len(confirmed)} hospitals on both lists):")
    print("  " + "-" * 66)
    for tgar, csv_name, score, method, shared in confirmed:
        if tgar == csv_name:
            print(f"    {tgar}")
        else:
            print(f"    {tgar}")
            print(f"      = {csv_name}")

    print(f"\n  TROLLEYGAR ONLY ({len(tgar_only)} — not in CSV):")
    print("  " + "-" * 66)
    for h in tgar_only:
        print(f"    {h}")

    print(f"\n  CSV ONLY ({len(csv_only)} — not on TrolleyGAR):")
    print("  " + "-" * 66)
    for h in csv_only:
        print(f"    {h}")

    print(f"\n  SUMMARY:")
    print(f"    {len(confirmed)} confirmed overlap")
    print(f"    {len(tgar_only)} TrolleyGAR-only (no CSV equivalent)")
    print(f"    {len(csv_only)} CSV-only (not on TrolleyGAR)")


if __name__ == "__main__":
    main()
