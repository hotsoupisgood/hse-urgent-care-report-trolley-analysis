#!/usr/bin/env python3
"""Step 01 - Scrape the HSE TrolleyGAR daily report into one raw CSV.

Endpoint: uec.hse.ie/uec/TGAR.php?EDDATE=DD/MM/YYYY  (date is a query param, so
any past day is fetchable). Iterates every day in the range and concatenates.

Output: output/01_daily_by_hospital_raw.csv  (raw; still has the report's own
summary rows and negative values, which step 02 cleans).
"""

import random
import time
from datetime import datetime
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

# --- Configuration (hardcoded, edit here) ----------------------------------
BASE_URL = "https://uec.hse.ie/uec/TGAR.php"
START_DATE = datetime(2023, 1, 1)      # report has been published daily since here
END_DATE = datetime(2026, 4, 5)

MIN_DELAY = 1.0                        # polite, randomised delay between requests (s)
MAX_DELAY = 3.0
MAX_RETRIES = 10                       # retry transient faults this many times, then fail loud

OUTPUT_CSV = Path(__file__).parent / "output" / "01_daily_by_hospital_raw.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

# Region names are header/separator rows within the table, not hospitals.
REGIONS = [
    "HSE Dublin & North East",
    "HSE Dublin & Midlands",
    "HSE Dublin & South East",
    "HSE South West",
    "HSE Mid West",
    "HSE West & North West",
]

# The first eight columns repeat a regional summary block and are discarded.
COLS_TO_CUT = 8


# --- Scraping --------------------------------------------------------------

def fetch_report_table(url: str) -> pd.DataFrame:
    """GET the report and return its HTML table.

    Retries 5xx, timeouts, and empty pages (the HSE server flakes under load);
    fails loud on 404 and after MAX_RETRIES.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            table = BeautifulSoup(response.content, "html.parser").find("table")
            if table is None:
                raise ValueError("200 OK but no table in page")
            return pd.read_html(StringIO(str(table)), flavor="html5lib", skiprows=[0])[0]
        except (requests.Timeout, requests.ConnectionError, ValueError) as e:
            transient = e
        except requests.HTTPError as e:
            if e.response is None or e.response.status_code < 500:
                raise
            transient = e

        if attempt == MAX_RETRIES:
            raise RuntimeError(
                f"Giving up on {url} after {MAX_RETRIES} attempts: {transient}"
            )
        backoff = random.uniform(2 ** attempt, 2 ** attempt + 5)
        print(f"  transient fault ({transient}); retry {attempt}/{MAX_RETRIES} in {backoff:.0f}s")
        time.sleep(backoff)


def scrape_date(day: int, month: int, year: int) -> pd.DataFrame:
    """Fetch and clean a single day's report into a tidy-by-hospital frame."""
    print(f"Scraping {day:02d}/{month:02d}/{year}")
    url = f"{BASE_URL}?EDDATE={day}%2F{month}%2F{year}"
    df = fetch_report_table(url)

    # The HSE table is messy: a two-row header, region names sitting in their own
    # separator rows, and the first columns repeating a regional summary block.
    # The exact positions and names below (the 8-column cut, "Unnamed: 8/9_level_0")
    # are not principled. They were found by trial and error against the live pages
    # and just match how this particular table is laid out.
    df = df.replace(REGIONS, np.nan).infer_objects(copy=False)
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all")

    df = df.iloc[:, COLS_TO_CUT:]               # drop the repeated summary block
    df = df.drop("Unnamed: 9_level_0", axis=1)  # spare empty column
    df = df.rename(columns={"Unnamed: 8_level_0": "Hospital"})

    # metric names sit in the second header row; lift them out, then flatten
    second_level = df.columns.get_level_values(1).tolist()
    df.columns = df.columns.droplevel(1)
    df.loc[0] = second_level

    df.insert(0, "Date", f"{day:02d}/{month:02d}/{year}")
    return df


def main() -> None:
    dates = pd.date_range(start=START_DATE, end=END_DATE, freq="D")

    frames = []
    for d in dates:
        frames.append(scrape_date(d.day, d.month, d.year))
        time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    full = pd.concat(frames, ignore_index=True)
    full.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved {len(dates)} daily reports to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
