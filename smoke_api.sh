#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

COMPOSE_CMD=(docker compose)
BASE_URL="${BASE_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"
PASS="${PASS:-StrongPass123}"
REGION="${REGION:-Moscow}"
RUN_ID="$(date +%s)"

APPLICANT_USER="smoke_applicant_${RUN_ID}"
MODERATOR_USER="smoke_moderator_${RUN_ID}"
HELPER_USER="smoke_helper_${RUN_ID}"

log() {
  printf '%s\n' "$1"
}

require_command() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    log "ERROR: command not found: ${cmd}"
    exit 1
  fi
}

json_expr() {
  local expr="$1"
  python3 -c "import json,sys; data=json.load(sys.stdin); result=${expr}; print(result if result is not None else '')"
}

register_user() {
  local username="$1"
  local role="$2"
  local email="${username}@example.com"

  local response
  response="$(curl -fsS -X POST "${BASE_URL}/api/auth/register/" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${username}\",\"email\":\"${email}\",\"password\":\"${PASS}\",\"role\":\"${role}\",\"region\":\"${REGION}\"}")"

  local user_id
  user_id="$(printf '%s' "${response}" | json_expr "data.get('id')")"
  if [ -z "${user_id}" ]; then
    log "ERROR: user registration did not return id for ${username}"
    printf '%s\n' "${response}"
    exit 1
  fi
  log "OK: created ${role} user ${username}"
}

upsert_internal_user() {
  local username="$1"
  local role="$2"
  local email="${username}@example.com"

  "${COMPOSE_CMD[@]}" exec -T backend python manage.py upsert_user \
    --username "${username}" \
    --password "${PASS}" \
    --role "${role}" \
    --email "${email}" \
    --region "${REGION}" >/dev/null

  log "OK: created ${role} user ${username}"
}

get_access_token() {
  local username="$1"

  curl -fsS -X POST "${BASE_URL}/api/auth/token/" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"${username}\",\"password\":\"${PASS}\"}" | \
    json_expr "data.get('access')"
}

assert_http_ok() {
  local name="$1"
  local url="$2"

  log "Checking ${name}: ${url}"
  curl -fsS "${url}" >/dev/null
  log "OK: ${name}"
}

require_command curl
require_command python3
require_command docker

assert_http_ok "backend health" "${BASE_URL}/api/health/"
assert_http_ok "admin login page" "${BASE_URL}/admin/login/"
assert_http_ok "swagger" "${BASE_URL}/api/docs/swagger/"
assert_http_ok "frontend" "${FRONTEND_URL}/"

register_user "${APPLICANT_USER}" "applicant"
register_user "${HELPER_USER}" "helper"
upsert_internal_user "${MODERATOR_USER}" "moderator"

APPLICANT_TOKEN="$(get_access_token "${APPLICANT_USER}")"
MODERATOR_TOKEN="$(get_access_token "${MODERATOR_USER}")"
HELPER_TOKEN="$(get_access_token "${HELPER_USER}")"

if [ -z "${APPLICANT_TOKEN}" ] || [ -z "${MODERATOR_TOKEN}" ] || [ -z "${HELPER_TOKEN}" ]; then
  log "ERROR: failed to obtain one or more JWT tokens"
  exit 1
fi

log "OK: obtained JWT tokens"

CREATE_RESPONSE="$(curl -fsS -X POST "${BASE_URL}/api/requests/applicant/create/" \
  -H "Authorization: Bearer ${APPLICANT_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"category\":\"food\",
    \"title\":\"Smoke request ${RUN_ID}\",
    \"description\":\"Smoke test request flow\",
    \"region\":\"${REGION}\",
    \"requested_amount\":\"2500.00\",
    \"urgency\":3
  }")"

REQUEST_ID="$(printf '%s' "${CREATE_RESPONSE}" | json_expr "data.get('id')")"
REQUEST_STATUS="$(printf '%s' "${CREATE_RESPONSE}" | json_expr "data.get('status')")"

