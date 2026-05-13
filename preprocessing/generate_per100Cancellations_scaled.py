"""
Generate wide_weekly_scaledPer100Cancellations.csv

Response: total_trolleys / (cancellations_per_week / 100)
Unit:     trolleys per 100 hospital-initiated cancellations (per week)
Interpretation:
    Capacity-strain proxy: high values = ED demand outpacing the rate at which
    the same region is cancelling/deferring planned activity. Cancellations are
    partly downstream of ED pressure (HSE acknowledges this in PQ 1907/25), so
    this ratio should be read as a co-indicator of strain, not as a clean
    independent denominator like population or beds.

Denominator: HSE quarterly hospital-initiated cancellations from PQ 1907/25,
    aggregated hospital -> region using the mapping in
    2025_hr_beds_per_hospital.csv. Quarterly counts are spread to a daily rate
    (count / days_in_quarter) and re-aggregated to the trolley-weekly grid so
    that weeks crossing quarter boundaries are handled correctly.

Date range: 2023-01-02 to 2024-12-30 (Mondays).
    Lower bound: PDF data for 2022 is incomplete per HSE cover letter and not
    comparable; dropped.
    Upper bound: PDF stops at 2024 Q4; later weeks have no cancellation
    denominator.

Caveats:
    * Mid West cancellation reporting drops sharply in 2024 (UMH Limerick stops
      reporting; UH Limerick volatile). Mid West values on this scale are
      inflated relative to other regions and should be interpreted with care.
    * Daily-uniform spreading assumes cancellations are evenly distributed in a
      quarter. Real cancellations likely peak alongside winter ED pressure, so
      this smoothing dampens any winter signal in the denominator.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data'
SUPP = ROOT / 'supplementary data'

START = '2023-01-02'   # Monday
END   = '2024-12-30'   # last Monday whose week ends inside 2024

REGION_ORDER = [
    'HSE Dublin and Midlands',
    'HSE Dublin and North East',
    'HSE Dublin and South East',
    'HSE Mid West',
    'HSE South West',
    'HSE West and North West',
]

# --- 1. Quarterly cancellations per region ----------------------------
canc = pd.read_csv(SUPP / 'cancellations_quarterly_by_hospital.csv')
canc = canc[canc['Year'] >= 2023]   # drop 2022

region_qtr = (
    canc.groupby(['Region', 'Year', 'Quarter'])['Cancellations']
    .sum()
    .reset_index()
)
region_qtr['Region'] = 'HSE ' + region_qtr['Region']
region_qtr['quarter_start'] = pd.to_datetime(
    region_qtr['Year'].astype(str)
    + '-' + ((region_qtr['Quarter'] - 1) * 3 + 1).astype(str).str.zfill(2)
    + '-01'
)
region_qtr['quarter_end'] = (
    region_qtr['quarter_start'] + pd.offsets.QuarterEnd(0)
).dt.normalize()
region_qtr['days_in_quarter'] = (
    (region_qtr['quarter_end'] - region_qtr['quarter_start']).dt.days + 1
)
region_qtr['daily_rate'] = (
    region_qtr['Cancellations'] / region_qtr['days_in_quarter']
)

# --- 2. Daily series per region (Jan 2023 – Dec 2024) -----------------
daily = []
for region, sub in region_qtr.groupby('Region'):
    for _, row in sub.iterrows():
        idx = pd.date_range(row['quarter_start'], row['quarter_end'], freq='D')
        daily.append(pd.DataFrame({
            'Region': region,
            'date': idx,
            'cancellations_daily': row['daily_rate'],
        }))
daily = pd.concat(daily, ignore_index=True)

# --- 3. Trolley weekly data ------------------------------------------
wr = pd.read_csv(DATA / 'raw data' / 'weekly_by_region_202604082051.csv',
                 parse_dates=['week_start'])
wr = wr[(wr['week_start'] >= START) & (wr['week_start'] <= END)]

# Aggregate daily cancellations onto each week_start (sum over the 7 days)
daily['week_start'] = daily['date'] - pd.to_timedelta(daily['date'].dt.weekday, unit='D')
weekly_canc = (
    daily.groupby(['Region', 'week_start'])['cancellations_daily'].sum()
    .reset_index()
    .rename(columns={'cancellations_daily': 'cancellations_week'})
)

merged = wr.merge(weekly_canc, left_on=['region', 'week_start'],
                  right_on=['Region', 'week_start'], how='left')

missing = merged['cancellations_week'].isna().sum()
if missing:
    raise ValueError(f'{missing} weeks have no cancellation denominator')

# --- 4. Ratio scale --------------------------------------------------
merged['scaled'] = merged['total_trolleys'] / (merged['cancellations_week'] / 100)

wide = merged.pivot(index='region', columns='week_start', values='scaled')
wide.index.name = 'Region'
wide.columns = [c.strftime('%Y-%m-%d') for c in wide.columns]
wide = wide.loc[REGION_ORDER]

out = DATA / 'wide_weekly_scaledPer100Cancellations.csv'
wide.to_csv(out)

print(f'Written: {out}')
print(f'Shape: {wide.shape}  (regions x weeks)')
print()
print('Value ranges per region (trolleys per 100 cancellations):')
print(wide.T.describe().loc[['min', 'mean', 'max']].round(2).to_string())
print()
print('Sanity check — region totals 2023+2024 cancellations:')
print(canc[canc['Year'] >= 2023].groupby('Region')['Cancellations'].sum().to_string())
