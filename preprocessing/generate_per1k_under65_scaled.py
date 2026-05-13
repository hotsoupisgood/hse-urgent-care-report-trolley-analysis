"""
Generate wide_weekly_scaledPer1kUnder65.csv

Response: total_trolleys / (pop_under65 / 1000)
Unit:     trolleys per 1,000 residents aged under 65 (per week)
Interpretation: complement to the per1kOver65 scale. Inflates the rate in
             regions with a younger denominator. Useful as a sensitivity
             check: if a region's relative ranking is stable across both
             age-stratified denominators, the ranking is robust to age
             composition.
Denominator: pop_under65 = region_population - pop_65plus, where
             pop_65plus = region_population * pct_65plus / 100 and
             pct_65plus is the unweighted mean of Male and Female percentages
             of population aged 65+ from 2022_hr_age_dist.csv. (Sex-weighted
             population is unavailable; M:F ~50:50 across regions so the
             unweighted mean is within ~0.1pp of the true overall percentage.)

Date range matches generate_per1k_over65_scaled.py (2023-01-02 to 2026-03-30).
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

pct_by_sex = age.groupby(['HSE Regions', 'Sex'])['VALUE'].sum().unstack('Sex')
pct_65 = pct_by_sex.mean(axis=1).rename('pct_65plus')
pct_65.index = 'HSE ' + pct_65.index

print('Pct aged 65+ per region (mean of M and F):')
print(pct_65.round(2).to_string())
print()

# --- weekly trolley counts by region ----------------------------------
wr = pd.read_csv(DATA / 'raw data' / 'weekly_by_region_202604082051.csv',
                 parse_dates=['week_start'])

wr = wr[(wr['week_start'] >= '2023-01-02') & (wr['week_start'] <= '2026-03-30')]

wr = wr.merge(pct_65, left_on='region', right_index=True, how='left')

missing = wr['pct_65plus'].isna().sum()
if missing:
    raise ValueError(f'{missing} rows have no pct_65plus mapping — check region names')

wr['pop_under65'] = wr['region_population'] * (1 - wr['pct_65plus'] / 100)
wr['scaled']      = wr['total_trolleys'] / (wr['pop_under65'] / 1000)

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

out = DATA / 'wide_weekly_scaledPer1kUnder65.csv'
wide.to_csv(out)
print(f'Written: {out}')
print(f'Shape: {wide.shape}  (regions x weeks)')
print()
print('Value ranges per region:')
print(wide.T.describe().loc[['min', 'mean', 'max']].round(4).to_string())
