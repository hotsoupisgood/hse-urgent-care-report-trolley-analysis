from pathlib import Path

import numpy as np
import pandas as pd


# project root — two levels up from this file
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

_DEFAULT_DATA_PATH = 'data/wide_weekly_scaledPer10k.csv'


def load_observed(data_path=_DEFAULT_DATA_PATH):
    """Load the wide observed data matrix.

    Parameters
    ----------
    data_path : str or Path
        Path to the CSV file. Relative paths are resolved from the project root.

    Returns
    -------
    df_og : DataFrame
        Raw wide DataFrame with Region column removed, weeks as columns.
    regions : list[str]
        Region names in row order.
    n_region : int
    n_weeks : int
    y_matrix : np.ndarray
        Shape (n_region, n_weeks) for pyjags.
    """
    path = Path(data_path)
    if not path.is_absolute():
        path = _PROJECT_ROOT / path
    df = pd.read_csv(path)
    regions = df['Region'].tolist()
    df_og = df.drop(columns='Region')
    n_region = len(regions)
    n_weeks = df_og.shape[1]
    y_matrix = df_og.values.astype(float)
    return df_og, regions, n_region, n_weeks, y_matrix


def build_event_indicators(n_weeks, regions):
    """Build time vectors and event indicator arrays matching the R models."""
    t_vec = np.arange(1, n_weeks + 1)
    week_mod = t_vec % 52

    return {
        't_vec': t_vec,
        'cos_t': np.cos(2 * np.pi * t_vec / 52),
        'sin_t': np.sin(2 * np.pi * t_vec / 52),
        'cos_t26': np.cos(2 * np.pi * t_vec / 26),
        'sin_t26': np.sin(2 * np.pi * t_vec / 26),
        'cos_t4': np.cos(2 * np.pi * t_vec / 4),
        'sin_t4': np.sin(2 * np.pi * t_vec / 4),
        'cos_t10': np.cos(2 * np.pi * t_vec / 10),
        'sin_t10': np.sin(2 * np.pi * t_vec / 10),
        'cos_t8': np.cos(2 * np.pi * t_vec / 8),
        'sin_t8': np.sin(2 * np.pi * t_vec / 8),
        'ny_pre': (week_mod == 0).astype(float),
        'ny_mid': (week_mod == 1).astype(float),
        'ny_post': (week_mod == 2).astype(float),
        'fr_pre': (t_vec == 86).astype(float),
        'fr_mid': (t_vec == 87).astype(float),
        'fr_post': (t_vec == 88).astype(float),
        'mw': np.array([1.0 if r == 'HSE Mid West' else 0.0 for r in regions]),
    }


def load_region_covariate(csv_path, regions, value_col, key_col='Region',
                          center=False, scale=1.0):
    """Load a region-level covariate and align it to model region order."""
    df = pd.read_csv(_PROJECT_ROOT / csv_path)
    aligned = df.set_index(key_col).loc[regions].reset_index()
    aligned[value_col] = aligned[value_col].astype(float) * scale
    if center:
        aligned[f'{value_col}_centered'] = aligned[value_col] - aligned[value_col].mean()
    return aligned
