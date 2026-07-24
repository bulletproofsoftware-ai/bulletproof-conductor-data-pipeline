"""
Test suite for Classification Patterns (TODO-010).

Validates PII pattern matching for common column names and correct
non-PII classification per classification-patterns.yaml.
"""

import pytest

from agents import (
    load_classification_patterns,
    get_patterns,
    classify_column,
    classify_columns,
    CLASSIFICATION_PATTERNS_YAML,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def patterns_data():
    """Load raw classification patterns YAML."""
    return load_classification_patterns()


@pytest.fixture
def patterns():
    """Get list of pattern dicts."""
    return get_patterns()


# ===================================================================
# YAML LOADING
# ===================================================================

class TestPatternsLoading:
    """Tests for classification patterns YAML loading."""

    def test_patterns_yaml_exists(self):
        assert CLASSIFICATION_PATTERNS_YAML.exists(), f"Missing: {CLASSIFICATION_PATTERNS_YAML}"

    def test_patterns_data_parses(self, patterns_data):
        assert isinstance(patterns_data, dict)

    def test_has_patterns_key(self, patterns_data):
        assert "patterns" in patterns_data

    def test_has_metadata(self, patterns_data):
        assert "metadata" in patterns_data

    def test_patterns_not_empty(self, patterns):
        assert len(patterns) > 10  # Should have many patterns


# ===================================================================
# EMAIL PATTERN MATCHING
# ===================================================================

class TestEmailPatterns:
    """Tests for email column pattern matching."""

    def test_email_column(self, patterns):
        result = classify_column("customers.email", patterns)
        assert result is not None
        assert result["classification"] == "confidential"
        assert result["pii"] is True
        assert result["pii_type"] == "EMAIL"

    def test_mail_column(self, patterns):
        result = classify_column("users.mail", patterns)
        assert result is not None
        assert result["classification"] == "confidential"
        assert result["pii"] is True
        assert result["pii_type"] == "EMAIL"

    def test_email_any_table(self, patterns):
        result = classify_column("contacts.email", patterns)
        assert result is not None
        assert result["pii_type"] == "EMAIL"


# ===================================================================
# PHONE PATTERN MATCHING
# ===================================================================

class TestPhonePatterns:
    """Tests for phone column pattern matching."""

    def test_phone_column(self, patterns):
        result = classify_column("customers.phone", patterns)
        assert result is not None
        assert result["classification"] == "confidential"
        assert result["pii"] is True
        assert result["pii_type"] == "PHONE"

    def test_mobile_column(self, patterns):
        result = classify_column("customers.mobile", patterns)
        assert result is not None
        assert result["pii_type"] == "PHONE"

    def test_tel_column(self, patterns):
        result = classify_column("contacts.tel", patterns)
        assert result is not None
        assert result["pii_type"] == "PHONE"


# ===================================================================
# SSN PATTERN MATCHING (Restricted tier)
# ===================================================================

class TestSSNPatterns:
    """Tests for SSN column pattern matching -- restricted tier."""

    def test_ssn_column(self, patterns):
        result = classify_column("employees.ssn", patterns)
        assert result is not None
        assert result["classification"] == "restricted"
        assert result["pii"] is True
        assert result["pii_type"] == "SSN"

    def test_social_security_column(self, patterns):
        result = classify_column("hr.social_security_number", patterns)
        assert result is not None
        assert result["classification"] == "restricted"
        assert result["pii_type"] == "SSN"

    def test_social_security_partial(self, patterns):
        result = classify_column("payroll.social_security", patterns)
        assert result is not None
        assert result["classification"] == "restricted"


# ===================================================================
# NAME PATTERN MATCHING
# ===================================================================

class TestNamePatterns:
    """Tests for person name column pattern matching."""

    def test_name_column(self, patterns):
        result = classify_column("customers.name", patterns)
        assert result is not None
        assert result["classification"] == "confidential"
        assert result["pii"] is True
        assert result["pii_type"] == "PERSON"

    def test_first_name_column(self, patterns):
        result = classify_column("users.first_name", patterns)
        assert result is not None
        assert result["pii_type"] == "PERSON"

    def test_last_name_column(self, patterns):
        result = classify_column("users.last_name", patterns)
        assert result is not None
        assert result["pii_type"] == "PERSON"


# ===================================================================
# ADDRESS PATTERN MATCHING
# ===================================================================

class TestAddressPatterns:
    """Tests for address column pattern matching."""

    def test_address_column(self, patterns):
        result = classify_column("customers.address", patterns)
        assert result is not None
        assert result["classification"] == "confidential"
        assert result["pii"] is True
        assert result["pii_type"] == "ADDRESS"

    def test_address_suffix(self, patterns):
        result = classify_column("shipping.address_line1", patterns)
        assert result is not None
        assert result["pii_type"] == "ADDRESS"

    def test_street_column(self, patterns):
        result = classify_column("locations.street", patterns)
        assert result is not None
        assert result["pii_type"] == "ADDRESS"

    def test_street_suffix(self, patterns):
        result = classify_column("billing.street_address", patterns)
        assert result is not None
        assert result["pii_type"] == "ADDRESS"

    def test_city_column(self, patterns):
        result = classify_column("addresses.city", patterns)
        assert result is not None
        assert result["pii_type"] == "ADDRESS"

    def test_zip_column(self, patterns):
        result = classify_column("addresses.zip", patterns)
        assert result is not None
        assert result["pii_type"] == "ADDRESS"

    def test_zip_code_column(self, patterns):
        result = classify_column("addresses.zip_code", patterns)
        assert result is not None
        assert result["pii_type"] == "ADDRESS"


# ===================================================================
# CREDIT CARD PATTERN MATCHING (Restricted tier)
# ===================================================================

class TestCreditCardPatterns:
    """Tests for credit card column pattern matching -- restricted tier."""

    def test_credit_card_column(self, patterns):
        result = classify_column("payments.credit_card", patterns)
        assert result is not None
        assert result["classification"] == "restricted"
        assert result["pii"] is True
        assert result["pii_type"] == "CREDIT_CARD"

    def test_credit_card_number(self, patterns):
        result = classify_column("billing.credit_card_number", patterns)
        assert result is not None
        assert result["classification"] == "restricted"
        assert result["pii_type"] == "CREDIT_CARD"

    def test_card_number_column(self, patterns):
        result = classify_column("transactions.card_number", patterns)
        assert result is not None
        assert result["classification"] == "restricted"
        assert result["pii_type"] == "CREDIT_CARD"


# ===================================================================
# DATE OF BIRTH PATTERN MATCHING
# ===================================================================

class TestDOBPatterns:
    """Tests for date of birth column pattern matching."""

    def test_dob_column(self, patterns):
        result = classify_column("patients.dob", patterns)
        assert result is not None
        assert result["classification"] == "confidential"
        assert result["pii"] is True
        assert result["pii_type"] == "DATE_OF_BIRTH"

    def test_birth_date_column(self, patterns):
        result = classify_column("members.birth_date", patterns)
        assert result is not None
        assert result["pii_type"] == "DATE_OF_BIRTH"

    def test_birthday_column(self, patterns):
        result = classify_column("users.birthday", patterns)
        assert result is not None
        assert result["pii_type"] == "DATE_OF_BIRTH"


# ===================================================================
# NON-PII PATTERNS -- INTERNAL TIER
# ===================================================================

class TestInternalPatterns:
    """Tests for non-PII internal tier pattern matching."""

    def test_id_column(self, patterns):
        result = classify_column("customers.id", patterns)
        assert result is not None
        assert result["classification"] == "internal"
        assert result["pii"] is False

    def test_key_column(self, patterns):
        result = classify_column("sessions.key", patterns)
        assert result is not None
        assert result["classification"] == "internal"
        assert result["pii"] is False

    def test_foreign_key_column(self, patterns):
        result = classify_column("orders.customer_id", patterns)
        assert result is not None
        assert result["classification"] == "internal"
        assert result["pii"] is False

    def test_created_at_column(self, patterns):
        result = classify_column("users.created_at", patterns)
        assert result is not None
        assert result["classification"] == "internal"
        assert result["pii"] is False

    def test_updated_at_column(self, patterns):
        result = classify_column("orders.updated_at", patterns)
        assert result is not None
        assert result["classification"] == "internal"
        assert result["pii"] is False

    def test_timestamp_column(self, patterns):
        result = classify_column("events.timestamp", patterns)
        assert result is not None
        assert result["classification"] == "internal"
        assert result["pii"] is False


# ===================================================================
# NON-PII PATTERNS -- PUBLIC TIER
# ===================================================================

class TestPublicPatterns:
    """Tests for non-PII public tier pattern matching."""

    def test_status_column(self, patterns):
        result = classify_column("orders.status", patterns)
        assert result is not None
        assert result["classification"] == "public"
        assert result["pii"] is False

    def test_type_column(self, patterns):
        result = classify_column("products.type", patterns)
        assert result is not None
        assert result["classification"] == "public"
        assert result["pii"] is False

    def test_category_column(self, patterns):
        result = classify_column("items.category", patterns)
        assert result is not None
        assert result["classification"] == "public"
        assert result["pii"] is False


# ===================================================================
# UNMATCHED COLUMNS
# ===================================================================

class TestUnmatchedColumns:
    """Tests for columns that don't match any pattern."""

    def test_unmatched_returns_none(self, patterns):
        result = classify_column("orders.quantity", patterns)
        assert result is None

    def test_unmatched_unusual_name(self, patterns):
        result = classify_column("analytics.session_duration", patterns)
        assert result is None

    def test_unmatched_custom_column(self, patterns):
        result = classify_column("metrics.p99_latency", patterns)
        assert result is None


# ===================================================================
# BATCH CLASSIFICATION
# ===================================================================

class TestBatchClassification:
    """Tests for classify_columns (batch operation)."""

    def test_classify_multiple_columns(self, patterns):
        columns = [
            "customers.email",
            "customers.id",
            "customers.name",
            "orders.status",
            "orders.quantity",
        ]
        results = classify_columns(columns, patterns)
        assert len(results) == 5
        assert results["customers.email"]["pii"] is True
        assert results["customers.id"]["classification"] == "internal"
        assert results["customers.name"]["pii_type"] == "PERSON"
        assert results["orders.status"]["classification"] == "public"
        assert results["orders.quantity"] is None  # no match

    def test_empty_column_list(self, patterns):
        results = classify_columns([], patterns)
        assert results == {}

    def test_all_pii_columns(self, patterns):
        columns = [
            "users.email",
            "users.phone",
            "users.ssn",
            "users.name",
            "users.address",
        ]
        results = classify_columns(columns, patterns)
        for col, result in results.items():
            assert result is not None, f"{col} should match a pattern"
            assert result["pii"] is True, f"{col} should be PII"


# ===================================================================
# CLASSIFICATION TIER DISTRIBUTION
# ===================================================================

class TestClassificationTiers:
    """Tests for correct tier distribution across patterns."""

    def test_restricted_tier_patterns_exist(self, patterns):
        restricted = [p for p in patterns if p["classification"] == "restricted"]
        assert len(restricted) >= 3  # ssn, social_security*, credit_card*, card_number*

    def test_confidential_tier_patterns_exist(self, patterns):
        confidential = [p for p in patterns if p["classification"] == "confidential"]
        assert len(confidential) >= 10  # email, mail, phone, mobile, tel, name, first_name, last_name, address*, etc.

    def test_internal_tier_patterns_exist(self, patterns):
        internal = [p for p in patterns if p["classification"] == "internal"]
        assert len(internal) >= 5  # id, key, *_id, created_at, updated_at, timestamp

    def test_public_tier_patterns_exist(self, patterns):
        public = [p for p in patterns if p["classification"] == "public"]
        assert len(public) >= 3  # status, type, category

    def test_all_classifications_valid(self, patterns):
        valid_tiers = {"public", "internal", "confidential", "restricted"}
        for p in patterns:
            assert p["classification"] in valid_tiers, \
                f"Pattern '{p['pattern']}' has invalid classification: {p['classification']}"

    def test_all_pii_have_pii_type(self, patterns):
        """All patterns with pii=true should have a pii_type."""
        for p in patterns:
            if p["pii"]:
                assert "pii_type" in p, f"PII pattern '{p['pattern']}' missing pii_type"

    def test_non_pii_no_pii_type(self, patterns):
        """Patterns with pii=false should not have pii_type."""
        for p in patterns:
            if not p["pii"]:
                assert "pii_type" not in p, \
                    f"Non-PII pattern '{p['pattern']}' should not have pii_type"


# ===================================================================
# METADATA TESTS
# ===================================================================

class TestMetadata:
    """Tests for classification patterns metadata."""

    def test_metadata_version(self, patterns_data):
        assert patterns_data["metadata"]["version"] == 1

    def test_metadata_has_note(self, patterns_data):
        note = patterns_data["metadata"]["note"]
        assert "suggestion" in note.lower()

    def test_metadata_classification_tiers(self, patterns_data):
        tiers = patterns_data["metadata"]["classification_tiers"]
        assert tiers == ["public", "internal", "confidential", "restricted"]


# ===================================================================
# CASE SENSITIVITY
# ===================================================================

class TestCaseSensitivity:
    """Tests for case-insensitive pattern matching."""

    def test_uppercase_column_matches(self, patterns):
        result = classify_column("CUSTOMERS.EMAIL", patterns)
        assert result is not None
        assert result["pii_type"] == "EMAIL"

    def test_mixed_case_column_matches(self, patterns):
        result = classify_column("Users.Phone", patterns)
        assert result is not None
        assert result["pii_type"] == "PHONE"
