#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

COMPOSE_CMD=(docker compose)
BASE_URL="${BASE_URL:-http://localhost:8000}"
PASSWORD="${PASSWORD:-StrongPass123}"

echo "==> Waiting backend: ${BASE_URL}/api/health/"
until curl -sf "${BASE_URL}/api/health/" > /dev/null; do
  echo "waiting backend..."
  sleep 2
done

echo "==> Seeding demo users and requests"
"${COMPOSE_CMD[@]}" exec -T backend python manage.py seed_demo_data --password "${PASSWORD}" --reset

cat <<EOF

Demo data is ready.

Main demo accounts:
  applicant_demo / ${PASSWORD}
  helper_demo / ${PASSWORD}
  moderator_demo / ${PASSWORD}
  admin_demo / ${PASSWORD}

Useful follow-up:
  ./seed_users.sh
  ./smoke_api.sh
  ./smoke_negative_fraud.sh
EOF
