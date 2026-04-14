import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
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


def trace_with_lowess(pyjags_samples, var_names, save_dir=None, frac=0.1):
    """Trace plots with LOWESS smoother per chain — all params in one figure.

    Parameters
    ----------
    pyjags_samples : dict
        Raw pyjags samples dict.
    var_names : list[str]
        Which parameters to plot.
    save_dir : Path, optional
        If provided, saves as traces.png.
    frac : float
        LOWESS bandwidth fraction.
    """
    # collect all (label, array) pairs to determine subplot count
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

    n = len(panels)
    n_chains = panels[0][1].shape[1]
    fig, axes = plt.subplots(n, 1, figsize=(10, 2 * n), layout='constrained')
    if n == 1:
        axes = [axes]

    for ax, (label, data) in zip(axes, panels):
        n_iter = data.shape[0]
        x = np.arange(n_iter)
        for c in range(n_chains):
            vals = data[:, c]
            color = f'C{c}'
            ax.plot(x, vals, alpha=0.2, lw=0.4, color=color)
            smooth = lowess(vals, x, frac=frac, return_sorted=True)
            ax.plot(smooth[:, 0], smooth[:, 1], color=color, lw=1.5,
                    label=f'chain {c + 1}')
        ax.set_ylabel(label, fontsize=9)
        ax.tick_params(labelbottom=False)

    axes[-1].tick_params(labelbottom=True)
    axes[-1].set_xlabel('Iteration')
    axes[0].legend(loc='upper right', fontsize=8)

    if save_dir:
        fig.savefig(save_dir / 'traces.png', dpi=150, bbox_inches='tight')
    plt.close(fig)
