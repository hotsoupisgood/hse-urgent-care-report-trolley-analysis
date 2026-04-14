"""
Generate wide_weekly_scaledPerBudgetThousands.csv

Response: total_trolleys / (regional_budget / 1_000_000)
Unit:     trolleys per €1 billion of regional HSE budget

Budget stored in thousands of euros (e.g. 3,670,000 = €3.67B).
Dividing by 1,000,000 gives budget in billions → unit = trolleys per €1B.

Input:
  - data/raw data/weekly_by_region_202604082051.csv  (raw weekly region-level trolley counts)
  - data/2026_hr_budget.xlsx                         (HSE regional budgets, single row, regions as columns, units: €thousands)

Output:
  - data/wide_weekly_scaledPerBudgetThousands.csv    (wide: rows = regions, cols = week dates)
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'

# ── Load raw weekly data (full weeks only) ──
raw = pd.read_csv(
    DATA / 'raw data' / 'weekly_by_region_202604082051.csv',
    parse_dates=['week_start'],
)
raw = raw[raw['days_in_week'] == 7].copy()

# ── Load budget (single-row, regions as columns) ──
budget_wide = pd.read_excel(DATA / '2026_hr_budget.xlsx')
budget = budget_wide.T.reset_index()
budget.columns = ['Region', 'Budget']

# ── Merge and scale ──
df = raw.merge(budget, left_on='region', right_on='Region', how='left')

missing = df[df['Budget'].isna()]['region'].unique()
if len(missing) > 0:
    raise ValueError(f"Budget missing for regions: {list(missing)}")

df['scaled'] = df['total_trolleys'] / (df['Budget'] / 1_000_000)

# ── Pivot to wide format (rows = regions, cols = week_start dates) ──
wide = df.pivot_table(
    index='region',
    columns='week_start',
    values='scaled',
)
wide.columns = [c.strftime('%Y-%m-%d') for c in wide.columns]
wide = wide.reset_index().rename(columns={'region': 'Region'})
wide = wide.sort_values('Region').reset_index(drop=True)

# ── Save ──
out_path = DATA / 'wide_weekly_scaledPerBudgetThousands.csv'
wide.to_csv(out_path, index=False)

print(f"Wrote {out_path}")
print(f"  {wide.shape[0]} regions x {wide.shape[1] - 1} weeks")
print(f"\nFirst few values per region:")
print(wide.iloc[:, :4].to_string(index=False))
