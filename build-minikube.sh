#!/usr/bin/env bash
#
# Simulation Server: Minikube build and deployment
# =================================================
#
# Prerequisites:
#   minikube start --driver=docker
#   cp .env.example .env
#   chmod 600 .env
#
# For local use without OIDC credentials, set AUTH_DISABLED=true in .env.
# Otherwise populate OIDC_CLIENT_ID and OIDC_CLIENT_SECRET (the default mode).
# Choose a local DB_PASSWORD and generate SESSION_SECRET
# with:
#   openssl rand -hex 32
#
# HTTPS requires:
#   data/certs/key.pem
#   data/certs/cert.pem
#
# A local self-signed pair can be generated with:
#   mkdir -p data/certs
#   openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
#     -keyout data/certs/key.pem -out data/certs/cert.pem \
#     -subj "/CN=localhost" \
#     -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
#
# Keep the data mount running in a separate terminal:
#   minikube mount "$(pwd)/data:/data"
#
# Build and deploy:
#   ./build-minikube.sh
#
# Forward the HTTPS web service in another terminal:
#   kubectl -n simservice port-forward service/web 5001:5001
#   kubectl -n simservice port-forward service/mosaik-gui 8002:80
#
# Open:
#   https://localhost:5001
#   http://localhost:8002 (Mosaik scenario editor, sharing Orbit with the worker)
#
# Inspect the cluster:
#   kubectl -n simservice get pods,jobs
#   kubectl -n kafka get pods
#   kubectl -n simservice logs deployment/web -f
#   kubectl -n simservice logs deployment/simservice -f
#   kubectl -n simservice logs deployment/log-consumer -f
#   kubectl get events -A --sort-by=.lastTimestamp
#
# Set MINIKUBE_PROFILE before running to use a non-default profile.
# Back up existing PostgreSQL before the additive task-framework migration.
# Mosaik starts enabled for trusted local use; simulator code is not sandboxed.
# See docs/deployment-guide.md for setup, verification, and recovery.

set -Eeuo pipefail

readonly ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROFILE="${MINIKUBE_PROFILE:-minikube}"
readonly ENV_FILE="${ENV_FILE:-${ROOT_DIR}/.env}"
readonly MANIFEST="${ROOT_DIR}/simservice/k8s/minikube-full-stack.yaml"
readonly NAMESPACE="simservice"

TEMP_DIR=""

log() {
    printf '\n==> %s\n' "$*"
}

fail() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

cleanup() {
    if [[ -n "${TEMP_DIR}" && -d "${TEMP_DIR}" ]]; then
        rm -rf -- "${TEMP_DIR}"
    fi
}

trap cleanup EXIT
trap 'printf "Build failed at line %s.\n" "${LINENO}" >&2' ERR

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

require_value() {
    local name="$1"
    local value="${!name:-}"

    [[ -n "${value}" ]] || fail "${name} is missing from ${ENV_FILE}"
    case "${value}" in
        replace-*|change-me-*|\*\*\*REMOVED*)
            fail "${name} still contains a placeholder value"
            ;;
    esac
}

