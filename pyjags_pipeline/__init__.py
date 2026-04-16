import importlib
from pathlib import Path

from .compare import compare_dic
from .data import _DEFAULT_DATA_PATH

_DEFS_DIR = Path(__file__).parent / 'defs'


def get_model(version):
    """Import and return a Model instance. Accepts dot notation (v1.1) or underscore (v1_1)."""
    module_name = version.replace('.', '_')
    module = importlib.import_module(f'pyjags_pipeline.defs.{module_name}')
    return module.Model()


def list_models():
    """Return all available model version strings (dot notation)."""
    versions = []
    for p in sorted(_DEFS_DIR.glob('v*.py')):
        if p.stem.startswith('_'):
            continue
        try:
            mod = importlib.import_module(f'pyjags_pipeline.defs.{p.stem}')
            versions.append(mod.Model().version)
        except Exception:
            pass
    return versions


def run_model(version, data_path=_DEFAULT_DATA_PATH,
              chains=4, burnin=10000, sample=20000, adapt=1000, seed=None):
    """Fit a model and return a ModelResult.

    Parameters
    ----------
    version : str
        Model version, e.g. 'v3.1'.
    data_path : str or Path
        Path to the scaled CSV to use as input.
        Relative paths are resolved from the project root.
        Defaults to 'data/wide_weekly_scaledPer10k.csv'.
    chains, burnin, sample, adapt, seed
        Passed through to the JAGS sampler.

    Returns
    -------
    ModelResult
        Contains samples, DIC, Gelman, fitted values, residuals, output_dir.
    """
    model = get_model(version)
    return model.run(
        data_path=data_path,
        chains=chains,
        burnin=burnin,
        sample=sample,
        adapt=adapt,
        seed=seed,
    )
