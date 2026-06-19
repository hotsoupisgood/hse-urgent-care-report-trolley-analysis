"""Fit the regional-structure ablation models and export their DIC.

Baseline-ladder ablations (no AR, no event terms):
  v4.10 : global level (no regional alpha)      -- compare against v4.1
  v4.11 : regional level + shared annual cycle   -- compare against v4.2

Matched ablations of the reported model v4.6 (AR(2) + New Year + Mid West reset):
  v4.12 : v4.6 with a global level               -- compare against v4.6
  v4.13 : v4.6 with a shared annual cycle        -- compare against v4.6

Only fit + export are run. test_all is skipped because the global-level models
have no per-region alpha for the ranking test.
"""
from pyjags_pipeline import get_model

DATA = 'data/wide_weekly_scaledPer10k.csv'

for version in ['v4.10', 'v4.11', 'v4.12', 'v4.13']:
    model = get_model(version)
    result = model.fit(data_path=DATA, seed=42)
    model.export(result)
    print(f'{version}: {result.dic}')
