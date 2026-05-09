#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

COMPOSE_CMD=(docker compose)
BASE_URL="${BASE_URL:-http://localhost:8000}"
PASS="${PASS:-StrongPass123}"
REGION="${REGION:-Moscow}"
RUN_ID="$(date +%s)"

APPLICANT_USER="neg_applicant_${RUN_ID}"
SECOND_APPLICANT_USER="neg_applicant2_${RUN_ID}"
IP_APPLICANT_USER="neg_ip_applicant_${RUN_ID}"
IP_SECOND_APPLICANT_USER="neg_ip_applicant2_${RUN_ID}"
HIGH_AMOUNT_APPLICANT_USER="neg_amount_applicant_${RUN_ID}"
DUPLICATE_APPLICANT_USER="neg_duplicate_applicant_${RUN_ID}"
MODERATOR_USER="neg_moderator_${RUN_ID}"
HELPER1_USER="neg_helper1_${RUN_ID}"
HELPER2_USER="neg_helper2_${RUN_ID}"

API_STATUS=""
API_BODY=""

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

api_request() {
  local method="$1"
  local url="$2"
  local token="${3:-}"
  local data="${4:-}"
  shift 4 || true
  local body_file
  local curl_args

  body_file="$(mktemp)"
  curl_args=(-sS -o "${body_file}" -w "%{http_code}" -X "${method}")

  if [ -n "${token}" ]; then
    curl_args+=(-H "Authorization: Bearer ${token}")
  fi

  if [ -n "${data}" ]; then
    curl_args+=(-H "Content-Type: application/json" -d "${data}")
  fi

  for extra_header in "$@"; do
    if [ -n "${extra_header}" ]; then
      curl_args+=(-H "${extra_header}")
    fi
  done

  curl_args+=("${url}")

  API_STATUS="$(curl "${curl_args[@]}")"
  API_BODY="$(cat "${body_file}")"
  rm -f "${body_file}"
}

assert_status() {
  local expected="$1"
  local context="$2"

  if [ "${API_STATUS}" != "${expected}" ]; then
    log "ERROR: ${context} expected HTTP ${expected}, got ${API_STATUS}"
    printf '%s\n' "${API_BODY}"
    exit 1
  fi
}

require_command curl
require_command python3
require_command docker

log "Checking backend health..."
curl -fsS "${BASE_URL}/api/health/" >/dev/null
log "OK: backend health"

register_user "${APPLICANT_USER}" "applicant"
register_user "${SECOND_APPLICANT_USER}" "applicant"
register_user "${IP_APPLICANT_USER}" "applicant"
register_user "${IP_SECOND_APPLICANT_USER}" "applicant"
register_user "${HIGH_AMOUNT_APPLICANT_USER}" "applicant"
register_user "${DUPLICATE_APPLICANT_USER}" "applicant"
register_user "${HELPER1_USER}" "helper"
register_user "${HELPER2_USER}" "helper"
upsert_internal_user "${MODERATOR_USER}" "moderator"

APPLICANT_TOKEN="$(get_access_token "${APPLICANT_USER}")"
SECOND_APPLICANT_TOKEN="$(get_access_token "${SECOND_APPLICANT_USER}")"
IP_APPLICANT_TOKEN="$(get_access_token "${IP_APPLICANT_USER}")"
IP_SECOND_APPLICANT_TOKEN="$(get_access_token "${IP_SECOND_APPLICANT_USER}")"
HIGH_AMOUNT_APPLICANT_TOKEN="$(get_access_token "${HIGH_AMOUNT_APPLICANT_USER}")"
DUPLICATE_APPLICANT_TOKEN="$(get_access_token "${DUPLICATE_APPLICANT_USER}")"
MODERATOR_TOKEN="$(get_access_token "${MODERATOR_USER}")"
HELPER1_TOKEN="$(get_access_token "${HELPER1_USER}")"
HELPER2_TOKEN="$(get_access_token "${HELPER2_USER}")"

if [ -z "${APPLICANT_TOKEN}" ] || [ -z "${SECOND_APPLICANT_TOKEN}" ] || [ -z "${IP_APPLICANT_TOKEN}" ] || [ -z "${IP_SECOND_APPLICANT_TOKEN}" ] || [ -z "${HIGH_AMOUNT_APPLICANT_TOKEN}" ] || [ -z "${DUPLICATE_APPLICANT_TOKEN}" ] || [ -z "${MODERATOR_TOKEN}" ] || [ -z "${HELPER1_TOKEN}" ] || [ -z "${HELPER2_TOKEN}" ]; then
  log "ERROR: failed to obtain one or more JWT tokens"
  exit 1
