import pandas as pd
import numpy as np
from itertools import combinations
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.graphics.gofplots import qqplot
from statsmodels.nonparametric.smoothers_lowess import lowess
from statsmodels.graphics.tsaplots import plot_acf
from scipy.signal import periodogram

SHORT_NAMES = {
    'HSE Dublin and Midlands': 'Dublin & Midlands',
    'HSE Dublin and North East': 'Dublin & NE',
    'HSE Dublin and South East': 'Dublin & SE',
    'HSE Mid West': 'Mid West',
    'HSE South West': 'South West',
    'HSE West and North West': 'West & NW',
}

SHORT_NAMES_COMPACT = {
    'HSE Dublin and Midlands': 'Dub & Mid',
    'HSE Dublin and North East': 'Dub & NE',
    'HSE Dublin and South East': 'Dub & SE',
    'HSE Mid West': 'Mid West',
    'HSE South West': 'South West',
    'HSE West and North West': 'West & NW',
}


def load_model_data(version, data_csv='../../data/wide_weekly_scaledPer10k.csv'):
    """Load observed data, raw MCMC samples, and region list."""
    df_og = pd.read_csv(data_csv)
    raw_df = pd.read_csv(f'../../data/models/{version}/raw_samples.csv')
    regions = pd.read_csv('../../data/regions.csv')['region'].tolist()
    n_region = len(regions)
    return df_og, raw_df, regions, n_region


def load_region_covariate(csv_path, regions, value_col, key_col='Region',
                          center=False, scale=1.0):
    """Load a region-level covariate and align it to model region order."""
    df = pd.read_csv(csv_path)
    aligned = df.set_index(key_col).loc[regions].reset_index()
    aligned[value_col] = aligned[value_col].astype(float) * scale
    if center:
        aligned[f'{value_col}_centered'] = aligned[value_col] - aligned[value_col].mean()
    return aligned


def transpose_observed(df_og):
    """Transpose wide observed data from regions-as-rows to regions-as-columns."""
    df = df_og.T.copy()
    df.columns = df.iloc[0]
    df = df.drop(df.index[0]).reset_index(drop=True)
    return df


def build_event_indicators(n_weeks, regions):
    """Build time vectors and event indicator arrays matching the R model."""
    t_vec = np.arange(1, n_weeks + 1)
    week_mod = t_vec % 52

    indicators = {
        't_vec': t_vec,
        'cos_t': np.cos(2 * np.pi * t_vec / 52),
        'sin_t': np.sin(2 * np.pi * t_vec / 52),
        'cos_t4': np.cos(2 * np.pi * t_vec / 4),
        'sin_t4': np.sin(2 * np.pi * t_vec / 4),
        'cos_t10': np.cos(2 * np.pi * t_vec / 10),
        'sin_t10': np.sin(2 * np.pi * t_vec / 10),
        'ny_pre': (week_mod == 0).astype(float),
        'ny_mid': (week_mod == 1).astype(float),
        'ny_post': (week_mod == 2).astype(float),
        'fr_pre': (t_vec == 86).astype(float),
        'fr_mid': (t_vec == 87).astype(float),
        'fr_post': (t_vec == 88).astype(float),
        'mw': np.array([1.0 if r == 'HSE Mid West' else 0.0 for r in regions]),
    }
    return indicators


