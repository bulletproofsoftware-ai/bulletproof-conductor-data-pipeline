"""
Tests for the data_profile MCP tool.

Validates:
- Returns column statistics
- PII flags included
"""


from tools.data_profile import execute


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_dataset():
    """Standard test dataset."""
    return {
        "customers": [
            {"id": 1, "name": "Alice Smith", "email": "alice@example.com",
             "phone": "+1-555-0101", "tier": "gold", "score": 95.5},
            {"id": 2, "name": "Bob Jones", "email": "bob@example.com",
             "phone": "+1-555-0102", "tier": "silver", "score": 82.0},
            {"id": 3, "name": "Carol White", "email": "carol@example.com",
             "phone": "+1-555-0103", "tier": None, "score": None},
            {"id": 4, "name": "Dave Brown", "email": "dave@example.com",
             "phone": "+1-555-0104", "tier": "gold", "score": 91.2},
            {"id": 5, "name": "Eve Davis", "email": "eve@example.com",
             "phone": "+1-555-0105", "tier": "bronze", "score": 67.8},
        ],
    }


# ---------------------------------------------------------------------------
# Column Statistics Tests
# ---------------------------------------------------------------------------

class TestColumnStatistics:
    """Profile should return correct column-level statistics."""

    def test_returns_all_columns(self):
        result = execute({"dataset": _make_dataset()})
        assert result["status"] == "success"
        columns = result["data"]["tables"]["customers"]["columns"]
        col_names = [c["name"] for c in columns]
        assert "id" in col_names
        assert "name" in col_names
        assert "email" in col_names
        assert "phone" in col_names
        assert "tier" in col_names
        assert "score" in col_names

    def test_row_count(self):
        result = execute({"dataset": _make_dataset()})
        assert result["data"]["tables"]["customers"]["row_count"] == 5

    def test_null_rate_computed(self):
        result = execute({"dataset": _make_dataset()})
        columns = result["data"]["tables"]["customers"]["columns"]
        tier_col = next(c for c in columns if c["name"] == "tier")
        # 1 out of 5 is null
        assert tier_col["null_count"] == 1
        assert tier_col["null_rate"] == 0.2

    def test_cardinality_computed(self):
        result = execute({"dataset": _make_dataset()})
        columns = result["data"]["tables"]["customers"]["columns"]
        id_col = next(c for c in columns if c["name"] == "id")
        # All IDs unique
        assert id_col["distinct_count"] == 5
        assert id_col["cardinality_ratio"] == 1.0

    def test_type_detection(self):
        result = execute({"dataset": _make_dataset()})
        columns = result["data"]["tables"]["customers"]["columns"]
        id_col = next(c for c in columns if c["name"] == "id")
        assert id_col["type"] == "integer"
        name_col = next(c for c in columns if c["name"] == "name")
        assert name_col["type"] == "string"
        score_col = next(c for c in columns if c["name"] == "score")
        assert score_col["type"] == "float"

    def test_numeric_stats(self):
        result = execute({"dataset": _make_dataset()})
        columns = result["data"]["tables"]["customers"]["columns"]
        score_col = next(c for c in columns if c["name"] == "score")
        assert "min" in score_col
        assert "max" in score_col
        assert "mean" in score_col
        assert score_col["min"] == 67.8
        assert score_col["max"] == 95.5


# ---------------------------------------------------------------------------
# PII Detection Tests
# ---------------------------------------------------------------------------

class TestPIIDetection:
    """Profile should flag potential PII columns."""

    def test_email_column_flagged(self):
        result = execute({"dataset": _make_dataset()})
        columns = result["data"]["tables"]["customers"]["columns"]
        email_col = next(c for c in columns if c["name"] == "email")
        assert email_col["pii_flag"] is True
        assert email_col["pii_type"] == "EMAIL"

    def test_phone_column_flagged(self):
        result = execute({"dataset": _make_dataset()})
        columns = result["data"]["tables"]["customers"]["columns"]
        phone_col = next(c for c in columns if c["name"] == "phone")
        assert phone_col["pii_flag"] is True
        assert phone_col["pii_type"] == "PHONE"

    def test_name_column_flagged(self):
        result = execute({"dataset": _make_dataset()})
        columns = result["data"]["tables"]["customers"]["columns"]
        name_col = next(c for c in columns if c["name"] == "name")
        assert name_col["pii_flag"] is True
        assert name_col["pii_type"] == "PERSON"

    def test_non_pii_column_not_flagged(self):
        result = execute({"dataset": _make_dataset()})
        columns = result["data"]["tables"]["customers"]["columns"]
        id_col = next(c for c in columns if c["name"] == "id")
        assert id_col["pii_flag"] is False

    def test_total_pii_flags_counted(self):
        result = execute({"dataset": _make_dataset()})
        assert result["data"]["total_pii_flags"] >= 3  # name, email, phone at minimum

    def test_ssn_value_detection(self):
        """SSN detection by value pattern."""
        dataset = {
            "records": [
                {"id": 1, "tax_id": "123-45-6789"},
                {"id": 2, "tax_id": "987-65-4321"},
                {"id": 3, "tax_id": "111-22-3333"},
            ],
        }
        result = execute({"dataset": dataset})
        columns = result["data"]["tables"]["records"]["columns"]
        tax_col = next(c for c in columns if c["name"] == "tax_id")
        assert tax_col["pii_flag"] is True
        assert tax_col["pii_type"] == "SSN"


# ---------------------------------------------------------------------------
# Error Tests
# ---------------------------------------------------------------------------

class TestProfileErrors:
    """Error conditions should be handled."""

    def test_no_dataset_returns_error(self):
        result = execute({})
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "NO_DATASET"

    def test_empty_dataset_returns_error(self):
        result = execute({"dataset": {}})
        assert result["status"] == "error"
        assert result["data"]["error_code"] == "NO_DATASET"

    def test_empty_table_handled(self):
        result = execute({"dataset": {"empty": []}})
        assert result["status"] == "success"
        assert result["data"]["tables"]["empty"]["row_count"] == 0
