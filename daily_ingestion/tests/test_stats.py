"""
Tests for data quality: totals arithmetic, empty/null element counts,
and basic summary statistics.
"""

import numpy as np
import pandas as pd
import pytest

from ingest import parse_int


# ── Totals arithmetic ─────────────────────────────────────────────

def test_total_equals_ed_plus_ward(cleaned_df):
    """Total should equal ED + Ward (NaNs treated as 0)."""
    computed = cleaned_df['ed_trolleys'] + cleaned_df['ward_trolleys']
    mismatches = cleaned_df[computed != cleaned_df['total_trolleys']]
    assert mismatches.empty, (
        f"{len(mismatches)} rows where Total != ED + Ward:\n"
        f"{mismatches[['Hospital', 'ed_trolleys', 'ward_trolleys', 'total_trolleys']]}"
    )


def test_total_gte_ed_trolleys(cleaned_df):
    """Total trolleys should always be >= ED trolleys."""
    violations = cleaned_df[cleaned_df['total_trolleys'] < cleaned_df['ed_trolleys']]
    assert violations.empty, (
        f"{len(violations)} rows where Total < ED:\n"
        f"{violations[['Hospital', 'ed_trolleys', 'total_trolleys']]}"
    )


def test_total_gte_ward_trolleys(cleaned_df):
    """Total trolleys should always be >= Ward trolleys."""
    violations = cleaned_df[cleaned_df['total_trolleys'] < cleaned_df['ward_trolleys']]
    assert violations.empty, (
        f"{len(violations)} rows where Total < Ward:\n"
        f"{violations[['Hospital', 'ward_trolleys', 'total_trolleys']]}"
    )


def test_no_negative_values(cleaned_df):
    """No numeric column should have negative values."""
    numeric_cols = cleaned_df.select_dtypes(include='number').columns
    for col in numeric_cols:
        negatives = cleaned_df[cleaned_df[col] < 0]
        assert negatives.empty, (
            f"Negative values in '{col}':\n"
            f"{negatives[['Hospital', col]]}"
        )


# ── Empty / null element counts ───────────────────────────────────

def test_no_nulls_in_numeric_columns(cleaned_df):
    """All numeric columns should have zero NULLs (NaN treated as 0)."""
    numeric_cols = ['ed_trolleys', 'ward_trolleys', 'total_trolleys',
                    'surge_capacity_in_use', 'delayed_transfers_of_care',
                    'total_waiting_gt_24hrs', 'age_75plus_waiting_gt_24hrs']
    for col in numeric_cols:
        if col in cleaned_df.columns:
            null_count = cleaned_df[col].isna().sum()
            assert null_count == 0, (
                f"Column '{col}' has {null_count} nulls — should be 0"
            )


def test_hospital_column_never_null(cleaned_df):
    """Hospital name should never be null."""
    assert cleaned_df['Hospital'].notna().all()


def test_report_date_never_null(cleaned_df):
    """report_date should never be null."""
    assert cleaned_df['report_date'].notna().all()


def test_zero_counts_by_column(cleaned_df):
    """Report how many zeros per column — informational, always passes."""
    numeric_cols = ['ed_trolleys', 'ward_trolleys', 'total_trolleys',
                    'surge_capacity_in_use', 'delayed_transfers_of_care',
                    'total_waiting_gt_24hrs', 'age_75plus_waiting_gt_24hrs']
    for col in numeric_cols:
        if col in cleaned_df.columns:
            total = len(cleaned_df)
            zeros = (cleaned_df[col] == 0).sum()
            rate = zeros / total * 100
            print(f"  {col}: {zeros}/{total} zeros ({rate:.1f}%)")


# ── Region-level aggregation stats ────────────────────────────────

def test_region_totals_sum_correctly(cleaned_df):
    """Sum of hospital totals per region should equal region total."""
    by_region = cleaned_df.groupby('region')['total_trolleys'].sum()
    grand_total = cleaned_df['total_trolleys'].sum()
    assert by_region.sum() == grand_total, (
        f"Region sums ({by_region.sum()}) != grand total ({grand_total})"
    )