def reconstruct_mu(raw_df, regions, n_weeks, ev, region_delta=True,
                   monthly_harmonic=False, tenweek_harmonic=False):
    """Reconstruct posterior mu[i,t] from MCMC samples.

    Args:
        region_delta: if True, delta_pre[i] is per-region (V3+).
                      if False, delta_pre is global (V2).
        monthly_harmonic: if True, include beta4[i]/gamma4[i] period-4 terms (V8).
        tenweek_harmonic: if True, include beta10[i]/gamma10[i] period-10 terms (V9).
    Returns:
        df_mu, df_mu_lower, df_mu_upper, phi_mean
    """
    n_region = len(regions)
    mu_mean_arr = np.zeros((n_weeks, n_region))
    mu_lower_arr = np.zeros((n_weeks, n_region))
    mu_upper_arr = np.zeros((n_weeks, n_region))

    for i in range(n_region):
        mu_i = (raw_df[f'alpha[{i+1}]'].values[:, None]
                + raw_df[f'beta[{i+1}]'].values[:, None] * ev['cos_t'][None, :]
                + raw_df[f'gamma[{i+1}]'].values[:, None] * ev['sin_t'][None, :])

        if monthly_harmonic:
            mu_i += (raw_df[f'beta4[{i+1}]'].values[:, None] * ev['cos_t4'][None, :]
                     + raw_df[f'gamma4[{i+1}]'].values[:, None] * ev['sin_t4'][None, :])

        if tenweek_harmonic:
            mu_i += (raw_df[f'beta10[{i+1}]'].values[:, None] * ev['cos_t10'][None, :]
                     + raw_df[f'gamma10[{i+1}]'].values[:, None] * ev['sin_t10'][None, :])

        if region_delta:
            mu_i += (raw_df[f'delta_pre[{i+1}]'].values[:, None] * ev['ny_pre'][None, :]
                     + raw_df[f'delta_mid[{i+1}]'].values[:, None] * ev['ny_mid'][None, :]
                     + raw_df[f'delta_post[{i+1}]'].values[:, None] * ev['ny_post'][None, :])
        else:
            mu_i += (raw_df['delta_pre'].values[:, None] * ev['ny_pre'][None, :]
                     + raw_df['delta_mid'].values[:, None] * ev['ny_mid'][None, :]
                     + raw_df['delta_post'].values[:, None] * ev['ny_post'][None, :])

        mu_i += (raw_df['sigma_pre'].values[:, None] * (ev['fr_pre'] * ev['mw'][i])[None, :]
                 + raw_df['sigma_mid'].values[:, None] * (ev['fr_mid'] * ev['mw'][i])[None, :]
                 + raw_df['sigma_post'].values[:, None] * (ev['fr_post'] * ev['mw'][i])[None, :])

        mu_mean_arr[:, i] = mu_i.mean(axis=0)
        mu_lower_arr[:, i] = np.quantile(mu_i, 0.025, axis=0)
        mu_upper_arr[:, i] = np.quantile(mu_i, 0.975, axis=0)

    df_mu = pd.DataFrame(mu_mean_arr, columns=regions)
    df_mu_lower = pd.DataFrame(mu_lower_arr, columns=regions)
    df_mu_upper = pd.DataFrame(mu_upper_arr, columns=regions)
    phi_mean = raw_df['phi'].mean()

    return df_mu, df_mu_lower, df_mu_upper, phi_mean


def reconstruct_mu_ny_only(raw_df, regions, n_weeks, ev):
    """Reconstruct posterior mu[i,t] for V2a — New Year effect only, no Mid West reset.

    delta_pre, delta_mid, delta_post are global (not per-region).
    """
    n_region = len(regions)
    mu_mean_arr = np.zeros((n_weeks, n_region))
    mu_lower_arr = np.zeros((n_weeks, n_region))
    mu_upper_arr = np.zeros((n_weeks, n_region))

    for i in range(n_region):
        mu_i = (raw_df[f'alpha[{i+1}]'].values[:, None]
                + raw_df[f'beta[{i+1}]'].values[:, None] * ev['cos_t'][None, :]
                + raw_df[f'gamma[{i+1}]'].values[:, None] * ev['sin_t'][None, :]
                + raw_df['delta_pre'].values[:, None] * ev['ny_pre'][None, :]
                + raw_df['delta_mid'].values[:, None] * ev['ny_mid'][None, :]
                + raw_df['delta_post'].values[:, None] * ev['ny_post'][None, :])

        mu_mean_arr[:, i] = mu_i.mean(axis=0)
        mu_lower_arr[:, i] = np.quantile(mu_i, 0.025, axis=0)
        mu_upper_arr[:, i] = np.quantile(mu_i, 0.975, axis=0)

    df_mu = pd.DataFrame(mu_mean_arr, columns=regions)
    df_mu_lower = pd.DataFrame(mu_lower_arr, columns=regions)
    df_mu_upper = pd.DataFrame(mu_upper_arr, columns=regions)
    phi_mean = raw_df['phi'].mean()

    return df_mu, df_mu_lower, df_mu_upper, phi_mean


