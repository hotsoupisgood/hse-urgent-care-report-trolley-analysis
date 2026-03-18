#!/usr/bin/env python3
"""
Create the PostgreSQL database, tables, and seed reference data.
Idempotent — safe to re-run.
"""

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from config import get_connection_string, DB_NAME, HOSPITAL_TO_REGION, REGION_POPULATIONS


def create_database():
    """Create the database if it doesn't exist."""
    conn = psycopg2.connect(get_connection_string(dbname="postgres"))
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_NAME,))
    if cur.fetchone() is None:
        cur.execute(f'CREATE DATABASE "{DB_NAME}"')
        print(f"Created database: {DB_NAME}")
    else:
        print(f"Database already exists: {DB_NAME}")

    cur.close()
    conn.close()


def create_tables():
    """Create tables and indexes if they don't exist."""
    conn = psycopg2.connect(get_connection_string())
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            id     SERIAL PRIMARY KEY,
            name   TEXT NOT NULL UNIQUE,
            region TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS region_populations (
            region     TEXT PRIMARY KEY,
            population INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS trolley_data (
            id                          SERIAL PRIMARY KEY,
            hospital_id                 INTEGER NOT NULL REFERENCES hospitals(id),
            report_date                 DATE NOT NULL,
            ed_trolleys                 INTEGER NOT NULL DEFAULT 0,
            ward_trolleys               INTEGER NOT NULL DEFAULT 0,
            total_trolleys              INTEGER NOT NULL DEFAULT 0,
            surge_capacity_in_use       INTEGER NOT NULL DEFAULT 0,
            delayed_transfers_of_care   INTEGER NOT NULL DEFAULT 0,
            total_waiting_gt_24hrs      INTEGER NOT NULL DEFAULT 0,
            age_75plus_waiting_gt_24hrs INTEGER NOT NULL DEFAULT 0,
            scraped_at                  TIMESTAMP DEFAULT NOW(),
            UNIQUE (hospital_id, report_date)
        );
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_trolley_date
            ON trolley_data (report_date);
        CREATE INDEX IF NOT EXISTS idx_trolley_hospital_date
            ON trolley_data (hospital_id, report_date);
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Tables and indexes created.")


def seed_hospitals():
    """Insert hospital/region records. Skips existing rows."""
    conn = psycopg2.connect(get_connection_string())
    cur = conn.cursor()

    inserted = 0
    for name, region in HOSPITAL_TO_REGION.items():
        cur.execute(
            "INSERT INTO hospitals (name, region) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
            (name, region),
        )
        inserted += cur.rowcount

    conn.commit()
    cur.close()
    conn.close()
    print(f"Hospitals seeded: {inserted} new, {len(HOSPITAL_TO_REGION) - inserted} already existed.")


def seed_populations():
    """Insert region population records. Updates population if region already exists."""
    conn = psycopg2.connect(get_connection_string())
    cur = conn.cursor()

    for region, population in REGION_POPULATIONS.items():
        cur.execute(
            """INSERT INTO region_populations (region, population)
               VALUES (%s, %s)
               ON CONFLICT (region) DO UPDATE SET population = EXCLUDED.population""",
            (region, population),
        )

    conn.commit()
    cur.close()
    conn.close()
    print(f"Region populations seeded: {len(REGION_POPULATIONS)} regions.")


def create_weekly_views():
    """Create weekly summary views. Always fresh — no rebuild needed."""
    conn = psycopg2.connect(get_connection_string())
    cur = conn.cursor()

    # Drop tables if they exist from a previous approach
    cur.execute("DROP TABLE IF EXISTS weekly_by_hospital CASCADE")
    cur.execute("DROP TABLE IF EXISTS weekly_by_region CASCADE")

    cur.execute("""
        CREATE OR REPLACE VIEW weekly_by_hospital AS
        SELECT
            date_trunc('week', t.report_date)::date AS week_start,
            h.name                                  AS hospital,
            h.region,
            SUM(t.ed_trolleys)                      AS ed_trolleys,
            SUM(t.ward_trolleys)                    AS ward_trolleys,
            SUM(t.total_trolleys)                   AS total_trolleys,
            SUM(t.surge_capacity_in_use)            AS surge_capacity_in_use,
            SUM(t.delayed_transfers_of_care)        AS delayed_transfers_of_care,
            SUM(t.total_waiting_gt_24hrs)           AS total_waiting_gt_24hrs,
            SUM(t.age_75plus_waiting_gt_24hrs)      AS age_75plus_waiting_gt_24hrs,
            COUNT(*)                                AS days_in_week
        FROM trolley_data t
        JOIN hospitals h ON h.id = t.hospital_id
        GROUP BY week_start, h.name, h.region
        ORDER BY week_start, h.region, h.name
    """)

    cur.execute("""
        CREATE OR REPLACE VIEW weekly_by_region AS
        SELECT
            date_trunc('week', t.report_date)::date AS week_start,
            h.region,
            rp.population                           AS region_population,
            SUM(t.ed_trolleys)                      AS ed_trolleys,
            SUM(t.ward_trolleys)                    AS ward_trolleys,
            SUM(t.total_trolleys)                   AS total_trolleys,
            SUM(t.surge_capacity_in_use)            AS surge_capacity_in_use,
            SUM(t.delayed_transfers_of_care)        AS delayed_transfers_of_care,
            SUM(t.total_waiting_gt_24hrs)           AS total_waiting_gt_24hrs,
            SUM(t.age_75plus_waiting_gt_24hrs)      AS age_75plus_waiting_gt_24hrs,
            COUNT(DISTINCT t.report_date)           AS days_in_week,
            ROUND(SUM(t.total_trolleys)::numeric / rp.population * 10000, 4)
                                                    AS trolleys_per_10k
        FROM trolley_data t
        JOIN hospitals h ON h.id = t.hospital_id
        JOIN region_populations rp ON rp.region = h.region
        GROUP BY week_start, h.region, rp.population
        ORDER BY week_start, h.region
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Weekly summary views created.")


if __name__ == "__main__":
    print("=" * 50)
    print("HSE TrolleyGAR — Database Setup")
    print("=" * 50)

    create_database()
    create_tables()
    seed_hospitals()
    seed_populations()
    create_weekly_views()

    print("\nDone.")
