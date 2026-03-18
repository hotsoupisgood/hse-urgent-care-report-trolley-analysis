"""
Shared fixtures for daily_ingestion tests.
Provides sample DataFrames that mimic real scraped/CSV data without network or DB access.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Ensure the daily_ingestion package is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def raw_html_df():
    """
    Mimics the DataFrame that pd.read_html() returns from the HSE page
    BEFORE any cleaning — includes totals rows, regional headers, and NaN gaps.
    """
    return pd.DataFrame({
        'Unnamed: 0': [
            'Beaumont Hospital',
            'Cavan General Hospital',
            'Connolly Hospital',
            'Mater Misericordiae University Hospital',
            'HSE Dublin and North East Total',
            'CHI at Crumlin',
            'Tallaght University Hospital',
            'HSE Dublin and Midlands Total',
            'Cork University Hospital',
            'UH Kerry',
            'HSE South West Total',
            'Galway University Hospital',
            'Sligo University Hospital',
            'National Total',
        ],
        'ED Trolleys': [12, 5, 7, 30, 54, 4, 18, 22, 25, 3, 28, 14, 8, 104],
        'Ward Trolleys': [3, 1, np.nan, 0, 4, np.nan, 2, 2, 5, np.nan, 5, 0, 2, 13],
        'Total': [15, 6, 7, 30, 58, 4, 20, 24, 30, 3, 33, 14, 10, 117],
        'Surge Capacity in Use (Full report @14:00)': [
            24, 8, 33, 0, np.nan, np.nan, 0, np.nan, 10, 15, np.nan, 20, 12, np.nan
        ],
        'Delayed Transfers of Care (As of Midnight)': [
            19, 4, 9, 36, 68, np.nan, 42, 42, 18, 5, 23, 11, 7, 133
        ],
        'No of Total Waiting >24hrs': [
            np.nan, np.nan, np.nan, 5, 5, np.nan, 4, 4, 8, np.nan, 8, 3, np.nan, 17
        ],
        'No of >75+yrs Waiting >24hrs': [
            np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan,
            2, np.nan, 2, 1, np.nan, 3
        ],
    })


@pytest.fixture
def cleaned_df():
    """
    A cleaned DataFrame as produced by scraper.scrape_date() — totals filtered,
    columns renamed, region mapped. Represents a single day of data.
    """
    return pd.DataFrame({
        'Hospital': [
            'Beaumont Hospital',
            'Cavan General Hospital',
            'Connolly Hospital',
            'Mater Misericordiae University Hospital',
            'CHI at Crumlin',
            'Tallaght University Hospital',
            'Cork University Hospital',
            'UH Kerry',
            'Galway University Hospital',
            'Sligo University Hospital',
        ],
        'report_date': ['15/01/2024'] * 10,
        'region': [
            'HSE Dublin and North East',
            'HSE Dublin and North East',
            'HSE Dublin and North East',
            'HSE Dublin and North East',
            'HSE Dublin and Midlands',
            'HSE Dublin and Midlands',
            'HSE South West',
            'HSE South West',
            'HSE West and North West',
            'HSE West and North West',
        ],
        'ed_trolleys': [12, 5, 7, 30, 4, 18, 25, 3, 14, 8],
        'ward_trolleys': [3, 1, 0, 0, 0, 2, 5, 0, 0, 2],
        'total_trolleys': [15, 6, 7, 30, 4, 20, 30, 3, 14, 10],
        'surge_capacity_in_use': [24, 8, 33, 0, 0, 0, 10, 15, 20, 12],
        'delayed_transfers_of_care': [19, 4, 9, 36, 0, 42, 18, 5, 11, 7],
        'total_waiting_gt_24hrs': [0, 0, 0, 5, 0, 4, 8, 0, 3, 0],
        'age_75plus_waiting_gt_24hrs': [0, 0, 0, 0, 0, 0, 2, 0, 1, 0],
    })


@pytest.fixture
def multi_day_df(cleaned_df):
    """Two days of cleaned data stacked, for aggregation tests."""
    day1 = cleaned_df.copy()
    day2 = cleaned_df.copy()
    day2['report_date'] = '16/01/2024'
    # Slightly different values for day 2
    day2['ed_trolleys'] = day2['ed_trolleys'] + 2
    day2['total_trolleys'] = day2['total_trolleys'] + 2
    return pd.concat([day1, day2], ignore_index=True)


@pytest.fixture
def backfill_csv(tmp_path):
    """Write a small CSV mimicking the historical data file format."""
    csv_path = tmp_path / "test_data.csv"
    df = pd.DataFrame({
        'Unnamed: 0': range(4),
        'Date': ['01/01/2023', '01/01/2023', '02/01/2023', '02/01/2023'],
        'Hospital': [
            'Beaumont Hospital', 'Cork University Hospital',
            'Beaumont Hospital', 'Cork University Hospital',
        ],
        'ED Trolleys': [10, 20, 12, 22],
        'Ward Trolleys': [2, 5, 3, 4],
        'Total': [12, 25, 15, 26],
        'Surge Capacity in Use (Full report @14:00)': [24, 10, 24, 10],
        'Delayed Transfers of Care (As of Midnight)': [19, 18, 20, 19],
        'No of Total Waiting >24hrs': [np.nan, 8, np.nan, 9],
        'No of >75+yrs Waiting >24hrs': [np.nan, 2, np.nan, 3],
        'Region': [
            'HSE Dublin and North East', 'HSE South West',
            'HSE Dublin and North East', 'HSE South West',
        ],
    })
    df.to_csv(csv_path, index=False)
    return csv_path
