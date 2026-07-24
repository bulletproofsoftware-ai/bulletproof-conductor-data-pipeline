"""
Tests for contracts/schema_drift_detector.py -- Schema Drift Detection.

Validates:
- New column in source: warning, column excluded
- Missing column from source: SCHEMA_DRIFT error
- Type change: SCHEMA_DRIFT error
- No drift: clean pass
"""

import pytest

from contracts.schema_drift_detector import SchemaDriftDetector, SCHEMA_DRIFT


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def detector():
    return SchemaDriftDetector()


def _source_schema():
    """Source schema with standard columns."""
    return {
        "customers.id": {"type": "INTEGER"},
        "customers.name": {"type": "VARCHAR"},
        "customers.email": {"type": "VARCHAR"},
    }


def _contract_columns():
    """Contract columns matching the source schema."""
    return {
        "customers.id": {"classification": "internal", "pii": False, "source_type": "INTEGER"},
        "customers.name": {"classification": "confidential", "pii": True, "source_type": "VARCHAR"},
        "customers.email": {"classification": "confidential", "pii": True, "source_type": "VARCHAR"},
    }


# ---------------------------------------------------------------------------
# No Drift Tests
# ---------------------------------------------------------------------------

class TestNoDrift:
    """When source and contract match, no drift should be reported."""

    def test_matching_schemas_clean_pass(self, detector):
        report = detector.detect(
            source_schema=_source_schema(),
            contract_columns=_contract_columns(),
        )
        assert report.has_drift is False
        assert report.added_columns == []
        assert report.removed_columns == []
        assert report.type_changes == []
        assert report.errors == []
        assert report.warnings == []

    def test_no_breaking_drift(self, detector):
        report = detector.detect(
            source_schema=_source_schema(),
            contract_columns=_contract_columns(),
        )
        assert report.has_breaking_drift is False


# ---------------------------------------------------------------------------
# New Column in Source Tests (Warning, Not Extracted)
# ---------------------------------------------------------------------------

class TestNewColumnInSource:
    """New columns in source should produce warnings but not errors."""

    def test_new_column_produces_warning(self, detector):
        source = _source_schema()
        source["customers.phone"] = {"type": "VARCHAR"}

        report = detector.detect(
            source_schema=source,
            contract_columns=_contract_columns(),
        )
        assert report.has_drift is True
        assert len(report.added_columns) == 1
        assert report.added_columns[0].column == "customers.phone"
        assert report.added_columns[0].drift_type == "added"
        assert len(report.warnings) == 1
        assert "customers.phone" in report.warnings[0]

    def test_new_column_not_in_errors(self, detector):
        """New columns should NOT produce errors -- only warnings."""
        source = _source_schema()
        source["customers.phone"] = {"type": "VARCHAR"}

        report = detector.detect(
            source_schema=source,
            contract_columns=_contract_columns(),
        )
        assert report.errors == []
        assert report.has_breaking_drift is False

    def test_multiple_new_columns(self, detector):
        source = _source_schema()
        source["customers.phone"] = {"type": "VARCHAR"}
        source["customers.address"] = {"type": "TEXT"}

        report = detector.detect(
            source_schema=source,
            contract_columns=_contract_columns(),
        )
        assert len(report.added_columns) == 2
        assert len(report.warnings) == 2
        added_names = {d.column for d in report.added_columns}
        assert "customers.phone" in added_names
        assert "customers.address" in added_names


# ---------------------------------------------------------------------------
# Missing Column from Source Tests (SCHEMA_DRIFT Error)
# ---------------------------------------------------------------------------

class TestMissingColumn:
    """Columns in contract but missing from source produce SCHEMA_DRIFT errors."""

    def test_missing_column_produces_error(self, detector):
        source = _source_schema()
        del source["customers.email"]

        report = detector.detect(
            source_schema=source,
            contract_columns=_contract_columns(),
        )
        assert report.has_drift is True
        assert report.has_breaking_drift is True
        assert len(report.removed_columns) == 1
        assert report.removed_columns[0].column == "customers.email"
        assert report.removed_columns[0].drift_type == "removed"

    def test_missing_column_error_code(self, detector):
        source = _source_schema()
        del source["customers.email"]

        report = detector.detect(
            source_schema=source,
            contract_columns=_contract_columns(),
        )
        assert len(report.errors) == 1
        assert report.errors[0]["error_code"] == SCHEMA_DRIFT

    def test_multiple_missing_columns(self, detector):
        source = {"customers.id": {"type": "INTEGER"}}
        # Only id left; name and email are missing

        report = detector.detect(
            source_schema=source,
            contract_columns=_contract_columns(),
        )
        assert len(report.removed_columns) == 2
        assert len(report.errors) == 2
        removed_names = {d.column for d in report.removed_columns}
        assert "customers.name" in removed_names
        assert "customers.email" in removed_names

    def test_missing_column_has_detail_message(self, detector):
        source = _source_schema()
        del source["customers.name"]

        report = detector.detect(
            source_schema=source,
            contract_columns=_contract_columns(),
            table_name="customers",
        )
        assert "customers.name" in report.removed_columns[0].detail
        assert "missing" in report.removed_columns[0].detail.lower()


# ---------------------------------------------------------------------------
# Type Change Tests (SCHEMA_DRIFT Error)
# ---------------------------------------------------------------------------

class TestTypeChange:
    """Type changes between source and contract produce SCHEMA_DRIFT errors."""

    def test_type_change_produces_error(self, detector):
        source = _source_schema()
        source["customers.id"]["type"] = "BIGINT"  # Was INTEGER

        report = detector.detect(
            source_schema=source,
            contract_columns=_contract_columns(),
        )
        assert report.has_drift is True
        assert report.has_breaking_drift is True
        assert len(report.type_changes) == 1
        assert report.type_changes[0].column == "customers.id"
        assert report.type_changes[0].source_type == "BIGINT"
        assert report.type_changes[0].contract_type == "INTEGER"

    def test_type_change_error_code(self, detector):
        source = _source_schema()
        source["customers.id"]["type"] = "BIGINT"

        report = detector.detect(
            source_schema=source,
            contract_columns=_contract_columns(),
        )
        assert len(report.errors) == 1
        assert report.errors[0]["error_code"] == SCHEMA_DRIFT

    def test_no_type_info_no_error(self, detector):
        """If source has no type info, no type change error should be raised."""
        source = {
            "customers.id": {},
            "customers.name": {},
            "customers.email": {},
        }
        contract = {
            "customers.id": {"classification": "internal", "pii": False},
            "customers.name": {"classification": "confidential", "pii": True},
            "customers.email": {"classification": "confidential", "pii": True},
        }
        report = detector.detect(source_schema=source, contract_columns=contract)
        assert report.type_changes == []
        assert report.errors == []

    def test_mixed_drift(self, detector):
        """Combination of new columns, missing columns, and type changes."""
        source = _source_schema()
        source["customers.id"]["type"] = "BIGINT"  # type change
        source["customers.phone"] = {"type": "VARCHAR"}  # new column
        del source["customers.email"]  # removed column

        report = detector.detect(
            source_schema=source,
            contract_columns=_contract_columns(),
        )
        assert report.has_drift is True
        assert report.has_breaking_drift is True
        assert len(report.added_columns) == 1
        assert len(report.removed_columns) == 1
        assert len(report.type_changes) == 1
        # 2 errors: removed + type change (added is only a warning)
        assert len(report.errors) == 2
        assert len(report.warnings) == 1
