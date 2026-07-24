"""
DuckDB execution context for the Quality Assertion Engine.

Creates an in-memory DuckDB connection, loads datasets as named tables,
executes SQL assertions and transforms, and manages cleanup.
"""

from __future__ import annotations

import re

import duckdb
from typing import List, Dict, Any, Tuple

# DuckDB memory-limit config values (e.g. '1GB', '512MB', '2gb').
# Validated before interpolation because PRAGMA/SET does not accept bind params.
_MEMORY_LIMIT_RE = re.compile(r"^\d+(\.\d+)?\s?(B|KB|MB|GB|TB|KiB|MiB|GiB|TiB)$", re.I)


class DuckDBExecutor:
    """
    Manages an in-memory DuckDB database for quality assertions
    and transform operations.
    """

    def __init__(self, memory_limit: str = "1GB") -> None:
        """
        Initialize a new in-memory DuckDB connection.

        Args:
            memory_limit: Maximum memory DuckDB may use (e.g. '1GB', '512MB').
        """
        if not _MEMORY_LIMIT_RE.match(memory_limit.strip()):
            raise ValueError(f"Invalid memory_limit: '{memory_limit}'")
        self._conn = duckdb.connect(database=":memory:")
        self._memory_limit = memory_limit
        # SET is a DuckDB config PRAGMA that does not accept bind parameters;
        # memory_limit is validated against _MEMORY_LIMIT_RE above.
        self._conn.execute(f"SET memory_limit = '{memory_limit}'")  # nosemgrep: configs.sql-string-concatenation-python  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        self._tables: List[str] = []

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """Return the raw DuckDB connection (for advanced use)."""
        return self._conn

    @property
    def tables(self) -> List[str]:
        """Return list of loaded table names."""
        return list(self._tables)

    @property
    def memory_limit(self) -> str:
        """Return the configured memory limit."""
        return self._memory_limit

    def load_table(self, name: str, data: List[Dict[str, Any]]) -> None:
        """
        Load a list of dicts as a named DuckDB table.

        Args:
            name: Table name.
            data: List of row dicts. All dicts should have the same keys.

        Raises:
            ValueError: If data is empty or name is invalid.
        """
        if not name or not name.isidentifier():
            raise ValueError(f"Invalid table name: '{name}'")
        if not data:
            # Create empty table — infer columns from empty dict not possible,
            # so we create with a dummy and delete. `name` is a SQL identifier
            # (validated via str.isidentifier() above) and cannot be a bind param.
            # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            self._conn.execute(f"CREATE TABLE {name} AS SELECT 1 WHERE false")  # nosemgrep: configs.sql-string-concatenation-python
            self._tables.append(name)
            return

        # Build table from list of dicts using INSERT statements.
        # DuckDB 1.x replacement scans require pandas/pyarrow, so we
        # use explicit SQL to stay dependency-light.
        columns = list(data[0].keys())
        col_defs = ", ".join(columns)

        # Infer column types from first row for CREATE TABLE
        type_map = []
        for col in columns:
            val = data[0][col]
            if isinstance(val, bool):
                type_map.append(f"{col} BOOLEAN")
            elif isinstance(val, int):
                type_map.append(f"{col} BIGINT")
            elif isinstance(val, float):
                type_map.append(f"{col} DOUBLE")
            else:
                type_map.append(f"{col} VARCHAR")

        # `name` is a validated SQL identifier and column names come from dict
        # keys (schema), neither of which can be passed as bind parameters in DDL.
        create_sql = f"CREATE TABLE {name} ({', '.join(type_map)})"  # nosemgrep: configs.sql-string-concatenation-python
        self._conn.execute(create_sql)  # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query

        # Insert rows using parameterized queries: identifiers are interpolated
        # into the statement text but every row VALUE is bound via ? placeholders.
        placeholders = ", ".join(["?"] * len(columns))
        insert_sql = f"INSERT INTO {name} ({col_defs}) VALUES ({placeholders})"
        for row in data:
            values = [row.get(c) for c in columns]
            # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            self._conn.execute(insert_sql, values)

        self._tables.append(name)

    def load_table_from_columns(
        self, name: str, columns: Dict[str, List[Any]]
    ) -> None:
        """
        Load a table from column-oriented data.

        Args:
            name: Table name.
            columns: Dict mapping column names to lists of values.
        """
        if not name or not name.isidentifier():
            raise ValueError(f"Invalid table name: '{name}'")
        if not columns:
            # `name` validated via str.isidentifier() above; identifier, not a bind param.
            # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
            self._conn.execute(f"CREATE TABLE {name} AS SELECT 1 WHERE false")  # nosemgrep: configs.sql-string-concatenation-python
            self._tables.append(name)
            return

        # Convert to row-oriented
        keys = list(columns.keys())
        n_rows = len(next(iter(columns.values())))
        data = [
            {k: columns[k][i] for k in keys}
            for i in range(n_rows)
        ]
        self.load_table(name, data)

    def execute_sql(self, sql: str) -> List[Tuple]:
        """
        Execute a SQL query and return all result rows.

        Args:
            sql: Valid DuckDB SQL statement.

        Returns:
            List of tuples (one per row).
        """
        result = self._conn.execute(sql)
        return result.fetchall()

    def execute_assertion(self, sql: str) -> Tuple[bool, int]:
        """
        Execute an assertion SQL and determine pass/fail.

        For most assertion types, the SQL returns a single count.
        The assertion passes if the count is 0 (no failing rows).

        For ROW_COUNT assertions, the caller must handle the
        comparison logic separately.

        Args:
            sql: The assertion SQL to execute.

        Returns:
            Tuple of (passed, failing_count).
            For standard assertions: passed = (count == 0).
        """
        rows = self.execute_sql(sql)
        if not rows or not rows[0]:
            return (True, 0)

        count = rows[0][0]
        if count is None:
            count = 0
        passed = int(count) == 0
        return (passed, int(count))

    def table_exists(self, name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            self._conn.execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = ?",
                [name],
            )
            rows = self._conn.fetchall()
            return len(rows) > 0
        except Exception:
            return False

    def drop_table(self, name: str) -> None:
        """Drop a table by name."""
        # `name` is a SQL identifier drawn from the internal self._tables list
        # (each entry validated via str.isidentifier() at load time); DDL
        # identifiers cannot be passed as bind parameters.
        # nosemgrep: python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query
        self._conn.execute(f"DROP TABLE IF EXISTS {name}")  # nosemgrep: configs.sql-string-concatenation-python
        if name in self._tables:
            self._tables.remove(name)

    def cleanup(self) -> None:
        """Drop all loaded tables."""
        for table in list(self._tables):
            self.drop_table(table)
        self._tables.clear()

    def close(self) -> None:
        """Close the DuckDB connection and clean up."""
        self.cleanup()
        self._conn.close()

    def __enter__(self) -> "DuckDBExecutor":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
