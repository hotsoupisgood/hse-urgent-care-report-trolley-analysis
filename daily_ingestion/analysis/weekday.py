"""
Weekday mean trolley computation for the dashboard.
Adapted from exploratory/regions.ipynb.
"""

import pandas as pd

WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def compute_weekday_means(region_daily_df):
    """
    Compute mean trolleys_per_10k by day-of-week and region.

    Parameters
    ----------
    region_daily_df : DataFrame
        Must have columns: report_date, region, trolleys_per_10k.
        report_date should be datetime (load_daily_by_region parses it).

    Returns
    -------
    DataFrame with columns: weekday, weekday_label, region, mean_trolleys_per_10k
    """
    df = region_daily_df.copy()
    df["weekday"] = pd.to_datetime(df["report_date"]).dt.dayofweek

    means = (
        df.groupby(["weekday", "region"])
        .agg(
            mean_trolleys_per_10k=("trolleys_per_10k", "mean"),
            mean_total_trolleys=("total_trolleys", "mean"),
        )
        .reset_index()
    )
    means["weekday_label"] = means["weekday"].map(dict(enumerate(WEEKDAY_LABELS)))
    return means[["weekday", "weekday_label", "region",
                   "mean_trolleys_per_10k", "mean_total_trolleys"]]
