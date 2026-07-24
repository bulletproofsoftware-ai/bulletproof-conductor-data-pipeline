"""Tests for post-mask PII validation.

Covers:
- Clean masked data passes PII scan
- Unmasked name in Confidential column detected
- Properly tokenized values pass (not flagged as PII)
- Redacted columns with only [REDACTED] pass
- Mixed scenarios and edge cases
"""

import pytest

from gates.pii_validator import PIIValidator
from masking_engine.app.ner.presidio_client import MockPresidioClient


@pytest.fixture
def mock_client() -> MockPresidioClient:
    """Mock Presidio client."""
    return MockPresidioClient()


@pytest.fixture
def validator(mock_client: MockPresidioClient) -> PIIValidator:
    """PIIValidator with mock Presidio client and small sample size."""
    return PIIValidator(
        presidio_client=mock_client,
        sample_size=100,
        confidence_threshold=0.70,
    )


class TestCleanMaskedData:
    """Test that properly masked data passes PII scan."""

    def test_tokenized_values_pass(self, validator: PIIValidator) -> None:
        """Tokenized values with proper format should not trigger violations."""
        masked_dataset = {
            "customers": [
                {"name": "NAME_a1b2c3", "email": "EMAIL_x9y8z7"},
                {"name": "NAME_d4e5f6", "email": "EMAIL_w6v5u4"},
                {"name": "NAME_g7h8i9", "email": "EMAIL_t3s2r1"},
            ]
        }
        classifications = {
            "customers.name": "confidential",
            "customers.email": "confidential",
        }
        strategy_map = {
            "customers.name": "tokenize",
            "customers.email": "tokenize",
        }

        result = validator.validate(masked_dataset, classifications, strategy_map)

        assert result.passed is True
        assert result.violations == 0
        assert result.tables_scanned == 1
        assert result.columns_scanned == 2

    def test_redacted_values_pass(self, validator: PIIValidator) -> None:
        """Redacted columns with only [REDACTED] or NULL should pass."""
        masked_dataset = {
            "customers": [
                {"ssn": "[REDACTED]", "name": "NAME_a1"},
                {"ssn": None, "name": "NAME_b2"},
                {"ssn": "[REDACTED]", "name": "NAME_c3"},
            ]
        }
        classifications = {
            "customers.ssn": "restricted",
            "customers.name": "confidential",
        }
        strategy_map = {
            "customers.ssn": "redact",
            "customers.name": "tokenize",
        }

        result = validator.validate(masked_dataset, classifications, strategy_map)

        assert result.passed is True
        assert result.violations == 0

    def test_empty_dataset_passes(self, validator: PIIValidator) -> None:
        """Empty dataset should pass trivially."""
        result = validator.validate({}, {}, {})
        assert result.passed is True
        assert result.tables_scanned == 0

    def test_empty_table_passes(self, validator: PIIValidator) -> None:
        """Table with no rows should be skipped."""
        result = validator.validate(
            {"customers": []},
            {"customers.name": "confidential"},
            {"customers.name": "tokenize"},
        )
        assert result.passed is True
        assert result.tables_scanned == 0


class TestUnmaskedPIIDetection:
    """Test that unmasked PII is detected as violations."""

    def test_unmasked_name_detected(self, validator: PIIValidator) -> None:
        """A known name in a Confidential column should be detected."""
        masked_dataset = {
            "customers": [
                {"name": "John Doe", "email": "EMAIL_x9y8z7"},
                {"name": "NAME_d4e5f6", "email": "EMAIL_w6v5u4"},
            ]
        }
        classifications = {
            "customers.name": "confidential",
            "customers.email": "confidential",
        }
        strategy_map = {
            "customers.name": "tokenize",
            "customers.email": "tokenize",
        }

        result = validator.validate(masked_dataset, classifications, strategy_map)

        assert result.passed is False
        assert result.violations >= 1

        # Find the name column result
        name_result = next(
            (cr for cr in result.column_results if cr.column == "name"),
            None,
        )
        assert name_result is not None
        assert name_result.status == "violation"
        assert "PERSON" in name_result.violating_entity_types

    def test_unmasked_email_detected(self, validator: PIIValidator) -> None:
        """A real email address in a Confidential column should be detected."""
        masked_dataset = {
            "users": [
                {"email": "john@example.com", "phone": "PHONE_abc"},
            ]
        }
        classifications = {
            "users.email": "confidential",
            "users.phone": "confidential",
        }
        strategy_map = {
            "users.email": "fpe",
            "users.phone": "tokenize",
        }

        result = validator.validate(masked_dataset, classifications, strategy_map)

        assert result.passed is False
        email_result = next(
            (cr for cr in result.column_results if cr.column == "email"),
            None,
        )
        assert email_result is not None
        assert email_result.status == "violation"
        assert "EMAIL" in email_result.violating_entity_types

    def test_invalid_redaction_detected(self, validator: PIIValidator) -> None:
        """A value that should be redacted but isn't should fail."""
        masked_dataset = {
            "customers": [
                {"ssn": "123-45-6789"},  # Should be [REDACTED] or None
            ]
        }
        classifications = {
            "customers.ssn": "restricted",
        }
        strategy_map = {
            "customers.ssn": "redact",
        }

        result = validator.validate(masked_dataset, classifications, strategy_map)

        assert result.passed is False
        ssn_result = next(
            (cr for cr in result.column_results if cr.column == "ssn"),
            None,
        )
        assert ssn_result is not None
        assert ssn_result.status == "violation"


