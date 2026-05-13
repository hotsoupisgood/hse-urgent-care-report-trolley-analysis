"""
Generate wide_weekly_surge_scaledPer10k.csv

Response: surge_capacity_in_use / (region_population / 10_000)
Unit:     surge-bed-days per 10,000 residents (per week)
Interpretation: weekly volume of "Surge Capacity in Use" beds (HSE TrolleyGAR
             14:00 daily report) summed across hospitals and days in the
             region, normalised to population. A standalone demand-pressure
             variable distinct from the trolley response.

Aggregation:
  - surge_capacity_in_use in weekly_by_region is already the sum across
    daily hospital reports within the region-week (matches user's
    "sum across days and hospitals" choice).
  - Full weeks only (days_in_week == 7).
  - Date range 2023-01-02 to 2026-03-30 to align with other v6.x scalings.

Input:
  - data/raw data/weekly_by_region_202604082051.csv

Output:
  - data/wide_weekly_surge_scaledPer10k.csv  (rows = regions, cols = week dates)
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'

wr = pd.read_csv(
    DATA / 'raw data' / 'weekly_by_region_202604082051.csv',
    parse_dates=['week_start'],
)

wr = wr[wr['days_in_week'] == 7].copy()
wr = wr[(wr['week_start'] >= '2023-01-02') & (wr['week_start'] <= '2026-03-30')]

wr['scaled'] = wr['surge_capacity_in_use'] / (wr['region_population'] / 10_000)

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

out = DATA / 'wide_weekly_surge_scaledPer10k.csv'
wide.to_csv(out)
print(f'Written: {out}')
print(f'Shape: {wide.shape}  (regions x weeks)')
print()
print('Value ranges per region (surge-bed-days per 10k people per week):')
print(wide.T.describe().loc[['min', 'mean', 'max']].round(3).to_string())