fi

log "OK: obtained JWT tokens"

api_request POST "${BASE_URL}/api/requests/applicant/create/" "${APPLICANT_TOKEN}" "{
  \"category\":\"food\",
  \"title\":\"Negative flow ${RUN_ID}\",
  \"description\":\"Negative flow request\",
  \"region\":\"${REGION}\",
  \"requested_amount\":\"1500.00\",
  \"urgency\":3
}"
assert_status 201 "applicant create request"

REQUEST_ID="$(printf '%s' "${API_BODY}" | json_expr "data.get('id')")"
REQUEST_STATUS="$(printf '%s' "${API_BODY}" | json_expr "data.get('status')")"
if [ -z "${REQUEST_ID}" ] || [ "${REQUEST_STATUS}" != "on_moderation" ]; then
  log "ERROR: request creation returned unexpected payload"
  printf '%s\n' "${API_BODY}"
  exit 1
fi
log "OK: applicant created request #${REQUEST_ID}"

api_request POST "${BASE_URL}/api/requests/moderation/${REQUEST_ID}/" "${HELPER1_TOKEN}" '{"action":"approve","comment":"should fail"}'
assert_status 403 "helper cannot moderate"
log "OK: helper cannot moderate requests"

api_request POST "${BASE_URL}/api/requests/moderation/${REQUEST_ID}/" "${MODERATOR_TOKEN}" '{"action":"approve","comment":"negative-flow approve"}'
assert_status 200 "moderator approve"
log "OK: moderator approved request #${REQUEST_ID}"

api_request POST "${BASE_URL}/api/requests/helper/take/${REQUEST_ID}/" "${APPLICANT_TOKEN}" '{"method":"certificate","note":"should fail"}'
assert_status 403 "applicant cannot take request"
log "OK: applicant cannot take published requests"

api_request POST "${BASE_URL}/api/requests/helper/take/${REQUEST_ID}/" "${HELPER1_TOKEN}" '{"method":"certificate","note":"owner helper"}'
assert_status 200 "helper1 take request"
log "OK: helper1 took request #${REQUEST_ID}"

api_request PATCH "${BASE_URL}/api/requests/close/${REQUEST_ID}/" "${HELPER2_TOKEN}" '{}'
assert_status 403 "other helper cannot close"
log "OK: second helper cannot close чужую заявку"

api_request PATCH "${BASE_URL}/api/requests/close/${REQUEST_ID}/" "${HELPER1_TOKEN}" '{}'
assert_status 200 "owner helper close request"
log "OK: owner helper closed request #${REQUEST_ID}"

api_request GET "${BASE_URL}/api/requests/${REQUEST_ID}/history/" "${MODERATOR_TOKEN}"
assert_status 200 "moderator get history"
HAS_CLOSED_HISTORY="$(printf '%s' "${API_BODY}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
print(any(item.get("to_status") == "closed" for item in data))
')"
if [ "${HAS_CLOSED_HISTORY}" != "True" ]; then
  log "ERROR: history does not contain closed status for request #${REQUEST_ID}"
  printf '%s\n' "${API_BODY}"
  exit 1
fi
log "OK: history contains closed transition"

SHARED_DEVICE_ID="shared-device-${RUN_ID}"
DEVICE_IP_1="198.51.100.11"
DEVICE_IP_2="198.51.100.12"

api_request POST "${BASE_URL}/api/requests/applicant/create/" "${APPLICANT_TOKEN}" "{
  \"category\":\"food\",
  \"title\":\"Shared device duplicate ${RUN_ID}\",
  \"description\":\"Cross-account same-device duplicate check\",
  \"region\":\"${REGION}\",
  \"requested_amount\":\"1100.00\",
  \"urgency\":3
}" "X-Device-Id: ${SHARED_DEVICE_ID}" "X-Forwarded-For: ${DEVICE_IP_1}"
API_BODY_FIRST_DEVICE_REQ="${API_BODY}"
FIRST_SHARED_DEVICE_REQ_ID="$(printf '%s' "${API_BODY_FIRST_DEVICE_REQ}" | json_expr "data.get('id')")"
assert_status 201 "first same-device request create"