if [ -z "${REQUEST_ID}" ] || [ "${REQUEST_STATUS}" != "on_moderation" ]; then
  log "ERROR: request creation failed"
  printf '%s\n' "${CREATE_RESPONSE}"
  exit 1
fi

log "OK: applicant created request #${REQUEST_ID}"

QUEUE_RESPONSE="$(curl -fsS "${BASE_URL}/api/requests/moderation/queue/" \
  -H "Authorization: Bearer ${MODERATOR_TOKEN}")"

QUEUE_HAS_REQUEST="$(printf '%s' "${QUEUE_RESPONSE}" | python3 -c '
import json
import sys

request_id = int(sys.argv[1])
data = json.load(sys.stdin)
items = data.get("results", data if isinstance(data, list) else [])
print(any(item.get("id") == request_id for item in items))
' "${REQUEST_ID}")"

if [ "${QUEUE_HAS_REQUEST}" != "True" ]; then
  log "ERROR: request #${REQUEST_ID} not found in moderation queue"
  exit 1
fi

log "OK: moderator queue contains request #${REQUEST_ID}"

APPROVE_RESPONSE="$(curl -fsS -X POST "${BASE_URL}/api/requests/moderation/${REQUEST_ID}/" \
  -H "Authorization: Bearer ${MODERATOR_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"action":"approve","comment":"Smoke test approve"}')"

APPROVED_STATUS="$(printf '%s' "${APPROVE_RESPONSE}" | json_expr "data.get('new_status')")"
if [ "${APPROVED_STATUS}" != "published" ]; then
  log "ERROR: moderation approve failed"
  printf '%s\n' "${APPROVE_RESPONSE}"
  exit 1
fi

log "OK: moderator approved request #${REQUEST_ID}"

TAKE_RESPONSE="$(curl -fsS -X POST "${BASE_URL}/api/requests/helper/take/${REQUEST_ID}/" \
  -H "Authorization: Bearer ${HELPER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"method":"certificate","note":"Smoke test take"}')"

TAKE_STATUS="$(printf '%s' "${TAKE_RESPONSE}" | json_expr "data.get('new_status')")"
if [ "${TAKE_STATUS}" != "in_progress" ]; then
  log "ERROR: helper failed to take request"
  printf '%s\n' "${TAKE_RESPONSE}"
  exit 1
fi

log "OK: helper took request #${REQUEST_ID}"

CLOSE_RESPONSE="$(curl -fsS -X PATCH "${BASE_URL}/api/requests/close/${REQUEST_ID}/" \
  -H "Authorization: Bearer ${HELPER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{}')"

CLOSE_MESSAGE="$(printf '%s' "${CLOSE_RESPONSE}" | json_expr "data.get('detail')")"
if [ "${CLOSE_MESSAGE}" != "Request closed successfully." ]; then
  log "ERROR: helper failed to close request"
  printf '%s\n' "${CLOSE_RESPONSE}"
  exit 1
fi

log "OK: helper closed request #${REQUEST_ID}"

HISTORY_RESPONSE="$(curl -fsS "${BASE_URL}/api/requests/${REQUEST_ID}/history/" \
  -H "Authorization: Bearer ${MODERATOR_TOKEN}")"

HAS_CLOSED_EVENT="$(printf '%s' "${HISTORY_RESPONSE}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
print(any(item.get("to_status") == "closed" for item in data))
')"

if [ "${HAS_CLOSED_EVENT}" != "True" ]; then
  log "ERROR: history does not contain closed status"
  printf '%s\n' "${HISTORY_RESPONSE}"
  exit 1
fi

cat <<EOF

Smoke test passed.

Created users:
  applicant: ${APPLICANT_USER}
  moderator: ${MODERATOR_USER}
  helper: ${HELPER_USER}

Verified request flow for request #${REQUEST_ID}:
  on_moderation -> published -> in_progress -> closed
EOF
