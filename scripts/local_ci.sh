#!/usr/bin/env bash
# Run the same checks as .github/workflows/ci.yml, locally, before anything is pushed.
#
#   scripts/local_ci.sh            # from the main folder
#   PYTHON=/path/to/python3.11 scripts/local_ci.sh
#
# Backend: pytest on Python 3.11 (CI's version). Frontend: vitest, then a production
# build with Research and Scenario Lab on (same defaults as Pages).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-$ROOT/.venv-render/bin/python}"

step() { printf '\n== %s\n' "$1"; }

step "Backend tests ($("$PYTHON" -V 2>&1), every event must be cross-verified)"
SCENARIO_REQUIRE_VERIFIED=1 "$PYTHON" -m pytest backend/tests -q

if [ ! -d frontend/node_modules ]; then
  echo "frontend/node_modules is missing; run 'npm ci' in frontend/ first" >&2
  exit 1
fi

step "Frontend tests"
(cd frontend && npm test --silent)

step "Frontend build (Pages settings, Scenario Lab on)"
(cd frontend && VITE_BASE_PATH=/Arcus/ VITE_ENABLE_RESEARCH=true VITE_ENABLE_SCENARIOS=true npm run build --silent)
if ! grep -rq "dashboard/scenarios" frontend/dist; then
  echo "Scenario Lab route missing from a build where it should be on" >&2
  exit 1
fi
echo "Scenario Lab route compiled in: ok"

step "All local CI checks passed"
