"""
data_profile MCP Tool -- Analyze dataset statistics.

Returns column types, cardinality, null rates, and PII detection flags.
Elevated governance classification.
"""

import logging
import re
import time
from typing import Optional

logger = logging.getLogger(__name__)

# PII detection patterns (regex-based for v1)
_PII_PATTERNS = {
    "EMAIL": re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"),
    "SSN": re.compile(r"^\d{3}-?\d{2}-?\d{4}$"),
    "CREDIT_CARD": re.compile(r"^\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}$"),
    "IP_ADDRESS": re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"),
    "PHONE": re.compile(r"^[\+]?[\d\s\-\(\)]{7,20}$"),
}

# Column name patterns that suggest PII
_PII_NAME_PATTERNS = {
    "PERSON": re.compile(r"(name|first_name|last_name|full_name)", re.IGNORECASE),
    "EMAIL": re.compile(r"(email|e_mail|mail_address)", re.IGNORECASE),
    "PHONE": re.compile(r"(phone|mobile|cell|telephone|fax)", re.IGNORECASE),
    "SSN": re.compile(r"(ssn|social_security|sin|national_id)", re.IGNORECASE),
    "ADDRESS": re.compile(r"(address|street|city|zip|postal|state|country)", re.IGNORECASE),
    "DATE_OF_BIRTH": re.compile(r"(dob|date_of_birth|birthday|birth_date)", re.IGNORECASE),
    "CREDIT_CARD": re.compile(r"(credit_card|card_number|cc_num)", re.IGNORECASE),
}


def _detect_column_type(values: list) -> str:
    """Infer column data type from sample values."""
    non_null = [v for v in values if v is not None]
    if not non_null:
        return "null"

    sample = non_null[0]
    if isinstance(sample, bool):
        return "boolean"
    elif isinstance(sample, int):
        return "integer"
    elif isinstance(sample, float):
        return "float"
    elif isinstance(sample, str):
        # Check if it looks like a date
        if re.match(r"^\d{4}-\d{2}-\d{2}", sample):
            return "date"
        return "string"
    return "unknown"


def _detect_pii_by_value(values: list) -> Optional[str]:
    """Detect PII type by examining sample values."""
    non_null_strings = [str(v) for v in values if v is not None and isinstance(v, str)]
    if not non_null_strings:
        return None

    # Check each PII pattern against a sample of values
    sample = non_null_strings[:10]
    for pii_type, pattern in _PII_PATTERNS.items():
        match_count = sum(1 for v in sample if pattern.match(v))
        if match_count >= len(sample) * 0.5:  # >50% match rate
            return pii_type

    return None


def _detect_pii_by_name(column_name: str) -> Optional[str]:
    """Detect PII type by column name pattern."""
    for pii_type, pattern in _PII_NAME_PATTERNS.items():
        if pattern.search(column_name):
            return pii_type
    return None


def _profile_column(column_name: str, values: list) -> dict:
    """Generate statistics for a single column."""
    total = len(values)
    null_count = sum(1 for v in values if v is None)
    non_null = [v for v in values if v is not None]
    distinct_count = len(set(str(v) for v in non_null)) if non_null else 0

    profile = {
        "name": column_name,
        "type": _detect_column_type(values),
        "total_count": total,
        "null_count": null_count,
        "null_rate": round(null_count / total, 4) if total > 0 else 0.0,
        "distinct_count": distinct_count,
        "cardinality_ratio": round(distinct_count / len(non_null), 4) if non_null else 0.0,
    }

    # PII detection
    pii_by_name = _detect_pii_by_name(column_name)
    pii_by_value = _detect_pii_by_value(values)
    pii_detected = pii_by_name or pii_by_value

    profile["pii_flag"] = pii_detected is not None
    if pii_detected:
        profile["pii_type"] = pii_detected
        profile["pii_detection_method"] = "name_pattern" if pii_by_name else "value_pattern"

    # Numeric statistics
    if profile["type"] in ("integer", "float"):
        numeric_vals = [v for v in non_null if isinstance(v, (int, float))]
        if numeric_vals:
            profile["min"] = min(numeric_vals)
            profile["max"] = max(numeric_vals)
            profile["mean"] = round(sum(numeric_vals) / len(numeric_vals), 4)

    # String length statistics
    if profile["type"] == "string":
        str_vals = [str(v) for v in non_null]
        if str_vals:
            lengths = [len(s) for s in str_vals]
            profile["min_length"] = min(lengths)
            profile["max_length"] = max(lengths)

    return profile


def execute(params: dict) -> dict:
    """
    Profile a dataset: column types, cardinality, null rates, PII detection.

    Args:
        params: Dict with keys:
            - dataset (dict): Dataset as {table_name: [{col: val, ...}]}
            - pipeline_id (str, optional): Pipeline identifier

    Returns:
        Dict with status, data (profile results), and metadata.
    """
    dataset = params.get("dataset", {})
    pipeline_id = params.get("pipeline_id", "unknown")

    start_time = time.monotonic()

    if not dataset:
        return {
            "status": "error",
            "data": {"error_code": "NO_DATASET", "message": "No dataset provided for profiling"},
            "metadata": {"tool": "data_profile", "pipeline_id": pipeline_id},
        }

    table_profiles = {}
    total_pii_flags = 0

    for table_name, rows in dataset.items():
        if not rows:
            table_profiles[table_name] = {"columns": [], "row_count": 0}
            continue

        # Extract column values
        columns = list(rows[0].keys())
        column_profiles = []

        for col_name in columns:
            values = [row.get(col_name) for row in rows]
            profile = _profile_column(col_name, values)
            column_profiles.append(profile)
            if profile.get("pii_flag"):
                total_pii_flags += 1

        table_profiles[table_name] = {
            "columns": column_profiles,
            "row_count": len(rows),
        }

    elapsed = (time.monotonic() - start_time) * 1000

    return {
        "status": "success",
        "data": {
            "tables": table_profiles,
            "total_pii_flags": total_pii_flags,
        },
        "metadata": {
            "tool": "data_profile",
            "pipeline_id": pipeline_id,
            "elapsed_ms": round(elapsed, 2),
        },
    }
