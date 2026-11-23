#!/usr/bin/env bash
# Build the UI and redeploy the Databricks App. Usage: [DATABRICKS_PROFILE=<profile>] [VITE_BRAND=<brand id>] scripts/deploy.sh
# The UI brand is chosen at build time (VITE_BRAND, default = the neutral 'apex' brand).
set -euo pipefail
cd "$(dirname "$0")/.."
P="${DATABRICKS_PROFILE:-apex-construction}"
ME="$(databricks current-user me -p "$P" -o json | python3 -I -c 'import json,sys;print(json.load(sys.stdin)["userName"])')"
D="/Workspace/Users/$ME/apps/construction-control-tower"
(cd frontend && npm run build >/dev/null) && echo "✓ built frontend (brand: ${VITE_BRAND:-apex})"
# uv.lock/pyproject pin a laptop-local PyPI proxy — the app installs from requirements.txt instead.
databricks sync . "$D" --full --exclude "docs/**" --exclude "data_gen/out/**" --exclude "frontend/node_modules/**" \
  --exclude "uv.lock" --exclude "pyproject.toml" --exclude ".claude/**" --exclude "lakeflow/**" --exclude "evidence/**" \
  --exclude "deck/**" --exclude "_submission/**" --exclude "make_submission.py" -p "$P" >/dev/null && echo "✓ synced source"
databricks workspace import-dir frontend/dist "$D/frontend/dist" --overwrite -p "$P" >/dev/null && echo "✓ uploaded frontend/dist"
databricks apps deploy construction-control-tower --source-code-path "$D" -p "$P" -o json --timeout 20m | python3 -I -c "import json,sys;print('✓ deploy:', json.load(sys.stdin)['status'])"
