#!/usr/bin/env bash
# ===========================================================================
# Conductor Data Pipeline — Health Check Script
# ===========================================================================
#
# Verifies all 6 containers are running and healthy, validates health
# endpoints, tests inter-container connectivity, and reports memory usage.
#
# Exit codes:
#   0 — all services healthy
#   1 — one or more services unhealthy or unreachable
#
# Usage:
#   ./scripts/healthcheck.sh
# ===========================================================================

set -euo pipefail

COMPOSE_FILE="docker-compose.data-pipeline.yml"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
COMPOSE_CMD="docker compose -f ${PROJECT_DIR}/${COMPOSE_FILE}"

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

FAILURES=0
TOTAL_CHECKS=0

pass() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    printf "${GREEN}[PASS]${NC} %s\n" "$1"
}

fail() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    FAILURES=$((FAILURES + 1))
    printf "${RED}[FAIL]${NC} %s\n" "$1"
}

warn() {
    printf "${YELLOW}[WARN]${NC} %s\n" "$1"
}

header() {
    printf "\n${BOLD}=== %s ===${NC}\n" "$1"
}

# ===========================================================================
# 1. Check all containers are running
# ===========================================================================
header "Container Status"

EXPECTED_SERVICES=(
    "airbyte-db"
    "airbyte-server"
    "airbyte-worker"
    "masking-engine"
    "unstructured-api"
    "presidio-analyzer"
)

for svc in "${EXPECTED_SERVICES[@]}"; do
    status=$(${COMPOSE_CMD} ps --format '{{.State}}' "${svc}" 2>/dev/null || echo "not_found")
    if [ "${status}" = "running" ]; then
        pass "${svc} is running"
    else
        fail "${svc} is NOT running (state: ${status})"
    fi
done

# ===========================================================================
# 2. Check Docker health status
# ===========================================================================
header "Docker Health Status"

for svc in "${EXPECTED_SERVICES[@]}"; do
    health=$(${COMPOSE_CMD} ps --format '{{.Health}}' "${svc}" 2>/dev/null || echo "unknown")
    # Normalize: containers without healthcheck show empty or "unknown"
    case "${health}" in
        healthy)
            pass "${svc} health: healthy"
            ;;
        ""|" ")
            # No healthcheck defined (e.g., airbyte-server, airbyte-worker)
            warn "${svc} health: no healthcheck defined"
            ;;
        *)
            fail "${svc} health: ${health}"
            ;;
    esac
done

# ===========================================================================
# 3. Verify health endpoints respond
# ===========================================================================
header "Health Endpoint Verification"

# Helper: exec curl inside a running container to test an endpoint
check_endpoint() {
    local from_svc="$1"
    local target_url="$2"
    local description="$3"

    result=$(${COMPOSE_CMD} exec -T "${from_svc}" curl -sf --max-time 10 "${target_url}" 2>/dev/null) && \
        pass "${description}" || \
        fail "${description}"
}

# masking-engine /health (from within its own container)
check_endpoint "masking-engine" "http://localhost:8080/health" \
    "masking-engine /health endpoint"

# presidio-analyzer /health (from within its own container)
check_endpoint "presidio-analyzer" "http://localhost:5002/health" \
    "presidio-analyzer /health endpoint"

# unstructured-api /healthcheck (from within its own container)
check_endpoint "unstructured-api" "http://localhost:8000/healthcheck" \
    "unstructured-api /healthcheck endpoint"

# airbyte-db pg_isready (from within its own container)
pg_result=$(${COMPOSE_CMD} exec -T airbyte-db pg_isready -U airbyte 2>/dev/null) && \
    pass "airbyte-db pg_isready" || \
    fail "airbyte-db pg_isready"

# ===========================================================================
# 4. Verify inter-container connectivity
# ===========================================================================
header "Inter-Container Connectivity"

# masking-engine can reach presidio-analyzer
check_endpoint "masking-engine" "http://presidio-analyzer:5002/health" \
    "masking-engine -> presidio-analyzer connectivity"

# masking-engine can reach unstructured-api
check_endpoint "masking-engine" "http://unstructured-api:8000/healthcheck" \
    "masking-engine -> unstructured-api connectivity"

# airbyte-server can reach airbyte-db (via pg_isready from server container)
ab_pg=$(${COMPOSE_CMD} exec -T airbyte-server bash -c \
    "apt-get -qq list --installed postgresql-client 2>/dev/null && pg_isready -h airbyte-db -U airbyte || curl -sf http://airbyte-db:5432 2>/dev/null || echo reachable" \
    2>/dev/null)
# Simplify: just test TCP reachability from airbyte-server to airbyte-db:5432
tcp_result=$(${COMPOSE_CMD} exec -T airbyte-server bash -c \
    "timeout 5 bash -c 'echo > /dev/tcp/airbyte-db/5432' 2>/dev/null && echo ok || echo fail" \
    2>/dev/null || echo "fail")
if [[ "${tcp_result}" == *"ok"* ]]; then
    pass "airbyte-server -> airbyte-db:5432 connectivity"
else
    fail "airbyte-server -> airbyte-db:5432 connectivity"
fi

# ===========================================================================
# 5. Memory usage report
# ===========================================================================
header "Memory Usage"

printf "\n"
docker stats --no-stream --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}" \
    $(${COMPOSE_CMD} ps -q 2>/dev/null | tr '\n' ' ') 2>/dev/null || \
    warn "Could not retrieve memory stats (are containers running?)"
printf "\n"

# Check total memory limit from compose config
total_limit_mb=0
for svc in "${EXPECTED_SERVICES[@]}"; do
    limit=$(${COMPOSE_CMD} config --format json 2>/dev/null | \
        python3 -c "
import sys, json
cfg = json.load(sys.stdin)
svc = cfg.get('services', {}).get('${svc}', {})
lim = svc.get('mem_limit', 0)
if isinstance(lim, str):
    if lim.endswith('g'):
        print(int(float(lim[:-1]) * 1024))
    elif lim.endswith('m'):
        print(int(lim[:-1]))
    else:
        print(0)
else:
    print(int(lim / 1048576) if lim > 0 else 0)
" 2>/dev/null || echo 0)
    total_limit_mb=$((total_limit_mb + limit))
done

if [ "${total_limit_mb}" -gt 0 ]; then
    printf "Total memory limit: ${BOLD}%d MB${NC} (%.1f GB)\n" \
        "${total_limit_mb}" "$(echo "scale=1; ${total_limit_mb}/1024" | bc)"
    if [ "${total_limit_mb}" -le 6144 ]; then
        pass "Total memory limit under 6GB (${total_limit_mb}MB)"
    else
        fail "Total memory limit exceeds 6GB (${total_limit_mb}MB)"
    fi
fi

# ===========================================================================
# Summary
# ===========================================================================
header "Summary"

if [ "${FAILURES}" -eq 0 ]; then
    printf "${GREEN}All %d checks passed.${NC}\n" "${TOTAL_CHECKS}"
    exit 0
else
    printf "${RED}%d of %d checks failed.${NC}\n" "${FAILURES}" "${TOTAL_CHECKS}"
    exit 1
fi
