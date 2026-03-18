"""
Parse raw_samples.csv for each model into separate parameter CSVs,
derived quantities, and significance tests with Bonferroni correction.

For each model folder (v1, v2, etc.) that contains raw_samples.csv,
this script produces:
  Parameter summaries (mean, sd, 2.5%, 97.5%):
    summary.csv, alpha.csv, beta.csv, gamma.csv, tau.csv, phi.csv, ...

  Derived quantities:
    amplitude.csv     sqrt(beta^2 + gamma^2)
    phase.csv         atan2(-gamma, beta)

  Overall significance (H0: param = 0, Bonferroni for 6 regions):
    sig_overall_<param>.csv

  Pairwise significance (H0: region_i - region_j = 0, Bonferroni for C(6,2)=15):
    sig_pairwise_<param>.csv

Run:
  python scripts/parse_samples.py
"""
import os
import re
import pandas as pd
import numpy as np
from itertools import combinations

MODELS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data', 'models')

REGIONS = [
    'HSE Dublin and Midlands',
    'HSE Dublin and North East',
    'HSE Dublin and South East',
    'HSE Mid West',
    'HSE South West',
    'HSE West and North West',
]
N_REGION = len(REGIONS)
ALPHA = 0.05


def load_scalar_samples(model_dir):
    """Load raw_samples.csv, dropping fullmod/mu/resid matrix columns."""
    path = os.path.join(model_dir, 'raw_samples.csv')
    header = pd.read_csv(path, nrows=0).columns.tolist()
    keep = [c for c in header
            if not c.startswith(('fullmod[', 'mu[', 'resid['))]
    return pd.read_csv(path, usecols=keep)


def detect_indexed_params(df):
    """Return dict: {prefix: [col1, col2, ...]} sorted by index."""
    indexed = {}
    for col in df.columns:
        m = re.match(r'^(.+?)\[(\d+)\]$', col)
        if m:
            indexed.setdefault(m.group(1), []).append(col)
    for k in indexed:
        indexed[k] = sorted(
            indexed[k],
            key=lambda c: int(re.search(r'\[(\d+)\]', c).group(1))
        )
    return indexed


def detect_scalar_params(df):
    """Return list of non-indexed parameter names."""
    return [c for c in df.columns if not re.match(r'.+\[\d+\]$', c)]


# ── Summaries ────────────────────────────────────────────────────────
def summarise_indexed(df, cols, regions=None):
    rows = []
    for i, col in enumerate(cols):
        v = df[col]
        row = {
            'Mean': round(v.mean(), 4),
            'SD': round(v.std(), 4),
            '2.5%': round(v.quantile(0.025), 4),
            '97.5%': round(v.quantile(0.975), 4),
        }
        if regions and i < len(regions):
            row['Region'] = regions[i]
        rows.append(row)
    result = pd.DataFrame(rows)
    if 'Region' in result.columns:
        result = result[['Region'] + [c for c in result.columns if c != 'Region']]
    return result


def summarise_scalar(df, col):
    v = df[col]
    return pd.DataFrame([{
        'Mean': round(v.mean(), 4),
        'SD': round(v.std(), 4),
        '2.5%': round(v.quantile(0.025), 4),
        '97.5%': round(v.quantile(0.975), 4),
    }])


# ── Significance tests ──────────────────────────────────────────────
def overall_sig(samples_dict, n_tests):
    """H0: param = 0 for each region, Bonferroni corrected."""
    alpha_adj = ALPHA / n_tests
    lo_q = alpha_adj / 2
    hi_q = 1 - alpha_adj / 2
    lo_label = f'{lo_q*100:.2f}%'
    hi_label = f'{hi_q*100:.2f}%'

    rows = []
    for region, vals in samples_dict.items():
        ci_lo, ci_hi = np.quantile(vals, [lo_q, hi_q])
        rows.append({
            'Region': region,
            'Mean': round(np.mean(vals), 4),
            lo_label: round(ci_lo, 4),
            hi_label: round(ci_hi, 4),
            'Sig': 'Yes' if ci_lo > 0 or ci_hi < 0 else 'No',
        })
    return pd.DataFrame(rows).sort_values('Mean', ascending=False)


