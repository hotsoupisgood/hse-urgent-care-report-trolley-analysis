"""
Generate wide_weekly_scaledPerBudgetBillionsPer10k.csv

Response: total_trolleys / (budget_billions / (population / 10_000))
Unit:     trolleys per (€1B of regional HSE budget per 10,000 population)

Denominator is budget-per-capita expressed in billions per 10k people,
so the scaling jointly accounts for both funding level and catchment size.

Budget stored in thousands of euros (e.g. 3,670,000 = €3.67B).
  budget_billions      = Budget / 1_000_000
  population_per_10k   = population / 10_000
  denominator          = budget_billions / population_per_10k

Input:
  - data/raw data/weekly_by_region_202604082051.csv  (raw weekly region-level trolley counts)
  - data/2026_hr_budget.xlsx                         (HSE regional budgets, single row, regions as columns, units: €thousands)
  - data/encatchment_areas.csv                       (HSE region populations)

Output:
  - data/wide_weekly_scaledPerBudgetBillionsPer10k.csv  (wide: rows = regions, cols = week dates)
"""

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'

# ── Load raw weekly data (full weeks only) ──────────────────────────────────
raw = pd.read_csv(
    DATA / 'raw data' / 'weekly_by_region_202604082051.csv',
    parse_dates=['week_start'],
)
raw = raw[raw['days_in_week'] == 7].copy()

# ── Load budget (single-row xlsx, regions as columns, values in €thousands) ─
budget_wide = pd.read_excel(DATA / '2026_hr_budget.xlsx')
budget = budget_wide.T.reset_index()
budget.columns = ['Region', 'Budget_thousands']
budget['budget_billions'] = budget['Budget_thousands'] / 1_000_000

# ── Load population ─────────────────────────────────────────────────────────
pop = pd.read_csv(DATA / 'encatchment_areas.csv')
pop.columns = ['Region', 'Population']
# drop duplicate rows if present
pop = pop.drop_duplicates(subset='Region')

# ── Build denominator table ─────────────────────────────────────────────────
denom = budget.merge(pop, on='Region', how='left')

missing_pop = denom[denom['Population'].isna()]['Region'].tolist()
if missing_pop:
    raise ValueError(f"Population missing for regions: {missing_pop}")

# denominator: budget_billions per 10k people
denom['denominator'] = denom['budget_billions'] / (denom['Population'] / 10_000)

print("Denominator (€1B budget per 10k population) by region:")
print(denom[['Region', 'budget_billions', 'Population', 'denominator']].to_string(index=False))
print()

# ── Merge denominator into weekly data ──────────────────────────────────────
df = raw.merge(denom[['Region', 'denominator']], left_on='region', right_on='Region', how='left')

missing_denom = df[df['denominator'].isna()]['region'].unique()
if len(missing_denom) > 0:
    raise ValueError(f"Denominator missing for regions: {list(missing_denom)}")

df['scaled'] = df['total_trolleys'] / df['denominator']

# ── Pivot to wide format (rows = regions, cols = week_start dates) ──────────
wide = df.pivot_table(
    index='region',
    columns='week_start',
    values='scaled',
)
wide.columns = [c.strftime('%Y-%m-%d') for c in wide.columns]
wide = wide.reset_index().rename(columns={'region': 'Region'})
wide = wide.sort_values('Region').reset_index(drop=True)

# ── Save ────────────────────────────────────────────────────────────────────
out_path = DATA / 'wide_weekly_scaledPerBudgetBillionsPer10k.csv'
wide.to_csv(out_path, index=False)

print(f"Wrote {out_path}")
print(f"  {wide.shape[0]} regions x {wide.shape[1] - 1} weeks")
print(f"\nFirst few values per region:")
print(wide.iloc[:, :4].to_string(index=False))
