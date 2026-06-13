#!/usr/bin/env python3
"""Step 03 - Sum daily counts into Monday-start weekly totals per hospital.

week_start is the Monday of each day's week, e.g. Sun 2023-01-01 -> Mon 2022-12-26.
days_in_week counts how many days that week had a report, so partial weeks show.

In:  output/02_daily_by_hospital_clean.csv
Out: output/03_weekly_by_hospital.csv  (+ week_start, days_in_week)
"""

from pathlib import Path
import pandas as pd

# --- Configuration (hardcoded, edit here) ----------------------------------
INPUT_CSV = Path(__file__).parent / "output" / "02_daily_by_hospital_clean.csv"
OUTPUT_CSV = Path(__file__).parent / "output" / "03_weekly_by_hospital.csv"

COUNT_COLUMNS = ["ed_trolleys", "ward_trolleys", "total_trolleys"]

# --- Load ------------------------------------------------------------------
daily = pd.read_csv(INPUT_CSV, parse_dates=["date"])

# Assign each day to its Monday week_start.
daily["week_start"] = daily["date"] - pd.to_timedelta(daily["date"].dt.weekday, unit="D")

# --- Aggregate -------------------------------------------------------------
weekly = (
    daily.groupby(["hospital", "week_start"])
    .agg(
        ed_trolleys=("ed_trolleys", "sum"),
        ward_trolleys=("ward_trolleys", "sum"),
        total_trolleys=("total_trolleys", "sum"),
        days_in_week=("date", "nunique"),
    )
    .reset_index()
)

weekly = weekly[["week_start", "hospital", *COUNT_COLUMNS, "days_in_week"]]
weekly = weekly.sort_values(["week_start", "hospital"]).reset_index(drop=True)

# --- Save ------------------------------------------------------------------
weekly.to_csv(OUTPUT_CSV, index=False)
print(f"Written: {OUTPUT_CSV}")
print(f"Shape: {weekly.shape}  (hospital-weeks x columns)")
print(f"Weeks: {weekly['week_start'].nunique()}  "
      f"({weekly['week_start'].min().date()} -> {weekly['week_start'].max().date()})")
