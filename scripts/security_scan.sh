#!/bin/sh
set -eu
python -m pip install --quiet pip-audit
pip-audit -r requirements.txt
if command -v docker >/dev/null 2>&1; then
  echo "Container scanning should be run with Trivy/registry scanner in CI."
fi