class TestSampling:
    """Test that sampling works correctly."""

    def test_samples_up_to_100_rows(self, mock_client: MockPresidioClient) -> None:
        """Validator should sample at most 100 rows from a large table."""
        validator = PIIValidator(
            presidio_client=mock_client,
            sample_size=100,
        )

        # Create a dataset with 500 rows, all properly masked
        rows = [{"name": f"NAME_row{i}"} for i in range(500)]
        masked_dataset = {"customers": rows}
        classifications = {"customers.name": "confidential"}
        strategy_map = {"customers.name": "tokenize"}

        result = validator.validate(masked_dataset, classifications, strategy_map)

        # Should have sampled exactly 100 rows
        assert result.total_rows_sampled == 100
        assert result.passed is True

    def test_small_table_scans_all(self, mock_client: MockPresidioClient) -> None:
        """Tables smaller than sample size should be fully scanned."""
        validator = PIIValidator(
            presidio_client=mock_client,
            sample_size=100,
        )

        rows = [{"name": f"NAME_row{i}"} for i in range(10)]
        masked_dataset = {"customers": rows}
        classifications = {"customers.name": "confidential"}
        strategy_map = {"customers.name": "tokenize"}

        result = validator.validate(masked_dataset, classifications, strategy_map)

        assert result.total_rows_sampled == 10


class TestClassificationFiltering:
    """Test that only Confidential/Restricted columns are scanned."""

    def test_internal_columns_not_scanned(self, validator: PIIValidator) -> None:
        """Internal classification columns should not be scanned."""
        masked_dataset = {
            "customers": [
                {"name": "John Doe", "notes": "Internal notes here"},
            ]
        }
        # name is confidential (will be scanned), notes is internal (skipped)
        classifications = {
            "customers.name": "confidential",
            "customers.notes": "internal",
        }
        strategy_map = {
            "customers.name": "tokenize",
            "customers.notes": "passthrough",
        }

        result = validator.validate(masked_dataset, classifications, strategy_map)

        # Only name should be scanned (1 column)
        assert result.columns_scanned == 1

    def test_public_columns_not_scanned(self, validator: PIIValidator) -> None:
        """Public classification columns should not be scanned."""
        masked_dataset = {
            "products": [
                {"description": "A great product", "price": "29.99"},
            ]
        }
        classifications = {
            "products.description": "public",
            "products.price": "public",
        }
        strategy_map = {
            "products.description": "passthrough",
            "products.price": "passthrough",
        }

        result = validator.validate(masked_dataset, classifications, strategy_map)

        assert result.columns_scanned == 0
        assert result.passed is True


class TestScanResultSerialization:
    """Test PIIScanResult serialization."""

    def test_to_dict(self, validator: PIIValidator) -> None:
        masked_dataset = {
            "customers": [{"name": "NAME_a1b2c3"}]
        }
        classifications = {"customers.name": "confidential"}
        strategy_map = {"customers.name": "tokenize"}

        result = validator.validate(masked_dataset, classifications, strategy_map)
        d = result.to_dict()

        assert "tables_scanned" in d
        assert "columns_scanned" in d
        assert "total_rows_sampled" in d
        assert "violations" in d
        assert "passed" in d
        assert "column_results" in d
        assert isinstance(d["column_results"], list)