api_request POST "${BASE_URL}/api/requests/applicant/create/" "${SECOND_APPLICANT_TOKEN}" "{
  \"category\":\"food\",
  \"title\":\"Shared device duplicate ${RUN_ID}\",
  \"description\":\"Cross-account same-device duplicate check\",
  \"region\":\"${REGION}\",
  \"requested_amount\":\"1100.00\",
  \"urgency\":3
}" "X-Device-Id: ${SHARED_DEVICE_ID}" "X-Forwarded-For: ${DEVICE_IP_2}"
assert_status 201 "second same-device request create"
SECOND_SHARED_DEVICE_REQ_ID="$(printf '%s' "${API_BODY}" | json_expr "data.get('id')")"

api_request GET "${BASE_URL}/api/fraud/requests/${SECOND_SHARED_DEVICE_REQ_ID}/decision/" "${MODERATOR_TOKEN}"
assert_status 200 "same-device fraud decision"
SAME_DEVICE_ACTION="$(printf '%s' "${API_BODY}" | json_expr "data.get('action')")"
if [ "${SAME_DEVICE_ACTION}" != "manual_review" ]; then
  log "ERROR: expected same-device cross-account duplicate to be manual_review"
  printf '%s\n' "${API_BODY}"
  exit 1
fi

SAME_DEVICE_CODES="$(printf '%s' "${API_BODY}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
codes = {item.get("code") for item in data.get("reasons", [])}
print("DEVICE_SHARED_ACROSS_ACCOUNTS" in codes and "SAME_DEVICE_EXACT_DUPLICATE_CROSS_ACCOUNT" in codes)
')"
if [ "${SAME_DEVICE_CODES}" != "True" ]; then
  log "ERROR: expected same-device fraud reasons were not found"
  printf '%s\n' "${API_BODY}"
  exit 1
fi
log "OK: same-device cross-account duplicate escalated to manual_review"

SHARED_FORWARDED_IP="203.0.113.10"

api_request POST "${BASE_URL}/api/requests/applicant/create/" "${IP_APPLICANT_TOKEN}" "{
  \"category\":\"food\",
  \"title\":\"Shared IP duplicate ${RUN_ID}\",
  \"description\":\"Cross-account same-ip duplicate check\",
  \"region\":\"${REGION}\",
  \"requested_amount\":\"1150.00\",
  \"urgency\":3
}" "X-Forwarded-For: ${SHARED_FORWARDED_IP}"
assert_status 201 "first same-ip request create"

api_request POST "${BASE_URL}/api/requests/applicant/create/" "${IP_SECOND_APPLICANT_TOKEN}" "{
  \"category\":\"food\",
  \"title\":\"Shared IP duplicate ${RUN_ID}\",
  \"description\":\"Cross-account same-ip duplicate check\",
  \"region\":\"${REGION}\",
  \"requested_amount\":\"1150.00\",
  \"urgency\":3
}" "X-Forwarded-For: ${SHARED_FORWARDED_IP}"
assert_status 201 "second same-ip request create"
SECOND_SHARED_IP_REQ_ID="$(printf '%s' "${API_BODY}" | json_expr "data.get('id')")"

api_request GET "${BASE_URL}/api/fraud/requests/${SECOND_SHARED_IP_REQ_ID}/decision/" "${MODERATOR_TOKEN}"
assert_status 200 "same-ip fraud decision"
SAME_IP_ACTION="$(printf '%s' "${API_BODY}" | json_expr "data.get('action')")"
if [ "${SAME_IP_ACTION}" != "manual_review" ]; then
  log "ERROR: expected same-ip cross-account duplicate to be manual_review"
  printf '%s\n' "${API_BODY}"
  exit 1
fi

SAME_IP_CODES="$(printf '%s' "${API_BODY}" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
codes = {item.get("code") for item in data.get("reasons", [])}
print("IP_SHARED_ACROSS_ACCOUNTS" in codes and "SAME_IP_EXACT_DUPLICATE_CROSS_ACCOUNT" in codes)
')"
if [ "${SAME_IP_CODES}" != "True" ]; then
  log "ERROR: expected same-ip fraud reasons were not found"
  printf '%s\n' "${API_BODY}"
  exit 1
