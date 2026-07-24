#!/usr/bin/env bash
# ===========================================================================
# Conductor Data Pipeline — First-Time Setup Script
# ===========================================================================
#
# Performs initial setup:
#   1. Validate prerequisites (Docker, Docker Compose, .env)
#   2. Create Docker volumes
#   3. Pull all images
#   4. Build custom images (masking-engine)
#   5. Start all services
#   6. Wait for health checks to pass
#   7. Run healthcheck.sh for final verification
#
# Usage:
#   ./scripts/setup.sh
# ===========================================================================

set -euo pipefail

COMPOSE_FILE="docker-compose.data-pipeline.yml"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_CMD="docker compose -f ${PROJECT_DIR}/${COMPOSE_FILE}"
HEALTHCHECK_SCRIPT="${PROJECT_DIR}/scripts/healthcheck.sh"
HEALTH_TIMEOUT=120  # seconds to wait for all services to become healthy

# Colors (only if stdout is a terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[0;33m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BOLD=''
    NC=''
fi

info() {
    printf "${GREEN}[INFO]${NC} %s\n" "$1"
}

warn() {
    printf "${YELLOW}[WARN]${NC} %s\n" "$1"
}

error() {
    printf "${RED}[ERROR]${NC} %s\n" "$1"
}

header() {
    printf "\n${BOLD}=== %s ===${NC}\n" "$1"
}

# ===========================================================================
# 1. Validate prerequisites
# ===========================================================================
header "Checking Prerequisites"

# Docker daemon
if ! docker info >/dev/null 2>&1; then
    error "Docker is not running. Start Docker and try again."
    exit 1
fi
info "Docker daemon is running"

# Docker Compose v2
if ! docker compose version >/dev/null 2>&1; then
    error "Docker Compose v2 not found. Install docker-compose-plugin."
    exit 1
fi
compose_version=$(docker compose version --short 2>/dev/null || echo "unknown")
info "Docker Compose version: ${compose_version}"

# Compose file exists
if [ ! -f "${PROJECT_DIR}/${COMPOSE_FILE}" ]; then
    error "Compose file not found: ${PROJECT_DIR}/${COMPOSE_FILE}"
    exit 1
fi
info "Compose file found: ${COMPOSE_FILE}"

# .env file
if [ ! -f "${PROJECT_DIR}/.env" ]; then
    warn ".env file not found."
    if [ -f "${PROJECT_DIR}/.env.example" ]; then
        info "Copying .env.example to .env — fill in real values before production use."
        cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
    else
        error "No .env or .env.example found. Cannot continue."
        exit 1
    fi
fi
info ".env file present"

# Dockerfile for masking-engine
if [ ! -f "${PROJECT_DIR}/masking-engine/Dockerfile" ]; then
    error "masking-engine/Dockerfile not found. Cannot build masking-engine image."
    exit 1
fi
info "masking-engine/Dockerfile found"

# ===========================================================================
# 2. Create Docker volumes
# ===========================================================================
header "Creating Docker Volumes"

for vol in airbyte-db-data pipeline-artifacts; do
    if docker volume inspect "${vol}" >/dev/null 2>&1; then
        info "Volume '${vol}' already exists"
    else
        docker volume create "${vol}"
        info "Created volume '${vol}'"
    fi
done

# ===========================================================================
# 3. Pull images
# ===========================================================================
header "Pulling Docker Images"

info "Pulling all images (this may take a few minutes on first run)..."
${COMPOSE_CMD} pull --ignore-buildable 2>&1 | while IFS= read -r line; do
    printf "  %s\n" "${line}"
done
info "Image pull complete"

# ===========================================================================
# 4. Build custom images
# ===========================================================================
header "Building Custom Images"

info "Building masking-engine image..."
${COMPOSE_CMD} build masking-engine 2>&1 | while IFS= read -r line; do
    printf "  %s\n" "${line}"
done
info "Build complete"

# ===========================================================================
# 5. Start all services
# ===========================================================================
header "Starting Services"

info "Starting all services in detached mode..."
${COMPOSE_CMD} up -d 2>&1 | while IFS= read -r line; do
    printf "  %s\n" "${line}"
done
info "Services started"

# ===========================================================================
# 6. Wait for health checks
# ===========================================================================
header "Waiting for Health Checks (timeout: ${HEALTH_TIMEOUT}s)"

SERVICES_WITH_HEALTHCHECK=(
    "airbyte-db"
    "presidio-analyzer"
    "masking-engine"
    "unstructured-api"
)

elapsed=0
interval=5

while [ "${elapsed}" -lt "${HEALTH_TIMEOUT}" ]; do
    all_healthy=true

    for svc in "${SERVICES_WITH_HEALTHCHECK[@]}"; do
        health=$(${COMPOSE_CMD} ps --format '{{.Health}}' "${svc}" 2>/dev/null || echo "unknown")
        if [ "${health}" != "healthy" ]; then
            all_healthy=false
            break
        fi
    done

    if [ "${all_healthy}" = true ]; then
        info "All services with healthchecks are healthy (${elapsed}s elapsed)"
        break
    fi

    printf "  Waiting... (%ds / %ds)\r" "${elapsed}" "${HEALTH_TIMEOUT}"
    sleep "${interval}"
    elapsed=$((elapsed + interval))
done

if [ "${elapsed}" -ge "${HEALTH_TIMEOUT}" ]; then
    warn "Health check timeout reached (${HEALTH_TIMEOUT}s). Some services may not be healthy yet."
    printf "\nCurrent status:\n"
    ${COMPOSE_CMD} ps 2>/dev/null
fi

# ===========================================================================
# 7. Run healthcheck script for final verification
# ===========================================================================
header "Final Verification"

if [ -x "${HEALTHCHECK_SCRIPT}" ]; then
    info "Running healthcheck.sh..."
    if "${HEALTHCHECK_SCRIPT}"; then
        printf "\n${GREEN}${BOLD}Setup complete. All services are healthy.${NC}\n"
    else
        warn "Some healthcheck.sh checks failed. Review output above."
        printf "\n${YELLOW}${BOLD}Setup finished with warnings. Review the healthcheck output.${NC}\n"
        exit 1
    fi
else
    warn "healthcheck.sh not found or not executable at ${HEALTHCHECK_SCRIPT}"
    info "Showing service status instead:"
    ${COMPOSE_CMD} ps
fi

printf "\n${BOLD}Next steps:${NC}\n"
printf "  1. Review .env and set production values\n"
printf "  2. Verify: ./scripts/healthcheck.sh\n"
printf "  3. Access services through the MCP tool layer\n"
printf "\n"
