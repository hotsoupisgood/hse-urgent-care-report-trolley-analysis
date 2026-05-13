"""
PROTOTYPE — calendar-aware New Year indicators.

Drop-in replacement for `build_event_indicators` in `pyjags_pipeline/data.py`.
The only change is how `ny_pre`, `ny_mid`, `ny_post` are placed; everything
else (cosines/sines, fr_*, mw, fr2_*) is identical.

Why
---
The current implementation uses `t % 52`, which assumes a year is exactly
364 days. The Gregorian year is ~365.25 days, and the column label is the
Sunday end-date (week covers Mon..Sun). The combined effect is that for
the current 2023-01-01 .. 2025-11-16 dataset, `ny_mid` is correctly placed
only for NY 2023; for NY 2024 and NY 2025 it sits one column too early
(see the table at the bottom of this file when run).

Approach
--------
Take the column dates as input. For each calendar year covered, find the
column whose Mon..Sun window contains Jan 1 of that year and call that
`ny_mid`. The flanking columns become `ny_pre` and `ny_post`. No more
modular arithmetic, no drift, no day-of-week sensitivity.

Caveats / things to decide
--------------------------
- t=1 in the current `wide_weekly_scaled*.csv` files is a partial week
  (only Sun 1 Jan 2023; raw `days_in_week == 1`). This function still
  flags it as `ny_mid` because Jan 1 2023 *is* in that 7-day window. If
  you want to exclude partial weeks, do that upstream by trimming the
  first column from the wide CSV — keep this function calendar-only.
- Assumes the column label is the Sunday end-date (the current convention
  in `data/wide_weekly_scaled*.csv`). If you ever switch to Mon-start
  labels, change `starts = dates - 6d` to `dates` and `ends = dates` to
  `dates + 6d`.
- `fr_*` and `fr2_*` are still hard-coded by week index. Same drift bug
  in principle; out of scope for this prototype.
"""

from pathlib import Path

import numpy as np
import pandas as pd


_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def build_event_indicators(n_weeks, regions, column_dates=None):
    """Build time vectors and event indicator arrays.

    Parameters
    ----------
    n_weeks : int
    regions : list[str]
    column_dates : list-like of datetime-parseable, optional
        Sunday end-dates of each weekly column (length n_weeks). When
        provided, NY indicators are placed by calendar. When None, falls
        back to the legacy `t % 52` placement.
    """
    t_vec = np.arange(1, n_weeks + 1)
    week_mod = t_vec % 52  # legacy fallback only

    if column_dates is None:
        ny_pre  = (week_mod == 0).astype(float)
        ny_mid  = (week_mod == 1).astype(float)
        ny_post = (week_mod == 2).astype(float)
    else:
        # Each column label is a Sunday end-date; .to_period('W-SUN') maps any
        # date to the Mon..Sun week it belongs to, so col_period[i] is the
        # period for column i and any timestamp in the same week shares it.
        col_period = pd.DatetimeIndex(pd.to_datetime(list(column_dates))).to_period('W-SUN')
        if len(col_period) != n_weeks:
            raise ValueError(
                f'column_dates length ({len(col_period)}) != n_weeks ({n_weeks})')

        years = range(col_period.start_time.year.min(),
                      col_period.end_time.year.max() + 1)
        ny_periods = pd.PeriodIndex(
            [pd.Timestamp(y, 1, 1) for y in years], freq='W-SUN')

        mid_idx  = np.where(col_period.isin(ny_periods))[0]
        ny_mid   = np.zeros(n_weeks); ny_mid[mid_idx] = 1.0
        ny_pre   = np.zeros(n_weeks)
        ny_post  = np.zeros(n_weeks)
        pre_idx  = mid_idx - 1
        post_idx = mid_idx + 1
        ny_pre[pre_idx[pre_idx >= 0]] = 1.0
        ny_post[post_idx[post_idx < n_weeks]] = 1.0

    return {
        'ny_pre':  ny_pre,
        'ny_mid':  ny_mid,
        'ny_post': ny_post,
        'fr_pre':  (t_vec == 86).astype(float),
        'fr_mid':  (t_vec == 87).astype(float),
        'fr_post': (t_vec == 88).astype(float),
        'fr2_pre': (t_vec == 85).astype(float),
        'fr2_mid': (t_vec == 86).astype(float),
        'fr2_post':(t_vec == 87).astype(float),
        'mw': np.array([1.0 if r == 'HSE Mid West' else 0.0 for r in regions]),
    }


# ---- caller-side change required (preview only, not applied here) ----------
#
# In `pyjags_pipeline/base.py::BaseModel._load_data`, change:
#
#     indicators = _data.build_event_indicators(n_weeks, regions)
#
# to:
#
#     column_dates = df_og_wide.columns.tolist()
#     indicators = _data.build_event_indicators(n_weeks, regions,
#                                               column_dates=column_dates)
#
# No other model file needs to change — they all read indicators by key.

# ---------------------------------------------------------------------------
# Validation: run this module to print legacy vs. calendar placement on the
# canonical dataset.
#
#     cd CODE && venv/bin/python3 -m pyjags_pipeline.data_calendar_proto
# ---------------------------------------------------------------------------

def _validate(data_path='data/wide_weekly_scaledPer10k.csv'):
    df = pd.read_csv(_PROJECT_ROOT / data_path)
    cols = [c for c in df.columns if c != 'Region']
    n_weeks = len(cols)
    regions = df['Region'].tolist()

    legacy   = build_event_indicators(n_weeks, regions, column_dates=None)
    calendar = build_event_indicators(n_weeks, regions, column_dates=cols)

    def show(label, ind):
        for tag in ('ny_pre', 'ny_mid', 'ny_post'):
            ts = np.where(ind[tag] == 1)[0] + 1
            dates = [cols[t-1] for t in ts]
            print(f'  {label} {tag:7s}: t={list(ts)}  dates={dates}')

    print('Legacy (t % 52):')
    show('  legacy', legacy)
    print('\nCalendar-aware:')
    show('calendar', calendar)

    # cross-region mean for sanity
    mat = df.drop(columns='Region').values.mean(axis=0)
    print('\nCross-region mean trolley rate at calendar ny_mid columns '
          '(expect a holiday trough, then surge in ny_post):')
    for tag in ('ny_pre', 'ny_mid', 'ny_post'):
        ts = np.where(calendar[tag] == 1)[0]
        for t in ts:
            print(f'  {tag:7s}  t={t+1:3d}  {cols[t]}  mean={mat[t]:6.2f}')


if __name__ == '__main__':
    _validate()