def pairwise_sig(samples_dict, n_comparisons):
    """H0: region_i - region_j = 0, Bonferroni corrected."""
    alpha_adj = ALPHA / n_comparisons
    lo_q = alpha_adj / 2
    hi_q = 1 - alpha_adj / 2
    lo_label = f'{lo_q*100:.2f}%'
    hi_label = f'{hi_q*100:.2f}%'

    region_list = list(samples_dict.keys())
    rows = []
    for r1, r2 in combinations(range(len(region_list)), 2):
        diff = samples_dict[region_list[r1]] - samples_dict[region_list[r2]]
        ci_lo, ci_hi = np.quantile(diff, [lo_q, hi_q])
        rows.append({
            'Region1': region_list[r1],
            'Region2': region_list[r2],
            'MeanDiff': round(np.mean(diff), 4),
            lo_label: round(ci_lo, 4),
            hi_label: round(ci_hi, 4),
            'Sig': 'Yes' if ci_lo > 0 or ci_hi < 0 else 'No',
        })
    return pd.DataFrame(rows)


def extract_region_samples(df, prefix):
    """Pull samples for an indexed param into {region: array} dict."""
    d = {}
    for i in range(N_REGION):
        col = f'{prefix}[{i+1}]'
        if col in df.columns:
            d[REGIONS[i]] = df[col].values
    return d


# ── Derived quantities ───────────────────────────────────────────────
def compute_amplitude(df):
    """sqrt(beta^2 + gamma^2) per region."""
    d = {}
    for i in range(N_REGION):
        b = df[f'beta[{i+1}]'].values
        g = df[f'gamma[{i+1}]'].values
        d[REGIONS[i]] = np.sqrt(b**2 + g**2)
    return d


def compute_phase(df):
    """atan2(-gamma, beta) per region."""
    d = {}
    for i in range(N_REGION):
        b = df[f'beta[{i+1}]'].values
        g = df[f'gamma[{i+1}]'].values
        d[REGIONS[i]] = np.arctan2(-g, b)
    return d


# ── Residuals ────────────────────────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data')


def compute_residuals(model_dir):
    """Compute residuals from fitted.csv (saved by R) and observed data.

    residual = observed - fitted.  Model-agnostic: works for any version
    as long as fitted.csv exists.

    Returns DataFrame with columns: Region, time, residual
    """
    fitted_path = os.path.join(model_dir, 'fitted.csv')
    obs_path = os.path.join(DATA_DIR, 'wide_weekly_scaledPer10k.csv')
    if not os.path.isfile(fitted_path) or not os.path.isfile(obs_path):
        return None

    fitted = pd.read_csv(fitted_path)  # Region, time, fitted
    obs_wide = pd.read_csv(obs_path)

    # Pivot observed to long format matching fitted
    regions = obs_wide['Region'].tolist()
    obs_mat = obs_wide.drop(columns=['Region'])
    obs_long = []
    for i, region in enumerate(regions):
        for t in range(len(obs_mat.columns)):
            obs_long.append({
                'Region': region,
                'time': t + 1,
                'observed': obs_mat.iloc[i, t],
            })
    obs_df = pd.DataFrame(obs_long)

    merged = fitted.merge(obs_df, on=['Region', 'time'])
    merged['residual'] = round(merged['observed'] - merged['fitted'], 4)
    return merged[['Region', 'time', 'residual']]


