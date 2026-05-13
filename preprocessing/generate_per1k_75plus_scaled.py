"""
Generate wide_weekly_scaledPer1k75plus.csv

Response: total_trolleys / (pop_75plus / 1000)
Unit:     trolleys per 1,000 residents aged 75+ (per week)
Interpretation: a tighter version of the per1kOver65 scale that isolates the
             oldest cohort. Patients aged 75+ have the longest median ED LOS
             and the highest rate of trolley waits >24h, so this denominator
             corresponds more directly to the population at clinical risk
             than the broader 65+ cut. Useful as a sensitivity analysis: if
             a region's relative ranking is stable across per1kOver65 and
             per1k75plus, the ranking is robust to the upper-cohort cutoff.
Denominator: pop_75plus = region_population * pct_75plus / 100
             pct_75plus per region from 2022_hr_age_dist.csv, computed as
             the unweighted mean of Male and Female percentages of population
             aged 75+. Sex-weighted population is unavailable; M:F ratio is
             ~50:50 across all regions so the unweighted mean is within ~0.1pp
             of the true overall percentage.

Date range matches generate_per1k_over65_scaled.py (2023-01-02 to 2026-03-30)
so all v6.x scalings are directly comparable.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
SUPP = ROOT / 'supplementary data'

OVER75_BINS = [
    '75 - 79 years',
    '80 - 84 years',
    '85 years and over',
]

# --- pct aged 75+ per region ------------------------------------------
age = pd.read_csv(SUPP / '2022_hr_age_dist.csv')
age = age[age['Age Group'].isin(OVER75_BINS)]

# % 75+ per (region, sex), then unweighted mean of M and F
pct_by_sex = age.groupby(['HSE Regions', 'Sex'])['VALUE'].sum().unstack('Sex')
pct_75 = pct_by_sex.mean(axis=1).rename('pct_75plus')

# prepend 'HSE ' to match the convention used elsewhere
pct_75.index = 'HSE ' + pct_75.index

print('Pct aged 75+ per region (mean of M and F):')
print(pct_75.round(2).to_string())
print()

# --- weekly trolley counts by region ----------------------------------
wr = pd.read_csv(DATA / 'raw data' / 'weekly_by_region_202604082051.csv',
                 parse_dates=['week_start'])

wr = wr[(wr['week_start'] >= '2023-01-02') & (wr['week_start'] <= '2026-03-30')]

# attach pct_75plus and compute pop_75plus per row
wr = wr.merge(pct_75, left_on='region', right_index=True, how='left')

missing = wr['pct_75plus'].isna().sum()
if missing:
    raise ValueError(f'{missing} rows have no pct_75plus mapping — check region names')

wr['pop_75plus'] = wr['region_population'] * wr['pct_75plus'] / 100
wr['scaled']     = wr['total_trolleys'] / (wr['pop_75plus'] / 1000)

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

out = DATA / 'wide_weekly_scaledPer1k75plus.csv'
wide.to_csv(out)
print(f'Written: {out}')
print(f'Shape: {wide.shape}  (regions x weeks)')
print()
print('Value ranges per region:')
print(wide.T.describe().loc[['min', 'mean', 'max']].round(4).to_string())
