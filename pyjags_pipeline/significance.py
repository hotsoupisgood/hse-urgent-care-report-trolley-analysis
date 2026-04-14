import numpy as np
import pandas as pd


def summarize_global_parameters(raw_df, param_names):
    """Summarize scalar posterior parameters."""
    rows = []
    for name in param_names:
        vals = raw_df[name].values
        rows.append({
            'Parameter': name,
            'Mean': vals.mean(),
            'SD': vals.std(),
            '2.5%': np.quantile(vals, 0.025),
            '97.5%': np.quantile(vals, 0.975),
        })
    return pd.DataFrame(rows).round(4)


def compute_amplitude(raw_df, regions, beta_prefix='beta', gamma_prefix='gamma'):
    """Compute seasonal amplitude A_i = sqrt(beta^2 + gamma^2) per region."""
    ampl = {}
    for i, region in enumerate(regions):
        b = raw_df[f'{beta_prefix}[{i + 1}]']
        g = raw_df[f'{gamma_prefix}[{i + 1}]']
        ampl[region] = np.sqrt(b ** 2 + g ** 2)
    return ampl


def compute_phase(raw_df, regions, beta_prefix='beta', gamma_prefix='gamma',
                  period=52):
    """Compute peak week from arctan2(gamma, beta) per region."""
    phase = {}
    for i, region in enumerate(regions):
        b = raw_df[f'{beta_prefix}[{i + 1}]'].values
        g = raw_df[f'{gamma_prefix}[{i + 1}]'].values
        rad = np.arctan2(g, b)
        phase[region] = ((period / (2 * np.pi)) * rad) % period
    return phase


def build_ranked_alpha(raw_df, regions):
    """Build ranked alpha DataFrame from posterior samples."""
    alpha_df = pd.DataFrame(
        {regions[i]: raw_df[f'alpha[{i + 1}]'].values for i in range(len(regions))}
    )
    ranked = alpha_df.rank(axis=1, method='average')
    ranked.columns = regions
    return ranked
