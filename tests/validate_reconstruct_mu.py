"""Parity validation: JAGS-monitored mu/fullmod/resid vs _old Python reconstruction.

Run from the project root:
    python3 tests/validate_reconstruct_mu.py

Uses the synthetic fixture (tests/fixtures/synthetic_data.csv) — no real data needed.
Tests v2_1 (Annual Cycle), the canonical model.

What is checked
---------------
mu_mean
    The new path (JAGS monitoring) and the old path (Python reconstruction) estimate
    the same quantity: E[alpha[i] + beta[i]*cos_t + gamma[i]*sin_t | y].
    Both use the identical set of MCMC draws, just traversed in different orders.
    Agreement should be exact up to floating-point summation order (atol ~1e-10).

mu_lower / mu_upper
    Same argument; quantiles are order-invariant. Exact agreement expected.

fullmod_mean  (fitted values)
    Old path: fitted[t] = E[mu[t]] + phi_mean * (y[t-1] - E[mu[t-1]])
              — uses point estimates, ignores cov(phi, mu).
    New path: E[fullmod[t]] = E[mu[t] + phi*(y[t-1]-mu[t-1])]
              — uses the full joint posterior; statistically more correct.
    These will NOT agree exactly. We report the max absolute difference and
    flag if it is implausibly large (> 0.5 on the scaled-per-10k data scale).

resid_mean
    Follows from fullmod: E[resid[t]] = y[t] - E[fullmod[t]].
    Old path computes y - fitted_old; new path is E[resid] from JAGS.
    Same difference as fullmod; we report and do not assert exact equality.
"""
import sys
from pathlib import Path
import numpy as np

# resolve project root so imports work from any working directory
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from pyjags_pipeline.defs.v2_1 import Model
from pyjags_pipeline.data import build_event_indicators
from pyjags_pipeline import ar as _ar

FIXTURE = _ROOT / 'tests' / 'fixtures' / 'synthetic_data.csv'
CHAINS  = 2
BURNIN  = 500
SAMPLE  = 1000
ADAPT   = 200
SEED    = 99

ATOL_MU      = 1e-8   # mu paths use identical samples — expect near-exact agreement
MAX_DIFF_FM  = 0.5    # fullmod paths may differ due to nonlinear averaging; flag if > this


def _bold(s): return f'\033[1m{s}\033[0m'
def _ok(s):   return f'\033[92m{s}\033[0m'
def _warn(s): return f'\033[93m{s}\033[0m'
def _fail(s): return f'\033[91m{s}\033[0m'


