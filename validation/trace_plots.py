"""
Generate trace plots + Gelman-Rubin diagnostics from raw_samples.csv files.

Usage:
    python3 validation/trace_plots.py v4          # single model
    python3 validation/trace_plots.py v1 v2 v4    # multiple models
    python3 validation/trace_plots.py all          # all models with raw_samples.csv
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "models"
RHAT_THRESHOLD = 1.1


def load_samples(model_version: str) -> pd.DataFrame:
    """Load raw_samples.csv for a model version."""
    path = DATA_DIR / model_version / "raw_samples.csv"
    if not path.exists():
        raise FileNotFoundError(f"No raw_samples.csv found at {path}")
    df = pd.read_csv(path)
    if "chain" not in df.columns:
        raise ValueError(
            f"{path} has no 'chain' column. "
            "Re-knit the model Rmd to generate the updated format."
        )
    return df


def gelman_rubin(chains: list[np.ndarray]) -> float:
    """
    Compute Gelman-Rubin R-hat for a single parameter.
    chains: list of 1-D arrays, one per chain.
    """
    m = len(chains)
    n = min(len(c) for c in chains)
    chains = [c[:n] for c in chains]

    chain_means = np.array([c.mean() for c in chains])
    grand_mean = chain_means.mean()

    # Between-chain variance
    B = n * np.var(chain_means, ddof=1)
    # Within-chain variance
    W = np.mean([np.var(c, ddof=1) for c in chains])

    # Pooled variance estimate
    var_hat = ((n - 1) / n) * W + (1 / n) * B
    r_hat = np.sqrt(var_hat / W) if W > 0 else np.nan
    return r_hat


def make_trace_plots(model_version: str):
    """Generate trace + density plots and Gelman-Rubin table for a model."""
    df = load_samples(model_version)
    chain_ids = sorted(df["chain"].unique())
    param_cols = [c for c in df.columns if c != "chain"]
    n_chains = len(chain_ids)

    print(f"\n{'='*60}")
    print(f"Model {model_version}: {len(param_cols)} parameters, "
          f"{n_chains} chains, {len(df)} total samples")
    print(f"{'='*60}")

    # Compute Gelman-Rubin for all parameters
    rhat_results = {}
    for param in param_cols:
        chains = [df.loc[df["chain"] == ch, param].values for ch in chain_ids]
        rhat_results[param] = gelman_rubin(chains)

    # Print flagged parameters
    flagged = {p: r for p, r in rhat_results.items() if r > RHAT_THRESHOLD}
    if flagged:
        print(f"\n  WARNING: {len(flagged)} parameters with R-hat > {RHAT_THRESHOLD}:")
        for p, r in sorted(flagged.items(), key=lambda x: -x[1]):
            print(f"    {p}: {r:.4f}")
    else:
        print(f"\n  All parameters have R-hat <= {RHAT_THRESHOLD}")

    # Save Gelman-Rubin table
    out_dir = DATA_DIR / model_version / "trace_plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    rhat_df = pd.DataFrame([
        {"parameter": p, "r_hat": r, "converged": r <= RHAT_THRESHOLD}
        for p, r in rhat_results.items()
    ]).sort_values("r_hat", ascending=False)
    rhat_df.to_csv(out_dir / "gelman_rubin.csv", index=False)

    # Generate trace + density plots
    for param in param_cols:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.5))
        rhat = rhat_results[param]
        color_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]

        # Trace plot
        for i, ch in enumerate(chain_ids):
            vals = df.loc[df["chain"] == ch, param].values
            ax1.plot(vals, alpha=0.6, linewidth=0.3,
                     color=color_cycle[i % len(color_cycle)],
                     label=f"Chain {ch}")
        ax1.set_title(f"Trace: {param}")
        ax1.set_xlabel("Iteration")
        ax1.legend(fontsize=7, loc="upper right")

        # Density plot
        for i, ch in enumerate(chain_ids):
            vals = df.loc[df["chain"] == ch, param].values
            ax2.hist(vals, bins=60, density=True, alpha=0.4,
                     color=color_cycle[i % len(color_cycle)],
                     label=f"Chain {ch}")
        ax2.set_title(f"Density: {param}  (R-hat: {rhat:.4f})")
        ax2.legend(fontsize=7, loc="upper right")

        fig.tight_layout()
        safe_name = param.replace("[", "_").replace("]", "").replace(",", "_")
        fig.savefig(out_dir / f"{safe_name}.png", dpi=150)
        plt.close(fig)

    print(f"  Saved {len(param_cols)} plots to {out_dir}/")
    print(f"  Gelman-Rubin table: {out_dir / 'gelman_rubin.csv'}")


def find_all_models() -> list[str]:
    """Find all model versions that have a raw_samples.csv."""
    models = []
    for d in sorted(DATA_DIR.iterdir()):
        if d.is_dir() and (d / "raw_samples.csv").exists():
            models.append(d.name)
    return models


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    versions = sys.argv[1:]
    if versions == ["all"]:
        versions = find_all_models()
        if not versions:
            print("No models with raw_samples.csv found.")
            sys.exit(1)
        print(f"Found models: {', '.join(versions)}")

    for v in versions:
        try:
            make_trace_plots(v)
        except (FileNotFoundError, ValueError) as e:
            print(f"\n  SKIP {v}: {e}")
