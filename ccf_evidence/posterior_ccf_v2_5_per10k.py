"""
Cross-correlation matrix between v2.5 model residuals (posterior mean),
fit on per-10k weekly trolley counts.

Loads residuals_posterior_mean.csv and computes inter-region CCFs with
statsmodels.tsa.stattools.ccf. Reference bands are drawn at +/- 1.96/sqrt(T)
(white-noise approximation; valid only insofar as the v2.5 model has whitened
the residuals).

Run from project root:
    python3 ccf_evidence/posterior_ccf_v2_5_per10k.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import ccf as sm_ccf


RESID_PATH = PROJECT_ROOT / 'data/models/wide_weekly_scaledPer10k/v2.5/residuals_posterior_mean.csv'
OUT_DIR = PROJECT_ROOT / 'ccf_evidence'
FIG_PATH = OUT_DIR / 'figures/posterior_ccf_v2_5_per10k.png'

MAX_LAG = 26   # weeks (~6 months)

REGION_DISPLAY_ORDER = [
    'HSE Dublin and Midlands',
    'HSE Dublin and North East',
    'HSE Dublin and South East',
    'HSE West and North West',
    'HSE South West',
    'HSE Mid West',
]
BAR_COLOR = '#444444'


def two_sided_ccf(x, y, max_lag):
    """CCF at lags -max_lag..+max_lag using statsmodels.

    sm_ccf(x, y) returns r[k] = corr(x_t, y_{t+k}) for k = 0..T-1.
    Negative lags come from the symmetry corr(x_t, y_{t-k}) = sm_ccf(y, x)[k].
    """
    pos = sm_ccf(x, y, adjusted=False, fft=True)[: max_lag + 1]
    neg = sm_ccf(y, x, adjusted=False, fft=True)[1: max_lag + 1][::-1]
    return np.concatenate([neg, pos])


def main():
    resid = pd.read_csv(RESID_PATH)[REGION_DISPLAY_ORDER]
    T = len(resid)
    ci = 1.96 / np.sqrt(T)
    lags = np.arange(-MAX_LAG, MAX_LAG + 1)
    R = len(REGION_DISPLAY_ORDER)
    labels = [r.replace('HSE ', '') for r in REGION_DISPLAY_ORDER]

    fig, axes = plt.subplots(R, R, figsize=(18, 18), dpi=180, sharex=True, sharey=True)
    xtick_step = 4    # tick every 4 weeks across the +/- MAX_LAG window
    for i, ri in enumerate(REGION_DISPLAY_ORDER):
        for j, rj in enumerate(REGION_DISPLAY_ORDER):
            ax = axes[i, j]
            # Hide upper triangle (duplicates of the lower triangle by symmetry
            # ccf[i, j, k] == ccf[j, i, -k]) and diagonal (auto-correlation)
            if j >= i:
                ax.set_visible(False)
                continue
            r = two_sided_ccf(resid[ri].values, resid[rj].values, MAX_LAG)
            ax.bar(lags, r, width=1.0, color=BAR_COLOR, alpha=0.85, linewidth=0)
            ax.axhspan(-ci, ci, color='#1f77b4', alpha=0.18, linewidth=0)
            ax.axhline(0, color='black', linewidth=0.4)
            if i != j:
                for k in np.where(np.abs(r) > ci)[0]:
                    lag_k = int(lags[k])
                    val_k = float(r[k])
                    y_text = val_k + 0.035 if val_k >= 0 else val_k - 0.035
                    va = 'bottom' if val_k >= 0 else 'top'
                    ax.text(lag_k, y_text, f'{lag_k}',
                            ha='center', va=va, fontsize=8)
            ax.set_ylim(-0.5, 0.5)
            ax.set_xlim(-MAX_LAG, MAX_LAG)
            ax.set_xticks(np.arange(
                -(MAX_LAG // xtick_step) * xtick_step,
                (MAX_LAG // xtick_step) * xtick_step + 1,
                xtick_step,
            ))
            if i == R - 1:
                ax.set_xlabel(labels[j], fontsize=9)
            if j == 0:
                ax.set_ylabel(labels[i], fontsize=9, rotation=0,
                              ha='right', va='center', labelpad=35)
            ax.tick_params(labelsize=7, labelbottom=True)

    fig.text(0.5, -0.005,
             'Lag (weeks) -- column region leads row region at positive lags',
             ha='center', fontsize=10)
    fig.text(-0.005, 0.5, 'Cross-correlation',
             va='center', rotation='vertical', fontsize=10)
    fig.suptitle(
        f'Cross-correlation of v2.5 residuals (posterior mean, per-10k, +/-{MAX_LAG} weeks, T={T})',
        fontsize=12, y=1.005,
    )
    fig.tight_layout()
    fig.savefig(FIG_PATH, bbox_inches='tight')
    print(f'Saved -> {FIG_PATH}')


if __name__ == '__main__':
    main()
