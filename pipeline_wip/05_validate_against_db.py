#!/usr/bin/env python3
"""Step 05 - Check this pipeline against the dashboard's PostgreSQL export.

The live dashboard ingests the same reports through a separate code path. This
compares total_trolleys week-by-week, for steps 03 and 04, against its exports
(data/raw data/weekly_by_*). Only overlapping weeks are compared.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).parent / "output"
RAW = ROOT / "data" / "raw data"

HOSP_MINE = OUT / "03_weekly_by_hospital.csv"
HOSP_DB = RAW / "weekly_by_hospital_202604090859.csv"
REGION_MINE = OUT / "04_weekly_by_region.csv"
REGION_DB = RAW / "weekly_by_region_202604082051.csv"


def compare(mine_path, db_path, keys, label):
    mine = pd.read_csv(mine_path, parse_dates=["week_start"])
    db = pd.read_csv(db_path, parse_dates=["week_start"])

    mine = mine[[*keys, "total_trolleys"]].rename(columns={"total_trolleys": "mine"})
    db = db[[*keys, "total_trolleys"]].rename(columns={"total_trolleys": "db"})

    merged = mine.merge(db, on=keys, how="outer", indicator=True)
    both = merged[merged["_merge"] == "both"].copy()
    both["diff"] = both["mine"] - both["db"]
    mism = both[both["diff"] != 0].sort_values("week_start")

    print(f"\n=== {label} ===")
    print(f"  rows only in this pipeline : {(merged['_merge'] == 'left_only').sum()}")
    print(f"  rows only in DB export     : {(merged['_merge'] == 'right_only').sum()}")
    print(f"  rows compared (both)       : {len(both)}")
    print(f"  exact matches              : {int((both['diff'] == 0).sum())}")
    print(f"  mismatches                 : {len(mism)}")
    if len(mism):
        print("  mismatch detail:")
        print(mism.to_string(index=False))


compare(REGION_MINE, REGION_DB, ["region", "week_start"], "WEEKLY BY REGION (total_trolleys)")
compare(HOSP_MINE, HOSP_DB, ["hospital", "week_start"], "WEEKLY BY HOSPITAL (total_trolleys)")
