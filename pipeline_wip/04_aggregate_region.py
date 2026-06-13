#!/usr/bin/env python3
"""Step 04 - Sum weekly per-hospital totals into weekly per-region totals.

Uses one fixed hospital -> region map for the whole series. The report regrouped
hospitals over time (3 regions in 2023, 6 from 2024), but the analysis applies the
current 6-region structure to every week. All 42 hospitals map to one region.

In:  output/03_weekly_by_hospital.csv
Out: output/04_weekly_by_region.csv
"""

from pathlib import Path
import pandas as pd

# --- Configuration (hardcoded, edit here) ----------------------------------
INPUT_CSV = Path(__file__).parent / "output" / "03_weekly_by_hospital.csv"
OUTPUT_CSV = Path(__file__).parent / "output" / "04_weekly_by_region.csv"

COUNT_COLUMNS = ["ed_trolleys", "ward_trolleys", "total_trolleys"]

REGION_ORDER = [
    "HSE Dublin and Midlands",
    "HSE Dublin and North East",
    "HSE Dublin and South East",
    "HSE Mid West",
    "HSE South West",
    "HSE West and North West",
]

# Fixed hospital -> region map (42 hospitals).
# Validated 2026-06 against the current (2024) HSE 6-region structure, via the
# official HSE region listing endpoint:
#   https://www2.hse.ie/services/hospitals/health-regions/?health_region=HSE%20<Region>
# All 42 assignments confirmed. Note the report's hospital strings differ from the
# HSE's official strings (e.g. "MRH Mullingar" = "Regional Hospital Mullingar",
# "Cavan General Hospital" = "Cavan Monaghan General Hospital"); the report names
# are used here since that is what the scrape produces.
HOSPITAL_REGION = {
    "Bantry General Hospital": "HSE South West",
    "Beaumont Hospital": "HSE Dublin and North East",
    "CHI at Crumlin": "HSE Dublin and Midlands",
    "CHI at Tallaght": "HSE Dublin and Midlands",
    "CHI at Temple Street": "HSE Dublin and Midlands",
    "Cavan General Hospital": "HSE Dublin and North East",
    "Connolly Hospital": "HSE Dublin and North East",
    "Cork University Hospital": "HSE South West",
    "Ennis Hospital": "HSE Mid West",
    "Galway University Hospital": "HSE West and North West",
    "Letterkenny University Hospital": "HSE West and North West",
    "Louth County Hospital": "HSE Dublin and North East",
    "MRH Mullingar": "HSE Dublin and Midlands",
    "MRH Portlaoise": "HSE Dublin and Midlands",
    "MRH Tullamore": "HSE Dublin and Midlands",
    "Mallow General Hospital": "HSE South West",
    "Mater Misericordiae University Hospital": "HSE Dublin and North East",
    "Mayo University Hospital": "HSE West and North West",
    "Mercy University Hospital": "HSE South West",
    "Naas General Hospital": "HSE Dublin and Midlands",
    "National Orthopaedic Hospital Cappagh": "HSE Dublin and North East",
    "National Rehabilitation Hospital": "HSE Dublin and South East",
    "Nenagh Hospital": "HSE Mid West",
    "Our Lady of Lourdes Hospital": "HSE Dublin and North East",
    "Our Lady's Hospital Navan": "HSE Dublin and North East",
    "Portiuncula University Hospital": "HSE West and North West",
    "Roscommon University Hospital": "HSE West and North West",
    "Sligo University Hospital": "HSE West and North West",
    "South Infirmary Victoria University Hospital": "HSE South West",
    "St Luke's General Hospital Kilkenny": "HSE Dublin and South East",
    "St. Columcille's Hospital": "HSE Dublin and South East",
    "St. James's Hospital": "HSE Dublin and Midlands",
    "St. John's Hospital Limerick": "HSE Mid West",
    "St. Luke's Radiation Oncology Network": "HSE Dublin and Midlands",
    "St. Michael's Hospital": "HSE Dublin and South East",
    "St. Vincent's University Hospital": "HSE Dublin and South East",
    "Tallaght University Hospital": "HSE Dublin and Midlands",
    "Tipperary University Hospital": "HSE Dublin and South East",
    "UH Kerry": "HSE South West",
    "UH Limerick": "HSE Mid West",
    "UH Waterford": "HSE Dublin and South East",
    "Wexford General Hospital": "HSE Dublin and South East",
}

# --- Load ------------------------------------------------------------------
weekly = pd.read_csv(INPUT_CSV, parse_dates=["week_start"])

# Map every hospital to its region. Fails loud if an unmapped hospital appears.
weekly["region"] = weekly["hospital"].map(HOSPITAL_REGION)
unmapped = sorted(weekly.loc[weekly["region"].isna(), "hospital"].unique())
assert not unmapped, f"hospitals missing from HOSPITAL_REGION: {unmapped}"

# --- Aggregate -------------------------------------------------------------
region = (
    weekly.groupby(["region", "week_start"])
    .agg(
        ed_trolleys=("ed_trolleys", "sum"),
        ward_trolleys=("ward_trolleys", "sum"),
        total_trolleys=("total_trolleys", "sum"),
        days_in_week=("days_in_week", "max"),
    )
    .reset_index()
)

region["region"] = pd.Categorical(region["region"], categories=REGION_ORDER, ordered=True)
region = region[["week_start", "region", *COUNT_COLUMNS, "days_in_week"]]
region = region.sort_values(["week_start", "region"]).reset_index(drop=True)

# --- Save ------------------------------------------------------------------
region.to_csv(OUTPUT_CSV, index=False)
print(f"Written: {OUTPUT_CSV}")
print(f"Shape: {region.shape}  (region-weeks x columns)")
print(f"Regions: {region['region'].nunique()}   Weeks: {region['week_start'].nunique()}")
