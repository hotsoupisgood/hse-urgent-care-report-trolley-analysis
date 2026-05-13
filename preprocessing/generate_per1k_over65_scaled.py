"""
Generate wide_weekly_scaledPer1kOver65.csv

Response: total_trolleys / (pop_65plus / 1000)
Unit:     trolleys per 1,000 residents aged 65+ (per week)
Interpretation: demand pressure normalised to the elderly cohort, who drive
             a disproportionate share of ED admissions. A region with high
             trolley counts but a young population looks worse on this scale
             than on per10k, and vice versa.
Denominator: pop_65plus = region_population * pct_65plus / 100
             pct_65plus per region from 2022_hr_age_dist.csv, computed as
             the unweighted mean of Male and Female percentages of population
             aged 65+. Sex-weighted population is unavailable; M:F ratio is
             ~50:50 across all regions so the unweighted mean is within ~0.1pp
             of the true overall percentage.

Date range matches generate_beds_scaled.py and generate_budget_scaled.py
(2023-01-02 to 2026-03-30) so all v6.x scalings are directly comparable.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
SUPP = ROOT / 'supplementary data'

OVER65_BINS = [
    '65 - 69 years',
    '70 - 74 years',
    '75 - 79 years',
    '80 - 84 years',
    '85 years and over',
]

# --- pct aged 65+ per region ------------------------------------------
age = pd.read_csv(SUPP / '2022_hr_age_dist.csv')
age = age[age['Age Group'].isin(OVER65_BINS)]

# % 65+ per (region, sex), then unweighted mean of M and F
pct_by_sex = age.groupby(['HSE Regions', 'Sex'])['VALUE'].sum().unstack('Sex')
pct_65 = pct_by_sex.mean(axis=1).rename('pct_65plus')

# prepend 'HSE ' to match the convention used elsewhere
pct_65.index = 'HSE ' + pct_65.index

print('Pct aged 65+ per region (mean of M and F):')
print(pct_65.round(2).to_string())
print()

# --- weekly trolley counts by region ----------------------------------
wr = pd.read_csv(DATA / 'raw data' / 'weekly_by_region_202604082051.csv',
                 parse_dates=['week_start'])

wr = wr[(wr['week_start'] >= '2023-01-02') & (wr['week_start'] <= '2026-03-30')]

# attach pct_65plus and compute pop_65plus per row
wr = wr.merge(pct_65, left_on='region', right_index=True, how='left')

missing = wr['pct_65plus'].isna().sum()
if missing:
    raise ValueError(f'{missing} rows have no pct_65plus mapping — check region names')

wr['pop_65plus'] = wr['region_population'] * wr['pct_65plus'] / 100
wr['scaled']     = wr['total_trolleys'] / (wr['pop_65plus'] / 1000)

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

out = DATA / 'wide_weekly_scaledPer1kOver65.csv'
wide.to_csv(out)
print(f'Written: {out}')
print(f'Shape: {wide.shape}  (regions x weeks)')
print()
print('Value ranges per region:')
print(wide.T.describe().loc[['min', 'mean', 'max']].round(4).to_string())