def reconstruct_mu_mw_only(raw_df, regions, n_weeks, ev):
    """Reconstruct posterior mu[i,t] for V2b — Mid West reset only, no New Year effect.

    sigma_pre, sigma_mid, sigma_post are global, applied only to Mid West.
    """
    n_region = len(regions)
    mu_mean_arr = np.zeros((n_weeks, n_region))
    mu_lower_arr = np.zeros((n_weeks, n_region))
    mu_upper_arr = np.zeros((n_weeks, n_region))

    for i in range(n_region):
        mu_i = (raw_df[f'alpha[{i+1}]'].values[:, None]
                + raw_df[f'beta[{i+1}]'].values[:, None] * ev['cos_t'][None, :]
                + raw_df[f'gamma[{i+1}]'].values[:, None] * ev['sin_t'][None, :]
                + raw_df['sigma_pre'].values[:, None] * (ev['fr_pre'] * ev['mw'][i])[None, :]
                + raw_df['sigma_mid'].values[:, None] * (ev['fr_mid'] * ev['mw'][i])[None, :]
                + raw_df['sigma_post'].values[:, None] * (ev['fr_post'] * ev['mw'][i])[None, :])

        mu_mean_arr[:, i] = mu_i.mean(axis=0)
        mu_lower_arr[:, i] = np.quantile(mu_i, 0.025, axis=0)
        mu_upper_arr[:, i] = np.quantile(mu_i, 0.975, axis=0)

    df_mu = pd.DataFrame(mu_mean_arr, columns=regions)
    df_mu_lower = pd.DataFrame(mu_lower_arr, columns=regions)
    df_mu_upper = pd.DataFrame(mu_upper_arr, columns=regions)
    phi_mean = raw_df['phi'].mean()

    return df_mu, df_mu_lower, df_mu_upper, phi_mean


def reconstruct_mu_baseline(raw_df, regions, n_weeks):
    """Reconstruct mu[i,t] = alpha[i] for baseline models (V0a/V0b).

    No seasonality, no events — just a constant intercept per region.
    Returns df_mu, df_mu_lower, df_mu_upper.
    """
    n_region = len(regions)
    mu_mean_arr = np.zeros((n_weeks, n_region))
    mu_lower_arr = np.zeros((n_weeks, n_region))
    mu_upper_arr = np.zeros((n_weeks, n_region))

    for i in range(n_region):
        alpha_i = raw_df[f'alpha[{i+1}]'].values
        mu_mean_arr[:, i] = alpha_i.mean()
        mu_lower_arr[:, i] = np.quantile(alpha_i, 0.025)
        mu_upper_arr[:, i] = np.quantile(alpha_i, 0.975)

    df_mu = pd.DataFrame(mu_mean_arr, columns=regions)
    df_mu_lower = pd.DataFrame(mu_lower_arr, columns=regions)
    df_mu_upper = pd.DataFrame(mu_upper_arr, columns=regions)
    return df_mu, df_mu_lower, df_mu_upper


def compute_ar2_fitted(df_mu, df_og, phi1_mean, phi2_mean):
    """Compute AR(2) fitted values from mu and observed data."""
    n_weeks = df_mu.shape[0]
    df_ar2 = df_mu.copy()
    # t=2: mu + phi1*(y[t-1] - mu[t-1])
    df_ar2.iloc[1] = (df_mu.iloc[1]
                       + phi1_mean * (df_og.iloc[0].values - df_mu.iloc[0].values))
    # t>=3: mu + phi1*(y[t-1] - mu[t-1]) + phi2*(y[t-2] - mu[t-2])
    for t in range(2, n_weeks):
        df_ar2.iloc[t] = (df_mu.iloc[t]
                           + phi1_mean * (df_og.iloc[t-1].values - df_mu.iloc[t-1].values)
                           + phi2_mean * (df_og.iloc[t-2].values - df_mu.iloc[t-2].values))
    return df_ar2


def compute_ar1_fitted(df_mu, df_og, phi_mean):
    """Compute AR(1) fitted values from mu and observed data."""
    df_mu_t1 = df_mu.iloc[:df_mu.shape[0] - 1]
    df_og_t1 = df_og.iloc[:df_mu.shape[0] - 1]
    df_mu_first = pd.DataFrame([df_mu.iloc[0]])
    df_mu_rest = df_mu.iloc[1:].reset_index(drop=True)
    df_ar1 = df_mu_rest + (phi_mean * (df_og_t1 - df_mu_t1))
    df_ar1 = pd.concat([df_mu_first, df_ar1], ignore_index=True)
    return df_ar1


