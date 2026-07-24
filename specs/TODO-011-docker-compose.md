# TODO-011: Docker Compose & Infrastructure

## Requirements Covered
- REQ-DP-027: All components Dockerized with docker-compose
- REQ-DP-028: Total additional RAM footprint under 6GB
- REQ-DP-001: Support extraction from Oracle, MySQL, PostgreSQL, SQL Server, Snowflake via Airbyte OSS
- REQ-DP-002: Support document parsing (PDF, docx, 65+ types) via Unstructured.io
- REQ-DP-003: Support HTTP/API extraction (REST, GraphQL)

## Dependencies
- TODO-002 (Masking engine core — Dockerfile must exist)
- TODO-003 (NER integration — Presidio container required)

## Inputs
- SPEC.md Section 9 — Docker deployment specification
- Masking engine Dockerfile (from TODO-002)
- Existing conductor Docker network configuration
- Vault/Docker secrets configuration

## Outputs
- `docker-compose.data-pipeline.yml` — Complete compose file for all 6 containers
- `.env.example` — Environment variable template (no secrets, just placeholders)
- `scripts/healthcheck.sh` — Health check verification script
- `scripts/setup.sh` — One-time setup (create volumes, initialize Airbyte)
- Network configuration connecting to existing conductor services

## Implementation Scope

### Files to Create

**`docker-compose.data-pipeline.yml`** — Main Compose File
- 6 services per spec Section 9.1:
  1. `airbyte-db` (postgres:15, 256MB limit)
     - Health check: `pg_isready -U airbyte`
     - Volume: `airbyte-db-data` for persistent cursor state
     - Environment: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
  2. `airbyte-server` (airbyte/server:latest, 2GB limit)
     - Depends on: `airbyte-db` (healthy)
     - Environment: DATABASE_URL with placeholder
     - Port: internal only (no external exposure)
  3. `airbyte-worker` (airbyte/worker:latest, 1GB limit)
     - Depends on: `airbyte-server` (started)
     - Docker-in-Docker or volume mounts for connector execution
  4. `masking-engine` (build from ./masking-engine, 512MB limit)
     - Health check: `curl -f http://localhost:8080/health`
     - Depends on: `presidio-analyzer` (healthy)
     - Environment: VAULT_ADDR, VAULT_TOKEN (or Docker secrets mount)
     - Volume mount: `pipeline-artifacts` for YAML definitions
     - TLS configuration for `/approve` endpoint
  5. `unstructured-api` (unstructured-io/unstructured-api:latest, 1GB limit)
     - Health check: `curl -f http://localhost:8000/healthcheck`
     - Port: internal only
  6. `presidio-analyzer` (microsoft/presidio-analyzer:latest, 512MB limit)
     - Health check: `curl -f http://localhost:5002/health`
     - Port: internal only
- Shared network: `conductor-data-pipeline`
- Total RAM: 256 + 2048 + 1024 + 512 + 1024 + 512 = 5376MB (~5.3GB, under 6GB target)
- Volumes:
  - `airbyte-db-data` — Airbyte state persistence (cursor values)
  - `pipeline-artifacts` — shared YAML definitions (pipelines, contracts, policies)

**`.env.example`** — Environment Variable Template
- `AIRBYTE_DB_PASSWORD=changeme`
- `VAULT_ADDR=http://vault:8200`
- `VAULT_TOKEN=changeme`
- `MASKING_MASTER_SEED=changeme`
- `PIPELINE_MAX_CONCURRENT=3`
- `APPROVAL_TIMEOUT_HOURS=24`
- `OTLP_ENDPOINT=http://otel-collector:4317` (optional)
- `NOTIFICATION_WEBHOOK_URL=` (optional, for approval notifications)
- Comments explaining each variable
- WARNING: "Copy to .env and fill with real values. NEVER commit .env to git."

**`.gitignore`** — Ensure secrets excluded
- `.env`
- `*.secret`
- `/run/secrets/`

**`scripts/healthcheck.sh`** — Health Verification Script
- Check each container is running and healthy
- Verify all health check endpoints respond
- Verify inter-container connectivity (masking-engine can reach presidio-analyzer)
- Verify Airbyte API is responsive
- Report total memory usage via `docker stats --no-stream`
- Exit 0 if all healthy, exit 1 with details on failures

**`scripts/setup.sh`** — First-Time Setup Script
- Create Docker volumes
- Pull all images
- Initialize airbyte-db with schema
- Verify Vault connectivity (or Docker secrets directory)
- Run `docker compose up -d` and wait for all health checks
- Run `scripts/healthcheck.sh` to verify

**`masking-engine/Dockerfile`** — Masking Engine Container (if not in TODO-002)
- FROM python:3.11-slim
- WORKDIR /app
- COPY requirements.txt . && pip install --no-cache-dir -r requirements.txt
- COPY app/ ./app/
- EXPOSE 8080
- HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8080/health || exit 1
- CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

### Connector Support Notes

**Airbyte OSS Connectors** (REQ-DP-001):
- Oracle, MySQL, PostgreSQL, SQL Server, Snowflake supported via Airbyte connector catalog
- Connectors run as ephemeral Docker containers spawned by airbyte-worker
- airbyte-worker needs Docker socket access (or Docker-in-Docker)
- 400+ source connectors available, no custom JDBC code needed

**Unstructured.io** (REQ-DP-002):
- Handles PDF, DOCX, PPTX, HTML, TXT, CSV, 65+ file types
- API endpoint: `POST /general/v0/general` with file upload
- Returns structured JSON with element types (Title, NarrativeText, Table, etc.)

**HTTP/API Connector** (REQ-DP-003):
- Lightweight Python connector (custom, not Airbyte)
- Supports GET/POST with configurable auth headers (Bearer, Basic, API Key)
- JSON/XML response parsing
- Pagination support (offset, cursor, next-link)
- Rate limiting (configurable requests-per-second)
- Note: this may be implemented within the MCP tool layer (data_connect/data_extract) rather than as a separate container

### Tests to Write

**`tests/test_docker_compose.py`** (or shell script equivalent)
- `docker compose config` validates YAML syntax
- All 6 services defined
- Memory limits sum to under 6GB
- Health checks defined for all services
- No ports exposed externally (only internal network)
- Required environment variables have placeholders

**`tests/test_healthcheck.sh`**
- Health check script runs without error when all containers healthy
- Health check script detects unhealthy container

## Acceptance Criteria
1. `docker compose -f docker-compose.data-pipeline.yml up -d` brings up all 6 containers
2. All health checks pass within 120 seconds of startup
3. Total memory usage under 6GB (verify via `docker stats`)
4. No ports exposed externally — MCP tool layer is the only interface
5. Inter-container communication works (masking-engine reaches presidio-analyzer, etc.)
6. Airbyte API responsive and able to create source connections
7. Unstructured.io API responsive and able to parse a test PDF
8. Presidio analyzer API responsive and able to detect PII in sample text
9. Pipeline artifacts volume shared between masking-engine and tool layer
10. `.env.example` documents all required environment variables
11. `scripts/healthcheck.sh` exits 0 when all containers healthy
12. `scripts/setup.sh` performs clean first-time deployment

## Estimated Complexity
M (Medium — 100-500 lines; compose file + scripts + Dockerfile, but mostly configuration)
