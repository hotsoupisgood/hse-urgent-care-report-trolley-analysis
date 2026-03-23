"""
Geocode private hospitals in Ireland using Nominatim (OpenStreetMap).
Maps each to an HSE health region based on county.

Source: Private Hospitals Association member list (web.archive.org snapshot).
Geocoding: Nominatim API (OpenStreetMap), no API key required.

Usage:
    python3 preprocessing/geocode_private_hospitals.py

Output:
    data/private_hospitals_per_region.csv
"""

import urllib.request
import urllib.parse
import json
import time
import csv
import os

# --- Configuration -----------------------------------------------------------

OUTPUT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "private_hospitals_per_region.csv"
)

# Nominatim requires a descriptive User-Agent (no generic strings)
USER_AGENT = "HSE-TrolleyGAR-Research/1.0 (academic thesis, University of Galway)"

# Rate limit: Nominatim requires max 1 request/second
RATE_LIMIT_SECONDS = 1.1

# --- Private Hospitals (from PHA archive) ------------------------------------
# Source: Private Hospitals Association member list
# Retrieved via Wayback Machine snapshot of privatehospitals.ie

PRIVATE_HOSPITALS = [
    {"name": "Aut Even Hospital",                              "query": "Aut Even Hospital, Kilkenny, Ireland"},
    {"name": "Blackrock Clinic Dublin",                        "query": "Blackrock Clinic, Blackrock, Dublin, Ireland"},
    {"name": "Bon Secours Hospital Cork",                      "query": "Bon Secours Hospital, College Road, Cork, Ireland"},
    {"name": "Bon Secours Hospital Dublin",                    "query": "Bon Secours Hospital, Glasnevin, Dublin, Ireland"},
    {"name": "Bon Secours Hospital Galway",                    "query": "Bon Secours Hospital, Renmore, Galway, Ireland"},
    {"name": "Bon Secours Hospital Limerick at Barrington's",  "query": "Barrington's Hospital, George's Quay, Limerick, Ireland"},
    {"name": "Bon Secours Hospital Tralee",                    "query": "Bon Secours Hospital, Tralee, Kerry, Ireland"},
    {"name": "Clane General Hospital Kildare",                 "query": "Clane Hospital, Prosperous Road, Clane, Kildare, Ireland"},
    {"name": "Galway Clinic",                                  "query": "Galway Clinic, Doughiska, Galway, Ireland"},
    {"name": "Hermitage Clinic Dublin",                        "query": "Hermitage Clinic, Lucan, Dublin, Ireland"},
    {"name": "Kingsbridge Private Hospital Sligo",             "query": "Kingsbridge Private Hospital, Sligo, Ireland"},
    {"name": "Mater Private Hospital Dublin",                  "query": "Mater Private Hospital, Eccles Street, Dublin, Ireland"},
    {"name": "Mater Private Hospital Cork",                    "query": "Mater Private Hospital, Cork, Ireland"},
    {"name": "Sports Surgery Clinic",                          "query": "Sports Surgery Clinic, Santry Demesne, Dublin 9, Ireland"},
    {"name": "St Francis Private Hospital Mullingar",          "query": "St Francis Private Hospital, Mullingar, Ireland"},
    {"name": "St John of God Hospital Dublin",                 "query": "St John of God Hospital, Stillorgan, Dublin, Ireland"},
    {"name": "St Vincent's Private Hospital",                  "query": "Saint Vincents Private Hospital, Elm Park, Dublin 4, Ireland"},
    {"name": "UPMC Whitfield Waterford",                       "query": "UPMC Whitfield Hospital, Waterford, Ireland"},
]

# --- County -> HSE Region mapping --------------------------------------------
# Based on HSE health region boundaries (2024 reorganisation uses same 6)
# Dublin hospitals are mapped based on which public hospital catchment they
# fall within (verified against config.py HOSPITAL_TO_REGION)

