#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

OPEN_REPORT=1
ARGS=()
for arg in "$@"; do
  if [[ "$arg" == "--no-open" ]]; then
    OPEN_REPORT=0
  else
    ARGS+=("$arg")
  fi
done

if [[ -f .venv/bin/activate ]]; then
  source .venv/bin/activate
fi

echo "==> pytest ${ARGS[*]:-}"
pytest "${ARGS[@]:-}" || true

echo "==> generate allure report"
allure generate reports/allure-results -o reports/allure-report --clean

REPORT_INDEX="$(pwd)/reports/allure-report/index.html"
echo "==> report: ${REPORT_INDEX}"

if [[ "$OPEN_REPORT" == "1" ]]; then
  echo "==> allure open (Ctrl+C to stop)"
  allure open reports/allure-report
fi
