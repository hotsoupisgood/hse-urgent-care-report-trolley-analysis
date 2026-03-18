"""
SQL queries for the dashboard — psycopg2 + pandas.read_sql().
"""

import os
import sys
import warnings

import pandas as pd
import psycopg2

# psycopg2 connections work fine with pd.read_sql but pandas warns about it
warnings.filterwarnings("ignore", message=".*pandas only supports SQLAlchemy.*")

# Ensure daily_ingestion package root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import get_connection_string


def get_connection():
    """Return a new psycopg2 connection to the HSE database."""
    return psycopg2.connect(get_connection_string())


# ── Per-region daily data ────────────────────────────────────────────

def load_daily_by_region(conn, region=None, start_date=None, end_date=None):
    """
    Daily total_trolleys and trolleys_per_10k aggregated by region.

    Returns DataFrame with columns:
        report_date, region, total_trolleys, trolleys_per_10k
    """
    sql = """
        SELECT
            t.report_date,
            h.region,
            SUM(t.total_trolleys)                                       AS total_trolleys,
            ROUND(SUM(t.total_trolleys)::numeric / rp.population * 10000, 4)
                                                                        AS trolleys_per_10k
        FROM trolley_data t
        JOIN hospitals h            ON h.id = t.hospital_id
        JOIN region_populations rp  ON rp.region = h.region
        WHERE 1=1
    """
    params = []
    if region:
        if isinstance(region, list):
            sql += " AND h.region = ANY(%s)"
            params.append(region)
        else:
            sql += " AND h.region = %s"
            params.append(region)
    if start_date:
        sql += " AND t.report_date >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND t.report_date <= %s"
        params.append(end_date)

    sql += """
        GROUP BY t.report_date, h.region, rp.population
        ORDER BY t.report_date, h.region
    """
    return pd.read_sql(sql, conn, params=params or None, parse_dates=["report_date"])


# ── Per-hospital daily data ──────────────────────────────────────────

def load_daily_by_hospital(conn, hospital=None, region=None,
                           start_date=None, end_date=None):
    """
    Daily per-hospital data.

    Returns DataFrame with columns:
        report_date, hospital, region, total_trolleys,
        ed_trolleys, ward_trolleys
    """
    sql = """
        SELECT
            t.report_date,
            h.name          AS hospital,
            h.region,
            t.total_trolleys,
            t.ed_trolleys,
            t.ward_trolleys
        FROM trolley_data t
        JOIN hospitals h ON h.id = t.hospital_id
        WHERE 1=1
    """
    params = []
    if hospital:
        if isinstance(hospital, list):
            sql += " AND h.name = ANY(%s)"
            params.append(hospital)
        else:
            sql += " AND h.name = %s"
            params.append(hospital)
    if region:
        if isinstance(region, list):
            sql += " AND h.region = ANY(%s)"
            params.append(region)
        else:
            sql += " AND h.region = %s"
            params.append(region)
    if start_date:
        sql += " AND t.report_date >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND t.report_date <= %s"
        params.append(end_date)

    sql += " ORDER BY t.report_date, h.region, h.name"
    return pd.read_sql(sql, conn, params=params or None, parse_dates=["report_date"])


# ── Latest day by region (for choropleth) ────────────────────────────

def load_latest_day_by_region(conn, end_date=None):
    """
    Most recent day's totals per region.
    If end_date is given, returns the latest day <= end_date.

    Returns DataFrame with columns:
        report_date, region, total_trolleys, trolleys_per_10k
    """
    date_filter = ""
    params = []
    if end_date:
        date_filter = "WHERE t.report_date <= %s"
        params.append(end_date)

    sql = f"""
        WITH latest AS (
            SELECT MAX(t.report_date) AS max_date
            FROM trolley_data t
            {date_filter}
        )
        SELECT
            t.report_date,
            h.region,
            SUM(t.total_trolleys)                                       AS total_trolleys,
            ROUND(SUM(t.total_trolleys)::numeric / rp.population * 10000, 4)
                                                                        AS trolleys_per_10k
        FROM trolley_data t
        JOIN hospitals h            ON h.id = t.hospital_id
        JOIN region_populations rp  ON rp.region = h.region
        CROSS JOIN latest l
        WHERE t.report_date = l.max_date
        GROUP BY t.report_date, h.region, rp.population
        ORDER BY h.region
    """
    return pd.read_sql(sql, conn, params=params or None, parse_dates=["report_date"])


# ── Dropdown helpers ─────────────────────────────────────────────────

def load_hospital_list(conn):
    """Return sorted list of hospital names."""
    df = pd.read_sql("SELECT name FROM hospitals ORDER BY name", conn)
    return df["name"].tolist()


def load_region_list(conn):
    """Return sorted list of region names."""
    df = pd.read_sql("SELECT DISTINCT region FROM hospitals ORDER BY region", conn)
    return df["region"].tolist()


def load_date_range(conn):
    """Return (min_date, max_date) as Python date objects."""
    df = pd.read_sql(
        "SELECT MIN(report_date) AS min_d, MAX(report_date) AS max_d FROM trolley_data",
        conn,
    )
    return df["min_d"].iloc[0], df["max_d"].iloc[0]


def load_hospitals_for_regions(conn, regions):
    """Return sorted list of hospital names for given regions."""
    if not regions:
        return load_hospital_list(conn)
    df = pd.read_sql(
        "SELECT name FROM hospitals WHERE region = ANY(%s) ORDER BY name",
        conn,
        params=[regions],
    )
    return df["name"].tolist()
