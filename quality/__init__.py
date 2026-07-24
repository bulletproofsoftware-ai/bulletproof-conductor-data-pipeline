"""
Conductor Data Pipeline — Quality Assertion Engine.

DuckDB-based quality assertion engine that parses assertion strings from
pipeline YAML, executes them against in-memory datasets, and provides
transform operations (join/filter/derive/aggregate).
"""

from quality.assertion_engine import AssertionEngine, QualityAssertionError
from quality.assertion_parser import parse_assertion, AssertionParseError
from quality.duckdb_executor import DuckDBExecutor
from quality.transform_engine import TransformEngine
from quality.quality_report import AssertionResult, QualityReport

__all__ = [
    "AssertionEngine",
    "QualityAssertionError",
    "parse_assertion",
    "AssertionParseError",
    "DuckDBExecutor",
    "TransformEngine",
    "AssertionResult",
    "QualityReport",
]
