"""
data_connect MCP Tool -- Test connectivity to a data source.

Resolves credentials, simulates an Airbyte connection test, and returns
the source's schema catalog. Standard governance classification.
"""

import logging
import time

from tools.credential_resolver import CredentialResolver, CredentialResolverError

logger = logging.getLogger(__name__)

# Simulated schema catalog for known connector types (for testing without real Airbyte)
_SIMULATED_CATALOGS = {
    "airbyte/source-postgres": {
        "streams": [
            {
                "name": "customers",
                "columns": [
                    {"name": "id", "type": "integer", "nullable": False},
                    {"name": "name", "type": "varchar", "nullable": False},
                    {"name": "email", "type": "varchar", "nullable": True},
                    {"name": "phone", "type": "varchar", "nullable": True},
                    {"name": "address", "type": "text", "nullable": True},
                    {"name": "created_at", "type": "timestamp", "nullable": False},
                    {"name": "tier", "type": "varchar", "nullable": True},
                ],
                "primary_key": ["id"],
            },
            {
                "name": "orders",
                "columns": [
                    {"name": "id", "type": "integer", "nullable": False},
                    {"name": "customer_id", "type": "integer", "nullable": False},
                    {"name": "amount", "type": "decimal", "nullable": False},
                    {"name": "status", "type": "varchar", "nullable": True},
                    {"name": "created_at", "type": "timestamp", "nullable": False},
                ],
                "primary_key": ["id"],
            },
        ]
    },
    "airbyte/source-mysql": {
        "streams": [
            {
                "name": "users",
                "columns": [
                    {"name": "user_id", "type": "int", "nullable": False},
                    {"name": "username", "type": "varchar", "nullable": False},
                    {"name": "email", "type": "varchar", "nullable": True},
                ],
                "primary_key": ["user_id"],
            }
        ]
    },
}


def execute(params: dict) -> dict:
    """
    Test connectivity to a data source and return its schema catalog.

    Args:
        params: Dict with keys:
            - connector (str): Airbyte connector type (e.g. 'airbyte/source-postgres')
            - connection (dict): Connection config with possible ${VARIABLE} placeholders
            - credential_resolver (CredentialResolver, optional): Resolver instance

    Returns:
        Dict with status, data (catalog), and metadata.
    """
    connector = params.get("connector")
    connection = params.get("connection", {})
    resolver = params.get("credential_resolver")

    if not connector:
        return {
            "status": "error",
            "data": {"error_code": "MISSING_CONNECTOR", "message": "No connector specified"},
            "metadata": {"tool": "data_connect"},
        }

    # Resolve credential placeholders
    try:
        if resolver is None:
            resolver = CredentialResolver()
        resolved_connection = resolver.resolve_placeholders(connection)
    except CredentialResolverError as exc:
        return {
            "status": "error",
            "data": {
                "error_code": "CREDENTIAL_ERROR",
                "message": str(exc),
            },
            "metadata": {"tool": "data_connect", "connector": connector},
        }

    # Simulate connection test
    start_time = time.monotonic()

    # Check for simulated failure conditions
    host = resolved_connection.get("host", "")
    if host == "invalid-host" or host == "":
        elapsed = (time.monotonic() - start_time) * 1000
        return {
            "status": "error",
            "data": {
                "error_code": "CONNECTION_FAILED",
                "message": f"Cannot connect to {connector} at host '{host}'",
            },
            "metadata": {
                "tool": "data_connect",
                "connector": connector,
                "elapsed_ms": round(elapsed, 2),
            },
        }

    # Return simulated catalog or a generic one
    catalog = _SIMULATED_CATALOGS.get(connector, {
        "streams": [
            {
                "name": "default_table",
                "columns": [
                    {"name": "id", "type": "integer", "nullable": False},
                    {"name": "data", "type": "varchar", "nullable": True},
                ],
                "primary_key": ["id"],
            }
        ]
    })

    elapsed = (time.monotonic() - start_time) * 1000

    return {
        "status": "success",
        "data": {
            "connected": True,
            "connector": connector,
            "catalog": catalog,
        },
        "metadata": {
            "tool": "data_connect",
            "connector": connector,
            "elapsed_ms": round(elapsed, 2),
        },
    }
