# TODO-004: Masking Engine Synthetic Data Generation

## Requirements Covered
- REQ-DP-010: Synthetic data generation matching source distributions

## Dependencies
- TODO-002 (Masking engine core — strategy router, API layer, Pydantic models must exist)

## Inputs
- Source dataset statistics (mean, variance, cardinality, null rates, value distributions)
- Column type metadata from data contract
- Faker locale configuration (optional, defaults to en_US)
- Quality assertions from pipeline definition (synthetic data must pass these)

## Outputs
- Synthetic dataset matching source statistical distributions within 5% tolerance
- Distribution comparison report (source vs synthetic per column)
- Lineage metadata for synthetic generation operation

## Implementation Scope

### Files to Create

**`masking-engine/app/transformers/synthetic.py`** — Synthetic Data Generator
- Accept source dataset statistics (not the raw data — stats pre-computed by profiler)
- For each column, generate synthetic values using Faker:
  - `PERSON` PII type: `faker.name()`
  - `EMAIL` PII type: `faker.email()`
  - `PHONE` PII type: `faker.phone_number()`
  - `ADDRESS` PII type: `faker.address()`
  - `DATE_OF_BIRTH` PII type: `faker.date_of_birth()`
  - Non-PII strings: `faker.text()` with length matching source distribution
  - Integers: random within source min/max with matching distribution shape
  - Floats/decimals: normal distribution matching source mean/variance
  - Dates: random within source date range
  - Booleans: match source true/false ratio
  - Enums/categoricals: match source value frequency distribution
- Null injection: match source null rate per column (within 1% tolerance)
- Row count: match source row count exactly

**`masking-engine/app/transformers/distribution_analyzer.py`** — Source Distribution Analysis
- Compute per-column statistics from source dataset:
  - Numeric: min, max, mean, median, stddev, percentiles (25/50/75)
  - String: min_length, max_length, avg_length, charset
  - Categorical: value counts, unique count
  - All types: null_count, null_rate, total_count
- Return statistics object used by synthetic generator
- Statistics computed in DuckDB for efficiency on large datasets

**`masking-engine/app/transformers/distribution_validator.py`** — Distribution Comparison
- Compare synthetic dataset statistics against source statistics
- Tolerance: mean/variance within 5% of source
- Cardinality: synthetic unique count within 10% of source
- Null rate: within 1% of source
- Return pass/fail per column with deviation percentages

### Modifications to Existing Files

**`masking-engine/app/strategy_router.py`** — Add synthetic strategy
- Route `strategy: synthetic` to synthetic generator
- Synthetic requires source statistics as additional input (passed via masking request)

**`masking-engine/requirements.txt`** — Add Faker dependency
- `faker>=20.0`

### Tests to Write

**`masking-engine/tests/test_synthetic.py`**
- Generated names are valid (non-empty strings, no PII from source)
- Generated emails match email format
- Numeric columns: mean within 5% of source
- Null rate matches source within 1%
- Row count matches exactly
- Zero real data from source in output

**`masking-engine/tests/test_distribution_analyzer.py`**
- Correct statistics for known dataset (pre-computed expected values)
- Handle all-null columns gracefully
- Handle single-value columns

**`masking-engine/tests/test_distribution_validator.py`**
- Matching distributions pass validation
- 10% deviation detected and reported
- Edge case: zero-variance column (all same value)

## Acceptance Criteria
1. Synthetic generator produces data using Faker for PII-typed columns
2. Numeric distributions match source mean/variance within 5%
3. Null rates match within 1%
4. Row counts match exactly
5. Zero real source data appears in synthetic output
6. Synthetic data passes the same quality assertions defined in the pipeline
7. Distribution comparison report shows per-column deviation metrics
8. All tests pass: `pytest masking-engine/tests/test_synthetic.py masking-engine/tests/test_distribution_*.py`

## Estimated Complexity
M (Medium — 100-500 lines; 3 modules + Faker integration + distribution analysis)
