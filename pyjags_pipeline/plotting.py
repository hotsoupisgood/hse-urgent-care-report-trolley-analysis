import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.nonparametric.smoothers_lowess import lowess
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.graphics.gofplots import qqplot
from scipy.signal import welch


def _week_xlabels(index, start='2023-01-01'):
    return (pd.to_datetime(start) + pd.to_timedelta(index, unit='W')).strftime('%Y-%m')


def _sorted_legend(ax, data_for_sort, loc='upper right', fontsize=7):
    handles, labels = ax.get_legend_handles_labels()
    mean_vals = {lab: data_for_sort[lab].mean() for lab in labels}
    order = sorted(range(len(labels)), key=lambda i: mean_vals[labels[i]], reverse=True)
    ax.legend([handles[i] for i in order],
              [labels[i] for i in order],
              loc=loc, fontsize=fontsize)


def plot_mu(df_mu, df_mu_lower, df_mu_upper, save_path):
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
    _sorted_legend(axs, df_mu)
    plt.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.close()


def plot_fitted(df_fitted, save_path, ylabel='Trolley Rate (per 10k)'):
    fig, ax = plt.subplots(figsize=(12, 4), dpi=150, layout='constrained')
    for col in df_fitted.columns:
        ax.plot(df_fitted.index, df_fitted[col], label=col)
    ax.axvline(x=104, color='black', linestyle='--', linewidth=0.8)
    ax.axvline(x=52, color='black', linestyle='--', linewidth=0.8)
    ax.annotate('2 years', xy=(104, ax.get_ylim()[1] * 0.85), fontsize=8)
    ax.annotate('1 year', xy=(52, ax.get_ylim()[1] * 0.85), fontsize=8)
    ax.set_xlim(0, df_fitted.shape[0])
    ax.set_title('Posterior Mean Rates by Region')
    ax.set_xlabel('Weeks')
    ax.set_ylabel(ylabel)
    ax.set_xticks(df_fitted.index[::20])
    x_labels = pd.to_datetime('2023-01-01') + pd.to_timedelta(df_fitted.index, unit='W')
    ax.set_xticklabels(x_labels.strftime('%Y-%m')[::20])
    _sorted_legend(ax, df_fitted)
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.close(fig)


def plot_residuals_combined(df_std_resid, save_path):
    fig, ax = plt.subplots(figsize=(12, 4), dpi=150, layout='constrained')
    for col in df_std_resid.columns:
        ax.plot(df_std_resid.index, df_std_resid[col], linewidth=0.8, label=col)
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
    ax.set_xlim(0, df_std_resid.shape[0])
    ax.set_title('Standardized Residuals — All Regions')
    ax.set_xlabel('Weeks')
    ax.set_ylabel('Standardized Residuals')
    ax.set_xticks(df_std_resid.index[::20])
    ax.set_xticklabels(_week_xlabels(df_std_resid.index)[::20])
    handles, labels = ax.get_legend_handles_labels()
    order = sorted(range(len(labels)),
                   key=lambda i: df_std_resid[labels[i]].abs().mean(), reverse=True)
    ax.legend([handles[i] for i in order], [labels[i] for i in order],
              loc='upper right', fontsize=7)
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.close(fig)


def plot_residuals_ts(df_std_resid, save_path):
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), sharey=True, layout='constrained')
    for col, ax in zip(df_std_resid.columns, axes.flatten()):
        ax.plot(df_std_resid[col], linewidth=0.8)
        ax.axhline(y=0, linestyle='--', linewidth=1)
        ax.set_title(col, fontsize=10)
        ax.set_ylabel('')
        ax.set_xlabel('')
    fig.suptitle('Standardized Residuals')
    fig.supxlabel('Weeks')
    fig.supylabel('Standardized Residuals')
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.close(fig)


def plot_residuals_acf(df_std_resid, save_path, lags=53):
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharey=True, layout='constrained')
    for ax, col in zip(axes.flatten(), df_std_resid.columns):
        plot_acf(df_std_resid[col].dropna(), ax=ax, lags=lags, alpha=0.05)
        ax.set_title(col, fontsize=10)
        ax.set_ylabel('')
        ax.set_xlabel('')
        ax.axvline(52, color='red', linestyle='--', linewidth=0.8, alpha=0.6)
    fig.suptitle('Autocorrelation of Residuals')
    fig.supxlabel('Lag (weeks)')
    fig.supylabel('ACF')
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.close(fig)


