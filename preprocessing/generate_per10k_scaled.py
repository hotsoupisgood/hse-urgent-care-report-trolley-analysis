"""
Generate wide_weekly_scaledPer10k.csv

Response: total_trolleys / (region_population / 10000)
Unit:     trolleys per 10,000 residents (per week)
Interpretation: baseline demographic normalisation. Removes the first-order
             effect of catchment size so cross-region comparisons reflect
             intensity rather than scale. Companion to the age- and
             budget-stratified scalings.
Denominator: region_population from the weekly_by_region export (2022 census
             figures attached to each region row).

Date range matches generate_per1k_over65_scaled.py / generate_beds_scaled.py
(2023-01-02 to 2026-03-30) so all v6.x scalings are directly comparable.

Note: the legacy wide_weekly_scaledPer10k.csv was previously produced by
preprocessing/cleaning.ipynb cell 36, which aggregated *daily* per-10k values
to weekly via groupby(freq='W') (Sunday-ending). This script switches to the
week_start (Monday-starting) convention used by every other generate_*_scaled
script, so column dates here are offset by one day relative to the legacy file.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'

# --- weekly trolley counts by region ----------------------------------
wr = pd.read_csv(DATA / 'raw data' / 'weekly_by_region_202604082051.csv',
                 parse_dates=['week_start'])

wr = wr[(wr['week_start'] >= '2023-01-02') & (wr['week_start'] <= '2026-03-30')]

wr['scaled'] = wr['total_trolleys'] / (wr['region_population'] / 10_000)

# pivot to wide (Region x week_start)
wide = wr.pivot(index='region', columns='week_start', values='scaled')
wide.index.name = 'Region'
wide.columns = [c.strftime('%Y-%m-%d') for c in wide.columns]

region_order = [
    'HSE Dublin and Midlands',
    'HSE Dublin and North East',
    'HSE Dublin and South East',
    'HSE Mid West',
    'HSE South West',
    'HSE West and North West',
]
wide = wide.loc[region_order]

out = DATA / 'wide_weekly_scaledPer10k.csv'
wide.to_csv(out)
print(f'Written: {out}')
print(f'Shape: {wide.shape}  (regions x weeks)')
print()
print('Value ranges per region:')
print(wide.T.describe().loc[['min', 'mean', 'max']].round(4).to_string())