# ── Main ─────────────────────────────────────────────────────────────
def process_model(model_dir):
    model_name = os.path.basename(model_dir)
    print(f'=== {model_name} ===')

    df = load_scalar_samples(model_dir)
    print(f'  {len(df)} samples, {len(df.columns)} columns')

    indexed = detect_indexed_params(df)
    scalars = detect_scalar_params(df)

    n_overall = N_REGION
    n_pairwise = len(list(combinations(range(N_REGION), 2)))

    def save(name, data):
        path = os.path.join(model_dir, name)
        data.to_csv(path, index=False)
        print(f'  -> {name}')

    # ── Full summary ──
    all_rows = []
    for prefix, cols in sorted(indexed.items()):
        for col in cols:
            v = df[col]
            all_rows.append({
                'parameter': col,
                'Mean': round(v.mean(), 4),
                'SD': round(v.std(), 4),
                '2.5%': round(v.quantile(0.025), 4),
                '97.5%': round(v.quantile(0.975), 4),
            })
    for col in scalars:
        v = df[col]
        all_rows.append({
            'parameter': col,
            'Mean': round(v.mean(), 4),
            'SD': round(v.std(), 4),
            '2.5%': round(v.quantile(0.025), 4),
            '97.5%': round(v.quantile(0.975), 4),
        })
    save('summary.csv', pd.DataFrame(all_rows))

    # ── Per param summaries ──
    for prefix, cols in indexed.items():
        save(f'{prefix}.csv', summarise_indexed(df, cols, REGIONS))

    for col in scalars:
        save(f'{col}.csv', summarise_scalar(df, col))

    # ── Derived: amplitude & phase ──
    if 'beta' in indexed and 'gamma' in indexed:
        ampl = compute_amplitude(df)
        ampl_summary = []
        for region in REGIONS:
            v = ampl[region]
            ampl_summary.append({
                'Region': region,
                'Mean': round(v.mean(), 4),
                'SD': round(v.std(), 4),
                '2.5%': round(np.quantile(v, 0.025), 4),
                '97.5%': round(np.quantile(v, 0.975), 4),
            })
        save('amplitude.csv', pd.DataFrame(ampl_summary))

        phase = compute_phase(df)
        phase_summary = []
        for region in REGIONS:
            v = phase[region]
            phase_summary.append({
                'Region': region,
                'Mean': round(v.mean(), 4),
                'SD': round(v.std(), 4),
                '2.5%': round(np.quantile(v, 0.025), 4),
                '97.5%': round(np.quantile(v, 0.975), 4),
            })
        save('phase.csv', pd.DataFrame(phase_summary))

    # ── Overall sig tests ──
    for prefix in indexed:
        samples_dict = extract_region_samples(df, prefix)
        if len(samples_dict) == N_REGION:
            save(f'sig_overall_{prefix}.csv',
                 overall_sig(samples_dict, n_overall))

    # Derived overall sig
    if 'beta' in indexed and 'gamma' in indexed:
        save('sig_overall_amplitude.csv',
             overall_sig(ampl, n_overall))
        save('sig_overall_phase.csv',
             overall_sig(phase, n_overall))

    # ── Pairwise sig tests ──
    for prefix in indexed:
        samples_dict = extract_region_samples(df, prefix)
        if len(samples_dict) == N_REGION:
            save(f'sig_pairwise_{prefix}.csv',
                 pairwise_sig(samples_dict, n_pairwise))

    # Derived pairwise sig
    if 'beta' in indexed and 'gamma' in indexed:
        save('sig_pairwise_amplitude.csv',
             pairwise_sig(ampl, n_pairwise))
        save('sig_pairwise_phase.csv',
             pairwise_sig(phase, n_pairwise))

    # ── Residuals ──
    resid_df = compute_residuals(model_dir)
    if resid_df is not None:
        save('residuals.csv', resid_df)

    print()


def main():
    models_dir = os.path.normpath(MODELS_DIR)
    print(f'Scanning {models_dir}\n')
    for entry in sorted(os.listdir(models_dir)):
        model_dir = os.path.join(models_dir, entry)
        if os.path.isdir(model_dir):
            raw_path = os.path.join(model_dir, 'raw_samples.csv')
            if os.path.isfile(raw_path):
                process_model(model_dir)

    print('Done.')


if __name__ == '__main__':
    main()
