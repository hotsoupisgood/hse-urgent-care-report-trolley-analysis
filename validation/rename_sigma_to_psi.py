"""One-shot backfill: rename sigma_* -> psi_* in data/models/ outputs.

Touches:
  raw_samples.csv         -- column headers
  gelman.csv              -- Parameter column values
  gelman_summary.csv      -- Parameter column values
  global_parameters.csv   -- Parameter column values
  sigma_overall.csv       -- Parameter column values + file renamed to psi_overall.csv

Idempotent: if psi_* is already present (and no sigma_* remains), the file is skipped.
Run with --dry-run (default) to preview, --apply to write.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1] / 'data' / 'models'
SIGMA_RE = re.compile(r'^sigma_')


def rename_token(token: str) -> str:
    return SIGMA_RE.sub('psi_', token)


def process_column_headers(path: Path, apply: bool) -> list[str]:
    df = pd.read_csv(path, nrows=0)
    sigma_cols = [c for c in df.columns if c.startswith('sigma_')]
    if not sigma_cols:
        return []
    msgs = [f'  cols: {sigma_cols} -> {[rename_token(c) for c in sigma_cols]}']
    if apply:
        df_full = pd.read_csv(path)
        df_full = df_full.rename(columns={c: rename_token(c) for c in sigma_cols})
        df_full.to_csv(path, index=False)
    return msgs


def process_parameter_values(path: Path, apply: bool) -> list[str]:
    df = pd.read_csv(path)
    col = next((c for c in ('Parameter', 'param') if c in df.columns), None)
    if col is None:
        return []
    mask = df[col].astype(str).str.startswith('sigma_')
    if not mask.any():
        return []
    old_vals = sorted(df.loc[mask, col].unique().tolist())
    new_vals = [rename_token(v) for v in old_vals]
    msgs = [f'  {col} rows: {old_vals} -> {new_vals}']
    if apply:
        df.loc[mask, col] = df.loc[mask, col].map(rename_token)
        df.to_csv(path, index=False)
    return msgs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='Write changes. Without this flag, dry-run only.')
    args = ap.parse_args()
    apply = args.apply
    mode = 'APPLY' if apply else 'DRY-RUN'
    print(f'[{mode}] root: {ROOT}')

    if not ROOT.exists():
        print(f'ERROR: {ROOT} does not exist')
        return 1

    n_files_changed = 0
    n_files_renamed = 0

    handlers = {
        'raw_samples.csv':       process_column_headers,
        'gelman.csv':            process_parameter_values,
        'gelman_summary.csv':    process_parameter_values,
        'global_parameters.csv': process_parameter_values,
    }

    for path in sorted(ROOT.rglob('*.csv')):
        rel = path.relative_to(ROOT)
        name = path.name
        if name in handlers:
            msgs = handlers[name](path, apply)
            if msgs:
                print(f'[{mode}] {rel}')
                for m in msgs:
                    print(m)
                n_files_changed += 1
        elif name == 'sigma_overall.csv':
            new_path = path.with_name('psi_overall.csv')
            print(f'[{mode}] {rel}  ->  {new_path.relative_to(ROOT)}')
            msgs = process_parameter_values(path, apply)
            for m in msgs:
                print(m)
            if apply:
                path.rename(new_path)
            n_files_renamed += 1
            n_files_changed += 1

    print()
    print(f'[{mode}] files modified: {n_files_changed}')
    print(f'[{mode}] files renamed:  {n_files_renamed}')
    if not apply:
        print('Re-run with --apply to write changes.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
