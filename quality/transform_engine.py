"""
Transform engine for the Conductor Data Pipeline.

Parses transform operations from pipeline YAML and executes them
via DuckDB: join, filter, derive, aggregate.

Transforms execute sequentially in the order defined in the pipeline YAML.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from quality.duckdb_executor import DuckDBExecutor


class TransformError(Exception):
    """Raised when a transform operation fails."""
    pass


class TransformEngine:
    """
    Executes transform operations against a DuckDB executor.

    Supported operations:
        - join: SQL JOIN on DuckDB tables
        - filter: SQL WHERE clause creating a new table
        - derive: New column via SQL expression
        - aggregate: GROUP BY with aggregate functions
    """

    def __init__(self, executor: DuckDBExecutor) -> None:
        self._executor = executor

    def execute_transforms(self, transforms: List[Dict[str, Any]]) -> None:
        """
        Execute a list of transform operations sequentially.

        Args:
            transforms: List of transform dicts from pipeline YAML.
                Each must have an 'operation' key.

        Raises:
            TransformError: If any transform fails.
        """
        for i, transform in enumerate(transforms):
            operation = transform.get("operation")
            if not operation:
                raise TransformError(
                    f"Transform at index {i} missing 'operation' key"
                )

            handler = {
                "join": self._execute_join,
                "filter": self._execute_filter,
                "derive": self._execute_derive,
                "aggregate": self._execute_aggregate,
            }.get(operation)

            if handler is None:
                # Skip non-transform operations (e.g., 'classify')
                continue

            try:
                handler(transform)
            except TransformError:
                raise
            except Exception as e:
                raise TransformError(
                    f"Transform '{operation}' at index {i} failed: {e}"
                ) from e

    def _execute_join(self, spec: Dict[str, Any]) -> None:
        """
        Execute a JOIN transform.

        Required keys: left, right, on
        Optional keys: type (default: 'inner'), output (default: '{left}_{right}_joined')

        SQL: CREATE TABLE {output} AS SELECT * FROM {left} {type} JOIN {right} ON {condition}
        """
        left = spec.get("left")
        right = spec.get("right")
        condition = spec.get("on")
        join_type = spec.get("type", "inner").upper()
        output = spec.get("output", f"{left}_{right}_joined")

        if not left or not right or not condition:
            raise TransformError(
                "JOIN requires 'left', 'right', and 'on' fields"
            )

        valid_join_types = {"LEFT", "RIGHT", "INNER", "CROSS", "FULL"}
        if join_type not in valid_join_types:
            raise TransformError(
                f"Invalid join type '{join_type}'. "
                f"Must be one of: {', '.join(sorted(valid_join_types))}"
            )

        if join_type == "CROSS":
            sql = (
                f"CREATE TABLE {output} AS "  # noqa: S608 — DuckDB in-process DDL; identifiers from pipeline YAML, not user input
                f"SELECT * FROM {left} CROSS JOIN {right}"
            )
        else:
            sql = (
                f"CREATE TABLE {output} AS "  # noqa: S608 — DuckDB in-process DDL; identifiers from pipeline YAML, not user input
                f"SELECT * FROM {left} {join_type} JOIN {right} ON {condition}"
            )

        self._executor.execute_sql(sql)
        if output not in self._executor.tables:
            self._executor._tables.append(output)

    def _execute_filter(self, spec: Dict[str, Any]) -> None:
        """
        Execute a FILTER transform.

        Required keys: input, expression
        Optional keys: output (default: '{input}_filtered')

        SQL: CREATE TABLE {output} AS SELECT * FROM {input} WHERE {expression}
        """
        input_table = spec.get("input")
        expression = spec.get("expression")
        output = spec.get("output", f"{input_table}_filtered")

        if not input_table or not expression:
            raise TransformError(
                "FILTER requires 'input' and 'expression' fields"
            )

        sql = (
            f"CREATE TABLE {output} AS "  # noqa: S608 — DuckDB in-process DDL; identifiers from pipeline YAML
            f"SELECT * FROM {input_table} WHERE {expression}"
        )

        self._executor.execute_sql(sql)
        if output not in self._executor.tables:
            self._executor._tables.append(output)

    def _execute_derive(self, spec: Dict[str, Any]) -> None:
        """
        Execute a DERIVE transform (add a new column).

        Required keys: table (or input), field, expression
        Optional keys: output

        For simple expressions:
            ALTER TABLE {table} ADD COLUMN {field} ...
            UPDATE {table} SET {field} = {expression}

        For aggregate expressions with GROUP BY:
            1. Create intermediate aggregate table
            2. Join back to source
            3. Store result as output table
        """
        table = spec.get("table") or spec.get("input")
        field = spec.get("field")
        expression = spec.get("expression")
        output = spec.get("output")

        if not table or not field or not expression:
            raise TransformError(
                "DERIVE requires 'table' (or 'input'), 'field', and 'expression' fields"
            )

        # Detect GROUP BY expressions
        group_by_match = re.search(
            r"\bGROUP\s+BY\s+(.+)$", expression, re.IGNORECASE
        )

        if group_by_match:
            # Aggregate derive: create intermediate and join back
            group_cols = group_by_match.group(1).strip()
            agg_expr = expression[: group_by_match.start()].strip()

            # Build the list of group-by column names for joining
            group_col_list = [c.strip() for c in group_cols.split(",")]

            # Strip table prefixes for the bare column names used in the join
            bare_group_cols = []
            for gc in group_col_list:
                parts = gc.split(".")
                bare_group_cols.append(parts[-1])

            intermediate = f"__{table}_{field}_agg"

            # Create intermediate aggregate table
            agg_sql = (
                f"CREATE TABLE {intermediate} AS "  # noqa: S608 — DuckDB in-process DDL; identifiers from pipeline YAML
                f"SELECT {group_cols}, {agg_expr} AS {field} "
                f"FROM {table} GROUP BY {group_cols}"
            )
            self._executor.execute_sql(agg_sql)

            # Build join condition using bare column names
            join_conds = []
            for gc_orig, gc_bare in zip(group_col_list, bare_group_cols):
                # gc_orig might be "customers.id", gc_bare is "id"
                join_conds.append(f"t1.{gc_bare} = t2.{gc_bare}")
            join_condition = " AND ".join(join_conds)

            # Determine output table name
            result_table = output or f"{table}_derived"

            # Join aggregate back to source
            join_sql = (
                f"CREATE TABLE {result_table} AS "  # noqa: S608 — DuckDB in-process DDL; identifiers from pipeline YAML
                f"SELECT t1.*, t2.{field} "
                f"FROM {table} t1 "
                f"LEFT JOIN {intermediate} t2 ON {join_condition}"
            )
            self._executor.execute_sql(join_sql)

            # Clean up intermediate
            self._executor.execute_sql(f"DROP TABLE {intermediate}")  # noqa: S608 — DuckDB in-process DDL; internal intermediate table name

            if result_table not in self._executor.tables:
                self._executor._tables.append(result_table)

        else:
            # Simple derive: add column directly
            if output and output != table:
                # Create new table with the derived column
                derive_sql = (
                    f"CREATE TABLE {output} AS "  # noqa: S608 — DuckDB in-process DDL; identifiers from pipeline YAML
                    f"SELECT *, ({expression}) AS {field} FROM {table}"
                )
                self._executor.execute_sql(derive_sql)
                if output not in self._executor.tables:
                    self._executor._tables.append(output)
            else:
                # Modify table in-place using a replacement
                temp = f"__{table}_derive_temp"
                derive_sql = (
                    f"CREATE TABLE {temp} AS "  # noqa: S608 — DuckDB in-process DDL; identifiers from pipeline YAML
                    f"SELECT *, ({expression}) AS {field} FROM {table}"
                )
                self._executor.execute_sql(derive_sql)
                self._executor.execute_sql(f"DROP TABLE {table}")  # noqa: S608 — DuckDB in-process DDL; internal table name
                self._executor.execute_sql(
                    f"ALTER TABLE {temp} RENAME TO {table}"  # noqa: S608 — DuckDB in-process DDL; internal table names
                )

    def _execute_aggregate(self, spec: Dict[str, Any]) -> None:
        """
        Execute an AGGREGATE transform.

        Required keys: input (or table), group_by, aggregations
        Optional keys: output (default: '{input}_aggregated')

        aggregations is a list of dicts like:
            [{"function": "SUM", "column": "amount", "alias": "total_amount"}, ...]
        Or a list of raw SQL expression strings:
            ["SUM(amount) AS total_amount", "COUNT(*) AS order_count"]

        SQL: SELECT {group_cols}, {agg_functions} FROM {table} GROUP BY {group_cols}
        """
        input_table = spec.get("input") or spec.get("table")
        group_by = spec.get("group_by")
        aggregations = spec.get("aggregations")
        output = spec.get("output", f"{input_table}_aggregated")

        if not input_table or not group_by or not aggregations:
            raise TransformError(
                "AGGREGATE requires 'input' (or 'table'), 'group_by', "
                "and 'aggregations' fields"
            )

        # group_by can be a string or list
        if isinstance(group_by, list):
            group_cols = ", ".join(group_by)
        else:
            group_cols = group_by

        # Build aggregation expressions
        agg_parts = []
        for agg in aggregations:
            if isinstance(agg, str):
                agg_parts.append(agg)
            elif isinstance(agg, dict):
                func = agg.get("function", "")
                col = agg.get("column", "")
                alias = agg.get("alias", f"{func}_{col}".lower())
                agg_parts.append(f"{func}({col}) AS {alias}")
            else:
                raise TransformError(
                    f"Invalid aggregation spec: {agg}"
                )

        agg_expr = ", ".join(agg_parts)

        sql = (
            f"CREATE TABLE {output} AS "  # noqa: S608 — DuckDB in-process DDL; identifiers from pipeline YAML
            f"SELECT {group_cols}, {agg_expr} "
            f"FROM {input_table} GROUP BY {group_cols}"
        )

        self._executor.execute_sql(sql)
        if output not in self._executor.tables:
            self._executor._tables.append(output)
