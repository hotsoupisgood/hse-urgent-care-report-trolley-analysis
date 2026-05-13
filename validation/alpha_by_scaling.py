"""
Compare per-region alpha (intercept) across input scalings for a fixed model.

Motivation: ranks are identical across PerBed and PerBudgetThousands. We
suspected a substantive coincidence; in fact bed counts and regional budget
are highly correlated (Pearson 0.97, Spearman 0.94), so any region-level
location parameter gets pulled the same way.

This script visualises the alpha posteriors for v2.5 across the four
scalings on a shared region axis. To make scalings visually comparable
despite different units, alpha is reported as a z-score across regions
within each scaling (mean across regions = 0, SD across regions = 1)
using posterior means; the 95% CI is shown in the same standardised
units (CI half-widths divided by the across-region SD of the posterior
means for that scaling).
"""

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
MODELS = ROOT / 'data' / 'models'
VERSION = 'v2.5'

REGION_ORDER = [
    'HSE Dublin and Midlands',
    'HSE Dublin and North East',
    'HSE Dublin and South East',
    'HSE Mid West',
    'HSE South West',
    'HSE West and North West',
]
SHORT = {
    'HSE Dublin and Midlands':   'D&M',
    'HSE Dublin and North East': 'D&NE',
    'HSE Dublin and South East': 'D&SE',
    'HSE Mid West':              'MW',
    'HSE South West':            'SW',
    'HSE West and North West':   'W&NW',
}

SCALINGS = [
    ('wide_weekly_scaledPer10k',          'per 10k pop'),
    ('wide_weekly_scaledPer1kOver65',     'per 1k over-65'),
    ('wide_weekly_scaledPerBed',          'per inpatient bed (×100)'),
    ('wide_weekly_scaledPerBudgetThousands', 'per €1B budget'),
]


def load_alpha(scaling_dir: str) -> pd.DataFrame:
    f = MODELS / scaling_dir / VERSION / 'raw_samples.csv'
    cols = [f'alpha[{i}]' for i in range(1, 7)]
    s = pd.read_csv(f, usecols=cols)
    s.columns = REGION_ORDER
    return s


def summarise(samples: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        'mean': samples.mean(),
        'lo':   samples.quantile(0.025),
        'hi':   samples.quantile(0.975),
    })


def main():
    raw = {label: summarise(load_alpha(d)) for d, label in SCALINGS}

    # Native-units table (audit trail)
    native = pd.concat({k: v for k, v in raw.items()}, axis=1)
    native.index = [SHORT[r] for r in native.index]
    print("\nAlpha posterior (native units, v2.5):")
    print(native.round(3).to_string())

    # Standardise within each scaling for a comparable plot
    std = {}
    for label, df in raw.items():
        sd = df['mean'].std(ddof=0)
        mu = df['mean'].mean()
        std[label] = pd.DataFrame({
            'z':     (df['mean'] - mu) / sd,
            'z_lo':  (df['lo']   - mu) / sd,
            'z_hi':  (df['hi']   - mu) / sd,
        })

    # Spearman of alpha-mean across scalings (rank stability)
    rank_tbl = pd.DataFrame({label: df['mean'] for label, df in raw.items()}).rank()
    print("\nSpearman rank correlation between scalings (alpha posterior mean):")
    print(rank_tbl.corr(method='spearman').round(3).to_string())

    # ---- plot ---------------------------------------------------------
    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(REGION_ORDER))
    short_labels = [SHORT[r] for r in REGION_ORDER]

    cmap = plt.get_cmap('tab10')
    jitter = np.linspace(-0.12, 0.12, len(SCALINGS))

    for i, (_, label) in enumerate(SCALINGS):
        d = std[label].loc[REGION_ORDER]
        xj = x + jitter[i]
        yerr = np.vstack([d['z'] - d['z_lo'], d['z_hi'] - d['z']])
        ax.errorbar(
            xj, d['z'], yerr=yerr,
            fmt='o-', color=cmap(i), label=label,
            alpha=0.55, lw=1.6, ms=5, capsize=3,
        )

    ax.axhline(0, color='black', lw=0.5, alpha=0.4)
    ax.set_xticks(x)
    ax.set_xticklabels(short_labels)
    ax.set_xlabel('Region')
    ax.set_ylabel('alpha (standardised across regions, per scaling)')
    ax.set_title(f'v2.5 alpha posteriors across input scalings\n'
                 f'(z-scored within scaling so shapes are comparable)')
    ax.legend(loc='best', frameon=False, fontsize=9)
    ax.grid(alpha=0.25, linestyle=':')
    fig.tight_layout()

    out = ROOT / 'data' / 'misc_plots' / 'alpha_by_scaling_v2_5.png'
    fig.savefig(out, dpi=170)
    print(f"\nWrote {out}")

    # ---- also save the native-units side-by-side as a 2nd figure -----
    fig2, axes = plt.subplots(1, len(SCALINGS), figsize=(14, 4), sharey=False)
    for ax2, (_, label), color_idx in zip(axes, SCALINGS, range(len(SCALINGS))):
        d = raw[label].loc[REGION_ORDER]
        yerr = np.vstack([d['mean'] - d['lo'], d['hi'] - d['mean']])
        ax2.errorbar(
            x, d['mean'], yerr=yerr,
            fmt='o-', color=cmap(color_idx),
            alpha=0.7, lw=1.5, ms=5, capsize=3,
        )
        ax2.set_xticks(x)
        ax2.set_xticklabels(short_labels, rotation=30, ha='right')
        ax2.set_title(label, fontsize=10)
        ax2.grid(alpha=0.25, linestyle=':')
    axes[0].set_ylabel('alpha (native units)')
    fig2.suptitle('v2.5 alpha posteriors per scaling (native units)', y=1.02)
    fig2.tight_layout()
    out2 = ROOT / 'data' / 'misc_plots' / 'alpha_by_scaling_v2_5_native.png'
    fig2.savefig(out2, dpi=170, bbox_inches='tight')
    print(f"Wrote {out2}")


if __name__ == '__main__':
    main()