COUNTY_TO_REGION = {
    # Dublin and North East
    "Louth":    "HSE Dublin and North East",
    "Meath":    "HSE Dublin and North East",
    "Cavan":    "HSE Dublin and North East",
    "Monaghan": "HSE Dublin and North East",
    # Dublin and Midlands
    "Laois":      "HSE Dublin and Midlands",
    "Offaly":     "HSE Dublin and Midlands",
    "Westmeath":  "HSE Dublin and Midlands",
    "Longford":   "HSE Dublin and Midlands",
    "Kildare":    "HSE Dublin and Midlands",
    # Dublin and South East
    "Wicklow":    "HSE Dublin and South East",
    "Wexford":    "HSE Dublin and South East",
    "Carlow":     "HSE Dublin and South East",
    "Kilkenny":   "HSE Dublin and South East",
    "Waterford":  "HSE Dublin and South East",
    "Tipperary":  "HSE Dublin and South East",
    # South West
    "Cork":  "HSE South West",
    "Kerry": "HSE South West",
    # Mid West
    "Limerick": "HSE Mid West",
    "Clare":    "HSE Mid West",
    # West and North West
    "Galway":    "HSE West and North West",
    "Mayo":      "HSE West and North West",
    "Roscommon": "HSE West and North West",
    "Sligo":     "HSE West and North West",
    "Leitrim":   "HSE West and North West",
    "Donegal":   "HSE West and North West",
}

# Dublin hospitals need manual region assignment (Dublin spans 3 HSE regions).
# Assigned based on geographic proximity to public hospital catchments.
DUBLIN_OVERRIDES = {
    "Blackrock Clinic Dublin":       "HSE Dublin and South East",   # South Dublin, near St Vincent's
    "Bon Secours Hospital Dublin":   "HSE Dublin and North East",   # Glasnevin, near Mater/Beaumont
    "Hermitage Clinic Dublin":       "HSE Dublin and Midlands",     # Lucan, west Dublin, near Tallaght
    "Mater Private Hospital Dublin": "HSE Dublin and North East",   # Eccles St, beside Mater public
    "Sports Surgery Clinic":         "HSE Dublin and North East",   # Santry, near Beaumont
    "St John of God Hospital Dublin":"HSE Dublin and South East",   # Stillorgan, south Dublin
    "St Vincent's Private Hospital": "HSE Dublin and South East",   # Merrion Rd, same campus as SVUH
}


# --- Geocoding ---------------------------------------------------------------

