# TODO-006: Quality Assertion Engine

## Requirements Covered
- REQ-DP-026: Data quality assertions (non-null, unique, range, non-empty)
- REQ-DP-038: DuckDB-based quality assertion engine with pre-mask and post-mask execution
- REQ-DP-025: Join, filter, derive, aggregate operations (transform engine shares DuckDB)

## Dependencies
- TODO-001 (JSON Schema definitions — pipeline schema defines assertion syntax)

## Inputs
- Quality assertions from pipeline definition YAML (`quality.assertions` array)
- Dataset as in-memory table (loaded into DuckDB)
- Pipeline `quality.on_failure` setting: `block` or `warn`
- Execution phase: `pre_mask` or `post_mask`

## Outputs
- Assertion results: per-assertion pass/fail with failing row counts
- Quality report JSON (for lineage event inclusion)
- Transform results (for join/filter/derive/aggregate operations)
- Typed error: `QUALITY_ASSERTION_FAILED` (when on_failure=block and assertion fails)

## Implementation Scope

### Files to Create

**`quality/assertion_engine.py`** — Core Assertion Engine
- Parse assertion strings from pipeline YAML into DuckDB SQL:
  - `column IS NOT NULL` → `SELECT COUNT(*) FROM {table} WHERE {column} IS NULL` (fail if > 0)
  - `column IS UNIQUE` → `SELECT COUNT(*) - COUNT(DISTINCT {column}) FROM {table}` (fail if > 0)
  - `column >= N` → `SELECT COUNT(*) FROM {table} WHERE NOT ({column} >= N)` (fail if > 0)
  - `column BETWEEN N AND M` → `SELECT COUNT(*) FROM {table} WHERE {column} NOT BETWEEN N AND M`
  - `ROW_COUNT(table) > N` → `SELECT COUNT(*) FROM {table}` (fail if <= N)
  - `column IN (v1, v2, ...)` → `SELECT COUNT(*) FROM {table} WHERE {column} NOT IN (v1, v2, ...)`
  - `column MATCHES 'regex'` → `SELECT COUNT(*) FROM {table} WHERE NOT regexp_matches({column}, 'regex')`
  - `COUNT(DISTINCT column) >= N` → `SELECT COUNT(DISTINCT {column}) FROM {table}` (fail if < N)
  - `ASSERT <custom SQL>` → execute directly, fail if result has > 0 rows
- Return per-assertion: assertion_text, phase, result (pass/fail), failing_row_count, execution_time_ms

**`quality/duckdb_executor.py`** — DuckDB Execution Context
- Create in-memory DuckDB database
- Load dataset(s) as named tables (from JSON/CSV/Parquet)
- Execute SQL assertions and return results
- Execute transform operations (join, filter, derive, aggregate)
- Memory management: limit DuckDB memory to configurable cap (default 1GB)
- Clean up tables after pipeline completes

**`quality/transform_engine.py`** — Transform Operations
- `join`: SQL JOIN on DuckDB tables (left, right, inner, cross)
- `filter`: SQL WHERE clause
- `derive`: SQL expression creating new column (supports aggregates with GROUP BY)
- `aggregate`: SQL GROUP BY with aggregate functions
- Parse transform operations from pipeline YAML `transform` array
- Execute in order (transforms are sequential, not parallel)
- Return transformed dataset as new DuckDB table

**`quality/assertion_parser.py`** — Assertion String Parser
- Parse the assertion DSL strings from pipeline YAML
- Validate syntax before execution (catch malformed assertions early)
- Map table names: resolve `customers.email` to table `customers`, column `email`
- Reject SQL injection vectors: only allow the defined assertion syntax, not arbitrary SQL
  - Exception: `ASSERT <SQL>` allows custom SQL but is audited in lineage
- Return parsed assertion objects ready for execution

**`quality/quality_report.py`** — Report Generator
- Aggregate assertion results into quality report JSON
- Include: assertions_run, assertions_passed, assertions_failed, phase, execution_time_total
- Per-assertion detail: text, result, failing_rows, execution_time
- Format compatible with lineage event `quality` field (Section 7.1)

### Tests to Write

**`tests/test_assertion_engine.py`**
- Each assertion type tested with passing and failing datasets
- `IS NOT NULL`: dataset with nulls fails, without nulls passes
- `IS UNIQUE`: dataset with duplicates fails, without passes
- `>= N`: values below threshold fail
- `ROW_COUNT > 0`: empty table fails
- `MATCHES 'regex'`: non-matching values fail
- Custom `ASSERT` SQL executes correctly

**`tests/test_duckdb_executor.py`**
- Dataset loads correctly into DuckDB
- SQL execution returns expected results
- Memory limit respected (large dataset doesn't OOM)
- Cleanup removes tables after use

**`tests/test_transform_engine.py`**
- JOIN: correct row count, correct columns
- FILTER: only matching rows remain
- DERIVE: new column computed correctly
- AGGREGATE: GROUP BY produces correct aggregates
- Sequential transforms: output of one feeds into next

**`tests/test_assertion_parser.py`**
- Valid assertion strings parsed correctly
- Invalid syntax rejected with clear error
- SQL injection attempt rejected
- Table/column names resolved correctly

## Acceptance Criteria
1. All assertion types from Section 12.6 compile to valid DuckDB SQL
2. Assertions execute twice per pipeline: pre-mask and post-mask
3. `on_failure: block` halts pipeline on assertion failure
4. `on_failure: warn` logs warning and continues on assertion failure
5. Assertion results included in quality report JSON matching lineage event format
6. Transform engine supports join, filter, derive, aggregate operations
7. DuckDB memory usage stays within configured cap
8. Assertion parser rejects malformed syntax and SQL injection attempts
9. Custom `ASSERT <SQL>` supported for advanced assertions
10. All tests pass: `pytest tests/test_assertion_engine.py tests/test_duckdb_executor.py tests/test_transform_engine.py tests/test_assertion_parser.py`

## Estimated Complexity
L (Large — 500+ lines; DuckDB integration, assertion parser, transform engine, 4+ modules)
