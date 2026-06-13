# Trolley data pipeline (work in progress)

Self-contained, file-based pipeline that turns the HSE TrolleyGAR daily report
into weekly trolley counts per HSE region. Each stage is one script that reads
one file and writes one file, so the whole chain is auditable end to end.

Kept here, separate from the rest of the codebase, until it is ready to replace
the existing notebook-based preprocessing.

## Stages

| Step | Script | Reads | Writes |
|------|--------|-------|--------|
| 01 | `01_scrape.py` | HSE TrolleyGAR endpoint (live) | `output/01_daily_by_hospital_raw.csv` |
| 02 | `02_preprocess.py` | `01_daily_by_hospital_raw.csv` | `output/02_daily_by_hospital_clean.csv` |
| 03 | `03_aggregate_weekly.py` | `02_daily_by_hospital_clean.csv` | `output/03_weekly_by_hospital.csv` |
| 04 | `04_aggregate_region.py` | `03_weekly_by_hospital.csv` | `output/04_weekly_by_region.csv` |
| 05 | `05_validate_against_db.py` | steps 03 & 04 + DB exports | console report |

Run in order:

```bash
python3 01_scrape.py          # ~40 min (1,191 daily requests); output is committed, rarely re-run
python3 02_preprocess.py
python3 03_aggregate_weekly.py
python3 04_aggregate_region.py
python3 05_validate_against_db.py
```

## What each stage does

- **01 Scrape.** One HTTP GET per day from `uec.hse.ie/uec/TGAR.php?EDDATE=DD/MM/YYYY`
  (1 Jan 2023 to 5 Apr 2026). Parses the single HTML table per day. Retries
  transient server faults (504, timeout, empty page) up to 10 times, then fails
  loud. Raw output still holds the report's summary rows and any negative values.

- **02 Preprocess.** Drops the report's `<Region> Total` / `National Total` rows,
  coerces counts to integers (blank = 0), and `abs()`-es negative counts
  (impossible patient counts; data-entry artifacts, quantified in
  `negatives_report.ipynb`). Result: tidy daily counts for 42 hospitals.

- **03 Aggregate by week.** Sums daily counts into Monday-start weeks per hospital,
  recording `days_in_week` so partial weeks are visible.

- **04 Aggregate hospital to region.** Maps each of the 42 hospitals to one of the
  6 HSE health regions (fixed map embedded in the script) and sums to weekly
  regional totals.

## Validation

`05_validate_against_db.py` cross-checks steps 03 and 04 against the live
dashboard's PostgreSQL exports (`data/raw data/weekly_by_*`), which ingest the
same reports through a completely separate code path.

Result: **1025 / 1026 region-weeks and 6551 / 6552 hospital-weeks reproduce the
database exactly.** The single difference is Sligo University Hospital in the week
of 2026-03-30 (the latest, still-open week), where the HSE revised the source
value after the database had scraped it live. Not a pipeline discrepancy.

## Other files

- `negatives_report.ipynb` — lists every hospital and date with a negative raw
  count and quantifies them (93 values, all ED trolleys, 84 in 2023).
- `output/` — generated intermediate and final CSVs.
- `backfill.log` — log from the full 01 scrape run.
