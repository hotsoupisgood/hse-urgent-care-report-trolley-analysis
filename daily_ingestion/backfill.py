#!/usr/bin/env python3
"""
One-time backfill: import historical CSV data into PostgreSQL.
Uses ON CONFLICT DO NOTHING — safe to re-run.

Usage:
    python backfill.py
    python backfill.py --csv ../data/uec_data_2023_2025_full_with_regions.csv
"""

import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2

from config import get_connection_string


DEFAULT_CSV = Path(__file__).parent.parent / "data" / "uec_data_2023_2025_full_with_regions.csv"


def parse_int(value):
    """Convert value to int, treating NaN/empty as 0."""
    if pd.isna(value):
        return 0
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


def backfill(csv_path):
    """Read historical CSV and bulk-insert into PostgreSQL."""
    print(f"Reading {csv_path} ...")
    df = pd.read_csv(csv_path, index_col=0)
    print(f"  {len(df)} rows loaded")

    # Column mapping: CSV name -> what we need
    # CSV: Date, Hospital, ED Trolleys, Ward Trolleys, Total,
    #      Surge Capacity in Use (Full report @14:00),
    #      Delayed Transfers of Care (As of Midnight),
    #      No of Total Waiting >24hrs, No of >75+yrs Waiting >24hrs, Region
    col_map = {
        'Date': 'date',
        'Hospital': 'hospital',
        'ED Trolleys': 'ed_trolleys',
        'Ward Trolleys': 'ward_trolleys',
        'Total': 'total_trolleys',
        'Surge Capacity in Use (Full report @14:00)': 'surge_capacity_in_use',
        'Delayed Transfers of Care (As of Midnight)': 'delayed_transfers_of_care',
        'No of Total Waiting >24hrs': 'total_waiting_gt_24hrs',
        'No of >75+yrs Waiting >24hrs': 'age_75plus_waiting_gt_24hrs',
    }
    df = df.rename(columns=col_map)

    conn = psycopg2.connect(get_connection_string())
    cur = conn.cursor()

    # Load hospital_id map
    cur.execute("SELECT id, name FROM hospitals")
    hospital_map = {name: hid for hid, name in cur.fetchall()}

    inserted = 0
    skipped_unmapped = 0
    skipped_conflict = 0

    for _, row in df.iterrows():
        hospital_id = hospital_map.get(row['hospital'])
        if hospital_id is None:
            skipped_unmapped += 1
            continue

        report_date = datetime.strptime(row['date'], '%d/%m/%Y').date()

        cur.execute(
            """INSERT INTO trolley_data
                   (hospital_id, report_date, ed_trolleys, ward_trolleys,
                    total_trolleys, surge_capacity_in_use,
                    delayed_transfers_of_care, total_waiting_gt_24hrs,
                    age_75plus_waiting_gt_24hrs)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (hospital_id, report_date) DO NOTHING""",
            (
                hospital_id,
                report_date,
                parse_int(row['ed_trolleys']),
                parse_int(row['ward_trolleys']),
                parse_int(row['total_trolleys']),
                parse_int(row['surge_capacity_in_use']),
                parse_int(row['delayed_transfers_of_care']),
                parse_int(row['total_waiting_gt_24hrs']),
                parse_int(row['age_75plus_waiting_gt_24hrs']),
            ),
        )
        if cur.rowcount == 1:
            inserted += 1
        else:
            skipped_conflict += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nBackfill complete:")
    print(f"  Inserted:          {inserted}")
    print(f"  Already existed:   {skipped_conflict}")
    print(f"  Unmapped hospitals: {skipped_unmapped}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Backfill historical CSV into PostgreSQL')
    parser.add_argument('--csv', default=str(DEFAULT_CSV), help='Path to CSV file')
    args = parser.parse_args()

    print("=" * 50)
    print("HSE TrolleyGAR — Historical Backfill")
    print("=" * 50)

    backfill(args.csv)