def main():
    print(_bold('\n=== validate_reconstruct_mu.py ===\n'))

    model = Model()

    # ------------------------------------------------------------------ #
    # 1. Fit model — this uses the new JAGS-monitored path
    # ------------------------------------------------------------------ #
    print('Fitting v2.1 on synthetic fixture ...')
    result = model.fit(
        data_path=str(FIXTURE),
        chains=CHAINS, burnin=BURNIN, sample=SAMPLE, adapt=ADAPT, seed=SEED,
    )

    regions   = result.regions
    n_weeks   = result.n_weeks
    raw_df    = result.raw_df
    df_og     = result.df_og
    indicators = result.indicators

    # ------------------------------------------------------------------ #
    # 2. Run _old reconstruction on the same raw_df
    # ------------------------------------------------------------------ #
    print('Running _old reconstruction paths ...')
    df_mu_old, df_mu_lower_old, df_mu_upper_old = model.reconstruct_mu_old(
        raw_df, regions, n_weeks, indicators)
    df_fitted_old = model.compute_fitted_old(df_mu_old, df_og, raw_df)
    df_resid_old, _ = _ar.compute_residuals(df_og, df_fitted_old)

    # ------------------------------------------------------------------ #
    # 3. Compare mu_mean
    # ------------------------------------------------------------------ #
    print('\n--- mu_mean ---')
    diff_mu = np.abs(result.df_mu.values - df_mu_old.values)
    max_diff_mu = diff_mu.max()
    mean_diff_mu = diff_mu.mean()
    print(f'  max |new - old|  : {max_diff_mu:.2e}')
    print(f'  mean |new - old| : {mean_diff_mu:.2e}')
    if max_diff_mu < ATOL_MU:
        print(_ok(f'  PASS  (atol {ATOL_MU:.0e})'))
        mu_ok = True
    else:
        print(_fail(f'  FAIL  max diff {max_diff_mu:.2e} exceeds atol {ATOL_MU:.0e}'))
        mu_ok = False

    # ------------------------------------------------------------------ #
    # 4. Compare mu_lower
    # ------------------------------------------------------------------ #
    print('\n--- mu_lower (2.5th pct) ---')
    diff_lower = np.abs(result.df_mu_lower.values - df_mu_lower_old.values)
    max_diff_lower = diff_lower.max()
    print(f'  max |new - old|  : {max_diff_lower:.2e}')
    if max_diff_lower < ATOL_MU:
        print(_ok(f'  PASS  (atol {ATOL_MU:.0e})'))
        lower_ok = True
    else:
        print(_fail(f'  FAIL  max diff {max_diff_lower:.2e} exceeds atol {ATOL_MU:.0e}'))
        lower_ok = False

    # ------------------------------------------------------------------ #
    # 5. Compare mu_upper
    # ------------------------------------------------------------------ #
    print('\n--- mu_upper (97.5th pct) ---')
    diff_upper = np.abs(result.df_mu_upper.values - df_mu_upper_old.values)
    max_diff_upper = diff_upper.max()
    print(f'  max |new - old|  : {max_diff_upper:.2e}')
    if max_diff_upper < ATOL_MU:
        print(_ok(f'  PASS  (atol {ATOL_MU:.0e})'))
        upper_ok = True
    else:
        print(_fail(f'  FAIL  max diff {max_diff_upper:.2e} exceeds atol {ATOL_MU:.0e}'))
        upper_ok = False

    # ------------------------------------------------------------------ #
    # 6. Report fullmod diff (not a pass/fail — new is statistically superior)
    # ------------------------------------------------------------------ #
    print('\n--- fullmod_mean (fitted values) ---')
    diff_fm = np.abs(result.df_fitted.values - df_fitted_old.values)
    max_diff_fm = diff_fm.max()
    mean_diff_fm = diff_fm.mean()
    print(f'  max |new - old|  : {max_diff_fm:.4f}')
    print(f'  mean |new - old| : {mean_diff_fm:.4f}')
    print('  NOTE: new path is E[fullmod | y] (joint posterior); old path uses')
    print('        point estimates of mu and phi — small discrepancy is expected.')
    if max_diff_fm > MAX_DIFF_FM:
        print(_warn(f'  WARN  max diff {max_diff_fm:.4f} > {MAX_DIFF_FM} — unusually large, investigate'))
    else:
        print(_ok(f'  OK    max diff within plausible range (<{MAX_DIFF_FM})'))

    # ------------------------------------------------------------------ #
    # 7. Report resid diff
    # ------------------------------------------------------------------ #
    print('\n--- resid_mean ---')
    diff_r = np.abs(result.df_residuals.values - df_resid_old.values)
    print(f'  max |new - old|  : {diff_r.max():.4f}')
    print(f'  mean |new - old| : {diff_r.mean():.4f}')
    print('  NOTE: mirrors fullmod diff — expected small discrepancy.')

    # ------------------------------------------------------------------ #
    # 8. Summary
    # ------------------------------------------------------------------ #
    print('\n' + _bold('=== Summary ==='))
    all_ok = mu_ok and lower_ok and upper_ok
    if all_ok:
        print(_ok('  mu mean/lower/upper: PASS — JAGS-monitored path agrees with Python reconstruction'))
    else:
        print(_fail('  mu mean/lower/upper: FAIL — check extraction logic in base._extract_matrix_summary'))

    print(f'  fullmod / resid: expected small discrepancy (new path is more correct)')
    print()

    return 0 if all_ok else 1


if __name__ == '__main__':
    sys.exit(main())
