#!/usr/bin/env python3
"""
Scrape HSE TrolleyGAR data for a given date.
Parses the individual 14-cell hospital rows from the HSE HTML table,
with cleaning logic from preprocessing/cleaning.ipynb.
"""

import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

from config import HOSPITAL_TO_REGION

# Fixed cell positions in the 14-cell hospital rows:
#   [0]  empty spacer
#   [1]  Hospital name (colspan=8)
#   [2]  empty spacer
#   [3]  ED Trolleys
#   [4]  Ward Trolleys
#   [5]  Total Trolleys
#   [6]  empty spacer
#   [7]  Surge Capacity in Use
#   [8]  empty spacer
#   [9]  Delayed Transfers of Care
#   [10] empty spacer
#   [11] Total Waiting >24hrs
#   [12] empty spacer
#   [13] Age 75+ Waiting >24hrs

DATA_POSITIONS = {
    'ed_trolleys': 3,
    'ward_trolleys': 4,
    'total_trolleys': 5,
    'surge_capacity_in_use': 7,
    'delayed_transfers_of_care': 9,
    'total_waiting_gt_24hrs': 11,
    'age_75plus_waiting_gt_24hrs': 13,
}


def scrape_date(date_str=None):
    """
    Scrape HSE TrolleyGAR data for a specific date.

    Extracts data from the 14-cell individual hospital rows in the HTML
    table, then applies cleaning from preprocessing/cleaning.ipynb:
      - Filter to only known hospitals (mapped to regions)
      - Standardise column names

    Args:
        date_str: Date in format 'DD/MM/YYYY'. If None, uses today.

    Returns:
        pd.DataFrame with columns: Hospital, report_date, region,
        ed_trolleys, ward_trolleys, total_trolleys, surge_capacity_in_use,
        delayed_transfers_of_care, total_waiting_gt_24hrs,
        age_75plus_waiting_gt_24hrs.
        Returns None if scraping fails.
    """
    if date_str is None:
        date_str = datetime.now().strftime('%d/%m/%Y')

    encoded_date = date_str.replace('/', '%2F')
    url = f'https://uec.hse.ie/uec/TGAR.php?EDDATE={encoded_date}'

    print(f"  Fetching {date_str} ... ", end="", flush=True)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table')

    if not table:
        print("no table found!")
        return None

    rows = table.find_all('tr')
    data = []

    for row in rows:
        cells = row.find_all(['td', 'th'])

        # Individual hospital rows always have exactly 14 cells
        if len(cells) != 14:
            continue

        # Cell [1] must be the hospital name with colspan >= 8
        name_cell = cells[1]
        if int(name_cell.get('colspan', 1)) < 8:
            continue

        hospital_name = name_cell.get_text(strip=True)
        if not hospital_name:
            continue

        # Extract data values by fixed position
        record = {'Hospital': hospital_name}
        for col_name, pos in DATA_POSITIONS.items():
            val = cells[pos].get_text(strip=True)
            record[col_name] = val if val else None

        data.append(record)

    if not data:
        print("no hospital data found!")
        return None

    df = pd.DataFrame(data)

    # --- Cleaning (from preprocessing/cleaning.ipynb) ---

    # Keep only hospitals we have a region mapping for (also removes totals)
    df = df[df['Hospital'].isin(HOSPITAL_TO_REGION)]

    # Add region from mapping
    df['region'] = df['Hospital'].map(HOSPITAL_TO_REGION)

    # Add report date
    df['report_date'] = date_str

    df = df.reset_index(drop=True)

    print(f"{len(df)} hospitals")
    return df