def compute_residuals(df_og, df_ar1):
    """Compute raw and standardized residuals."""
    df_residuals = df_og - df_ar1
    df_std_resid = df_residuals / df_residuals.std()
    return df_residuals, df_std_resid


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


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _week_xlabels(index, start='2023-01-01'):
    """Convert week index to date labels."""
    return (pd.to_datetime(start) + pd.to_timedelta(index, unit='W')).strftime('%Y-%m')


def _sorted_legend(ax, short_names, data_for_sort, loc='upper right', fontsize=7):
    """Sort legend entries by mean value descending."""
    handles, labels = ax.get_legend_handles_labels()
    mean_vals = {lab: data_for_sort[lab].mean() for lab in labels}
    order = sorted(range(len(labels)), key=lambda i: mean_vals[labels[i]], reverse=True)
    ax.legend([handles[i] for i in order],
              [short_names.get(labels[i], labels[i]) for i in order],
              loc=loc, fontsize=fontsize)


def plot_mu(df_mu, df_mu_lower, df_mu_upper, save_path):
    """Plot posterior mean of mu with 95% CI bands."""
    plt.figure(figsize=(12, 4), dpi=150)
    axs = sns.lineplot(data=df_mu)
    for col in df_mu.columns:
        plt.fill_between(df_mu.index, df_mu_lower[col], df_mu_upper[col], alpha=0.2)
    axs.set_title('Posterior Mean of mu by Region')
    axs.set_xlabel('Weeks')
    axs.set_ylabel('mu')
    axs.set_xlim(0, df_mu.shape[0])
    axs.set_xticks(df_mu.index[::20])
    axs.set_xticklabels(_week_xlabels(df_mu.index)[::20])
    _sorted_legend(axs, SHORT_NAMES, df_mu)
    plt.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.show()


def plot_ar1_fit(df_ar1, save_path, ylabel='Trolley Rate (per 10k)'):
    """Plot AR(1) fitted values with year markers."""
    fig, ax = plt.subplots(figsize=(12, 4), dpi=150, layout='constrained')
    for col in df_ar1.columns:
        ax.plot(df_ar1.index, df_ar1[col], label=col)
    ax.axvline(x=104, color='black', linestyle='--', linewidth=0.8)
    ax.axvline(x=52, color='black', linestyle='--', linewidth=0.8)
    ax.annotate('2 years', xy=(104, ax.get_ylim()[1] * 0.85), fontsize=8)
    ax.annotate('1 year', xy=(52, ax.get_ylim()[1] * 0.85), fontsize=8)
    ax.set_xlim(0, df_ar1.shape[0])
    ax.set_title('Posterior Mean Rates by Region')
    ax.set_xlabel('Weeks')
    ax.set_ylabel(ylabel)
    ax.set_xticks(df_ar1.index[::20])
    x_labels = pd.to_datetime('2023-01-01') + pd.to_timedelta(df_ar1.index, unit='W')
    ax.set_xticklabels(x_labels.strftime('%Y-%m')[::20])
    _sorted_legend(ax, SHORT_NAMES, df_ar1)
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.show()


def plot_residuals_ts(df_std_resid, save_path):
    """Standardized residuals time series — 3x2 grid."""
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), sharey=True, layout='constrained')
    for col, ax in zip(df_std_resid.columns, axes.flatten()):
        ax.plot(df_std_resid[col], linewidth=0.8)
        ax.axhline(y=0, linestyle='--', linewidth=1)
        ax.set_title(SHORT_NAMES.get(col, col), fontsize=10)
        ax.set_ylabel('')
        ax.set_xlabel('')
    fig.suptitle('Standardized Residuals')
    fig.supxlabel('Weeks')
    fig.supylabel('Standardized Residuals')
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.show()


def plot_residuals_acf(df_std_resid, save_path, lags=40):
    """ACF of residuals — 3x2 grid."""
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharey=True, layout='constrained')
    for ax, col in zip(axes.flatten(), df_std_resid.columns):
        plot_acf(df_std_resid[col].dropna(), ax=ax, lags=lags, alpha=0.05)
        ax.set_title(SHORT_NAMES.get(col, col), fontsize=10)
        ax.set_ylabel('')
        ax.set_xlabel('')
    fig.suptitle('Autocorrelation of Residuals')
    fig.supxlabel('Lag (weeks)')
    fig.supylabel('ACF')
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.show()


