#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

COMPOSE_CMD=(docker compose)

BASE_URL="${BASE_URL:-http://localhost:8000}"
PASS="${PASS:-StrongPass123}"
REGION="${REGION:-Moscow}"

echo "==> Waiting backend: ${BASE_URL}/api/health/"
until curl -sf "${BASE_URL}/api/health/" > /dev/null; do
  echo "waiting backend..."
  sleep 2
done

upsert_user () {
  local username="$1"
  local email="$2"
  local role="$3"

  "${COMPOSE_CMD[@]}" exec -T backend python manage.py upsert_user \
    --username "${username}" \
    --password "${PASS}" \
    --role "${role}" \
    --email "${email}" \
    --region "${REGION}"
}

get_access () {
  local username="$1"
  local token
  token=$(curl -s -X POST "${BASE_URL}/api/auth/token/" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${username}\",\"password\":\"${PASS}\"}" | \
    python3 -c 'import sys,json; d=json.load(sys.stdin); print(d.get("access",""))' 2>/dev/null || true)
  echo "$token"
}

echo "==> Register users"
upsert_user "applicant1" "a1@example.com" "applicant"
upsert_user "moderator1" "m1@example.com" "moderator"
upsert_user "helper1" "h1@example.com" "helper"

echo "==> Get tokens"
APPLICANT_TOKEN=$(get_access "applicant1")
MODERATOR_TOKEN=$(get_access "moderator1")
HELPER_TOKEN=$(get_access "helper1")

echo ""
echo "APPLICANT_TOKEN length: ${#APPLICANT_TOKEN}"
echo "MODERATOR_TOKEN length: ${#MODERATOR_TOKEN}"
echo "HELPER_TOKEN length: ${#HELPER_TOKEN}"

if [ ${#APPLICANT_TOKEN} -eq 0 ] || [ ${#MODERATOR_TOKEN} -eq 0 ] || [ ${#HELPER_TOKEN} -eq 0 ]; then
  echo "ERROR: some token is empty. Check backend logs and credentials."
  exit 1
fi

cat > .env.tokens <<EOF
APPLICANT_TOKEN=${APPLICANT_TOKEN}
MODERATOR_TOKEN=${MODERATOR_TOKEN}
HELPER_TOKEN=${HELPER_TOKEN}
EOF

echo ""
echo "Saved tokens to .env.tokens"
echo "Use: source .env.tokens"
echo "Then test:"
echo "curl -s ${BASE_URL}/api/auth/me/ -H \"Authorization: Bearer \$HELPER_TOKEN\""
