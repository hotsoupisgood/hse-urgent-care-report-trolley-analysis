"""
Tests for analysis modules (pacf, weekday).
Uses mock DataFrames — no database required.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.pacf import compute_pacf_by_region
from analysis.weekday import WEEKDAY_LABELS, compute_weekday_means


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def region_daily_df():
    """
    Synthetic daily data for 2 regions, ~100 days each.
    Mimics the output of queries.load_daily_by_region().
    """
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    rows = []
    for region in ["HSE Dublin and North East", "HSE South West"]:
        for d in dates:
            rows.append({
                "report_date": d,
                "region": region,
                "total_trolleys": np.random.randint(10, 80),
                "trolleys_per_10k": round(np.random.uniform(0.3, 2.5), 4),
            })
    return pd.DataFrame(rows)


# ── PACF tests ───────────────────────────────────────────────────────

def test_pacf_returns_dict(region_daily_df):
    result = compute_pacf_by_region(region_daily_df, nlags=20)
    assert isinstance(result, dict)
    assert len(result) == 2


def test_pacf_keys_per_region(region_daily_df):
    result = compute_pacf_by_region(region_daily_df, nlags=20)
    for region, data in result.items():
        assert "lags" in data
        assert "pacf" in data
        assert "ci_lower" in data
        assert "ci_upper" in data


def test_pacf_lag_count(region_daily_df):
    nlags = 30
    result = compute_pacf_by_region(region_daily_df, nlags=nlags)
    for region, data in result.items():
        assert len(data["lags"]) == nlags + 1
        assert len(data["pacf"]) == nlags + 1


def test_pacf_lag_zero_is_one(region_daily_df):
    result = compute_pacf_by_region(region_daily_df, nlags=20)
    for region, data in result.items():
        assert data["pacf"][0] == pytest.approx(1.0)


def test_pacf_skips_short_series():
    """If a region has fewer observations than nlags+1, it should be skipped."""
    df = pd.DataFrame({
        "report_date": pd.date_range("2024-01-01", periods=5),
        "region": ["HSE Mid West"] * 5,
        "trolleys_per_10k": [1.0, 1.1, 1.2, 1.3, 1.4],
    })
    result = compute_pacf_by_region(df, nlags=60)
    assert len(result) == 0


# ── Weekday tests ────────────────────────────────────────────────────

def test_weekday_returns_all_days(region_daily_df):
    result = compute_weekday_means(region_daily_df)
    labels = result["weekday_label"].unique()
    assert set(labels) == set(WEEKDAY_LABELS)


def test_weekday_has_correct_columns(region_daily_df):
    result = compute_weekday_means(region_daily_df)
    expected = {"weekday", "weekday_label", "region",
                "mean_trolleys_per_10k", "mean_total_trolleys"}
    assert set(result.columns) == expected


def test_weekday_rows_per_region(region_daily_df):
    """Each region should have 7 rows (one per weekday)."""
    result = compute_weekday_means(region_daily_df)
    for region in region_daily_df["region"].unique():
        region_rows = result[result["region"] == region]
        assert len(region_rows) == 7


def test_weekday_means_positive(region_daily_df):
    result = compute_weekday_means(region_daily_df)
    assert (result["mean_trolleys_per_10k"] > 0).all()