def plot_residuals_vs_fitted(df_std_resid, df_ar1, save_path):
    """Residuals vs fitted — 3x2 grid with LOWESS smoother."""
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), sharey=True, layout='constrained')
    for col, ax in zip(df_std_resid.columns, axes.flatten()):
        sns.scatterplot(x=df_ar1[col], y=df_std_resid[col], ax=ax, s=15, alpha=0.6)
        smooth = lowess(df_std_resid[col], df_ar1[col], frac=2 / 3, return_sorted=True)
        sns.lineplot(x=smooth[:, 0], y=smooth[:, 1], ax=ax, color='red')
        ax.set_title(SHORT_NAMES.get(col, col), fontsize=10)
        ax.set_ylabel('')
        ax.set_xlabel('')
    fig.suptitle('Residuals vs Fitted Values')
    fig.supxlabel('Fitted Values')
    fig.supylabel('Residuals')
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.show()


def plot_residuals_qq(df_std_resid, save_path):
    """QQ plot of residuals — 3x2 grid."""
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharey=True, layout='constrained')
    for ax, col in zip(axes.flatten(), df_std_resid.columns):
        qqplot(df_std_resid[col], line='45', ax=ax)
        ax.set_title(SHORT_NAMES.get(col, col), fontsize=10)
        ax.set_ylabel('')
        ax.set_xlabel('')
    fig.suptitle('Residual QQ Plot')
    fig.supxlabel('Theoretical Quantiles')
    fig.supylabel('Sample Quantiles')
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.show()


def plot_residuals_periodogram(df_std_resid, save_path, fs=1.0):
    """Power spectral density of residuals via periodogram — 3x2 grid.

    Parameters
    ----------
    df_std_resid : DataFrame
        Standardized residuals, one column per region.
    save_path : str
        Path to save the figure.
    fs : float
        Sampling frequency in cycles per week (default 1.0 = weekly data).
    """
    fig, axes = plt.subplots(3, 2, figsize=(14, 10), layout='constrained')

    ref_periods = [
        (52, '1 Year'),
        (26, '6 Months'),
        (13, '1 Quarter'),
        (4, '1 Month'),
    ]

    for ax, col in zip(axes.flatten(), df_std_resid.columns):
        resid = df_std_resid[col].dropna().values
        freqs, psd = periodogram(resid, fs=fs, window='hann')

        # Convert frequency to period; skip DC component (freq=0)
        mask = freqs > 0
        periods = 1.0 / freqs[mask]
        power = psd[mask]

        ax.plot(periods, power, linewidth=0.8)

        ax.set_title(f'PSD (Power Spectral Density): {SHORT_NAMES.get(col, col)}',
                      fontsize=10)
        ax.set_ylabel('Power')
        ax.set_xlabel('Period (weeks)')
        ax.set_xlim(0, 52)

        for period, label in ref_periods:
            ax.axvline(period, color='red', linestyle='--', linewidth=0.8)
            ax.annotate(
                f'\u25c0{label}', xy=(period, 95),
                fontsize=7, va='top',
            )

    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.show()


def plot_labeled_scatter(df, x_col, y_col, label_col, save_path, title,
                         xlabel=None, ylabel=None):
    """Scatter plot with region labels and a simple fitted line."""
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150, layout='constrained')
    sns.regplot(
        data=df,
        x=x_col,
        y=y_col,
        ci=None,
        scatter_kws={'s': 60, 'color': '#2c7bb6'},
        line_kws={'color': '#9e0142', 'linewidth': 1.5},
        ax=ax,
    )

    for _, row in df.iterrows():
        label = SHORT_NAMES_COMPACT.get(row[label_col], row[label_col])
        ax.annotate(label, (row[x_col], row[y_col]),
                    textcoords='offset points', xytext=(4, 4), fontsize=8)

    corr = df[[x_col, y_col]].corr().iloc[0, 1]
    ax.annotate(f'r = {corr:.2f}', xy=(0.02, 0.98), xycoords='axes fraction',
                ha='left', va='top', fontsize=8)
    ax.set_title(title)
    ax.set_xlabel(xlabel or x_col)
    ax.set_ylabel(ylabel or y_col)
    sns.despine(ax=ax)
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.show()


# ---------------------------------------------------------------------------
# Significance testing
# ---------------------------------------------------------------------------

