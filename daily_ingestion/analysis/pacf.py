"""
Partial autocorrelation computation for the dashboard.
Adapted from exploratory/autocorrelaltions.ipynb — uses statsmodels numeric
output (not matplotlib) so results can be rendered as Plotly charts.
"""

import numpy as np
from statsmodels.tsa.stattools import pacf


def compute_pacf_by_region(region_daily_df, nlags=60, alpha=0.05):
    """
    Compute PACF for each region in the DataFrame.

    Parameters
    ----------
    region_daily_df : DataFrame
        Must have columns: report_date, region, trolleys_per_10k.
        Sorted by date (load_daily_by_region already does this).
    nlags : int
        Number of lags to compute.
    alpha : float
        Significance level for confidence intervals.

    Returns
    -------
    dict of {region: {"lags": array, "pacf": array,
                      "ci_lower": array, "ci_upper": array}}
    """
    results = {}
    for region, grp in region_daily_df.groupby("region"):
        series = grp.sort_values("report_date")["trolleys_per_10k"].dropna().values
        if len(series) <= nlags + 1:
            continue
        pacf_vals, confint = pacf(series, nlags=nlags, alpha=alpha)
        lags = np.arange(len(pacf_vals))
        results[region] = {
            "lags": lags,
            "pacf": pacf_vals,
            "ci_lower": confint[:, 0] - pacf_vals,
            "ci_upper": confint[:, 1] - pacf_vals,
        }
    return results
