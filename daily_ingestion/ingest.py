#!/usr/bin/env python3
"""
Main entry point: scrape HSE TrolleyGAR data and insert into PostgreSQL.
Idempotent — re-running for the same date inserts nothing.

Usage:
    python ingest.py                              # catch up: last DB date+1 through today
    python ingest.py --mode date --date 15/01/2024
    python ingest.py --mode range --start-date 01/01/2024 --end-date 31/01/2024
"""

import argparse
from datetime import datetime, timedelta

import pandas as pd
import psycopg2

from config import get_connection_string
from scraper import scrape_date


def parse_int(value):
    """Convert scraped value to int, treating NaN/empty/invalid as 0."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


def get_hospital_id_map(conn):
    """Load hospital name -> id mapping from the database."""
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM hospitals")
    mapping = {name: hid for hid, name in cur.fetchall()}
    cur.close()
    return mapping


def insert_day(conn, df, hospital_map):
    """
    Insert one day of cleaned/scraped data into trolley_data.
    Uses ON CONFLICT DO NOTHING for idempotency.

    Returns (inserted, skipped) counts.
    """
    cur = conn.cursor()
    inserted = 0
    skipped = 0

    for _, row in df.iterrows():
        hospital_name = row['Hospital']
        hospital_id = hospital_map.get(hospital_name)
        if hospital_id is None:
            skipped += 1
            continue

        report_date = datetime.strptime(row['report_date'], '%d/%m/%Y').date()

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
                parse_int(row.get('ed_trolleys')),
                parse_int(row.get('ward_trolleys')),
                parse_int(row.get('total_trolleys')),
                parse_int(row.get('surge_capacity_in_use')),
                parse_int(row.get('delayed_transfers_of_care')),
                parse_int(row.get('total_waiting_gt_24hrs')),
                parse_int(row.get('age_75plus_waiting_gt_24hrs')),
            ),
        )
        inserted += cur.rowcount  # 1 if inserted, 0 if conflict

    conn.commit()
    cur.close()
    return inserted, skipped


def ingest_date(conn, hospital_map, date_str):
    """Scrape and insert a single date. Returns (inserted, skipped)."""
    df = scrape_date(date_str)
    if df is None or df.empty:
        return 0, 0
    return insert_day(conn, df, hospital_map)


def ingest_range(conn, hospital_map, start_str, end_str):
    """Scrape and insert a date range. Returns total (inserted, skipped)."""
    start = datetime.strptime(start_str, '%d/%m/%Y')
    end = datetime.strptime(end_str, '%d/%m/%Y')

    total_inserted = 0
    total_skipped = 0
    current = start

    while current <= end:
        date_str = current.strftime('%d/%m/%Y')
        try:
            ins, skip = ingest_date(conn, hospital_map, date_str)
            total_inserted += ins
            total_skipped += skip
        except Exception as e:
            print(f"  Error on {date_str}: {e}")
        current += timedelta(days=1)

    return total_inserted, total_skipped


def get_latest_date(conn):
    """Get the most recent report_date in the database, or None if empty."""
    cur = conn.cursor()
    cur.execute("SELECT MAX(report_date) FROM trolley_data")
    result = cur.fetchone()[0]
    cur.close()
    return result


def main():
    parser = argparse.ArgumentParser(description='Ingest HSE TrolleyGAR data into PostgreSQL')
    parser.add_argument('--mode', choices=['catchup', 'date', 'range'], default='catchup',
                        help='catchup (default): fill from last DB date to today. '
                             'date: single date. range: explicit date range.')
    parser.add_argument('--date', help='Date to scrape (DD/MM/YYYY)')
    parser.add_argument('--start-date', help='Range start (DD/MM/YYYY)')
    parser.add_argument('--end-date', help='Range end (DD/MM/YYYY)')
    args = parser.parse_args()

    conn = psycopg2.connect(get_connection_string())
    hospital_map = get_hospital_id_map(conn)

    print("=" * 50)

    if args.mode == 'catchup':
        today = datetime.now().date()
        latest = get_latest_date(conn)

        if latest is None:
            print("Database is empty — scraping today only")
            print("-" * 50)
            inserted, skipped = ingest_date(conn, hospital_map, today.strftime('%d/%m/%Y'))
        elif latest >= today:
            print(f"Already up to date (latest: {latest.strftime('%d/%m/%Y')})")
            print("=" * 50)
            conn.close()
            return
        else:
            start = latest + timedelta(days=1)
            days_behind = (today - latest).days
            print(f"Catching up: {start.strftime('%d/%m/%Y')} to {today.strftime('%d/%m/%Y')} ({days_behind} day{'s' if days_behind != 1 else ''})")
            print("-" * 50)
            inserted, skipped = ingest_range(
                conn, hospital_map,
                start.strftime('%d/%m/%Y'),
                today.strftime('%d/%m/%Y'),
            )

    elif args.mode == 'date':
        if not args.date:
            parser.error("--date required for date mode")
        print(f"Single date ingestion: {args.date}")
        print("-" * 50)
        inserted, skipped = ingest_date(conn, hospital_map, args.date)

    elif args.mode == 'range':
        if not args.start_date or not args.end_date:
            parser.error("--start-date and --end-date required for range mode")
        print(f"Range ingestion: {args.start_date} to {args.end_date}")
        print("-" * 50)
        inserted, skipped = ingest_range(conn, hospital_map, args.start_date, args.end_date)

    print("-" * 50)
    print(f"Inserted: {inserted} rows")
    print(f"Skipped:  {skipped} (unmapped hospitals)")
    print("=" * 50)

    conn.close()


if __name__ == "__main__":
    main()