def calc_bonf(n_comparisons, one_sided=False):
    """Bonferroni-corrected alpha and quantile bounds."""
    alpha = 0.05 / n_comparisons
    if one_sided:
        lower_q = alpha
        upper_q = 1 - alpha
    else:
        lower_q = alpha / 2
        upper_q = 1 - alpha / 2
    side = "one-sided" if one_sided else "two-sided"
    print(f"n_comparisons={n_comparisons}, alpha={alpha:.6f}, "
          f"lower_q={lower_q:.6f}, upper_q={upper_q:.6f} ({side})")
    return alpha, lower_q, upper_q


def pairwise_test(samples_dict, regions, epsilon=0.5):
    """Pairwise posterior probability test on a dict of {region: samples}.

    Returns DataFrame with MeanDiff, CIs, P(|diff| > epsilon), P(diff > 0).
    """
    results = []
    for r1, r2 in combinations(range(len(regions)), 2):
        diff = samples_dict[regions[r1]] - samples_dict[regions[r2]]
        ci_lower, ci_upper = np.quantile(diff, [0.025, 0.975])
        p_dir = (diff > 0).mean()
        p_abs = (np.abs(diff) > epsilon).mean()
        results.append({
            'Region A': regions[r1], 'Region B': regions[r2],
            'MeanDiff': diff.mean(),
            '2.5%': ci_lower,
            '97.5%': ci_upper,
            f'P(|diff| > {epsilon})': round(p_abs, 3),
            'P(diff > 0)': round(p_dir, 3),
            'P(diff < 0)': round(1 - p_dir, 3),
        })
    return pd.DataFrame(results).round(3)


def pairwise_heatmap(df_pw, col, title, save_path,
                     r1_col='Region A', r2_col='Region B',
                     vmin=0, vmax=1, cmap='RdBu_r', fmt='.2f'):
    """Triangular heatmap from a pairwise DataFrame."""
    labels = sorted(set(df_pw[r1_col]) | set(df_pw[r2_col]))
    short = [SHORT_NAMES_COMPACT.get(l, l) for l in labels]
    n = len(labels)
    mat = np.full((n, n), np.nan)
    idx = {l: i for i, l in enumerate(labels)}
    for _, row in df_pw.iterrows():
        i, j = idx[row[r1_col]], idx[row[r2_col]]
        mat[i, j] = row[col]
        mat[j, i] = 1 - row[col] if vmax == 1 else -row[col]

    fig, ax = plt.subplots(figsize=(7, 6), dpi=150, layout='constrained')
    sns.heatmap(mat, annot=True, fmt=fmt, cmap=cmap,
                vmin=vmin, vmax=vmax, square=True, linewidths=0.5,
                xticklabels=short, yticklabels=short, ax=ax,
                cbar_kws={'label': col, 'shrink': 0.8})
    ax.set_xlabel('Region A')
    ax.set_ylabel('Region B')
    ax.set_title(title, fontsize=12, fontweight='bold')
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.show()


def compute_amplitude(raw_df, regions, beta_prefix='beta', gamma_prefix='gamma'):
    """Compute seasonal amplitude A_i = sqrt(beta^2 + gamma^2) per region."""
    ampl = {}
    for i, region in enumerate(regions):
        b = raw_df[f'{beta_prefix}[{i+1}]']
        g = raw_df[f'{gamma_prefix}[{i+1}]']
        ampl[region] = np.sqrt(b ** 2 + g ** 2)
    return ampl


def compute_phase(raw_df, regions, beta_prefix='beta', gamma_prefix='gamma',
                  period=52):
    """Compute peak week from arctan2(gamma, beta) per region.

    Args:
        period: cycle period in weeks (52 for annual, 4 for monthly).

    Returns dict of {region: peak_week_samples} (each an array of floats in [0, period)).
    """
    phase = {}
    for i, region in enumerate(regions):
        b = raw_df[f'{beta_prefix}[{i+1}]'].values
        g = raw_df[f'{gamma_prefix}[{i+1}]'].values
        rad = np.arctan2(g, b)
        phase[region] = ((period / (2 * np.pi)) * rad) % period
    return phase


def build_ranked_alpha(raw_df, regions):
    """Build ranked alpha DataFrame from posterior samples."""
    alpha_df = pd.DataFrame(
        {regions[i]: raw_df[f'alpha[{i+1}]'].values for i in range(len(regions))}
    )
    ranked = alpha_df.rank(axis=1, method='average')
    ranked.columns = regions
    return ranked
