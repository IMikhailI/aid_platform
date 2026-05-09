#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

COMPOSE_CMD=(docker compose)
BASE_URL="${BASE_URL:-http://localhost:8000}"
REPORT_PATH="${REPORT_PATH:-/app/docs/antifraud_report.json}"

echo "==> Waiting backend: ${BASE_URL}/api/health/"
until curl -sf "${BASE_URL}/api/health/" > /dev/null; do
  echo "waiting backend..."
  sleep 2
done

echo "==> Purging all requests"
"${COMPOSE_CMD[@]}" exec -T backend python manage.py purge_requests --yes

echo "==> Running antifraud unit tests"
"${COMPOSE_CMD[@]}" exec -T backend python manage.py test users.tests fraud.tests requests_app.tests

echo "==> Running negative/fraud smoke scenario"
./smoke_negative_fraud.sh

echo "==> Generating antifraud smoke report"
"${COMPOSE_CMD[@]}" exec -T backend python manage.py antifraud_smoke --out "${REPORT_PATH}"

cat <<EOF

Antifraud lab finished.

Artifacts:
  Backend report: backend/docs/antifraud_report.json

Useful follow-up:
  ./seed_demo.sh
  docker compose exec backend python manage.py test fraud.tests.test_antifraud_engine
EOF
