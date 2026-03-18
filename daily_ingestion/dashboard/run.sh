#!/usr/bin/env bash
# Launch the HSE TrolleyGAR dashboard
cd "$(dirname "$0")"
source ../../venv/bin/activate 2>/dev/null || true
python3 app.py