def test_all_six_regions_present_in_full_day():
    """A full day should have all 6 HSE regions represented."""
    from config import HOSPITAL_TO_REGION, REGION_POPULATIONS
    mapped_regions = set(HOSPITAL_TO_REGION.values())
    expected_regions = set(REGION_POPULATIONS.keys())
    assert mapped_regions == expected_regions


def test_multi_day_no_cross_day_leakage(multi_day_df):
    """Each day's data should be independent — dates shouldn't mix."""
    dates = multi_day_df['report_date'].unique()
    assert len(dates) == 2

    for date in dates:
        day = multi_day_df[multi_day_df['report_date'] == date]
        # Each hospital should appear exactly once per day
        dupes = day.groupby('Hospital').size()
        dupes = dupes[dupes > 1]
        assert dupes.empty, f"Duplicates on {date}: {dupes}"


# ── Outlier detection (values significantly different from mean) ──

NUMERIC_COLS = ['ed_trolleys', 'ward_trolleys', 'total_trolleys',
                'surge_capacity_in_use', 'delayed_transfers_of_care',
                'total_waiting_gt_24hrs', 'age_75plus_waiting_gt_24hrs']

ZSCORE_THRESHOLD = 3


def test_no_outliers_beyond_3_sigma(cleaned_df):
    """No value should be more than 3 standard deviations from the column mean."""
    for col in NUMERIC_COLS:
        if col not in cleaned_df.columns:
            continue
        mean = cleaned_df[col].mean()
        std = cleaned_df[col].std()
        if std == 0:
            continue  # all values identical, no outliers possible
        z_scores = ((cleaned_df[col] - mean) / std).abs()
        outliers = cleaned_df[z_scores > ZSCORE_THRESHOLD]
        assert outliers.empty, (
            f"Outliers in '{col}' (>{ZSCORE_THRESHOLD}σ from mean={mean:.1f}, std={std:.1f}):\n"
            f"{outliers[['Hospital', col]]}"
        )


def test_multi_day_no_outliers_across_hospitals(multi_day_df):
    """Across all days, no value should be > 3σ from the overall column mean."""
    for col in NUMERIC_COLS:
        if col not in multi_day_df.columns:
            continue
        mean = multi_day_df[col].mean()
        std = multi_day_df[col].std()
        if std == 0:
            continue
        z_scores = ((multi_day_df[col] - mean) / std).abs()
        outliers = multi_day_df[z_scores > ZSCORE_THRESHOLD]
        assert outliers.empty, (
            f"Outliers in '{col}' across days (>{ZSCORE_THRESHOLD}σ from "
            f"mean={mean:.1f}, std={std:.1f}):\n"
            f"{outliers[['Hospital', 'report_date', col]]}"
        )


def test_outlier_detection_catches_extreme_value():
    """Verify that an injected extreme value would be flagged as an outlier."""
    # Need enough normal data points so the extreme value doesn't dominate the std
    normal_values = [10, 12, 11, 13, 9, 14, 10, 12, 11, 13,
                     9, 14, 10, 12, 11, 13, 9, 14, 10, 12]
    hospitals = [f'Hospital_{i}' for i in range(len(normal_values) + 1)]
    df = pd.DataFrame({
        'Hospital': hospitals,
        'total_trolleys': normal_values + [500],  # 500 is an obvious outlier
    })
    mean = df['total_trolleys'].mean()
    std = df['total_trolleys'].std()
    z_scores = ((df['total_trolleys'] - mean) / std).abs()
    outliers = df[z_scores > ZSCORE_THRESHOLD]
    assert not outliers.empty, "Detection should flag the extreme value of 500"
    assert 500 in outliers['total_trolleys'].values


# ── parse_int edge cases ──────────────────────────────────────────

@pytest.mark.parametrize("input_val,expected", [
    (0, 0),
    (5, 5),
    ("12", 12),
    ("3.0", 3),
    (7.0, 7),
    (None, 0),
    (float('nan'), 0),
    ("", 0),
    ("N/A", 0),
    (np.nan, 0),
])
def test_parse_int(input_val, expected):
    assert parse_int(input_val) == expected
