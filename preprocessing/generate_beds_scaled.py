"""
Generate wide_weekly_scaledPerBed.csv

Response: (total_trolleys / tx_inpatient_beds_per_region) * 100
Unit:     trolleys per 100 inpatient beds (per week)
Interpretation: overcapacity rate — for every 100 inpatient beds, how many
             patients are waiting on trolleys. Trolleys represent demand that
             exceeded bed capacity, so this is a direct system-strain metric.
Denominator: sum of tx_inpatient across hospitals in each region.
             tx_inpatient chosen as the directly relevant capacity measure
             for patients awaiting inpatient admission.
             NaN hospital values are dropped before summing (2 hospitals
             missing tx_inpatient in the source CSV).

Date range matches wide_weekly_scaledPerBudgetThousands.csv (2023-01-02
to 2026-03-30) so v6.1 and v6.2 are directly comparable.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
SUPP = ROOT / 'supplementary data'

# --- beds per region ---------------------------------------------------
beds_raw = pd.read_csv(SUPP / '2025_hr_beds_per_hospital.csv')

# Source file region names lack the 'HSE ' prefix used by weekly_by_region;
# prepend so the downstream merge on region matches.
beds_raw['region'] = 'HSE ' + beds_raw['region']

beds_by_region = (beds_raw
                  .groupby('region')['tx_inpatient']
                  .sum()          # NaN hospitals silently excluded by sum()
                  .rename('inpatient_beds'))

print('Inpatient beds per region:')
print(beds_by_region.to_string())
print()

# --- weekly trolley counts by region ----------------------------------
wr = pd.read_csv(DATA / 'raw data' / 'weekly_by_region_202604082051.csv',
                 parse_dates=['week_start'])

# align date range to budget-scaled CSV
wr = wr[(wr['week_start'] >= '2023-01-02') & (wr['week_start'] <= '2026-03-30')]

# merge bed counts
wr = wr.merge(beds_by_region, left_on='region', right_index=True, how='left')

missing = wr['inpatient_beds'].isna().sum()
if missing:
    raise ValueError(f'{missing} rows have no beds mapping — check region names')

# scale: trolleys per 100 inpatient beds (overcapacity rate)
wr['scaled'] = (wr['total_trolleys'] / wr['inpatient_beds']) * 100

# pivot to wide (Region x week_start)
wide = wr.pivot(index='region', columns='week_start', values='scaled')
wide.index.name = 'Region'
wide.columns = [c.strftime('%Y-%m-%d') for c in wide.columns]

# reorder rows to match other wide CSVs
region_order = [
    'HSE Dublin and Midlands',
    'HSE Dublin and North East',
    'HSE Dublin and South East',
    'HSE Mid West',
    'HSE South West',
    'HSE West and North West',
]
wide = wide.loc[region_order]

out = DATA / 'wide_weekly_scaledPerBed.csv'
wide.to_csv(out)
print(f'Written: {out}')
print(f'Shape: {wide.shape}  (regions x weeks)')
print()
print('Value ranges per region:')
print(wide.T.describe().loc[['min', 'mean', 'max']].round(4).to_string())