def geocode(query: str) -> dict:
    """Query Nominatim for a single address. Returns parsed result or None."""
    url = (
        f"https://nominatim.openstreetmap.org/search"
        f"?q={urllib.parse.quote(query)}"
        f"&format=json&addressdetails=1&limit=1&countrycodes=ie"
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    resp = urllib.request.urlopen(req)
    data = json.loads(resp.read().decode())
    if not data:
        return None
    return data[0]


def extract_county(address: dict) -> str:
    """Extract county from Nominatim address components."""
    county = address.get("county", "")
    # Nominatim sometimes returns "County Kilkenny" or "Co. Cork"
    for prefix in ["County ", "Co. "]:
        if county.startswith(prefix):
            county = county[len(prefix):]
    # Handle "City" suffixes (e.g., "Cork City", "Galway City")
    if county.endswith(" City"):
        county = county[:-5]
    # Sometimes county is empty but state/city has it
    if not county:
        city = address.get("city", address.get("town", ""))
        state = address.get("state", "")
        for candidate in [city, state]:
            cleaned = candidate.replace("County ", "").replace("Co. ", "")
            if cleaned in COUNTY_TO_REGION:
                return cleaned
    return county


def assign_region(name: str, county: str) -> str:
    """Assign HSE region from county, with Dublin overrides."""
    if name in DUBLIN_OVERRIDES:
        return DUBLIN_OVERRIDES[name]
    region = COUNTY_TO_REGION.get(county, "UNKNOWN")
    return region


# --- Manual fallbacks for hospitals Nominatim can't find ---------------------
# These are verified against Google Maps / individual hospital websites.
# If Nominatim finds them in a future run, the fallback is skipped.

MANUAL_FALLBACKS = {
    "Bon Secours Hospital Limerick at Barrington's": {
        "address": "Barrington's Hospital, George's Quay, Limerick, V94 W9YX",
        "county": "Limerick",
        "region": "HSE Mid West",
        "lat": "52.6638",
        "lon": "-8.6310",
        "source": "Google Maps + hospital website (bonsecourshealth.ie/limerick)",
    },
    "Sports Surgery Clinic": {
        "address": "Sports Surgery Clinic, Santry Demesne, Dublin 9, D09 C523",
        "county": "Dublin",
        "region": "HSE Dublin and North East",
        "lat": "53.3928",
        "lon": "-6.2486",
        "source": "Google Maps + hospital website (sportssurgeryclinic.com)",
    },
    "St Vincent's Private Hospital": {
        "address": "St Vincent's Private Hospital, Merrion Road, Dublin 4, D04 YN26",
        "county": "Dublin",
        "region": "HSE Dublin and South East",
        "lat": "53.3178",
        "lon": "-6.2198",
        "source": "Google Maps + hospital website (svph.ie)",
    },
}


# --- Main --------------------------------------------------------------------

def main():
    results = []
    errors = []

    print(f"Geocoding {len(PRIVATE_HOSPITALS)} private hospitals via Nominatim...\n")

    for h in PRIVATE_HOSPITALS:
        name = h["name"]
        query = h["query"]

        geo = geocode(query)
        if geo is None:
            if name in MANUAL_FALLBACKS:
                fb = MANUAL_FALLBACKS[name]
                print(f"  FALLBACK: {name} (Nominatim miss, using manual entry)")
                print(f"        -> {fb['county']} -> {fb['region']}")
                print(f"        Source: {fb['source']}")
                results.append({
                    "name": name,
                    "address": fb["address"],
                    "county": fb["county"],
                    "region": fb["region"],
                    "lat": fb["lat"],
                    "lon": fb["lon"],
                })
            else:
                print(f"  MISS: {name} (query: {query})")
                errors.append(name)
                results.append({
                    "name": name,
                    "address": "NOT FOUND",
                    "county": "",
                    "region": "UNKNOWN",
                    "lat": "",
                    "lon": "",
                })
        else:
            addr = geo.get("address", {})
            county = extract_county(addr)
            region = assign_region(name, county)
            display = geo.get("display_name", "")
            lat = geo.get("lat", "")
            lon = geo.get("lon", "")

            results.append({
                "name": name,
                "address": display,
                "county": county,
                "region": region,
                "lat": lat,
                "lon": lon,
            })
            print(f"  OK:   {name}")
            print(f"        -> {county} -> {region}")
            print(f"        {display[:80]}...")

        time.sleep(RATE_LIMIT_SECONDS)

    # Write CSV
    output = os.path.abspath(OUTPUT_PATH)
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "address", "county", "region", "lat", "lon"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nSaved to {output}")
    print(f"Total: {len(results)}, Errors: {len(errors)}")

    # Validation summary
    print("\n--- Validation ---")
    from collections import Counter
    region_counts = Counter(r["region"] for r in results)
    for region, count in sorted(region_counts.items()):
        names_in_region = [r["name"] for r in results if r["region"] == region]
        print(f"  {region}: {count}")
        for n in names_in_region:
            print(f"    - {n}")

    if errors:
        print(f"\n  FAILED TO GEOCODE: {errors}")
    if any(r["region"] == "UNKNOWN" for r in results):
        unknown = [r["name"] for r in results if r["region"] == "UNKNOWN"]
        print(f"\n  UNKNOWN REGION: {unknown}")


if __name__ == "__main__":
    main()
