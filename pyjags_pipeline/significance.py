import numpy as np
import pandas as pd


def summarize_global_parameters(raw_df, param_names):
    """Summarize scalar posterior parameters.

    Columns: Parameter, Median, Mean, SD, 2.5%, 50%, 97.5%.
    Median is the recommended point estimate (Vehtari et al. 2021,
    https://projecteuclid.org/journals/bayesian-analysis/volume-16/issue-2/Rank-Normalization-Folding-and-Localization-An-Improved-Rhat-for/10.1214/20-BA1221.full).
    """
    rows = []
    for name in param_names:
        vals = raw_df[name].values
        q025, q500, q975 = np.quantile(vals, [0.025, 0.5, 0.975])
        rows.append({
            'Parameter': name,
            'Median': q500,
            'Mean': vals.mean(),
            'SD': vals.std(),
            '2.5%': q025,
            '50%': q500,
            '97.5%': q975,
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


# Meteorological winter (Met Eireann, https://www.met.ie/climate/climate-of-ireland),
# in weeks relative to the New Year (wk 0):
#   Dec 1      = -31 days = -31/7 weeks
#   end of Feb = +59 days = +59/7 weeks
WINTER_LO_WK = -31 / 7
WINTER_HI_WK = 59 / 7


def _wrap_period(x, period=52):
    """Wrap a week value into (-period/2, period/2] -- the year is a circle."""
    half = period / 2
    return ((x + half) % period) - half


def compute_winter_probability(raw_df, regions, beta_prefix='beta',
                               gamma_prefix='gamma', period=52):
    """Posterior probability the annual-cycle peak falls in meteorological
    winter (Dec 1 to end of Feb) per region.

    Columns: region, p_winter.
    """
    rows = []
    for i, region in enumerate(regions):
        b = raw_df[f'{beta_prefix}[{i + 1}]'].values
        g = raw_df[f'{gamma_prefix}[{i + 1}]'].values
        peak = _wrap_period(np.arctan2(g, b) * period / (2 * np.pi), period)
        rows.append({
            'region': region,
            'p_winter': np.mean((peak >= WINTER_LO_WK) & (peak <= WINTER_HI_WK)),
        })
    return pd.DataFrame(rows)


def build_ranked_alpha(raw_df, regions):
    """Build ranked alpha DataFrame from posterior samples."""
    alpha_df = pd.DataFrame(
        {regions[i]: raw_df[f'alpha[{i + 1}]'].values for i in range(len(regions))}
    )
    ranked = alpha_df.rank(axis=1, method='average', ascending=False)
    ranked.columns = regions
    return ranked