fi
log "OK: same-ip cross-account duplicate escalated to manual_review"

api_request POST "${BASE_URL}/api/requests/applicant/create/" "${HIGH_AMOUNT_APPLICANT_TOKEN}" "{
  \"category\":\"food\",
  \"title\":\"High amount urgent ${RUN_ID}\",
  \"description\":\"Amount plus urgency fraud signal check\",
  \"region\":\"${REGION}\",
  \"requested_amount\":\"50000.00\",
  \"urgency\":5
}"
assert_status 201 "high amount urgent request create"
HIGH_AMOUNT_REQ_ID="$(printf '%s' "${API_BODY}" | json_expr "data.get('id')")"

api_request GET "${BASE_URL}/api/fraud/requests/${HIGH_AMOUNT_REQ_ID}/decision/" "${MODERATOR_TOKEN}"
assert_status 200 "moderator fraud decision for amount+urgency"
HIGH_AMOUNT_ACTION="$(printf '%s' "${API_BODY}" | json_expr "data.get('action')")"
if [ "${HIGH_AMOUNT_ACTION}" != "manual_review" ]; then
  log "ERROR: expected high amount + urgency request to be manual_review"
  printf '%s\n' "${API_BODY}"
  exit 1
fi
log "OK: high amount + urgency request escalated to manual_review"

api_request POST "${BASE_URL}/api/requests/applicant/create/" "${DUPLICATE_APPLICANT_TOKEN}" "{
  \"category\":\"food\",
  \"title\":\"Fraud duplicate ${RUN_ID}\",
  \"description\":\"Exact duplicate payload\",
  \"region\":\"${REGION}\",
  \"requested_amount\":\"1200.00\",
  \"urgency\":3
}"
assert_status 201 "fraud duplicate create #1"
FRAUD_REQ1_ID="$(printf '%s' "${API_BODY}" | json_expr "data.get('id')")"

api_request POST "${BASE_URL}/api/requests/applicant/create/" "${DUPLICATE_APPLICANT_TOKEN}" "{
  \"category\":\"food\",
  \"title\":\"Fraud duplicate ${RUN_ID}\",
  \"description\":\"Exact duplicate payload\",
  \"region\":\"${REGION}\",
  \"requested_amount\":\"1200.00\",
  \"urgency\":3
}"
assert_status 201 "fraud duplicate create #2"
FRAUD_REQ2_ID="$(printf '%s' "${API_BODY}" | json_expr "data.get('id')")"

api_request POST "${BASE_URL}/api/requests/applicant/create/" "${DUPLICATE_APPLICANT_TOKEN}" "{
  \"category\":\"food\",
  \"title\":\"Fraud duplicate ${RUN_ID}\",
  \"description\":\"Exact duplicate payload\",
  \"region\":\"${REGION}\",
  \"requested_amount\":\"1200.00\",
  \"urgency\":3
}"
assert_status 201 "fraud duplicate create #3"
FRAUD_REQ3_ID="$(printf '%s' "${API_BODY}" | json_expr "data.get('id')")"

log "OK: created fraud duplicate series (${FRAUD_REQ1_ID}, ${FRAUD_REQ2_ID}, ${FRAUD_REQ3_ID})"

api_request GET "${BASE_URL}/api/fraud/requests/${FRAUD_REQ3_ID}/decision/" "${HELPER1_TOKEN}"
assert_status 403 "helper cannot read fraud decision"
log "OK: helper is forbidden from fraud decision"

api_request GET "${BASE_URL}/api/fraud/requests/${FRAUD_REQ2_ID}/decision/" "${MODERATOR_TOKEN}"
assert_status 200 "moderator fraud decision #2"
FRAUD_REQ2_ACTION="$(printf '%s' "${API_BODY}" | json_expr "data.get('action')")"
if [ "${FRAUD_REQ2_ACTION}" != "manual_review" ]; then
  log "ERROR: expected request #${FRAUD_REQ2_ID} fraud action manual_review"
  printf '%s\n' "${API_BODY}"
  exit 1
fi
log "OK: second duplicate escalated to manual_review"

api_request GET "${BASE_URL}/api/fraud/requests/${FRAUD_REQ3_ID}/decision/" "${MODERATOR_TOKEN}"
assert_status 200 "moderator fraud decision #3"
FRAUD_REQ3_ACTION="$(printf '%s' "${API_BODY}" | json_expr "data.get('action')")"
if [ "${FRAUD_REQ3_ACTION}" != "block" ]; then
  log "ERROR: expected request #${FRAUD_REQ3_ID} fraud action block"
  printf '%s\n' "${API_BODY}"
  exit 1
