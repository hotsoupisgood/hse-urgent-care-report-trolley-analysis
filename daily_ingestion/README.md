# HSE TrolleyGAR — Daily Ingestion Pipeline

Scrapes daily Irish HSE emergency department trolley data into PostgreSQL, runs analysis, and serves an interactive dashboard.

## Project Structure

```
daily_ingestion/
    config.py              # DB connection settings, hospital/region mappings
    setup_db.py            # Create database, tables, views (idempotent)
    backfill.py            # One-time historical CSV import
    scraper.py             # Scrape HSE TrolleyGAR HTML page for a given date
    ingest.py              # Scrape + insert into PostgreSQL (daily driver)
    analysis/
        queries.py         # SQL queries -> DataFrames (psycopg2 + pd.read_sql)
        pacf.py            # PACF computation via statsmodels
        weekday.py         # Mean trolleys by day-of-week
    dashboard/
        app.py             # Main Dash app (two tabs: Data + Modeling)
        data_tab.py        # Data tab: map, time series, PACF, weekday charts
        modeling_tab.py    # Modeling tab: DIC, alpha map, parameters, sig tests
        hse_regions.geojson
        run.sh             # Launch script
    scripts/
        parse_samples.py   # Parse Bayesian model raw_samples.csv into parameter CSVs
    tests/
        conftest.py        # Shared fixtures (mock DataFrames, no DB needed)
        test_stats.py      # Data quality tests
        test_cleaning.py   # Scraper cleaning tests
        test_analysis.py   # PACF and weekday module tests
```

## Setup

### 1. Install PostgreSQL

```bash
brew install postgresql@17
brew services start postgresql@17
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Create database and tables

```bash
python setup_db.py
```

Creates `hse_trolleygar` database, tables (`hospitals`, `region_populations`, `trolley_data`), weekly summary views, and seeds reference data. Idempotent.

### 4. Backfill historical data

```bash
python backfill.py
```

Imports `../data/uec_data_2023_2025_full_with_regions.csv` into PostgreSQL. Safe to re-run.

## Daily Ingestion

```bash
# Catch up: scrape from last DB date through today (default)
python ingest.py

# Single date
python ingest.py --mode date --date 15/01/2024

# Date range
python ingest.py --mode range --start-date 01/01/2024 --end-date 31/01/2024
```

All inserts use `ON CONFLICT DO NOTHING` — re-running the same date is a no-op.

## Dashboard

```bash
cd dashboard && bash run.sh
# -> http://127.0.0.1:8050
```

**Data tab** (default): choropleth map (latest day), time series with LOWESS smoothing, PACF grid, weekday means. Toggle between count and per-10k rate.

**Modeling tab**: DIC comparison across models, alpha map, parameter tables, Bonferroni significance tests, Gelman-Rubin diagnostics.

## Bayesian Model Pipeline

### Running models (R)

Models are R Markdown files in `../bayes_models/` using JAGS:

```bash
# From bayes_models/ directory, knit in R:
Rscript -e "rmarkdown::render('Model_V1.Rmd')"
Rscript -e "rmarkdown::render('Model_V2.Rmd')"
```

Each model writes to `../data/models/<version>/`:
- `raw_samples.csv` — MCMC posterior samples
- `dic.csv` — Deviance Information Criterion
- `gelman.csv` — Gelman-Rubin convergence diagnostics

### Parsing model output

```bash
python scripts/parse_samples.py
```

Scans `../data/models/` for folders containing `raw_samples.csv` and produces:
- Per-parameter summaries: `alpha.csv`, `beta.csv`, `gamma.csv`, `tau.csv`, `phi.csv`
- Derived quantities: `amplitude.csv`, `phase.csv`
- Overall significance tests (Bonferroni, 6 regions): `sig_overall_<param>.csv`
- Pairwise significance tests (Bonferroni, 15 pairs): `sig_pairwise_<param>.csv`

## Tests

```bash
python -m pytest tests/ -v
```

## Configuration

Edit `config.py` to change database connection (host, port, user, password).

## Schema

- **hospitals** — 42 hospitals mapped to 6 HSE regions
- **region_populations** — population per region (for per-capita rates)
- **trolley_data** — daily metrics per hospital, unique on `(hospital_id, report_date)`
- **weekly_by_hospital** / **weekly_by_region** — views (always fresh)

---

## Airflow Pipeline Design

A proposed Apache Airflow DAG to automate the full pipeline.

### DAG: `hse_trolleygar_daily` (runs daily at 15:00)

```
scrape_and_ingest  ->  run_tests  ->  refresh_dashboard_cache
```

| Task | Operator | What it does |
|------|----------|-------------|
| `scrape_and_ingest` | `BashOperator` | `python ingest.py` (catchup mode) |
| `run_tests` | `BashOperator` | `python -m pytest tests/test_stats.py` on the new day's data |
| `refresh_dashboard_cache` | `PythonOperator` | Optional: warm any startup caches / notify |

### DAG: `hse_trolleygar_model_refit` (runs monthly or on-demand)

```
export_training_data  ->  run_jags_model  ->  parse_samples  ->  notify
```

| Task | Operator | What it does |
|------|----------|-------------|
| `export_training_data` | `PythonOperator` | Query PostgreSQL, write CSV for R |
| `run_jags_model` | `BashOperator` | `Rscript -e "rmarkdown::render('Model_V1.Rmd')"` |
| `parse_samples` | `BashOperator` | `python scripts/parse_samples.py` |
| `notify` | `PythonOperator` | Log/email completion, new DIC values |

### Considerations

- **HSE site availability**: The scraper depends on `https://www.hse.ie/eng/services/news/media/pressrel/trolley-figures/` being up. Add retries with exponential backoff (3 attempts, 5-minute intervals). Weekends/bank holidays may have no data — the scraper already handles empty pages gracefully.
- **Idempotency**: All inserts use `ON CONFLICT DO NOTHING`, so retries and backfills are safe. The daily DAG can use `catchup=True` to auto-recover missed days.
- **Database credentials**: Move from `config.py` hardcoded values to Airflow Variables or Connections. Use `PostgresHook` instead of raw `psycopg2.connect()` in Airflow tasks.
- **Dashboard deployment**: The Dash app currently runs as a dev server. For production, serve behind Gunicorn (`gunicorn dashboard.app:app.server`) and use a process manager (systemd/supervisor). The dashboard reads from PostgreSQL on each callback, so it always shows current data without needing a restart.

### R Model Challenges

- **R environment**: The Airflow worker needs R, JAGS, and the required R packages (`rjags`, `dplyr`, `tidyr`, `ggplot2`, `tibble`, `stringr`). Easiest approach: build a Docker image with both Python and R, or use a dedicated R worker node.
- **Long runtime**: MCMC fitting takes 10-30+ minutes depending on chain length and model complexity. Set generous Airflow task timeouts (e.g. `execution_timeout=timedelta(hours=1)`). Mark the task as `pool='heavy_compute'` with a single slot to avoid parallel model runs competing for resources.
- **Data handoff**: The R models currently read from static CSVs (`wide_weekly_scaledPer10k.csv`). The `export_training_data` task should query PostgreSQL and write a fresh CSV in the format the Rmd expects, so models always train on the latest data.
- **Model versioning**: Each run should write to a timestamped or versioned subfolder under `data/models/` (e.g. `v1_20260217/`) so previous results are preserved and the dashboard can compare across runs.
- **Triggering**: Model refits don't need to run daily — monthly or on a manual trigger (`TriggerDagRunOperator` or Airflow UI) is sufficient. A sensor could trigger a refit after N new days of data accumulate.
