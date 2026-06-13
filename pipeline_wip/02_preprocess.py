#!/usr/bin/env python3
"""Step 02 - Clean the raw scrape into tidy numeric daily counts.

Drops the report's '<Region> Total' / 'National Total' summary rows, reads blank
cells as 0, and takes abs() of the counts. The raw data has negative trolley
counts (impossible; data-entry artifacts, see negatives_report.ipynb), so abs()
recovers the magnitude. Total is the reported total, not recomputed from ED+Ward.

In:  output/01_daily_by_hospital_raw.csv
Out: output/02_daily_by_hospital_clean.csv  (date, hospital, ed/ward/total_trolleys)
"""

from pathlib import Path
import pandas as pd

# --- Configuration (hardcoded, edit here) ----------------------------------
INPUT_CSV = Path(__file__).parent / "output" / "01_daily_by_hospital_raw.csv"
OUTPUT_CSV = Path(__file__).parent / "output" / "02_daily_by_hospital_clean.csv"

# Raw report column -> tidy column name. Only the trolley counts are carried
# forward; the other report metrics are not used by the analysis.
COUNT_COLUMNS = {
    "ED Trolleys": "ed_trolleys",
    "Ward Trolleys": "ward_trolleys",
    "Total": "total_trolleys",
}

# --- Load ------------------------------------------------------------------
raw = pd.read_csv(INPUT_CSV, dtype=str)

# drop the report's own '<Region> Total' / 'National Total' rows
clean = raw[~raw["Hospital"].str.endswith("Total")].copy()
clean["date"] = pd.to_datetime(clean["Date"], format="%d/%m/%Y")  # DD/MM/YYYY

tidy = pd.DataFrame({"date": clean["date"], "hospital": clean["Hospital"]})
for raw_col, tidy_col in COUNT_COLUMNS.items():
    counts = pd.to_numeric(clean[raw_col], errors="coerce").fillna(0)  # blank = 0
    tidy[tidy_col] = counts.abs().astype(int)                          # abs: see docstring

tidy = tidy.sort_values(["date", "hospital"]).reset_index(drop=True)

# --- Save ------------------------------------------------------------------
tidy.to_csv(OUTPUT_CSV, index=False)
print(f"Written: {OUTPUT_CSV}")
print(f"Shape: {tidy.shape}  (hospital-days x columns)")
print(f"Hospitals: {tidy['hospital'].nunique()}   "
      f"Dates: {tidy['date'].nunique()}  "
      f"({tidy['date'].min().date()} -> {tidy['date'].max().date()})")
