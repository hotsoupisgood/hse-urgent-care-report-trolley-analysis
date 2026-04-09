"""
SQL queries for the dashboard — psycopg2 + pandas.read_sql().
Trimmed from the full analysis/queries.py to only what the dashboard needs.
"""

import os
import sys
import warnings

import pandas as pd
import psycopg2

# psycopg2 connections work fine with pd.read_sql but pandas warns about it
warnings.filterwarnings("ignore", message=".*pandas only supports SQLAlchemy.*")

def get_connection():
    """Return a new psycopg2 connection to the HSE database."""
    db_name = os.environ.get("DB_NAME", "hse_trolleygar")
    parts = [f"dbname={db_name}"]
    for key, env in [("host", "DB_HOST"), ("port", "DB_PORT"),
                     ("user", "DB_USER"), ("password", "DB_PASSWORD")]:
        val = os.environ.get(env, "")
        if val:
            parts.append(f"{key}={val}")
    return psycopg2.connect(" ".join(parts))


# -- Latest day by region (for choropleth) --------------------------------

def load_day_by_region(conn, report_date=None):
    """
    Totals per region for a given date (defaults to most recent).

    Returns DataFrame with columns:
        report_date, region, total_trolleys, trolleys_per_10k,
        delayed_transfers_of_care, total_waiting_gt_24hrs
    """
    if report_date:
        date_clause = "WHERE t.report_date = %s"
        params = [report_date]
    else:
        date_clause = """
            WHERE t.report_date = (
                SELECT MAX(report_date) FROM trolley_data
            )"""
        params = None

    sql = f"""
        SELECT
            t.report_date,
            h.region,
            SUM(t.total_trolleys)                                       AS total_trolleys,
            ROUND(SUM(t.total_trolleys)::numeric / rp.population * 10000, 4)
                                                                        AS trolleys_per_10k,
            SUM(t.delayed_transfers_of_care)                            AS delayed_transfers_of_care,
            SUM(t.total_waiting_gt_24hrs)                               AS total_waiting_gt_24hrs
        FROM trolley_data t
        JOIN hospitals h            ON h.id = t.hospital_id
        JOIN region_populations rp  ON rp.region = h.region
        {date_clause}
        GROUP BY t.report_date, h.region, rp.population
        ORDER BY h.region
    """
    return pd.read_sql(sql, conn, params=params, parse_dates=["report_date"])


# -- Day by hospital (for the table) --------------------------------------

def load_day_by_hospital(conn, report_date=None):
    """
    Per-hospital counts for a given date (defaults to most recent).

    Returns DataFrame with columns:
        report_date, hospital, region, ed_trolleys, ward_trolleys,
        total_trolleys, delayed_transfers_of_care, total_waiting_gt_24hrs
    """
    if report_date:
        date_clause = "WHERE t.report_date = %s"
        params = [report_date]
    else:
        date_clause = """
            WHERE t.report_date = (
                SELECT MAX(report_date) FROM trolley_data
            )"""
        params = None

    sql = f"""
        SELECT
            t.report_date,
            h.name AS hospital,
            h.region,
            t.ed_trolleys,
            t.ward_trolleys,
            t.total_trolleys,
            t.delayed_transfers_of_care,
            t.total_waiting_gt_24hrs
        FROM trolley_data t
        JOIN hospitals h ON h.id = t.hospital_id
        {date_clause}
        ORDER BY h.region, h.name
    """
    return pd.read_sql(sql, conn, params=params, parse_dates=["report_date"])


# -- Dropdown helpers -----------------------------------------------------

def load_available_dates(conn):
    """Return list of available report dates, most recent first."""
    df = pd.read_sql(
        "SELECT DISTINCT report_date FROM trolley_data ORDER BY report_date DESC",
        conn, parse_dates=["report_date"],
    )
    return df["report_date"].tolist()


def load_region_list(conn):
    """Return sorted list of region names."""
    df = pd.read_sql("SELECT DISTINCT region FROM hospitals ORDER BY region", conn)
    return df["region"].tolist()


# -- Time series queries (for /trends page) --------------------------------

_TS_COLS = """
    SUM(ed_trolleys) AS ed_trolleys,
    SUM(ward_trolleys) AS ward_trolleys,
    SUM(total_trolleys) AS total_trolleys,
    SUM(surge_capacity_in_use) AS surge_capacity_in_use,
    SUM(delayed_transfers_of_care) AS delayed_transfers_of_care,
    SUM(total_waiting_gt_24hrs) AS total_waiting_gt_24hrs,
    SUM(age_75plus_waiting_gt_24hrs) AS age_75plus_waiting_gt_24hrs
"""


def load_weekly_national(conn):
    """Weekly totals across all regions (aggregates weekly_by_region view)."""
    sql = f"""
        SELECT week_start, {_TS_COLS},
               SUM(region_population) AS population
        FROM weekly_by_region
        GROUP BY week_start
        ORDER BY week_start
    """
    return pd.read_sql(sql, conn, parse_dates=["week_start"])


def load_weekly_by_region(conn):
    """Weekly totals per region from the weekly_by_region view."""
    return pd.read_sql(
        """SELECT week_start, region, region_population AS population,
                  ed_trolleys, ward_trolleys, total_trolleys,
                  surge_capacity_in_use, delayed_transfers_of_care,
                  total_waiting_gt_24hrs, age_75plus_waiting_gt_24hrs
           FROM weekly_by_region
           ORDER BY week_start, region""",
        conn, parse_dates=["week_start"],
    )


def load_daily_national(conn):
    """Daily totals across all hospitals."""
    sql = f"""
        SELECT t.report_date, {_TS_COLS},
               (SELECT SUM(population) FROM region_populations) AS population
        FROM trolley_data t
        GROUP BY t.report_date
        ORDER BY t.report_date
    """
    return pd.read_sql(sql, conn, parse_dates=["report_date"])


def load_daily_by_region(conn):
    """Daily totals per region."""
    sql = f"""
        SELECT t.report_date, h.region, rp.population, {_TS_COLS}
        FROM trolley_data t
        JOIN hospitals h ON h.id = t.hospital_id
        JOIN region_populations rp ON rp.region = h.region
        GROUP BY t.report_date, h.region, rp.population
        ORDER BY t.report_date, h.region
    """
    return pd.read_sql(sql, conn, parse_dates=["report_date"])
