#!/usr/bin/env python3
"""
Scrape hospital/urgent care facility names from the HSE "Find Urgent Emergency Care" page.

Target URL: https://www2.hse.ie/services/find-urgent-emergency-care/
The site lists 166 facilities, paginated at 10 per page (17 pages).

Pagination uses the query parameter ?page=N (N = 1..17).
Each result card has an <a> tag with data-testid="hse-result-card__title__link"
whose text content is the facility name.
"""

import csv
import re
import sys
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = "https://www2.hse.ie/services/find-urgent-emergency-care/"
SITE_ROOT = "https://www2.hse.ie"
SELECTOR = '[data-testid="hse-result-card__title__link"]'
ADDRESS_SELECTOR = '[data-testid="hse-page-header__address"]'
RESULTS_PER_PAGE = 10
DELAY_SECONDS = 1.5  # polite delay between requests
OUTPUT_CSV = Path(__file__).parent / "hospital_names.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


# ---------------------------------------------------------------------------
# Scraping helpers
# ---------------------------------------------------------------------------

def fetch_page(page_number: int) -> BeautifulSoup:
    """Fetch a single page and return its parsed HTML."""
    url = f"{BASE_URL}?page={page_number}"
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def extract_names_and_urls(soup: BeautifulSoup) -> list[dict]:
    """
    Extract facility names and detail page URLs from a parsed listing page.

    Each matching <a> tag's text content is a facility name,
    and its href points to the facility's detail page.
    """
    links = soup.select(SELECTOR)
    results = []
    for link in links:
        name = link.get_text(strip=True)
        href = link.get("href", "")
        # hrefs are relative like /services/find-urgent-emergency-care/bantry-local-injury-unit/
        url = f"{SITE_ROOT}{href}" if href.startswith("/") else href
        results.append({"name": name, "url": url})
    return results


def fetch_address(detail_url: str) -> str:
    """
    Fetch a facility's detail page and extract the address from:
      [data-testid="hse-page-header__address"]
    """
    try:
        response = requests.get(detail_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        addr_el = soup.select_one(ADDRESS_SELECTOR)
        if addr_el:
            return addr_el.get_text(strip=True)
    except requests.RequestException as e:
        print(f"    ERROR fetching {detail_url}: {e}")
    return ""


def get_total_pages(soup: BeautifulSoup) -> int:
    """
    Determine the total number of pages from the first page's pagination.

    Strategy: look for pagination links and find the highest page number.
    Falls back to calculating from "X of Y results" text if pagination
    links are not found.
    """
    # Look for pagination links with page numbers
    pagination_links = soup.select('a[href*="?page="]')
    if pagination_links:
        max_page = 1
        for link in pagination_links:
            href = link.get("href", "")
            # Extract page number from href like "...?page=17"
            if "?page=" in href:
                try:
                    page_num = int(href.split("?page=")[-1].split("&")[0])
                    max_page = max(max_page, page_num)
                except ValueError:
                    continue
        if max_page > 1:
            return max_page

    # Fallback: look for text like "Showing X to Y of Z results"
    text = soup.get_text()
    match = re.search(r"of\s+(\d+)\s+results", text, re.IGNORECASE)
    if match:
        total = int(match.group(1))
        return (total + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE

    # Hard fallback based on our prior inspection
    print("WARNING: Could not detect total pages dynamically. Using default of 17.")
    return 17


# ---------------------------------------------------------------------------
# Main scraper
# ---------------------------------------------------------------------------

def scrape_all_hospitals() -> list[dict]:
    """Scrape all hospital/facility names and addresses across all pages."""

    # -- Step 1: Fetch listing pages to get names + detail URLs --
    print("STEP 1: Fetching listing pages for facility names + URLs\n")

    print("Fetching page 1 to determine total pages...")
    first_page = fetch_page(1)
    total_pages = get_total_pages(first_page)
    print(f"Detected {total_pages} pages of results.\n")

    all_facilities = extract_names_and_urls(first_page)
    print(f"  Page  1: found {len(all_facilities)} facilities")

    for page_num in range(2, total_pages + 1):
        time.sleep(DELAY_SECONDS)
        print(f"  Page {page_num:>2}: ", end="", flush=True)

        try:
            soup = fetch_page(page_num)
            facilities = extract_names_and_urls(soup)
            print(f"found {len(facilities)} facilities")
            all_facilities.extend(facilities)
        except requests.RequestException as e:
            print(f"ERROR fetching page {page_num}: {e}")
            continue

    # -- Step 2: Fetch each detail page for the address --
    print(f"\nSTEP 2: Fetching {len(all_facilities)} detail pages for addresses\n")

    for i, facility in enumerate(all_facilities, start=1):
        time.sleep(DELAY_SECONDS)
        print(f"  {i:>3}/{len(all_facilities)}: {facility['name']}... ", end="", flush=True)
        facility["address"] = fetch_address(facility["url"])
        print(facility["address"] or "(no address found)")

    return all_facilities


def save_to_csv(facilities: list[dict], output_path: Path) -> None:
    """Save the list of facilities to a CSV file."""
    today = date.today().strftime("%d/%m/%Y")
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["number", "facility_name", "address", "date_scraped"])
        for i, fac in enumerate(facilities, start=1):
            writer.writerow([i, fac["name"], fac["address"], today])
    print(f"\nSaved {len(facilities)} facilities to: {output_path}")


def validate_results(facilities: list[dict]) -> None:
    """Run basic validation checks on the scraped data."""
    names = [f["name"] for f in facilities]
    print("\n--- Validation ---")

    # Check total count
    expected = 166
    actual = len(names)
    if actual == expected:
        print(f"  [OK] Count matches expected: {actual}")
    else:
        print(f"  [!!] Count mismatch: expected {expected}, got {actual}")

    # Check for duplicates
    unique = set(names)
    if len(unique) == len(names):
        print(f"  [OK] No duplicates found")
    else:
        dupes = [n for n in names if names.count(n) > 1]
        print(f"  [!!] {len(names) - len(unique)} duplicate(s) found: {set(dupes)}")

    # Check for empty or suspiciously short names
    short = [n for n in names if len(n) < 3]
    if short:
        print(f"  [!!] Suspiciously short names: {short}")
    else:
        print(f"  [OK] No suspiciously short names")

    # Check for HTML artifacts
    artifacts = [n for n in names if any(c in n for c in ["<", ">", "&amp;", "&lt;"])]
    if artifacts:
        print(f"  [!!] Names with HTML artifacts: {artifacts}")
    else:
        print(f"  [OK] No HTML artifacts detected")

    # Check addresses scraped
    missing = [f["name"] for f in facilities if not f["address"]]
    if missing:
        print(f"  [!!] {len(missing)} facilities missing address: {missing}")
    else:
        print(f"  [OK] All facilities have addresses")

    print("--- End validation ---\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("HSE Urgent/Emergency Care Facility Scraper")
    print("=" * 60)
    print(f"Target: {BASE_URL}")
    print(f"Selector: {SELECTOR}")
    print()

    # Scrape all pages
    facilities = scrape_all_hospitals()

    # Validate
    validate_results(facilities)

    # Print numbered list
    print("=" * 60)
    print("ALL FACILITIES")
    print("=" * 60)
    for i, fac in enumerate(facilities, start=1):
        print(f"  {i:>3}. {fac['name']}")
        print(f"       {fac['address']}")

    # Save to CSV
    save_to_csv(facilities, OUTPUT_CSV)

    print("\nDone.")
