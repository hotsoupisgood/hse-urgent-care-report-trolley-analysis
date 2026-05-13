"""
Generate wide_weekly_scaledPer1kMedicalCard.csv

Response: total_trolleys / (pop_medical_card / 1000)
Unit:     trolleys per 1,000 medical-card holders (per week)
Interpretation:
    Medical card eligibility in Ireland is concentrated among low-income and
    elderly residents — both groups disproportionately drive ED demand. This
    scale normalises trolley pressure to the size of the cohort most likely
    to require unscheduled care, acting as a deprivation/need-weighted
    denominator.

Caveat:
    Eligibility rules (income thresholds, age 70+ universal coverage) mean
    the medical-card population is *not* a clean deprivation index — it
    correlates with both age and income. Read alongside per1kOver65 to
    separate elderly cohort effects from socioeconomic effects.

Denominator:
    pop_medical_card = region_population × pct_medical_card / 100
    pct from 2022_hr_medical_card_perc.csv (27%–34% across regions).

Input:
  - data/raw data/weekly_by_region_202604082051.csv  (weekly trolley counts)
  - supplementary data/2022_hr_medical_card_perc.csv (% with medical card by region)

Output:
  - data/wide_weekly_scaledPer1kMedicalCard.csv      (regions × week_start)
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
SUPP = ROOT / 'supplementary data'

REGION_ORDER = [
    'HSE Dublin and Midlands',
    'HSE Dublin and North East',
    'HSE Dublin and South East',
    'HSE Mid West',
    'HSE South West',
    'HSE West and North West',
]

# --- pct with medical card per region --------------------------------
mc = pd.read_csv(SUPP / '2022_hr_medical_card_perc.csv')
mc = mc.rename(columns={'HSE Health Regions': 'Region', 'VALUE': 'Pct'})
mc = mc[['Region', 'Pct']].drop_duplicates(subset='Region')
mc['Region'] = 'HSE ' + mc['Region']

print('Pct with medical card per region:')
print(mc.set_index('Region')['Pct'].to_string())
print()

# --- weekly trolley counts -------------------------------------------
wr = pd.read_csv(DATA / 'raw data' / 'weekly_by_region_202604082051.csv',
                 parse_dates=['week_start'])
wr = wr[wr['days_in_week'] == 7].copy()

wr = wr.merge(mc, left_on='region', right_on='Region', how='left')

missing = wr['Pct'].isna().sum()
if missing:
    raise ValueError(f'{missing} rows missing medical-card pct — check region names')

wr['pop_medical_card'] = wr['region_population'] * wr['Pct'] / 100
wr['scaled'] = wr['total_trolleys'] / (wr['pop_medical_card'] / 1000)

# --- pivot wide ------------------------------------------------------
wide = wr.pivot(index='region', columns='week_start', values='scaled')
wide.index.name = 'Region'
wide.columns = [c.strftime('%Y-%m-%d') for c in wide.columns]
wide = wide.loc[REGION_ORDER]

out = DATA / 'wide_weekly_scaledPer1kMedicalCard.csv'
wide.to_csv(out)

print(f'Written: {out}')
print(f'Shape: {wide.shape}  (regions × weeks)')
print()
print('Value ranges per region (trolleys per 1k medical-card holders):')
print(wide.T.describe().loc[['min', 'mean', 'max']].round(3).to_string())