build_image() {
    local tag="$1"
    local context="$2"

    log "Building ${tag}"
    docker build --tag "${tag}" "${context}"
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    sed -n '2,/^set -Eeuo pipefail$/p' "${BASH_SOURCE[0]}" | sed '$d'
    exit 0
fi

[[ $# -eq 0 ]] || fail "Unknown argument: $1"

for command_name in minikube kubectl docker npm python3; do
    require_command "${command_name}"
done

[[ -f "${ENV_FILE}" ]] || fail "Create ${ENV_FILE} from .env.example and populate it first"
[[ -f "${MANIFEST}" ]] || fail "Kubernetes manifest not found: ${MANIFEST}"
[[ -f "${ROOT_DIR}/data/certs/key.pem" ]] || fail "Missing data/certs/key.pem"
[[ -f "${ROOT_DIR}/data/certs/cert.pem" ]] || fail "Missing data/certs/cert.pem"

chmod 600 "${ENV_FILE}"
set -a
# shellcheck disable=SC1090
source "${ENV_FILE}"
set +a

AUTH_DISABLED="${AUTH_DISABLED:-false}"
case "${AUTH_DISABLED}" in
    true|false) ;;
    *) fail "AUTH_DISABLED must be true or false" ;;
esac

for variable_name in DB_PASSWORD SESSION_SECRET; do
    require_value "${variable_name}"
done
if [[ "${AUTH_DISABLED}" == "false" ]]; then
    require_value OIDC_CLIENT_ID
    require_value OIDC_CLIENT_SECRET
else
    log "Local login enabled: all visitors share one development account. Keep access local."
fi

if [[ "$(minikube -p "${PROFILE}" status --format='{{.Host}}' 2>/dev/null || true)" != "Running" ]]; then
    fail "Minikube profile '${PROFILE}' is not running. Start it before running this script"
fi

current_context="$(kubectl config current-context 2>/dev/null || true)"
[[ "${current_context}" == "${PROFILE}" ]] || fail \
    "kubectl context is '${current_context:-unset}', expected '${PROFILE}'. Run: kubectl config use-context ${PROFILE}"

log "Using Minikube profile ${PROFILE}"
eval "$(minikube -p "${PROFILE}" docker-env --shell bash)"
docker info >/dev/null

log "Building frontend assets"
npm --prefix "${ROOT_DIR}/frontend" ci
npm --prefix "${ROOT_DIR}/frontend" run build

build_image "simaas-web:latest" "${ROOT_DIR}/fastapi_app"
build_image "simservice/simservice:latest" "${ROOT_DIR}/simservice"
build_image "simservice/pandapowerwrapper-wrapper:latest" "${ROOT_DIR}/simservice/PandaPowerWrapper"
build_image "simservice/sumowrapper-wrapper:latest" "${ROOT_DIR}/simservice/cppbase+sumowrapper"

build_image "simaas-mosaik-worker:latest" "${ROOT_DIR}/mosaik/mosaik-worker"

build_image "simservice/controllerwrapper-wrapper:latest" "${ROOT_DIR}/simservice/ControllerWrapper"


log "Preparing Kubernetes credentials"
kubectl create namespace "${NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

encoded_db_password="$(
    python3 - <<'PY'
import os
from urllib.parse import quote

print(quote(os.environ["DB_PASSWORD"], safe=""))
PY
)"

TEMP_DIR="$(mktemp -d)"
chmod 700 "${TEMP_DIR}"

{
    printf 'POSTGRES_USER=%s\n' "simserver"
    printf 'POSTGRES_PASSWORD=%s\n' "${DB_PASSWORD}"
    printf 'POSTGRES_DB=%s\n' "simserver"
} > "${TEMP_DIR}/postgres.env"

{
    printf 'OIDC_CLIENT_ID=%s\n' "${OIDC_CLIENT_ID:-}"
    printf 'OIDC_CLIENT_SECRET=%s\n' "${OIDC_CLIENT_SECRET:-}"
    printf 'SESSION_SECRET=%s\n' "${SESSION_SECRET}"
    printf 'DATABASE_URL=postgresql://simserver:%s@postgres.simservice.svc.cluster.local:5432/simserver\n' \
        "${encoded_db_password}"
} > "${TEMP_DIR}/web.env"

chmod 600 "${TEMP_DIR}/postgres.env" "${TEMP_DIR}/web.env"

kubectl -n "${NAMESPACE}" create secret generic postgres-secret \
    --from-env-file="${TEMP_DIR}/postgres.env" \
    --dry-run=client -o yaml | kubectl apply -f -

kubectl -n "${NAMESPACE}" create secret generic web-secret \
    --from-env-file="${TEMP_DIR}/web.env" \
    --dry-run=client -o yaml | kubectl apply -f -

cleanup
TEMP_DIR=""

log "Applying the full Minikube stack"
kubectl apply -f "${MANIFEST}"
kubectl -n "${NAMESPACE}" set env deployment/web AUTH_DISABLED="${AUTH_DISABLED}"

log "Migrating task framework metadata"
migration_job="$(kubectl create -f "${ROOT_DIR}/simservice/k8s/task-framework-migration.yaml" -o name)"
if ! kubectl -n "${NAMESPACE}" wait --for=condition=complete "${migration_job}" --timeout=180s; then
    kubectl -n "${NAMESPACE}" logs "${migration_job}" --all-containers=true || true
    fail "Metadata migration failed; inspect the migration job before continuing"
fi

log "Restarting local-image deployments"
kubectl -n "${NAMESPACE}" rollout restart \
    deployment/web \
    deployment/log-consumer \
    deployment/simservice \
    deployment/mosaik-worker \
    deployment/mosaik-gui

log "Deployment submitted"
kubectl -n kafka get pods
kubectl -n "${NAMESPACE}" get pods

cat <<EOF

Next terminals:
  minikube -p ${PROFILE} mount "${ROOT_DIR}/data:/data"
  kubectl -n ${NAMESPACE} port-forward service/web 5001:5001
  kubectl -n ${NAMESPACE} port-forward service/mosaik-gui 8002:80

Then open https://localhost:5001
The Mosaik Create scenario action opens http://localhost:8002
EOF
