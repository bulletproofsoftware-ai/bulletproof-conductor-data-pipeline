"""
Tests for the Credential Resolver.

Validates:
- Docker secrets read
- Environment variable fallback
- Missing credential error
- Access logging
- Vault tier (mocked)
"""

import pytest

from tools.credential_resolver import (
    CredentialResolver,
    CredentialResolverError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def docker_secrets_dir(tmp_path):
    """Create a temporary Docker secrets directory with test secrets."""
    # Create secret files
    (tmp_path / "db_password").write_text("secret_from_docker")
    (tmp_path / "api_key").write_text("key_from_docker")
    return str(tmp_path)


@pytest.fixture
def resolver_with_docker(docker_secrets_dir):
    """Resolver configured to read from temp Docker secrets dir."""
    return CredentialResolver(docker_secrets_dir=docker_secrets_dir)


@pytest.fixture
def resolver_no_vault():
    """Resolver with no Vault client and no Docker secrets."""
    return CredentialResolver(docker_secrets_dir="/nonexistent")


# ---------------------------------------------------------------------------
# Docker Secrets Tests
# ---------------------------------------------------------------------------

class TestDockerSecrets:
    """Docker secrets should be read from the file system."""

    def test_reads_docker_secret_file(self, resolver_with_docker):
        value = resolver_with_docker.resolve("DB_PASSWORD")
        assert value == "secret_from_docker"

    def test_docker_secret_case_lowered(self, resolver_with_docker):
        """Docker secret filenames are lowercased."""
        value = resolver_with_docker.resolve("API_KEY")
        assert value == "key_from_docker"

    def test_docker_secret_logged(self, resolver_with_docker):
        resolver_with_docker.resolve("DB_PASSWORD")
        log = resolver_with_docker.access_log
        docker_entries = [e for e in log if e.source == "docker_secret" and e.resolved]
        assert len(docker_entries) == 1
        assert docker_entries[0].variable == "DB_PASSWORD"


# ---------------------------------------------------------------------------
# Environment Variable Fallback Tests
# ---------------------------------------------------------------------------

class TestEnvVarFallback:
    """If Docker secrets and Vault both fail, env vars should be used."""

    def test_falls_back_to_env_var(self, resolver_no_vault, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "from_env")
        value = resolver_no_vault.resolve("MY_SECRET")
        assert value == "from_env"

    def test_env_var_logged(self, resolver_no_vault, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "from_env")
        resolver_no_vault.resolve("MY_SECRET")
        log = resolver_no_vault.access_log
        env_entries = [e for e in log if e.source == "env_var" and e.resolved]
        assert len(env_entries) == 1
        assert env_entries[0].variable == "MY_SECRET"


# ---------------------------------------------------------------------------
# Missing Credential Tests
# ---------------------------------------------------------------------------

class TestMissingCredential:
    """Missing credentials must raise CredentialResolverError."""

    def test_missing_credential_raises(self, resolver_no_vault):
        with pytest.raises(CredentialResolverError) as exc_info:
            resolver_no_vault.resolve("NONEXISTENT_VAR")
        assert "NONEXISTENT_VAR" in str(exc_info.value)
        assert exc_info.value.variable == "NONEXISTENT_VAR"

    def test_all_tiers_logged_on_failure(self, resolver_no_vault):
        with pytest.raises(CredentialResolverError):
            resolver_no_vault.resolve("MISSING")

        log = resolver_no_vault.access_log
        sources = [e.source for e in log]
        # Should have attempted vault, docker_secret, env_var
        assert "vault" in sources
        assert "docker_secret" in sources
        assert "env_var" in sources
        # None should have resolved
        assert all(not e.resolved for e in log)


# ---------------------------------------------------------------------------
# Access Logging Tests
# ---------------------------------------------------------------------------

class TestAccessLogging:
    """All credential access attempts must be logged."""

    def test_successful_access_logged(self, resolver_no_vault, monkeypatch):
        monkeypatch.setenv("TEST_VAR", "value")
        resolver_no_vault.resolve("TEST_VAR")

        log = resolver_no_vault.access_log
        assert len(log) > 0
        # At least one entry should show resolved=True
        resolved = [e for e in log if e.resolved]
        assert len(resolved) >= 1

    def test_failed_access_logged(self, resolver_no_vault):
        with pytest.raises(CredentialResolverError):
            resolver_no_vault.resolve("NOPE")

        log = resolver_no_vault.access_log
        assert len(log) >= 3  # vault, docker, env
        assert all(not e.resolved for e in log)

    def test_log_has_timestamps(self, resolver_no_vault, monkeypatch):
        monkeypatch.setenv("TIMED", "val")
        resolver_no_vault.resolve("TIMED")

        for entry in resolver_no_vault.access_log:
            assert entry.timestamp > 0


# ---------------------------------------------------------------------------
# Placeholder Resolution Tests
# ---------------------------------------------------------------------------

class TestPlaceholderResolution:
    """resolve_placeholders should recursively resolve ${VAR} in dicts."""

    @pytest.mark.parametrize(
        "env_vars, input_config, expected",
        [
            (
                {"HOST": "db.example.com"},
                {"host": "${HOST}"},
                {"host": "db.example.com"},
            ),
            (
                {"USER": "admin"},
                {"url": "http://${USER}@host"},
                {"url": "http://admin@host"},
            ),
            (
                {},
                {"key": "plain_value"},
                {"key": "plain_value"},
            ),
        ],
        ids=["simple-placeholder", "mixed-literal-and-placeholder", "no-placeholder"],
    )
    def test_resolve_placeholders(
        self, resolver_no_vault, monkeypatch, env_vars, input_config, expected
    ):
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        result = resolver_no_vault.resolve_placeholders(input_config)
        assert result == expected

    def test_resolves_nested_placeholders(self, resolver_no_vault, monkeypatch):
        monkeypatch.setenv("DB_HOST", "db.local")
        monkeypatch.setenv("DB_PORT", "5432")
        config = {
            "connection": {
                "host": "${DB_HOST}",
                "port": "${DB_PORT}",
            }
        }
        result = resolver_no_vault.resolve_placeholders(config)
        assert result["connection"]["host"] == "db.local"
        assert result["connection"]["port"] == "5432"

    def test_unresolvable_placeholder_raises(self, resolver_no_vault):
        with pytest.raises(CredentialResolverError):
            resolver_no_vault.resolve_placeholders({"host": "${MISSING_VAR}"})


# ---------------------------------------------------------------------------
# Vault Tier Tests (Mocked)
# ---------------------------------------------------------------------------

class TestVaultTier:
    """Vault resolution should be attempted first."""

    def test_vault_success_preempts_other_tiers(self, monkeypatch):
        """If Vault resolves, Docker secrets and env vars are not tried."""
        class MockVault:
            class secrets:
                class kv:
                    class v2:
                        @staticmethod
                        def read_secret_version(path, mount_point):
                            return {"data": {"data": {"value": "from_vault"}}}

        resolver = CredentialResolver(
            vault_client=MockVault(),
            docker_secrets_dir="/nonexistent",
        )
        value = resolver.resolve("SOME_SECRET")
        assert value == "from_vault"

        # Only vault entry should be in log
        resolved = [e for e in resolver.access_log if e.resolved]
        assert len(resolved) == 1
        assert resolved[0].source == "vault"

    def test_vault_failure_falls_through(self, monkeypatch):
        """If Vault fails, should fall through to Docker secrets / env vars."""
        class MockVault:
            class secrets:
                class kv:
                    class v2:
                        @staticmethod
                        def read_secret_version(path, mount_point):
                            raise Exception("Vault sealed")

        monkeypatch.setenv("FALLBACK_VAR", "env_value")
        resolver = CredentialResolver(
            vault_client=MockVault(),
            docker_secrets_dir="/nonexistent",
        )
        value = resolver.resolve("FALLBACK_VAR")
        assert value == "env_value"
