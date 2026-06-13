import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from scipy.stats import gaussian_kde
from statsmodels.nonparametric.smoothers_lowess import lowess
from pyjags import from_pyjags
import arviz as az


def convergence_summary(pyjags_samples, var_names=None):
    """Compute R-hat, bulk ESS, and tail ESS for all parameters.

    Returns DataFrame with columns: param, R-hat, ESS_bulk, ESS_tail.
    """
    idata = from_pyjags(pyjags_samples)
    rhat = az.rhat(idata)
    ess_bulk = az.ess(idata, method='bulk')
    ess_tail = az.ess(idata, method='tail')

    check_vars = var_names or list(rhat.data_vars)
    rows = []
    for var in check_vars:
        r = np.atleast_1d(rhat[var].values)
        eb = np.atleast_1d(ess_bulk[var].values)
        et = np.atleast_1d(ess_tail[var].values)
        for i in range(len(r)):
            label = f'{var}[{i + 1}]' if len(r) > 1 else var
            rows.append({
                'param': label,
                'R-hat': round(float(r[i]), 4),
                'ESS_bulk': int(eb[i]),
                'ESS_tail': int(et[i]),
            })

    return pd.DataFrame(rows)


def trace_with_dist(pyjags_samples, var_names, save_dir=None, frac=0.1):
    """Trace + LOWESS (left) with per-chain rotated KDE (right), y-axes shared.

    Parameters
    ----------
    pyjags_samples : dict
        Raw pyjags samples dict.
    var_names : list[str]
        Which parameters to plot.
    save_dir : Path, optional
        If provided, saves as traces.pdf (one parameter per page).
    frac : float
        LOWESS bandwidth fraction.
    """
    panels = []
    for var in var_names:
        if var not in pyjags_samples:
            continue
        arr = pyjags_samples[var]
        if arr.ndim == 3:
            n_elem = arr.shape[0]
        else:
            arr = arr.reshape(1, *arr.shape)
            n_elem = 1
        for elem in range(n_elem):
            label = f'{var}[{elem + 1}]' if n_elem > 1 else var
            panels.append((label, arr[elem]))

    if not panels:
        return

    n_chains = panels[0][1].shape[1]

    def _draw_panel(ax_tr, ax_kd, label, data, show_legend, show_xlabel):
        ax_kd.sharey(ax_tr)
        n_iter = data.shape[0]
        x = np.arange(n_iter)
        for c in range(n_chains):
            vals = data[:, c]
            color = f'C{c}'
            ax_tr.plot(x, vals, alpha=0.2, lw=0.4, color=color)
            smooth = lowess(vals, x, frac=frac, return_sorted=True)
            ax_tr.plot(smooth[:, 0], smooth[:, 1], color=color, lw=1.5,
                       label=f'chain {c + 1}')
            kde = gaussian_kde(vals)
            y_grid = np.linspace(vals.min(), vals.max(), 300)
            density = kde(y_grid)
            ax_kd.plot(density, y_grid, color=color, lw=1.5)
        ax_tr.set_ylabel('')
        ax_tr.set_title(label, fontsize=9, loc='left')
        ax_kd.tick_params(left=False, labelleft=False, labelbottom=False)
        ax_kd.spines['left'].set_visible(False)
        ax_kd.spines['right'].set_visible(False)
        ax_kd.spines['top'].set_visible(False)
        ax_kd.set_yticks([])
        if show_xlabel:
            ax_tr.set_xlabel('Iteration')
        if show_legend:
            ax_tr.legend(loc='upper right', fontsize=8)

    if save_dir:
        with PdfPages(save_dir / 'traces.pdf') as pdf:
            for i, (label, data) in enumerate(panels):
                fig, axes = plt.subplots(
                    1, 2,
                    figsize=(12, 2),
                    gridspec_kw={'width_ratios': [3, 1]},
                    layout='constrained',
                )
                _draw_panel(axes[0], axes[1], label, data,
                            show_legend=True, show_xlabel=True)
                pdf.savefig(fig)
                plt.close(fig)
    else:
        for i, (label, data) in enumerate(panels):
            fig, axes = plt.subplots(
                1, 2,
                figsize=(12, 2),
                gridspec_kw={'width_ratios': [3, 1]},
                layout='constrained',
            )
            _draw_panel(axes[0], axes[1], label, data,
                        show_legend=True, show_xlabel=True)
            plt.show()
            plt.close(fig)


def trace_with_lowess(pyjags_samples, var_names, save_dir=None, frac=0.1):
    """Deprecated alias for trace_with_dist."""
    trace_with_dist(pyjags_samples, var_names, save_dir=save_dir, frac=frac)