def plot_residuals_pacf(df_std_resid, save_path, lags=53):
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharey=True, layout='constrained')
    for ax, col in zip(axes.flatten(), df_std_resid.columns):
        plot_pacf(df_std_resid[col].dropna(), ax=ax, lags=lags, alpha=0.05, method='ywm')
        ax.set_title(col, fontsize=10)
        ax.set_ylabel('')
        ax.set_xlabel('')
        ax.axvline(52, color='red', linestyle='--', linewidth=0.8, alpha=0.6)
    fig.suptitle('Partial Autocorrelation of Residuals')
    fig.supxlabel('Lag (weeks)')
    fig.supylabel('PACF')
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.close(fig)


def plot_residuals_vs_fitted(df_std_resid, df_fitted, save_path):
    fig, axes = plt.subplots(3, 2, figsize=(12, 10), sharey=True, layout='constrained')
    for col, ax in zip(df_std_resid.columns, axes.flatten()):
        sns.scatterplot(x=df_fitted[col], y=df_std_resid[col], ax=ax, s=15, alpha=0.6)
        smooth = lowess(df_std_resid[col], df_fitted[col], frac=2 / 3, return_sorted=True)
        sns.lineplot(x=smooth[:, 0], y=smooth[:, 1], ax=ax, color='red')
        ax.set_title(col, fontsize=10)
        ax.set_ylabel('')
        ax.set_xlabel('')
    fig.suptitle('Residuals vs Fitted Values')
    fig.supxlabel('Fitted Values')
    fig.supylabel('Residuals')
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.close(fig)


def plot_residuals_qq(df_std_resid, save_path):
    fig, axes = plt.subplots(3, 2, figsize=(12, 9), sharey=True, layout='constrained')
    for ax, col in zip(axes.flatten(), df_std_resid.columns):
        qqplot(df_std_resid[col], line='45', ax=ax)
        ax.set_title(col, fontsize=10)
        ax.set_ylabel('')
        ax.set_xlabel('')
    fig.suptitle('Residual QQ Plot')
    fig.supxlabel('Theoretical Quantiles')
    fig.supylabel('Sample Quantiles')
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.close(fig)


def plot_residuals_periodogram(df_std_resid, save_path, fs=1.0, nperseg=52):
    # Welch's method: nperseg=52 preserves annual-cycle frequency resolution;
    # with ~150 obs and 50% overlap this yields ~5 averaged segments.
    ref_periods = [
        (52, '1 Year'),
        (26, '6 Months'),
        (13, '1 Quarter'),
        (4, '1 Month'),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(14, 10), layout='constrained')
    for ax, col in zip(axes.flatten(), df_std_resid.columns):
        resid = df_std_resid[col].dropna().values
        freqs, psd = welch(resid, fs=fs, nperseg=min(nperseg, len(resid)),
                           noverlap=nperseg // 2, window='hann')
        mask = freqs > 0
        periods = 1.0 / freqs[mask]
        power = psd[mask]
        ax.plot(periods, power, linewidth=0.8)
        ax.set_title(f'PSD: {col}', fontsize=10)
        ax.set_ylabel('Power')
        ax.set_xlabel('Period (weeks)')
        ax.set_xlim(0, 53)
        y_top = power.max() * 0.95
        for period, label in ref_periods:
            ax.axvline(period, color='red', linestyle='--', linewidth=0.8)
            ax.annotate(f'\u25c0{label}', xy=(period, y_top), fontsize=7, va='top')
    fig.savefig(save_path, bbox_inches='tight', dpi=150)
    plt.close(fig)


def plot_labeled_scatter(df, x_col, y_col, label_col, save_path, title,
                         xlabel=None, ylabel=None):
    fig, ax = plt.subplots(figsize=(6, 4), dpi=150, layout='constrained')
    sns.regplot(data=df, x=x_col, y=y_col, ci=None,
                scatter_kws={'s': 60, 'color': '#2c7bb6'},
                line_kws={'color': '#9e0142', 'linewidth': 1.5}, ax=ax)
    for _, row in df.iterrows():
        label = row[label_col]
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
    plt.close(fig)
