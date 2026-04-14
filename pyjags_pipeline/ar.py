import numpy as np
import pandas as pd


def compute_ar1_fitted(df_mu, df_og, phi_mean):
    """Compute AR(1) fitted values: fitted[t] = mu[t] + phi * (y[t-1] - mu[t-1])."""
    fitted = df_mu.copy()
    for t in range(1, len(df_mu)):
        fitted.iloc[t] = df_mu.iloc[t] + phi_mean * (df_og.iloc[t - 1] - df_mu.iloc[t - 1])
    return fitted


def compute_ar2_fitted(df_mu, df_og, phi1_mean, phi2_mean):
    """Compute AR(2) fitted values from mu and observed data."""
    n_weeks = df_mu.shape[0]
    df_ar2 = df_mu.copy()
    df_ar2.iloc[1] = (df_mu.iloc[1]
                       + phi1_mean * (df_og.iloc[0].values - df_mu.iloc[0].values))
    for t in range(2, n_weeks):
        df_ar2.iloc[t] = (df_mu.iloc[t]
                           + phi1_mean * (df_og.iloc[t-1].values - df_mu.iloc[t-1].values)
                           + phi2_mean * (df_og.iloc[t-2].values - df_mu.iloc[t-2].values))
    return df_ar2


def compute_residuals(df_og, df_fitted):
    """Compute raw and standardized residuals."""
    df_residuals = df_og - df_fitted
    df_std_resid = df_residuals / df_residuals.std()
    return df_residuals, df_std_resid
