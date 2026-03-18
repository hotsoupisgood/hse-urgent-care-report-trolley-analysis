"""
Tests for the cleaning logic applied during scraping.
Verifies that totals rows are removed, hospitals map to regions,
and column names are standardised.
"""

import numpy as np
import pandas as pd

from config import HOSPITAL_TO_REGION, REGION_POPULATIONS
from scraper import DATA_POSITIONS


# ── Totals filtering ─────────────────────────────────────────────

def test_total_rows_removed(raw_html_df):
    """Rows ending in ' Total' must be stripped out."""
    hospital_col = raw_html_df.columns[0]
    filtered = raw_html_df[~raw_html_df[hospital_col].astype(str).str.endswith(' Total')]

    totals_remaining = filtered[hospital_col].astype(str).str.endswith(' Total').sum()
    assert totals_remaining == 0, f"Found {totals_remaining} total rows still present"


def test_total_rows_count(raw_html_df):
    """raw_html_df fixture should have exactly 3 regional totals + 1 national total."""
    hospital_col = raw_html_df.columns[0]
    total_rows = raw_html_df[hospital_col].astype(str).str.endswith(' Total').sum()
    assert total_rows == 4


def test_no_totals_in_cleaned(cleaned_df):
    """Cleaned output should never contain total rows."""
    assert not cleaned_df['Hospital'].str.endswith(' Total').any()


# ── Hospital-to-region mapping ────────────────────────────────────

def test_all_cleaned_hospitals_have_region(cleaned_df):
    """Every hospital in cleaned output must have a non-null region."""
    assert cleaned_df['region'].notna().all(), (
        f"Unmapped hospitals: {cleaned_df[cleaned_df['region'].isna()]['Hospital'].tolist()}"
    )


def test_all_cleaned_hospitals_in_config(cleaned_df):
    """Every hospital in cleaned output must exist in the config mapping."""
    unknown = set(cleaned_df['Hospital']) - set(HOSPITAL_TO_REGION.keys())
    assert unknown == set(), f"Hospitals not in config: {unknown}"


def test_region_mapping_covers_all_regions():
    """Every region in REGION_POPULATIONS should have at least one hospital."""
    mapped_regions = set(HOSPITAL_TO_REGION.values())
    pop_regions = set(REGION_POPULATIONS.keys())
    missing = pop_regions - mapped_regions
    assert missing == set(), f"Regions with population but no hospitals: {missing}"


def test_no_duplicate_hospitals_per_day(cleaned_df):
    """Each hospital should appear at most once per report_date."""
    dupes = cleaned_df.groupby(['Hospital', 'report_date']).size()
    dupes = dupes[dupes > 1]
    assert dupes.empty, f"Duplicate hospital-date pairs:\n{dupes}"


# ── Column standardisation ────────────────────────────────────────

def test_cleaned_columns_are_lowercase(cleaned_df):
    """Data columns in cleaned output should be lowercase/snake_case."""
    data_cols = [c for c in cleaned_df.columns if c not in ('Hospital', 'report_date', 'region')]
    for col in data_cols:
        assert col == col.lower(), f"Column '{col}' is not lowercase"


def test_data_columns_present(cleaned_df):
    """All DATA_POSITIONS column names should be present in cleaned output."""
    expected = set(DATA_POSITIONS.keys())
    actual = set(cleaned_df.columns)
    missing = expected - actual
    assert missing == set(), f"Missing columns after cleaning: {missing}"
