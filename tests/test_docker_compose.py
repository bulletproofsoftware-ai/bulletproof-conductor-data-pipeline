"""
Tests for Docker Compose infrastructure (TODO-011).

Validates the compose file, Dockerfile, .env.example, and .gitignore
by parsing YAML/text — does NOT require a running Docker daemon.
"""

import os

import pytest
import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
COMPOSE_PATH = os.path.join(PROJECT_ROOT, "docker-compose.data-pipeline.yml")
ENV_EXAMPLE_PATH = os.path.join(PROJECT_ROOT, ".env.example")
GITIGNORE_PATH = os.path.join(PROJECT_ROOT, ".gitignore")
DOCKERFILE_PATH = os.path.join(PROJECT_ROOT, "masking-engine", "Dockerfile")
HEALTHCHECK_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "healthcheck.sh")
SETUP_SCRIPT = os.path.join(PROJECT_ROOT, "scripts", "setup.sh")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def compose_data() -> dict:
    """Load and parse the Docker Compose YAML."""
    with open(COMPOSE_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def services(compose_data) -> dict:
    """Extract the services block from the compose file."""
    return compose_data.get("services", {})


@pytest.fixture(scope="module")
def env_example_content() -> str:
    """Load .env.example as raw text."""
    with open(ENV_EXAMPLE_PATH) as f:
        return f.read()


@pytest.fixture(scope="module")
def gitignore_content() -> str:
    """Load .gitignore as raw text."""
    with open(GITIGNORE_PATH) as f:
        return f.read()


@pytest.fixture(scope="module")
def dockerfile_content() -> str:
    """Load the masking-engine Dockerfile as raw text."""
    with open(DOCKERFILE_PATH) as f:
        return f.read()


# ===================================================================
# 1. COMPOSE FILE — SERVICE DEFINITIONS
# ===================================================================


EXPECTED_SERVICES = [
    "airbyte-db",
    "airbyte-server",
    "airbyte-worker",
    "masking-engine",
    "unstructured-api",
    "presidio-analyzer",
]


class TestServiceDefinitions:
    """All 6 required services must be defined."""

    def test_compose_file_exists(self):
        assert os.path.isfile(COMPOSE_PATH), "docker-compose.data-pipeline.yml not found"

    def test_all_six_services_defined(self, services):
        for svc in EXPECTED_SERVICES:
            assert svc in services, f"Service '{svc}' not defined in compose file"

    def test_exactly_six_services(self, services):
        assert len(services) == 6, (
            f"Expected 6 services, found {len(services)}: {list(services.keys())}"
        )

    def test_airbyte_db_image(self, services):
        assert services["airbyte-db"]["image"] == "postgres:15"

    def test_airbyte_server_image(self, services):
        assert services["airbyte-server"]["image"] == "airbyte/server:latest"

    def test_airbyte_worker_image(self, services):
        assert services["airbyte-worker"]["image"] == "airbyte/worker:latest"

    def test_masking_engine_build_context(self, services):
        build = services["masking-engine"].get("build")
        assert build is not None, "masking-engine must have a 'build' directive"
        # Can be a string or dict with 'context'
        if isinstance(build, dict):
            assert "context" in build
        else:
            assert build == "./masking-engine"

    def test_unstructured_api_image(self, services):
        image = services["unstructured-api"]["image"]
        assert "unstructured" in image.lower(), (
            f"unstructured-api image should reference unstructured: {image}"
        )

    def test_presidio_analyzer_image(self, services):
        image = services["presidio-analyzer"]["image"]
        assert "presidio" in image.lower(), (
            f"presidio-analyzer image should reference presidio: {image}"
        )


# ===================================================================
# 2. MEMORY LIMITS
# ===================================================================


def _parse_mem_limit_mb(value) -> int:
    """Parse a Docker mem_limit value into megabytes."""
    if isinstance(value, (int, float)):
        # Raw bytes
        return int(value / (1024 * 1024))
    s = str(value).strip().lower()
    if s.endswith("g"):
        return int(float(s[:-1]) * 1024)
    if s.endswith("m"):
        return int(float(s[:-1]))
    if s.endswith("k"):
        return int(float(s[:-1]) / 1024)
    return int(s)


class TestMemoryLimits:
    """Memory limits must be defined and sum to <= 6GB."""

    def test_all_services_have_mem_limit(self, services):
        for svc_name in EXPECTED_SERVICES:
            svc = services[svc_name]
            assert "mem_limit" in svc, (
                f"Service '{svc_name}' missing mem_limit"
            )

    def test_individual_mem_limits(self, services):
        """Verify individual memory limits match the spec."""
        expected_mb = {
            "airbyte-db": 256,
            "airbyte-server": 2048,
            "airbyte-worker": 1024,
            "masking-engine": 512,
            "unstructured-api": 1024,
            "presidio-analyzer": 512,
        }
        for svc_name, expected in expected_mb.items():
            actual = _parse_mem_limit_mb(services[svc_name]["mem_limit"])
            assert actual == expected, (
                f"{svc_name}: expected {expected}MB, got {actual}MB"
            )

    def test_total_memory_under_6gb(self, services):
        total_mb = sum(
            _parse_mem_limit_mb(services[svc]["mem_limit"])
            for svc in EXPECTED_SERVICES
        )
        assert total_mb <= 6144, (
            f"Total memory {total_mb}MB exceeds 6GB (6144MB) limit"
        )

    def test_total_memory_approximately_5_3gb(self, services):
        """Spec targets ~5.3GB (5376MB)."""
        total_mb = sum(
            _parse_mem_limit_mb(services[svc]["mem_limit"])
            for svc in EXPECTED_SERVICES
        )
        assert total_mb == 5376, (
            f"Total memory {total_mb}MB != expected 5376MB (~5.3GB)"
        )


# ===================================================================
# 3. HEALTH CHECKS
# ===================================================================


class TestHealthChecks:
    """Health checks must be defined for key services."""

    SERVICES_WITH_HEALTHCHECK = [
        "airbyte-db",
        "masking-engine",
        "unstructured-api",
        "presidio-analyzer",
    ]

    def test_healthchecks_defined(self, services):
        for svc_name in self.SERVICES_WITH_HEALTHCHECK:
            svc = services[svc_name]
            assert "healthcheck" in svc, (
                f"Service '{svc_name}' missing healthcheck"
            )
            hc = svc["healthcheck"]
            assert "test" in hc, (
                f"Service '{svc_name}' healthcheck missing 'test' command"
            )

    def test_airbyte_db_pg_isready(self, services):
        hc_test = services["airbyte-db"]["healthcheck"]["test"]
        test_str = " ".join(hc_test) if isinstance(hc_test, list) else str(hc_test)
        assert "pg_isready" in test_str, (
            "airbyte-db healthcheck should use pg_isready"
        )

    @pytest.mark.parametrize(
        "service_name, expected_port",
        [
            ("masking-engine", "8080"),
            ("unstructured-api", "8000"),
            ("presidio-analyzer", "5002"),
        ],
        ids=["masking-engine", "unstructured-api", "presidio-analyzer"],
    )
    def test_service_curl_health(self, services, service_name, expected_port):
        hc_test = services[service_name]["healthcheck"]["test"]
        test_str = " ".join(hc_test) if isinstance(hc_test, list) else str(hc_test)
        assert "curl" in test_str and expected_port in test_str, (
            f"{service_name} healthcheck should curl localhost:{expected_port}"
        )

    @pytest.mark.parametrize("field", ["interval", "timeout", "retries"])
    def test_healthcheck_has_required_field(self, services, field):
        for svc_name in self.SERVICES_WITH_HEALTHCHECK:
            hc = services[svc_name]["healthcheck"]
            assert field in hc, (
                f"{svc_name} healthcheck should have {field}"
            )


# ===================================================================
# 4. NO EXTERNAL PORT MAPPINGS
# ===================================================================


class TestNoExternalPorts:
    """No service should expose ports to the host (only 'expose' for internal)."""

    def test_no_ports_directive(self, services):
        """The 'ports' key binds to the host. Must not be present."""
        for svc_name, svc in services.items():
            assert "ports" not in svc, (
                f"Service '{svc_name}' has 'ports' (host binding). "
                "Use 'expose' for internal-only communication."
            )

    def test_expose_is_internal_only(self, services):
        """'expose' only makes ports available to linked containers, not the host."""
        for svc_name, svc in services.items():
            if "expose" in svc:
                for port in svc["expose"]:
                    # 'expose' values should be simple port numbers (str or int)
                    port_str = str(port)
                    assert ":" not in port_str, (
                        f"Service '{svc_name}' expose entry '{port}' looks like "
                        "a host:container mapping. Use plain port numbers."
                    )


# ===================================================================
# 5. ENVIRONMENT VARIABLES
# ===================================================================


class TestEnvironmentVariables:
    """Required env vars must have placeholders in compose and .env.example."""

    def test_airbyte_db_postgres_env(self, services):
        env = services["airbyte-db"].get("environment", {})
        # Environment can be a dict or list of KEY=VALUE strings
        env_str = str(env)
        assert "POSTGRES_USER" in env_str, "airbyte-db missing POSTGRES_USER"
        assert "POSTGRES_PASSWORD" in env_str, "airbyte-db missing POSTGRES_PASSWORD"
        assert "POSTGRES_DB" in env_str, "airbyte-db missing POSTGRES_DB"

    def test_airbyte_server_database_url(self, services):
        env = services["airbyte-server"].get("environment", {})
        env_str = str(env)
        assert "DATABASE_URL" in env_str, "airbyte-server missing DATABASE_URL"
        assert "AIRBYTE_DB_PASSWORD" in env_str, (
            "airbyte-server DATABASE_URL should reference AIRBYTE_DB_PASSWORD"
        )

    def test_masking_engine_vault_env(self, services):
        env = services["masking-engine"].get("environment", {})
        env_str = str(env)
        assert "VAULT_ADDR" in env_str, "masking-engine missing VAULT_ADDR"
        assert "VAULT_TOKEN" in env_str, "masking-engine missing VAULT_TOKEN"

    def test_masking_engine_seed_env(self, services):
        env = services["masking-engine"].get("environment", {})
        env_str = str(env)
        assert "MASKING_MASTER_SEED" in env_str, (
            "masking-engine missing MASKING_MASTER_SEED"
        )

    def test_env_example_has_all_required_vars(self, env_example_content):
        required_vars = [
            "AIRBYTE_DB_PASSWORD",
            "VAULT_ADDR",
            "VAULT_TOKEN",
            "MASKING_MASTER_SEED",
            "PIPELINE_MAX_CONCURRENT",
            "APPROVAL_TIMEOUT_HOURS",
            "OTLP_ENDPOINT",
            "NOTIFICATION_WEBHOOK_URL",
        ]
        for var in required_vars:
            assert var in env_example_content, (
                f".env.example missing required variable: {var}"
            )

    def test_env_example_has_warning(self, env_example_content):
        content_lower = env_example_content.lower()
        assert "never commit" in content_lower or "never" in content_lower, (
            ".env.example should warn against committing .env to git"
        )

    def test_env_example_has_changeme_placeholders(self, env_example_content):
        assert "changeme" in env_example_content, (
            ".env.example should use 'changeme' placeholders for secrets"
        )


# ===================================================================
# 6. VOLUMES
# ===================================================================


class TestVolumes:
    """Required volumes must be defined."""

    def test_volumes_section_exists(self, compose_data):
        assert "volumes" in compose_data, "Compose file missing 'volumes' section"

    def test_airbyte_db_data_volume(self, compose_data):
        volumes = compose_data["volumes"]
        assert "airbyte-db-data" in volumes, "Missing 'airbyte-db-data' volume"

    def test_pipeline_artifacts_volume(self, compose_data):
        volumes = compose_data["volumes"]
        assert "pipeline-artifacts" in volumes, "Missing 'pipeline-artifacts' volume"

    def test_airbyte_db_mounts_data_volume(self, services):
        svc = services["airbyte-db"]
        volumes = svc.get("volumes", [])
        vol_str = str(volumes)
        assert "airbyte-db-data" in vol_str, (
            "airbyte-db should mount airbyte-db-data volume"
        )

    def test_masking_engine_mounts_artifacts_volume(self, services):
        svc = services["masking-engine"]
        volumes = svc.get("volumes", [])
        vol_str = str(volumes)
        assert "pipeline-artifacts" in vol_str, (
            "masking-engine should mount pipeline-artifacts volume"
        )


# ===================================================================
# 7. NETWORK
# ===================================================================


class TestNetwork:
    """The conductor-data-pipeline network must be configured."""

    def test_network_defined(self, compose_data):
        networks = compose_data.get("networks", {})
        # Check either a named network or default with name
        found = False
        for net_name, net_config in networks.items():
            if net_config and isinstance(net_config, dict):
                if net_config.get("name") == "conductor-data-pipeline":
                    found = True
                    break
            if net_name == "conductor-data-pipeline":
                found = True
                break
        assert found, (
            "Network 'conductor-data-pipeline' not defined in compose file"
        )


# ===================================================================
# 8. DEPENDENCY CHAIN
# ===================================================================


class TestDependencyChain:
    """Service dependency ordering must be correct."""

    def test_airbyte_server_depends_on_airbyte_db(self, services):
        deps = services["airbyte-server"].get("depends_on", {})
        assert "airbyte-db" in deps, (
            "airbyte-server must depend on airbyte-db"
        )

    def test_airbyte_server_waits_for_db_healthy(self, services):
        deps = services["airbyte-server"]["depends_on"]
        db_dep = deps["airbyte-db"]
        if isinstance(db_dep, dict):
            assert db_dep.get("condition") == "service_healthy", (
                "airbyte-server should wait for airbyte-db to be healthy"
            )

    def test_airbyte_worker_depends_on_airbyte_server(self, services):
        deps = services["airbyte-worker"].get("depends_on", {})
        assert "airbyte-server" in deps, (
            "airbyte-worker must depend on airbyte-server"
        )

    def test_airbyte_worker_waits_for_server_started(self, services):
        deps = services["airbyte-worker"]["depends_on"]
        server_dep = deps["airbyte-server"]
        if isinstance(server_dep, dict):
            assert server_dep.get("condition") == "service_started", (
                "airbyte-worker should wait for airbyte-server to start"
            )

    def test_masking_engine_depends_on_presidio(self, services):
        deps = services["masking-engine"].get("depends_on", {})
        assert "presidio-analyzer" in deps, (
            "masking-engine must depend on presidio-analyzer"
        )

    def test_masking_engine_waits_for_presidio_healthy(self, services):
        deps = services["masking-engine"]["depends_on"]
        presidio_dep = deps["presidio-analyzer"]
        if isinstance(presidio_dep, dict):
            assert presidio_dep.get("condition") == "service_healthy", (
                "masking-engine should wait for presidio-analyzer to be healthy"
            )

    def test_full_dependency_chain_airbyte(self, services):
        """Verify: airbyte-db -> airbyte-server -> airbyte-worker."""
        # airbyte-db has no depends_on (root of chain)
        assert "depends_on" not in services["airbyte-db"] or \
            not services["airbyte-db"].get("depends_on"), (
            "airbyte-db should be the root of the Airbyte dependency chain"
        )
        # airbyte-server depends on airbyte-db
        assert "airbyte-db" in services["airbyte-server"]["depends_on"]
        # airbyte-worker depends on airbyte-server
        assert "airbyte-server" in services["airbyte-worker"]["depends_on"]

    def test_full_dependency_chain_masking(self, services):
        """Verify: presidio-analyzer -> masking-engine."""
        # presidio has no depends_on (root)
        assert "depends_on" not in services["presidio-analyzer"] or \
            not services["presidio-analyzer"].get("depends_on"), (
            "presidio-analyzer should have no dependencies"
        )
        # masking-engine depends on presidio
        assert "presidio-analyzer" in services["masking-engine"]["depends_on"]


# ===================================================================
# 9. DOCKERFILE VALIDATION
# ===================================================================


class TestDockerfile:
    """The masking-engine Dockerfile must exist and be structurally valid."""

    def test_dockerfile_exists(self):
        assert os.path.isfile(DOCKERFILE_PATH), (
            "masking-engine/Dockerfile not found"
        )

    def test_from_python_311_slim(self, dockerfile_content):
        assert "FROM python:3.11-slim" in dockerfile_content, (
            "Dockerfile should use python:3.11-slim base image"
        )

    def test_workdir_app(self, dockerfile_content):
        assert "WORKDIR /app" in dockerfile_content

    def test_copy_requirements(self, dockerfile_content):
        assert "COPY requirements.txt" in dockerfile_content

    def test_pip_install(self, dockerfile_content):
        assert "pip install" in dockerfile_content
        assert "--no-cache-dir" in dockerfile_content

    def test_copy_app(self, dockerfile_content):
        assert "COPY app/" in dockerfile_content

    def test_expose_8080(self, dockerfile_content):
        assert "EXPOSE 8080" in dockerfile_content

    def test_healthcheck_defined(self, dockerfile_content):
        assert "HEALTHCHECK" in dockerfile_content
        assert "curl" in dockerfile_content
        assert "8080/health" in dockerfile_content

    def test_cmd_uvicorn(self, dockerfile_content):
        assert "uvicorn" in dockerfile_content
        assert "app.main:app" in dockerfile_content
        assert "8080" in dockerfile_content

    def test_user_directive_present(self, dockerfile_content):
        """CIS-DI-0001: Dockerfile must have a USER directive to avoid running as root."""
        assert "USER " in dockerfile_content, (
            "Dockerfile should have a USER directive to run as non-root"
        )

    def test_no_run_as_root_warning(self, dockerfile_content):
        """Dockerfile installs curl — verify no broken RUN instructions."""
        # Every RUN line should complete (no trailing backslash without continuation)
        lines = dockerfile_content.splitlines()
        in_run = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("RUN "):
                in_run = True
            if in_run and not stripped.endswith("\\"):
                in_run = False
        assert not in_run, "Dockerfile has an incomplete RUN instruction"


# ===================================================================
# 10. GITIGNORE
# ===================================================================


class TestGitignore:
    """The .gitignore must exclude secrets."""

    def test_gitignore_exists(self):
        assert os.path.isfile(GITIGNORE_PATH), ".gitignore not found"

    def test_env_excluded(self, gitignore_content):
        # Check .env is in gitignore (not .env.example)
        lines = [line.strip() for line in gitignore_content.splitlines()]
        assert ".env" in lines, ".gitignore should exclude .env"

    def test_env_example_not_excluded(self, gitignore_content):
        assert "!.env.example" in gitignore_content, (
            ".gitignore should NOT exclude .env.example (use ! prefix)"
        )

    def test_secret_files_excluded(self, gitignore_content):
        assert "*.secret" in gitignore_content, (
            ".gitignore should exclude *.secret files"
        )

    def test_run_secrets_excluded(self, gitignore_content):
        assert "/run/secrets/" in gitignore_content, (
            ".gitignore should exclude /run/secrets/"
        )


# ===================================================================
# 11. SCRIPTS
# ===================================================================


class TestScripts:
    """Health check and setup scripts must exist and be executable."""

    def test_healthcheck_script_exists(self):
        assert os.path.isfile(HEALTHCHECK_SCRIPT), (
            "scripts/healthcheck.sh not found"
        )

    def test_setup_script_exists(self):
        assert os.path.isfile(SETUP_SCRIPT), (
            "scripts/setup.sh not found"
        )

    def test_healthcheck_script_executable(self):
        assert os.access(HEALTHCHECK_SCRIPT, os.X_OK), (
            "scripts/healthcheck.sh is not executable"
        )

    def test_setup_script_executable(self):
        assert os.access(SETUP_SCRIPT, os.X_OK), (
            "scripts/setup.sh is not executable"
        )

    def test_healthcheck_has_shebang(self):
        with open(HEALTHCHECK_SCRIPT) as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!/"), (
            "scripts/healthcheck.sh missing shebang line"
        )

    def test_setup_has_shebang(self):
        with open(SETUP_SCRIPT) as f:
            first_line = f.readline().strip()
        assert first_line.startswith("#!/"), (
            "scripts/setup.sh missing shebang line"
        )

    def test_healthcheck_has_set_euo_pipefail(self):
        with open(HEALTHCHECK_SCRIPT) as f:
            content = f.read()
        assert "set -euo pipefail" in content, (
            "scripts/healthcheck.sh should use 'set -euo pipefail'"
        )

    def test_setup_has_set_euo_pipefail(self):
        with open(SETUP_SCRIPT) as f:
            content = f.read()
        assert "set -euo pipefail" in content, (
            "scripts/setup.sh should use 'set -euo pipefail'"
        )

    def test_healthcheck_checks_all_services(self):
        with open(HEALTHCHECK_SCRIPT) as f:
            content = f.read()
        for svc in EXPECTED_SERVICES:
            assert svc in content, (
                f"scripts/healthcheck.sh should check service '{svc}'"
            )

    def test_setup_references_compose_file(self):
        with open(SETUP_SCRIPT) as f:
            content = f.read()
        assert "docker-compose.data-pipeline.yml" in content, (
            "scripts/setup.sh should reference the compose file"
        )

    def test_setup_runs_healthcheck(self):
        with open(SETUP_SCRIPT) as f:
            content = f.read()
        assert "healthcheck" in content.lower(), (
            "scripts/setup.sh should run the healthcheck script"
        )
