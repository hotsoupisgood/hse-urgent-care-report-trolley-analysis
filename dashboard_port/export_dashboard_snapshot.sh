#!/bin/bash
# Port the Model-tab snapshot from the analysis repo into the dashboard repo.
#
# Copies the curated v4.6 (per 10,000 population) findings + phase results + plots,
# installs the Model tab code, and makes app.py the live entrypoint.
#
# Run from anywhere:  bash dashboard_port/export_dashboard_snapshot.sh
# Writes into ../dashboard_old, which is outside the sandbox, so run with the
# sandbox disabled.
set -euo pipefail

SRC="/Users/fluffypony/Library/Mobile Documents/com~apple~CloudDocs/Documents/Galway/PROJECT/CODE"
DST="/Users/fluffypony/Library/Mobile Documents/com~apple~CloudDocs/Documents/Galway/PROJECT/dashboard_old"
MODEL="$SRC/data/models/wide_weekly_scaledPer10k/v4.6"

# -- 1. App code --------------------------------------------------------------
cp "$SRC/dashboard_port/app.py"       "$DST/dashboard/app.py"
cp "$SRC/dashboard_port/model_tab.py" "$DST/dashboard/model_tab.py"
rm -f "$DST/dashboard/app_old.py"

# -- 2. Findings (CSV) --------------------------------------------------------
mkdir -p "$DST/dashboard/findings/v4.6"
cp "$MODEL/dic.csv"            "$DST/dashboard/findings/v4.6/dic.csv"
cp "$SRC/thesis/phase_table.csv"          "$DST/dashboard/findings/phase_table.csv"

# -- 3. Plots (PNG -> assets) -------------------------------------------------
mkdir -p "$DST/dashboard/assets/models/v4.6"
cp "$MODEL/plots/mu_fit.png"              "$DST/dashboard/assets/models/v4.6/mu_fit.png"
cp "$SRC/findings_draft/phase_forest.png" "$DST/dashboard/assets/phase_forest.png"
cp "$SRC/findings_draft/model_map_alpha.png" "$DST/dashboard/assets/model_map_alpha.png"
cp "$SRC/findings_draft/event_newyear.png"            "$DST/dashboard/assets/event_newyear.png"
cp "$SRC/findings_draft/event_midwest_reset.png"      "$DST/dashboard/assets/event_midwest_reset.png"
cp "$SRC/findings_draft/event_newyear_fit.png"        "$DST/dashboard/assets/event_newyear_fit.png"
cp "$SRC/findings_draft/event_midwest_reset_fit.png"  "$DST/dashboard/assets/event_midwest_reset_fit.png"

echo "Snapshot ported to $DST/dashboard"
echo "Next:"
echo "  cd \"$DST\" && bash start.sh --dev      # smoke-test locally"
echo "  then commit and run deploy.sh on the droplet"