fi
log "OK: third duplicate escalated to block"

api_request POST "${BASE_URL}/api/fraud/requests/${FRAUD_REQ3_ID}/recheck/" "${HELPER1_TOKEN}"
assert_status 403 "helper cannot recheck fraud"
log "OK: helper is forbidden from fraud recheck"

api_request POST "${BASE_URL}/api/fraud/requests/${FRAUD_REQ3_ID}/recheck/" "${MODERATOR_TOKEN}"
assert_status 200 "moderator fraud recheck"
RECHECK_ACTION="$(printf '%s' "${API_BODY}" | json_expr "data.get('action')")"
if [ "${RECHECK_ACTION}" != "block" ]; then
  log "ERROR: expected recheck to keep action block"
  printf '%s\n' "${API_BODY}"
  exit 1
fi
log "OK: moderator recheck returned block as expected"

api_request POST "${BASE_URL}/api/fraud/requests/${FRAUD_REQ3_ID}/override/" "${MODERATOR_TOKEN}" '{"new_action":"allow","comment":"Smoke override"}'
assert_status 201 "moderator fraud override"
OVERRIDE_ACTION="$(printf '%s' "${API_BODY}" | json_expr "data.get('new_action')")"
if [ "${OVERRIDE_ACTION}" != "allow" ]; then
  log "ERROR: fraud override did not return allow"
  printf '%s\n' "${API_BODY}"
  exit 1
fi
log "OK: moderator override changed action to allow"

api_request GET "${BASE_URL}/api/fraud/requests/${FRAUD_REQ3_ID}/decision/" "${MODERATOR_TOKEN}"
assert_status 200 "moderator fraud decision after override"
FINAL_BASE_ACTION="$(printf '%s' "${API_BODY}" | json_expr "data.get('base_action')")"
FINAL_ACTION="$(printf '%s' "${API_BODY}" | json_expr "data.get('action')")"
FINAL_IS_OVERRIDDEN="$(printf '%s' "${API_BODY}" | json_expr "data.get('is_overridden')")"
if [ "${FINAL_ACTION}" != "allow" ]; then
  log "ERROR: fraud decision was not updated after override"
  printf '%s\n' "${API_BODY}"
  exit 1
fi
if [ "${FINAL_BASE_ACTION}" != "block" ] || [ "${FINAL_IS_OVERRIDDEN}" != "True" ]; then
  log "ERROR: override metadata after decision fetch is inconsistent"
  printf '%s\n' "${API_BODY}"
  exit 1
fi

api_request POST "${BASE_URL}/api/fraud/requests/${FRAUD_REQ3_ID}/recheck/" "${MODERATOR_TOKEN}"
assert_status 200 "moderator fraud recheck after override"
POST_OVERRIDE_BASE_ACTION="$(printf '%s' "${API_BODY}" | json_expr "data.get('base_action')")"
POST_OVERRIDE_ACTION="$(printf '%s' "${API_BODY}" | json_expr "data.get('action')")"
POST_OVERRIDE_IS_OVERRIDDEN="$(printf '%s' "${API_BODY}" | json_expr "data.get('is_overridden')")"
if [ "${POST_OVERRIDE_BASE_ACTION}" != "block" ] || [ "${POST_OVERRIDE_ACTION}" != "allow" ] || [ "${POST_OVERRIDE_IS_OVERRIDDEN}" != "True" ]; then
  log "ERROR: override did not survive fraud recheck"
  printf '%s\n' "${API_BODY}"
  exit 1
fi
log "OK: override survives recheck and keeps effective action"

cat <<EOF

Negative and fraud smoke test passed.

Verified permissions:
  helper cannot moderate
  applicant cannot take published request
  second helper cannot close чужую заявку
  helper cannot access fraud decision/recheck

Verified fraud behavior:
  same device + cross-account duplicate -> manual_review
  same IP + cross-account duplicate -> manual_review
  high amount + urgency -> manual_review
  duplicate #2 -> manual_review
  duplicate #3 -> block
  moderator recheck works
  moderator override to allow works and survives recheck
EOF
