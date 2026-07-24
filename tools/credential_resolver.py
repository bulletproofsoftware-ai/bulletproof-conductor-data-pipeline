"""
Credential Resolver -- three-tier secret resolution.

Resolution order:
1. HashiCorp Vault (via hvac + AppRole)
2. Docker secrets (/run/secrets/)
3. Environment variables

All credential access is logged. Credentials exist in memory only during use.
"""

import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Pattern to match ${VARIABLE} placeholders
_PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

# Docker secrets default path
_DOCKER_SECRETS_DIR = "/run/secrets"


@dataclass
class CredentialAccessLog:
    """Audit record for a credential access."""
    variable: str
    source: str  # vault, docker_secret, env_var
    timestamp: float
    resolved: bool
    error: Optional[str] = None


class CredentialResolverError(Exception):
    """Raised when credential resolution fails."""

    def __init__(self, variable: str, message: str):
        super().__init__(f"Failed to resolve credential '{variable}': {message}")
        self.variable = variable


class CredentialResolver:
    """
    Three-tier credential resolver: Vault -> Docker secrets -> env vars.

    All access is logged for audit. Resolved values exist only in memory
    during the call and are not persisted.
    """

    def __init__(
        self,
        vault_client: Optional[Any] = None,
        docker_secrets_dir: str = _DOCKER_SECRETS_DIR,
    ):
        """
        Initialize the resolver.

        Args:
            vault_client: An hvac.Client instance (or mock). If None, Vault tier is skipped.
            docker_secrets_dir: Path to Docker secrets directory.
        """
        self._vault = vault_client
        self._docker_secrets_dir = docker_secrets_dir
        self._access_log: list[CredentialAccessLog] = []

    @property
    def access_log(self) -> list[CredentialAccessLog]:
        """Return the credential access audit log."""
        return list(self._access_log)

    def _log_access(
        self,
        variable: str,
        source: str,
        resolved: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record an access attempt to the audit log."""
        entry = CredentialAccessLog(
            variable=variable,
            source=source,
            timestamp=time.time(),
            resolved=resolved,
            error=error,
        )
        self._access_log.append(entry)
        if resolved:
            logger.info(  # nosemgrep: python-logger-credential-disclosure — logs variable name and source, not credential value
                "Credential resolved: variable=%s source=%s",
                variable,
                source,
            )
        else:
            # G6: Log a generic message at INFO; detailed error only at DEBUG
            # to avoid leaking sensitive path/connection info in production logs.
            logger.info(
                "Credential not found: variable=%s source=%s error=Resolution failed",
                variable,
                source,
            )
            logger.debug(  # nosemgrep: python-logger-credential-disclosure — logs variable name, not credential value
                "Credential resolution detail: variable=%s source=%s error=%s",
                variable,
                source,
                error or "not found",
            )

    def _resolve_from_vault(self, variable: str) -> Optional[str]:
        """Attempt to resolve a credential from HashiCorp Vault."""
        if self._vault is None:
            self._log_access(variable, "vault", False, "no vault client configured")
            return None

        try:
            # Read from Vault KV v2 secret engine at path conductor-data/{variable}
            response = self._vault.secrets.kv.v2.read_secret_version(
                path=f"conductor-data/{variable}",
                mount_point="secret",
            )
            value = response.get("data", {}).get("data", {}).get("value")
            if value is not None:
                self._log_access(variable, "vault", True)
                return str(value)
            self._log_access(variable, "vault", False, "key 'value' not in secret")
            return None
        except Exception as exc:
            logger.debug("Vault resolution error: variable=%s error=%s", variable, exc)  # nosemgrep: python-logger-credential-disclosure — logs exception type, not credential value
            self._log_access(variable, "vault", False, "Resolution failed")
            return None

    def _resolve_from_docker_secrets(self, variable: str) -> Optional[str]:
        """Attempt to resolve a credential from Docker secrets."""
        # G7: Try original case first, then lowercase as fallback
        for candidate in (variable, variable.lower()):
            secret_path = os.path.join(self._docker_secrets_dir, candidate)
            # C7: Resolve symlinks / ".." and verify the path stays within
            # the secrets directory to prevent path-traversal attacks.
            real_path = os.path.realpath(secret_path)
            real_base = os.path.realpath(self._docker_secrets_dir)
            if not real_path.startswith(real_base + os.sep) and real_path != real_base:
                self._log_access(
                    variable, "docker_secret", False,
                    "path traversal blocked",
                )
                return None
            try:
                if os.path.isfile(real_path):
                    with open(real_path, "r") as f:
                        value = f.read().strip()
                    if value:
                        self._log_access(variable, "docker_secret", True)
                        return value
            except Exception as exc:
                logger.debug(  # nosemgrep: python-logger-credential-disclosure — logs exception type, not credential value
                    "Docker secret read error: variable=%s error=%s",
                    variable, exc,
                )
                self._log_access(variable, "docker_secret", False, "Resolution failed")
                return None
        self._log_access(variable, "docker_secret", False, "file not found or empty")
        return None

    def _resolve_from_env(self, variable: str) -> Optional[str]:
        """Attempt to resolve a credential from environment variables."""
        value = os.environ.get(variable)
        if value is not None:
            self._log_access(variable, "env_var", True)
            return value
        self._log_access(variable, "env_var", False, "not set")
        return None

    def resolve(self, variable: str) -> str:
        """
        Resolve a single credential variable through the three-tier chain.

        Args:
            variable: The variable name (without ${} wrapping).

        Returns:
            The resolved credential value.

        Raises:
            CredentialResolverError: If the credential cannot be resolved.
        """
        # Tier 1: Vault
        value = self._resolve_from_vault(variable)
        if value is not None:
            return value

        # Tier 2: Docker secrets
        value = self._resolve_from_docker_secrets(variable)
        if value is not None:
            return value

        # Tier 3: Environment variables
        value = self._resolve_from_env(variable)
        if value is not None:
            return value

        raise CredentialResolverError(
            variable,
            "Not found in Vault, Docker secrets, or environment variables",
        )

    def resolve_placeholders(self, config: dict) -> dict:
        """
        Resolve all ${VARIABLE} placeholders in a configuration dict.

        Recursively processes nested dicts and string values.
        Returns a new dict with all placeholders resolved.

        Args:
            config: Dict that may contain ${VARIABLE} placeholders in string values.

        Returns:
            New dict with all placeholders resolved.

        Raises:
            CredentialResolverError: If any placeholder cannot be resolved.
        """
        return self._resolve_dict(config)

    def _resolve_dict(self, obj: Any) -> Any:
        """Recursively resolve placeholders in nested structures."""
        if isinstance(obj, dict):
            return {k: self._resolve_dict(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._resolve_dict(item) for item in obj]
        elif isinstance(obj, str):
            return self._resolve_string(obj)
        return obj

    def _resolve_string(self, value: str) -> str:
        """Resolve all ${VARIABLE} placeholders in a string."""
        def _replace(match: re.Match) -> str:
            variable = match.group(1)
            return self.resolve(variable)

        return _PLACEHOLDER_RE.sub(_replace, value)
