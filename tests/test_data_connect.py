"""
Tests for the data_connect MCP tool.

Validates:
- Success returns schema catalog
- Invalid credentials return error
- Placeholders resolved via credential resolver
"""

import pytest

from tools.data_connect import execute
from tools.credential_resolver import CredentialResolver


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def resolver(monkeypatch):
    """Credential resolver with env vars set."""
    monkeypatch.setenv("PROD_DB_HOST", "prod.db.example.com")
    monkeypatch.setenv("PROD_DB_PORT", "5432")
    return CredentialResolver(docker_secrets_dir="/nonexistent")


# ---------------------------------------------------------------------------
# Success Tests
# ---------------------------------------------------------------------------

class TestConnectSuccess:
    """Successful connections should return schema catalog."""

    def test_postgres_returns_catalog(self):
        result = execute({
            "connector": "airbyte/source-postgres",
            "connection": {"host": "localhost", "port": 5432},
        })
        assert result["status"] == "success"
        assert result["data"]["connected"] is True
        catalog = result["data"]["catalog"]
        assert "streams" in catalog
        assert len(catalog["streams"]) == 2
        stream_names = [s["name"] for s in catalog["streams"]]
        assert "customers" in stream_names
        assert "orders" in stream_names

    def test_mysql_returns_catalog(self):
        result = execute({
            "connector": "airbyte/source-mysql",
            "connection": {"host": "localhost"},
        })
        assert result["status"] == "success"
        stream_names = [s["name"] for s in result["data"]["catalog"]["streams"]]
        assert "users" in stream_names

    def test_unknown_connector_returns_default_catalog(self):
        result = execute({
            "connector": "airbyte/source-oracle",
            "connection": {"host": "localhost"},
        })
        assert result["status"] == "success"
        assert result["data"]["connected"] is True
        # Gets a generic default catalog
        assert "streams" in result["data"]["catalog"]

    def test_catalog_has_column_details(self):
        result = execute({
            "connector": "airbyte/source-postgres",
            "connection": {"host": "localhost"},
        })
        customers = next(
            s for s in result["data"]["catalog"]["streams"]
            if s["name"] == "customers"
        )
        col_names = [c["name"] for c in customers["columns"]]
        assert "id" in col_names
        assert "email" in col_names
        assert customers["primary_key"] == ["id"]

    def test_metadata_includes_elapsed(self):
        result = execute({
            "connector": "airbyte/source-postgres",
            "connection": {"host": "localhost"},
        })
        assert "elapsed_ms" in result["metadata"]
        assert result["metadata"]["elapsed_ms"] >= 0


# ---------------------------------------------------------------------------
# Error Tests
# ---------------------------------------------------------------------------

class TestConnectErrors:
    """Connection errors should return structured error responses."""

    def test_invalid_host_returns_error(self):
        result = execute({
            "connector": "airbyte/source-postgres",
            "connection": {"host": "invalid-host"},
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "CONNECTION_FAILED"

    def test_empty_host_returns_error(self):
        result = execute({
            "connector": "airbyte/source-postgres",
            "connection": {"host": ""},
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "CONNECTION_FAILED"

    def test_missing_connector_returns_error(self):
        result = execute({
            "connection": {"host": "localhost"},
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "MISSING_CONNECTOR"


# ---------------------------------------------------------------------------
# Credential Resolution Tests
# ---------------------------------------------------------------------------

class TestCredentialResolution:
    """Placeholders in connection config should be resolved."""

    def test_placeholders_resolved(self, resolver):
        result = execute({
            "connector": "airbyte/source-postgres",
            "connection": {
                "host": "${PROD_DB_HOST}",
                "port": "${PROD_DB_PORT}",
            },
            "credential_resolver": resolver,
        })
        assert result["status"] == "success"

    def test_unresolvable_placeholder_returns_error(self):
        resolver = CredentialResolver(docker_secrets_dir="/nonexistent")
        result = execute({
            "connector": "airbyte/source-postgres",
            "connection": {"host": "${MISSING_HOST}"},
            "credential_resolver": resolver,
        })
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "CREDENTIAL_ERROR"
