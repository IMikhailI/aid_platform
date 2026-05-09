#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

COMPOSE_CMD=(docker compose)

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
BACKEND_HEALTH_URL="${BACKEND_HEALTH_URL:-${BACKEND_URL}/api/health/}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"
DB_SERVICE="${DB_SERVICE:-db}"
WAIT_TIMEOUT_SECONDS="${WAIT_TIMEOUT_SECONDS:-180}"
CHECK_INTERVAL_SECONDS="${CHECK_INTERVAL_SECONDS:-3}"

CLEAN_IMAGES=0
RESET_DB=0
FOLLOW_LOGS=0
SEED_USERS=0
SEED_DEMO=0

usage() {
  cat <<'EOF'
Usage: ./start_platform.sh [options]

Options:
  --clean-images   Stop containers and remove built images before start
  --reset-db       Remove volumes before start (DANGEROUS: deletes DB data)
  --seed-users     Run seed_users.sh after successful startup
  --seed-demo      Run seed_demo.sh after successful startup
  --logs           Follow compose logs after successful startup
  --help           Show this help
EOF
}

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

load_env_file() {
  if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
  fi
}

wait_for_http() {
  local name="$1"
  local url="$2"
  local deadline=$((SECONDS + WAIT_TIMEOUT_SECONDS))

  log "Waiting for ${name}: ${url}"
  until curl -fsS "${url}" >/dev/null 2>&1; do
    if [ "${SECONDS}" -ge "${deadline}" ]; then
      log "ERROR: timed out waiting for ${name}"
      return 1
    fi
    sleep "${CHECK_INTERVAL_SECONDS}"
  done

  log "OK: ${name} is ready"
}

check_postgres() {
  local user="${POSTGRES_USER:-aid_user}"
  local db="${POSTGRES_DB:-aid_platform}"

  log "Checking PostgreSQL..."
  if "${COMPOSE_CMD[@]}" exec -T "${DB_SERVICE}" pg_isready -U "${user}" -d "${db}" >/dev/null 2>&1; then
    log "OK: PostgreSQL is ready"
  else
    log "WARN: PostgreSQL readiness check failed"
    return 1
  fi
}

show_service_urls() {
  cat <<EOF

Platform is up.

Available services:
  Frontend: ${FRONTEND_URL}
  Backend API: ${BACKEND_URL}
  Health check: ${BACKEND_HEALTH_URL}
  Admin: ${BACKEND_URL}/admin/
  Swagger: ${BACKEND_URL}/api/docs/swagger/
  ReDoc: ${BACKEND_URL}/api/docs/redoc/
  PostgreSQL: localhost:5433

Useful commands:
  docker compose logs -f
  docker compose ps
  docker compose down
  docker compose restart backend
  docker compose restart frontend
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --clean-images)
      CLEAN_IMAGES=1
      ;;
    --reset-db)
      RESET_DB=1
      ;;
    --seed-users)
      SEED_USERS=1
      ;;
    --seed-demo)
      SEED_DEMO=1
      ;;
    --logs)
      FOLLOW_LOGS=1
      ;;
    --help)
      usage
      exit 0
      ;;
    *)
      log "ERROR: unknown option: $1"
      usage
      exit 1
      ;;
  esac
  shift
done

require_command docker
require_command curl
load_env_file

log "Stopping existing containers..."
if [ "${RESET_DB}" -eq 1 ]; then
  "${COMPOSE_CMD[@]}" down -v
else
  "${COMPOSE_CMD[@]}" down
fi

if [ "${CLEAN_IMAGES}" -eq 1 ]; then
  log "Removing built images..."
  "${COMPOSE_CMD[@]}" down --rmi all
fi

log "Building and starting containers..."
"${COMPOSE_CMD[@]}" up --build -d

log "Container status:"
"${COMPOSE_CMD[@]}" ps

check_postgres || true
wait_for_http "backend" "${BACKEND_HEALTH_URL}"
wait_for_http "frontend" "${FRONTEND_URL}"

if [ "${SEED_USERS}" -eq 1 ]; then
  if [ -x "./seed_users.sh" ]; then
    log "Running seed_users.sh..."
    ./seed_users.sh
  else
    log "WARN: seed_users.sh is not executable; skipping seed"
  fi
fi

if [ "${SEED_DEMO}" -eq 1 ]; then
  if [ -x "./seed_demo.sh" ]; then
    log "Running seed_demo.sh..."
    ./seed_demo.sh
  else
    log "WARN: seed_demo.sh is not executable; skipping demo seed"
  fi
fi

show_service_urls

if [ "${FOLLOW_LOGS}" -eq 1 ]; then
  "${COMPOSE_CMD[@]}" logs -f
fi
