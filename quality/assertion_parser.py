"""
Assertion DSL parser for the Conductor Data Pipeline.

Parses assertion strings from pipeline YAML quality.assertions into
structured ParsedAssertion objects that can be executed against DuckDB.

Supported syntax (SPEC Section 12.6):
    table.column IS NOT NULL
    table.column IS UNIQUE
    table.column >= N
    table.column BETWEEN N AND M
    ROW_COUNT(table) > N
    table.column IN (v1, v2, ...)
    table.column MATCHES 'regex'
    COUNT(DISTINCT table.column) >= N
    ASSERT <custom SQL>

SQL injection protection:
    - Column names validated against [a-zA-Z_][a-zA-Z0-9_.]*
    - Numeric values validated as actual numbers
    - String values in IN() and MATCHES must be properly quoted
    - Only ASSERT allows raw SQL (audited)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class AssertionType(Enum):
    IS_NOT_NULL = "IS_NOT_NULL"
    IS_UNIQUE = "IS_UNIQUE"
    COMPARISON = "COMPARISON"
    BETWEEN = "BETWEEN"
    ROW_COUNT = "ROW_COUNT"
    IN_VALUES = "IN_VALUES"
    MATCHES = "MATCHES"
    COUNT_DISTINCT = "COUNT_DISTINCT"
    CUSTOM_ASSERT = "CUSTOM_ASSERT"


class AssertionParseError(Exception):
    """Raised when an assertion string cannot be parsed."""
    pass


# Regex for valid column/table identifiers (no SQL injection)
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
_QUALIFIED_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.]*$")

# Pattern for SQL injection red flags
_INJECTION_PATTERNS = [
    re.compile(r";\s*", re.IGNORECASE),
    re.compile(r"--", re.IGNORECASE),
    re.compile(r"/\*", re.IGNORECASE),
    re.compile(r"\bDROP\b", re.IGNORECASE),
    re.compile(r"\bDELETE\b", re.IGNORECASE),
    re.compile(r"\bINSERT\b", re.IGNORECASE),
    re.compile(r"\bUPDATE\b", re.IGNORECASE),
    re.compile(r"\bALTER\b", re.IGNORECASE),
    re.compile(r"\bCREATE\b", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\b", re.IGNORECASE),
    re.compile(r"\bEXEC\b", re.IGNORECASE),
]


@dataclass
class ParsedAssertion:
    """Parsed assertion ready for execution."""

    assertion_type: AssertionType
    original_text: str
    table: str
    column: Optional[str]
    sql: str
    fail_condition: str  # human-readable description of when this fails


def _validate_identifier(name: str, label: str = "identifier") -> None:
    """Validate that a name is a safe SQL identifier."""
    if not _QUALIFIED_IDENTIFIER_RE.match(name):
        raise AssertionParseError(
            f"Invalid {label}: '{name}'. "
            f"Must match [a-zA-Z_][a-zA-Z0-9_.]*"
        )


def _check_injection(text: str) -> None:
    """Check for SQL injection patterns in non-ASSERT assertion text."""
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            raise AssertionParseError(
                f"Potential SQL injection detected in assertion: '{text}'"
            )


# Statements that must never appear in a custom ASSERT. An assertion is a
# read-only question about the data; anything that writes, drops, attaches or
# reaches the filesystem is out of scope by definition.
_FORBIDDEN_IN_CUSTOM_SQL = [
    re.compile(r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE|REPLACE)\b", re.IGNORECASE),
    re.compile(r"\b(ATTACH|DETACH|COPY|EXPORT|IMPORT|INSTALL|LOAD|PRAGMA|SET)\b", re.IGNORECASE),
    re.compile(r"\b(read_csv|read_parquet|read_json)\w*\s*\(", re.IGNORECASE),
    re.compile(r"--"),
    re.compile(r"/\*"),
]


def _validate_custom_sql(sql: str) -> None:
    """Validate a custom ASSERT body: one read-only SELECT, nothing else.

    ASSERT necessarily accepts free-form SQL — that is its purpose — so it
    cannot use the identifier allow-list the other assertion types rely on.
    Previously it received no validation at all and was handed to DuckDB
    verbatim, which made it a direct execution primitive for anyone who could
    author a quality rule.

    The constraints below keep the feature usable while removing that:
      * exactly one statement (no stacked `;` payloads),
      * it must start with SELECT or WITH,
      * no DDL/DML, no ATTACH/COPY/INSTALL/LOAD/PRAGMA, no file-reading
        table functions, no comment sequences used to smuggle the above.
    """
    stripped = sql.strip()
    if not stripped:
        raise AssertionParseError("ASSERT requires a SQL statement")

    # Reject stacked statements. A single trailing semicolon is fine.
    body = stripped.rstrip(";").strip()
    if ";" in body:
        raise AssertionParseError(
            "ASSERT must contain exactly one statement; ';' is not allowed"
        )

    if not re.match(r"^(SELECT|WITH)\b", body, re.IGNORECASE):
        raise AssertionParseError(
            "ASSERT must be a read-only query beginning with SELECT or WITH"
        )

    for pattern in _FORBIDDEN_IN_CUSTOM_SQL:
        m = pattern.search(body)
        if m:
            raise AssertionParseError(
                f"ASSERT may not contain '{m.group(0)}' — assertions are read-only"
            )


def _validate_number(value: str) -> str:
    """Validate and return a numeric string."""
    value = value.strip()
    try:
        # Accept integers and floats, including negatives
        float(value)
        return value
    except ValueError:
        raise AssertionParseError(
            f"Invalid numeric value: '{value}'. Expected a number."
        )


def _resolve_table_column(qualified_name: str) -> Tuple[str, str]:
    """
    Resolve 'table.column' into (table, column).
    Raises AssertionParseError if format is invalid.
    """
    _validate_identifier(qualified_name, "column reference")
    parts = qualified_name.split(".")
    if len(parts) != 2:
        raise AssertionParseError(
            f"Column reference must be in 'table.column' format, "
            f"got: '{qualified_name}'"
        )
    table, column = parts
    _validate_identifier(table, "table name")
    _validate_identifier(column, "column name")
    return table, column


def parse_assertion(assertion_text: str) -> ParsedAssertion:
    """
    Parse a single assertion DSL string into a ParsedAssertion.

    Args:
        assertion_text: The assertion string from pipeline YAML.

    Returns:
        ParsedAssertion with generated SQL and metadata.

    Raises:
        AssertionParseError: If the assertion cannot be parsed or
            contains invalid syntax / injection attempts.
    """
    text = assertion_text.strip()
    if not text:
        raise AssertionParseError("Empty assertion string")

    # ----- ASSERT <custom SQL> -----
    assert_match = re.match(r"^ASSERT\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
    if assert_match:
        custom_sql = assert_match.group(1).strip()
        _validate_custom_sql(custom_sql)
        return ParsedAssertion(
            assertion_type=AssertionType.CUSTOM_ASSERT,
            original_text=text,
            table="__custom__",
            column=None,
            sql=custom_sql,
            fail_condition="result rows > 0",
        )

    # For non-ASSERT assertions, check for injection patterns
    _check_injection(text)

    # ----- ROW_COUNT(table) > N -----
    row_count_match = re.match(
        r"^ROW_COUNT\(\s*(\w+)\s*\)\s*(>=|<=|!=|>|<|=)\s*(.+)$",
        text,
        re.IGNORECASE,
    )
    if row_count_match:
        table = row_count_match.group(1)
        operator = row_count_match.group(2)
        value = _validate_number(row_count_match.group(3))
        _validate_identifier(table, "table name")
        sql = f"SELECT COUNT(*) FROM {table}"  # noqa: S608 — table validated via _validate_identifier()
        return ParsedAssertion(
            assertion_type=AssertionType.ROW_COUNT,
            original_text=text,
            table=table,
            column=None,
            sql=sql,
            fail_condition=f"count {_negate_operator(operator)} {value}",
        )

    # ----- COUNT(DISTINCT table.column) >= N -----
    count_distinct_match = re.match(
        r"^COUNT\(\s*DISTINCT\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s*\)\s*(>=|<=|!=|>|<|=)\s*(.+)$",
        text,
        re.IGNORECASE,
    )
    if count_distinct_match:
        qualified = count_distinct_match.group(1)
        operator = count_distinct_match.group(2)
        value = _validate_number(count_distinct_match.group(3))
        table, column = _resolve_table_column(qualified)
        sql = f"SELECT COUNT(DISTINCT {column}) FROM {table}"  # noqa: S608 — identifiers validated via _validate_identifier()
        return ParsedAssertion(
            assertion_type=AssertionType.COUNT_DISTINCT,
            original_text=text,
            table=table,
            column=column,
            sql=sql,
            fail_condition=f"count {_negate_operator(operator)} {value}",
        )

    # ----- table.column IS NOT NULL -----
    not_null_match = re.match(
        r"^([a-zA-Z_][a-zA-Z0-9_.]*)\s+IS\s+NOT\s+NULL$",
        text,
        re.IGNORECASE,
    )
    if not_null_match:
        qualified = not_null_match.group(1)
        table, column = _resolve_table_column(qualified)
        sql = f"SELECT COUNT(*) FROM {table} WHERE {column} IS NULL"  # noqa: S608 — identifiers validated via _validate_identifier()
        return ParsedAssertion(
            assertion_type=AssertionType.IS_NOT_NULL,
            original_text=text,
            table=table,
            column=column,
            sql=sql,
            fail_condition="count > 0",
        )

    # ----- table.column IS UNIQUE -----
    unique_match = re.match(
        r"^([a-zA-Z_][a-zA-Z0-9_.]*)\s+IS\s+UNIQUE$",
        text,
        re.IGNORECASE,
    )
    if unique_match:
        qualified = unique_match.group(1)
        table, column = _resolve_table_column(qualified)
        sql = f"SELECT COUNT(*) - COUNT(DISTINCT {column}) FROM {table}"  # noqa: S608 — identifiers validated via _validate_identifier()
        return ParsedAssertion(
            assertion_type=AssertionType.IS_UNIQUE,
            original_text=text,
            table=table,
            column=column,
            sql=sql,
            fail_condition="diff > 0",
        )

    # ----- table.column BETWEEN N AND M -----
    between_match = re.match(
        r"^([a-zA-Z_][a-zA-Z0-9_.]*)\s+BETWEEN\s+(\S+)\s+AND\s+(\S+)$",
        text,
        re.IGNORECASE,
    )
    if between_match:
        qualified = between_match.group(1)
        low = _validate_number(between_match.group(2))
        high = _validate_number(between_match.group(3))
        table, column = _resolve_table_column(qualified)
        sql = f"SELECT COUNT(*) FROM {table} WHERE {column} NOT BETWEEN {low} AND {high}"  # noqa: S608 — identifiers validated via _validate_identifier(); values validated via _validate_number()
        return ParsedAssertion(
            assertion_type=AssertionType.BETWEEN,
            original_text=text,
            table=table,
            column=column,
            sql=sql,
            fail_condition="count > 0",
        )

    # ----- table.column MATCHES 'regex' -----
    matches_match = re.match(
        r"^([a-zA-Z_][a-zA-Z0-9_.]*)\s+MATCHES\s+'((?:[^'\\]|\\.)*)'\s*$",
        text,
        re.IGNORECASE,
    )
    if matches_match:
        qualified = matches_match.group(1)
        regex_pattern = matches_match.group(2)
        table, column = _resolve_table_column(qualified)
        # Escape single quotes in the regex pattern for SQL
        safe_pattern = regex_pattern.replace("'", "''")
        sql = f"SELECT COUNT(*) FROM {table} WHERE NOT regexp_matches({column}, '{safe_pattern}')"  # noqa: S608 — identifiers validated via _validate_identifier()
        return ParsedAssertion(
            assertion_type=AssertionType.MATCHES,
            original_text=text,
            table=table,
            column=column,
            sql=sql,
            fail_condition="count > 0",
        )

    # ----- table.column IN (v1, v2, ...) -----
    in_match = re.match(
        r"^([a-zA-Z_][a-zA-Z0-9_.]*)\s+IN\s*\((.+)\)\s*$",
        text,
        re.IGNORECASE,
    )
    if in_match:
        qualified = in_match.group(1)
        values_str = in_match.group(2).strip()
        table, column = _resolve_table_column(qualified)
        # Parse individual values — they can be numbers or quoted strings
        values = _parse_in_values(values_str)
        sql = f"SELECT COUNT(*) FROM {table} WHERE {column} NOT IN ({values})"  # noqa: S608 — identifiers validated via _validate_identifier(); values parsed via _parse_in_values()
        return ParsedAssertion(
            assertion_type=AssertionType.IN_VALUES,
            original_text=text,
            table=table,
            column=column,
            sql=sql,
            fail_condition="count > 0",
        )

    # ----- table.column <op> N (comparison: >=, >, <=, <, =, !=) -----
    comparison_match = re.match(
        r"^([a-zA-Z_][a-zA-Z0-9_.]*)\s*(>=|<=|!=|>|<|=)\s*(.+)$",
        text,
        re.IGNORECASE,
    )
    if comparison_match:
        qualified = comparison_match.group(1)
        operator = comparison_match.group(2)
        value = _validate_number(comparison_match.group(3))
        table, column = _resolve_table_column(qualified)
        sql = f"SELECT COUNT(*) FROM {table} WHERE NOT ({column} {operator} {value})"  # noqa: S608 — identifiers validated via _validate_identifier(); value validated via _validate_number()
        return ParsedAssertion(
            assertion_type=AssertionType.COMPARISON,
            original_text=text,
            table=table,
            column=column,
            sql=sql,
            fail_condition="count > 0",
        )

    raise AssertionParseError(f"Unrecognized assertion syntax: '{text}'")


def _parse_in_values(values_str: str) -> str:
    """
    Parse the values inside IN(...) and return safe SQL value list.
    Accepts numbers and single-quoted strings.
    """
    values = []
    raw_parts = _split_in_values(values_str)

    for part in raw_parts:
        part = part.strip()
        if not part:
            continue
        # Quoted string
        if (part.startswith("'") and part.endswith("'")) or \
           (part.startswith('"') and part.endswith('"')):
            # Keep single-quoted for SQL, escape internal quotes
            inner = part[1:-1]
            safe = inner.replace("'", "''")
            values.append(f"'{safe}'")
        else:
            # Must be a number
            _validate_number(part)
            values.append(part)

    if not values:
        raise AssertionParseError("IN() clause requires at least one value")

    return ", ".join(values)


def _split_in_values(values_str: str) -> list:
    """Split IN values respecting quoted strings."""
    parts = []
    current = []
    in_quotes = False
    quote_char = None

    for char in values_str:
        if in_quotes:
            current.append(char)
            if char == quote_char:
                in_quotes = False
        elif char in ("'", '"'):
            in_quotes = True
            quote_char = char
            current.append(char)
        elif char == ",":
            parts.append("".join(current))
            current = []
        else:
            current.append(char)

    if current:
        parts.append("".join(current))

    return parts


def _negate_operator(op: str) -> str:
    """Return the negated comparison operator for fail condition description."""
    negations = {
        ">": "<=",
        ">=": "<",
        "<": ">=",
        "<=": ">",
        "=": "!=",
        "!=": "=",
    }
    return negations.get(op, f"NOT {op}")
