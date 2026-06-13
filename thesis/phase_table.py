"""Compute the annual-cycle peak-phase table from posterior samples.

Ports the phase calculation that previously lived inline in ThesisDraft_v2.Rmd
(chunks results-phase-inline, results-phase-plot, results-phase-table) into a
single source of truth. Reads the v2.8 per-10k posterior samples, computes the
per-region peak week of the annual cycle (relative to the New Year), its 95%
credible interval, the CI width, and the probability the peak falls in
meteorological winter (Dec 1 to end of Feb), then writes phase_table.csv.

The Rmd reads phase_table.csv instead of recomputing.
"""

import numpy as np
import pandas as pd

RAW_SAMPLES = "../data/models/wide_weekly_scaledPer10k/v2.8/raw_samples.csv"
OUT_CSV = "phase_table.csv"

REGIONS = [
    "HSE Dublin and Midlands",
    "HSE Dublin and North East",
    "HSE Dublin and South East",
    "HSE Mid West",
    "HSE South West",
    "HSE West and North West",
]

# Meteorological winter (Met Eireann), in weeks relative to the New Year (wk 0):
#   Dec 1     = -31 days = -31/7 weeks
#   end of Feb = +59 days = +59/7 weeks
WINTER_LO = -31 / 7
WINTER_HI = 59 / 7


def wrap52(x):
    """Wrap a week value into (-26, 26] -- the year is a 52-week circle."""
    return ((x + 26) % 52) - 26


def phase_stats(raw, i):
    """Circular peak-week statistics for region i (1-indexed)."""
    b = raw[f"beta[{i}]"].to_numpy()
    g = raw[f"gamma[{i}]"].to_numpy()

    # Peak week per sample, relative to New Year.
    peak = wrap52(np.arctan2(g, b) * 52 / (2 * np.pi))

    # Circular mean via the direction-vector trick so wrap-around is handled.
    mean_dir = np.arctan2(
        np.mean(np.sin(2 * np.pi * peak / 52)),
        np.mean(np.cos(2 * np.pi * peak / 52)),
    ) * 52 / (2 * np.pi)

    # Re-centre samples on the mean before taking quantiles.
    shifted = wrap52(peak - mean_dir)
    q_lo, q_hi = np.quantile(shifted, [0.025, 0.975])

    return {
        "region": REGIONS[i - 1],
        "mean_pk": mean_dir,
        "ci_lo": mean_dir + q_lo,
        "ci_hi": mean_dir + q_hi,
        "width": q_hi - q_lo,
        "p_winter": np.mean((peak >= WINTER_LO) & (peak <= WINTER_HI)),
    }


def main():
    raw = pd.read_csv(RAW_SAMPLES)
    tab = pd.DataFrame(phase_stats(raw, i) for i in range(1, len(REGIONS) + 1))
    tab = tab.sort_values("region").reset_index(drop=True)
    tab.to_csv(OUT_CSV, index=False)
    print(tab.to_string(index=False))


if __name__ == "__main__":
    main()
