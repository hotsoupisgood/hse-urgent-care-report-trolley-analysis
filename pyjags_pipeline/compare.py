"""DIC comparison across model versions for a given data path."""
from pathlib import Path

import pandas as pd


_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MODELS_ROOT = _PROJECT_ROOT / 'data' / 'models'


def compare_dic(data_path, versions=None):
    """Load DIC results for all fitted models under a given data path.

    Parameters
    ----------
    data_path : str or Path
        The CSV used for fitting, e.g. 'data/wide_weekly_scaledPerBed.csv'.
        Only the filename stem is used to locate the output directory.
    versions : list[str], optional
        Restrict to these version strings (e.g. ['v3.1', 'v4.1']).
        If None, all versions with a dic.csv in the output dir are included.

    Returns
    -------
    pd.DataFrame
        Columns: version, deviance, penalty, DIC — sorted by DIC ascending.
    """
    stem = Path(data_path).stem
    scale_dir = _MODELS_ROOT / stem

    if not scale_dir.exists():
        raise FileNotFoundError(
            f'No output found for {stem!r}. '
            f'Expected directory: {scale_dir}'
        )

    rows = []
    for dic_path in sorted(scale_dir.glob('*/dic.csv')):
        version = dic_path.parent.name
        if versions is not None and version not in versions:
            continue
        df = pd.read_csv(dic_path)
        row = df.iloc[0].to_dict()
        row['version'] = version
        rows.append(row)

    if not rows:
        raise ValueError(
            f'No dic.csv files found under {scale_dir}. '
            'Run models first with run_model().'
        )

    result = pd.DataFrame(rows)[['version', 'deviance', 'penalty', 'DIC']]
    return result.sort_values('DIC').reset_index(drop=True)
