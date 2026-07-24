# Security Scan Report: conductor-data-pipeline

**Scan ID:** `e92070dc-0f9f-4024-9c89-ef0f498bddd7`
**Date:** 2026-03-18T17:40:23.515Z
**Score:** 1000/1000 (excellent)
**Branch:** main | **Commit:** `N/A`
**Profile:** comprehensive

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 0 |
| Medium | 0 |
| Low | 0 |
| Info | 0 |
| **Total** | **0** |

## Scanners Executed

| Scanner | Status | Findings | Duration |
|---------|--------|----------|----------|
| opengrep | pass | 38 | 8.9s |
| bandit | pass | 2121 | 2.0s |
| gosec | pass | 0 | 0.0s |
| eslint-security | pass | 0 | 0.2s |
| pmd | pass | 0 | 1.8s |
| nuclei | skipped | 0 | 0.0s |
| zap | skipped | 0 | 0.0s |
| trivy | pass | 0 | 1.4s |
| grype | pass | 0 | 0.7s |
| gitleaks | pass | 0 | 0.0s |
| checkov | pass | 0 | 1.2s |
| newman | skipped | 0 | 0.0s |
| restler | skipped | 0 | 0.0s |
| schemathesis | skipped | 0 | 0.0s |
| keploy | pass | 134 | 0.0s |
| syft | pass | 0 | 1.4s |
| cosign | skipped | 0 | 0.0s |
| dockle | pass | 0 | 0.0s |
| opa | skipped | 0 | 0.0s |
| conftest | skipped | 0 | 0.0s |
| package-validator | skipped | 0 | 0.0s |
| scancode | pass | 0 | 0.4s |
| stryker | skipped | 0 | 0.0s |
| mutmut | skipped | 0 | 0.0s |
| pitest | skipped | 0 | 0.0s |
| deepeval | pass | 296 | 0.1s |
| jest | skipped | 0 | 0.0s |
| pytest | pass | 45 | 2.2s |
| aflpp | skipped | 0 | 0.0s |
| threatmodel | pass | 1 | 0.1s |
| knip | skipped | 0 | 0.0s |
| oxlint | skipped | 0 | 0.0s |
| jscpd | pass | 51 | 1.6s |
| ruff | pass | 0 | 0.0s |
| phpstan | skipped | 0 | 0.0s |
| typos | pass | 0 | 0.0s |
| libyear | skipped | 0 | 0.0s |
| vale | pass | 0 | 0.0s |
| actionlint | skipped | 0 | 0.0s |
| poutine | skipped | 0 | 0.0s |
| scorecard | pass | 6 | 0.5s |
| kubeconform | skipped | 0 | 0.0s |
| kube-linter | skipped | 0 | 0.0s |
| cargo-audit | skipped | 0 | 0.0s |
| spectral | skipped | 0 | 0.0s |
| dotenv-linter | skipped | 0 | 0.0s |
| license-finder | skipped | 0 | 0.0s |
| cdxgen | pass | 0 | 0.0s |
| selenium-gen | pass | 2 | 0.2s |
| _file_inventory | pass | 0 | 0.0s |

## High Findings (204)

### [HIGH] Using outdated libraries with known security issues.

- **Scanner:** scorecard
- **Rule:** `SCORECARD-TOKEN-PERMISSIONS`
- **OWASP:** A06:2021-Vulnerable and Outdated Components

**What's wrong:** No tokens found

**How to fix:** Improve the Token-Permissions score. See: https://github.com/ossf/scorecard/blob/ea7e27ed41b76ab879c862fa0ca4cc9c61764ee4/docs/checks.md#token-permissions

**Action:** Address this issue as soon as possible.

---

### [HIGH] Using outdated libraries with known security issues.

- **Scanner:** scorecard
- **Rule:** `SCORECARD-PINNED-DEPENDENCIES`
- **OWASP:** A06:2021-Vulnerable and Outdated Components

**What's wrong:** dependency not pinned by hash detected -- score normalized to 0

**How to fix:** Improve the Pinned-Dependencies score. See: https://github.com/ossf/scorecard/blob/ea7e27ed41b76ab879c862fa0ca4cc9c61764ee4/docs/checks.md#pinned-dependencies

**Action:** Address this issue as soon as possible.

---

### [HIGH] Using outdated libraries with known security issues.

- **Scanner:** scorecard
- **Rule:** `SCORECARD-DEPENDENCY-UPDATE-TOOL`
- **OWASP:** A06:2021-Vulnerable and Outdated Components

**What's wrong:** no update tool detected

**How to fix:** Improve the Dependency-Update-Tool score. See: https://github.com/ossf/scorecard/blob/ea7e27ed41b76ab879c862fa0ca4cc9c61764ee4/docs/checks.md#dependency-update-tool

**Action:** Address this issue as soon as possible.

---

### [HIGH] Using outdated libraries with known security issues.

- **Scanner:** scorecard
- **Rule:** `SCORECARD-DANGEROUS-WORKFLOW`
- **OWASP:** A06:2021-Vulnerable and Outdated Components

**What's wrong:** no workflows found

**How to fix:** Improve the Dangerous-Workflow score. See: https://github.com/ossf/scorecard/blob/ea7e27ed41b76ab879c862fa0ca4cc9c61764ee4/docs/checks.md#dangerous-workflow

**Action:** Address this issue as soon as possible.

---

### [HIGH] Using outdated libraries with known security issues.

- **Scanner:** scorecard
- **Rule:** `SCORECARD-BINARY-ARTIFACTS`
- **OWASP:** A06:2021-Vulnerable and Outdated Components

**What's wrong:** binaries present in source code

**How to fix:** Improve the Binary-Artifacts score. See: https://github.com/ossf/scorecard/blob/ea7e27ed41b76ab879c862fa0ca4cc9c61764ee4/docs/checks.md#binary-artifacts

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_workflow_phases.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_workflow_phases.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_workflow_phases'

- **File:** `tests/test_workflow_phases.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_workflow_phases.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_workflow_phases.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_workflow_phases'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_workflow_phases.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__ini
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_transform_engine.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_transform_engine.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_transform_engine'

- **File:** `tests/test_transform_engine.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_transform_engine.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_transform_engine.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_transform_engine'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_transform_engine.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__in
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_tool_registry.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_tool_registry.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_tool_registry'

- **File:** `tests/test_tool_registry.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_tool_registry.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_tool_registry.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_tool_registry'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_tool_registry.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init_
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_steward_gate.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_steward_gate.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_steward_gate'

- **File:** `tests/test_steward_gate.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_steward_gate.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_steward_gate.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_steward_gate'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_steward_gate.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_schemas.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_schemas.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_schemas'

- **File:** `tests/test_schemas.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_schemas.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_schemas.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_schemas'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_schemas.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:9
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_schema_drift_detector.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_schema_drift_detector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_schema_drift_detector'

- **File:** `tests/test_schema_drift_detector.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_schema_drift_detector.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_schema_drift_detector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_schema_drift_detector'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_schema_drift_detector.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_quality_report.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_quality_report.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_quality_report'

- **File:** `tests/test_quality_report.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_quality_report.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_quality_report.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_quality_report'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_quality_report.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_qdrant_writer.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_qdrant_writer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_qdrant_writer'

- **File:** `tests/test_qdrant_writer.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_qdrant_writer.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_qdrant_writer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_qdrant_writer'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_qdrant_writer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init_
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_post_data_pipeline_gate.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_post_data_pipeline_gate.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_post_data_pipeline_gate'

- **File:** `tests/test_post_data_pipeline_gate.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_post_data_pipeline_gate.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_post_data_pipeline_gate.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_post_data_pipeline_gate'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_post_data_pipeline_gate.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importl
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_pii_validator.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_pii_validator.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_pii_validator'

- **File:** `tests/test_pii_validator.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_pii_validator.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_pii_validator.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_pii_validator'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_pii_validator.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init_
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_pg_writer.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_pg_writer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_pg_writer'

- **File:** `tests/test_pg_writer.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_pg_writer.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_pg_writer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_pg_writer'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_pg_writer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_otel_emitter.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_otel_emitter.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_otel_emitter'

- **File:** `tests/test_otel_emitter.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_otel_emitter.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_otel_emitter.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_otel_emitter'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_otel_emitter.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_lineage_query.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_lineage_query.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_lineage_query'

- **File:** `tests/test_lineage_query.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_lineage_query.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_lineage_query.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_lineage_query'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_lineage_query.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init_
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_lineage_emitter.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_lineage_emitter.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_lineage_emitter'

- **File:** `tests/test_lineage_emitter.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_lineage_emitter.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_lineage_emitter.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_lineage_emitter'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_lineage_emitter.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__ini
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_key_rotation.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_key_rotation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_key_rotation'

- **File:** `tests/test_key_rotation.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_key_rotation.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_key_rotation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_key_rotation'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_key_rotation.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_human_approval.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_human_approval.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_human_approval'

- **File:** `tests/test_human_approval.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_human_approval.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_human_approval.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_human_approval'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_human_approval.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_handoff_protocol.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_handoff_protocol.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_handoff_protocol'

- **File:** `tests/test_handoff_protocol.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_handoff_protocol.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_handoff_protocol.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_handoff_protocol'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_handoff_protocol.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__in
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_gdpr_article30.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_gdpr_article30.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_gdpr_article30'

- **File:** `tests/test_gdpr_article30.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_gdpr_article30.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_gdpr_article30.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_gdpr_article30'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_gdpr_article30.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_duckdb_executor.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_duckdb_executor.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_duckdb_executor'

- **File:** `tests/test_duckdb_executor.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_duckdb_executor.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_duckdb_executor.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_duckdb_executor'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_duckdb_executor.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__ini
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_docker_compose.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_docker_compose.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_docker_compose'

- **File:** `tests/test_docker_compose.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_docker_compose.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_docker_compose.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_docker_compose'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_docker_compose.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_data_transform.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_transform.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_transform'

- **File:** `tests/test_data_transform.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_data_transform.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_transform.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_transform'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_data_transform.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_data_profile.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_profile.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_profile'

- **File:** `tests/test_data_profile.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_data_profile.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_profile.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_profile'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_data_profile.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_data_mask.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_mask.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_mask'

- **File:** `tests/test_data_mask.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_data_mask.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_mask.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_mask'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_data_mask.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_data_load.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_load.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_load'

- **File:** `tests/test_data_load.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_data_load.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_load.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_load'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_data_load.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_data_lineage_query_tool.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_lineage_query_tool.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_lineage_query_tool'

- **File:** `tests/test_data_lineage_query_tool.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_data_lineage_query_tool.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_lineage_query_tool.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_lineage_query_tool'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_data_lineage_query_tool.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importl
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_data_extract.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_extract.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_extract'

- **File:** `tests/test_data_extract.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_data_extract.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_extract.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_extract'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_data_extract.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_data_contract_validate.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_contract_validate.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_contract_validate'

- **File:** `tests/test_data_contract_validate.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_data_contract_validate.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_contract_validate.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_contract_validate'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_data_contract_validate.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importli
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_data_connect.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_connect.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_connect'

- **File:** `tests/test_data_connect.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_data_connect.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_data_connect.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_data_connect'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_data_connect.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_credential_resolver.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_credential_resolver.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_credential_resolver'

- **File:** `tests/test_credential_resolver.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_credential_resolver.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_credential_resolver.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_credential_resolver'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_credential_resolver.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/_
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_contract_validator.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_contract_validator.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_contract_validator'

- **File:** `tests/test_contract_validator.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_contract_validator.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_contract_validator.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_contract_validator'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_contract_validator.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_contract_manager.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_contract_manager.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_contract_manager'

- **File:** `tests/test_contract_manager.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_contract_manager.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_contract_manager.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_contract_manager'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_contract_manager.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__in
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_classification_patterns.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_classification_patterns.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_classification_patterns'

- **File:** `tests/test_classification_patterns.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_classification_patterns.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_classification_patterns.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_classification_patterns'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_classification_patterns.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importl
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_assertion_parser.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_assertion_parser.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_assertion_parser'

- **File:** `tests/test_assertion_parser.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_assertion_parser.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_assertion_parser.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_assertion_parser'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_assertion_parser.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__in
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_assertion_engine.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_assertion_engine.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_assertion_engine'

- **File:** `tests/test_assertion_engine.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_assertion_engine.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_assertion_engine.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_assertion_engine'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_assertion_engine.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__in
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_artifact_integrity.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_artifact_integrity.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_artifact_integrity'

- **File:** `tests/test_artifact_integrity.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_artifact_integrity.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_artifact_integrity.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_artifact_integrity'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_artifact_integrity.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/test_agent_definitions.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_agent_definitions.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_agent_definitions'

- **File:** `tests/test_agent_definitions.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/test_agent_definitions.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/tests/test_agent_definitions.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
E   ModuleNotFoundError: No module named 'tests.test_agent_definitions'

**Code:**
```python
ImportError while importing test module '/scan-target/tests/test_agent_definitions.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__i
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from tests/integration. This usually indicates a syntax error or import failure.

/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen importlib._bootstrap>:1387: in _gcd_import
    ???
<frozen importlib._bootstrap>:1360: in _find_and_load
    ???
<frozen importlib._bootstrap>:1310: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:488: in _call_with_frames_removed
    ???
<frozen importlib._bootstrap>:1387: in _gcd_i

- **File:** `tests/integration`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from tests/integration. This usually indicates a syntax error or import failure.

/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen importlib._bootstrap>:1387: in _gcd_import
    ???
<frozen importlib._bootstrap>:1360: in _find_and_load
    ???
<frozen importlib._bootstrap>:1310: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:488: in _call_with_frames_removed
    ???
<frozen importlib._bootstrap>:1387: in _gcd_i

**Code:**
```
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen i
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from masking_engine/tests/test_synthetic.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking_engine/tests/test_synthetic.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_synthetic.py:9: in <module>
    from app.transformers.synthetic import SyntheticGenerator
masking-engine/app/

- **File:** `masking_engine/tests/test_synthetic.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from masking_engine/tests/test_synthetic.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking_engine/tests/test_synthetic.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_synthetic.py:9: in <module>
    from app.transformers.synthetic import SyntheticGenerator
masking-engine/app/

**Code:**
```python
ImportError while importing test module '/scan-target/masking_engine/tests/test_synthetic.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/import
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from masking_engine/tests/test_fpe.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking_engine/tests/test_fpe.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_fpe.py:4: in <module>
    from app.transformers.fpe import FPETransformer, _passes_luhn
masking-engine/app/transfor

- **File:** `masking_engine/tests/test_fpe.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from masking_engine/tests/test_fpe.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking_engine/tests/test_fpe.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_fpe.py:4: in <module>
    from app.transformers.fpe import FPETransformer, _passes_luhn
masking-engine/app/transfor

**Code:**
```python
ImportError while importing test module '/scan-target/masking_engine/tests/test_fpe.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from masking_engine/tests/test_distribution_analyzer.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking_engine/tests/test_distribution_analyzer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_distribution_analyzer.py:8: in <module>
    from app.transformers.distribution_analyzer import Di

- **File:** `masking_engine/tests/test_distribution_analyzer.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from masking_engine/tests/test_distribution_analyzer.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking_engine/tests/test_distribution_analyzer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_distribution_analyzer.py:8: in <module>
    from app.transformers.distribution_analyzer import Di

**Code:**
```python
ImportError while importing test module '/scan-target/masking_engine/tests/test_distribution_analyzer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/pytho
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from masking_engine/tests/test_api.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking_engine/tests/test_api.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_api.py:5: in <module>
    from fastapi.testclient import TestClient
E   ModuleNotFoundError: No module named 'fasta

- **File:** `masking_engine/tests/test_api.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from masking_engine/tests/test_api.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking_engine/tests/test_api.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_api.py:5: in <module>
    from fastapi.testclient import TestClient
E   ModuleNotFoundError: No module named 'fasta

**Code:**
```python
ImportError while importing test module '/scan-target/masking_engine/tests/test_api.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from masking-engine/tests/test_synthetic.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking-engine/tests/test_synthetic.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_synthetic.py:9: in <module>
    from app.transformers.synthetic import SyntheticGenerator
masking-engine/app/

- **File:** `masking-engine/tests/test_synthetic.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from masking-engine/tests/test_synthetic.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking-engine/tests/test_synthetic.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_synthetic.py:9: in <module>
    from app.transformers.synthetic import SyntheticGenerator
masking-engine/app/

**Code:**
```python
ImportError while importing test module '/scan-target/masking-engine/tests/test_synthetic.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/import
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from masking-engine/tests/test_fpe.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking-engine/tests/test_fpe.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_fpe.py:4: in <module>
    from app.transformers.fpe import FPETransformer, _passes_luhn
masking-engine/app/transfor

- **File:** `masking-engine/tests/test_fpe.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from masking-engine/tests/test_fpe.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking-engine/tests/test_fpe.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_fpe.py:4: in <module>
    from app.transformers.fpe import FPETransformer, _passes_luhn
masking-engine/app/transfor

**Code:**
```python
ImportError while importing test module '/scan-target/masking-engine/tests/test_fpe.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from masking-engine/tests/test_distribution_analyzer.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking-engine/tests/test_distribution_analyzer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_distribution_analyzer.py:8: in <module>
    from app.transformers.distribution_analyzer import Di

- **File:** `masking-engine/tests/test_distribution_analyzer.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from masking-engine/tests/test_distribution_analyzer.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking-engine/tests/test_distribution_analyzer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_distribution_analyzer.py:8: in <module>
    from app.transformers.distribution_analyzer import Di

**Code:**
```python
ImportError while importing test module '/scan-target/masking-engine/tests/test_distribution_analyzer.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/pytho
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

### [HIGH] pytest could not collect tests from masking-engine/tests/test_api.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking-engine/tests/test_api.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_api.py:5: in <module>
    from fastapi.testclient import TestClient
E   ModuleNotFoundError: No module named 'fasta

- **File:** `masking-engine/tests/test_api.py`
- **Scanner:** pytest
- **Rule:** `PYTEST-ERROR`

**What's wrong:** pytest could not collect tests from masking-engine/tests/test_api.py. This usually indicates a syntax error or import failure.

ImportError while importing test module '/scan-target/masking-engine/tests/test_api.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
masking-engine/tests/test_api.py:5: in <module>
    from fastapi.testclient import TestClient
E   ModuleNotFoundError: No module named 'fasta

**Code:**
```python
ImportError while importing test module '/scan-target/masking-engine/tests/test_api.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
/usr/lib/python3.12/importlib/__
```

**How to fix:** Fix the syntax or import error preventing test collection.

**Action:** Address this issue as soon as possible.

---

> ... and 154 more high findings

## Medium Findings (371)

### [MEDIUM] 13 lines (0 tokens) of duplicated python code.
- lineage/pg_writer.py:294
- lineage/pg_writer.py:272
Overall duplication: 17.86%

- **File:** `lineage/pg_writer.py:294`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 13 lines (0 tokens) of duplicated python code.
- lineage/pg_writer.py:294
- lineage/pg_writer.py:272
Overall duplication: 17.86%

**Code:**
```python
visited = set()
        result = []
        stack = [event_id]

        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            event = self._events.get(current)
            if event:
                result.append(event)
            for edge in self.get_children
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 13 lines (0 tokens) of duplicated python code.
- quality/assertion_engine.py:229
- quality/assertion_engine.py:207
Overall duplication: 17.86%

- **File:** `quality/assertion_engine.py:229`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 13 lines (0 tokens) of duplicated python code.
- quality/assertion_engine.py:229
- quality/assertion_engine.py:207
Overall duplication: 17.86%

**Code:**
```python
,
            parsed.original_text,
            re.IGNORECASE,
        )
        if not match:
            return False

        operator = match.group(1)
        threshold = int(float(match.group(2).strip()))
        return _compare(actual_count, operator, threshold)


def _compare
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 14 lines (0 tokens) of duplicated python code.
- tests/test_assertion_engine.py:30
- tests/test_transform_engine.py:30
Overall duplication: 17.86%

- **File:** `tests/test_assertion_engine.py:30`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 14 lines (0 tokens) of duplicated python code.
- tests/test_assertion_engine.py:30
- tests/test_transform_engine.py:30
Overall duplication: 17.86%

**Code:**
```python
},
    ]
    orders = [
        {"id": 10, "customer_id": 1, "amount": 100, "status": "active"},
        {"id": 11, "customer_id": 1, "amount": 200, "status": "active"},
        {"id": 12, "customer_id": 2, "amount": 50, "status": "pending"},
        {"id": 13, "customer_id": 3, "amount": 300, "status": "complete"},
    ]
    executor.load_table("customers", customers)
    executor.load_table("orders", orders)


# ===================================================================
# IS NOT NULL
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 15 lines (0 tokens) of duplicated python code.
- tests/test_contract_manager.py:267
- tests/test_contract_manager.py:216
Overall duplication: 17.86%

- **File:** `tests/test_contract_manager.py:267`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 15 lines (0 tokens) of duplicated python code.
- tests/test_contract_manager.py:267
- tests/test_contract_manager.py:216
Overall duplication: 17.86%

**Code:**
```python
(self, manager):
        manager.create_contract(
            pipeline_ref="pipe-001",
            steward_id="nhi_data-steward_alice",
            columns=COLUMNS_V1,
            raw_yaml=RAW_YAML_V1,
        )
        manager.update_contract(
            pipeline_ref="pipe-001",
            changes={"columns": COLUMNS_V2},
            raw_yaml=RAW_YAML_V2,
            steward_id="nhi_data-steward_alice",
        )

        all_versions
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 15 lines (0 tokens) of duplicated python code.
- tests/test_contract_manager.py:235
- tests/test_contract_manager.py:216
Overall duplication: 17.86%

- **File:** `tests/test_contract_manager.py:235`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 15 lines (0 tokens) of duplicated python code.
- tests/test_contract_manager.py:235
- tests/test_contract_manager.py:216
Overall duplication: 17.86%

**Code:**
```python
(self, manager):
        manager.create_contract(
            pipeline_ref="pipe-001",
            steward_id="nhi_data-steward_alice",
            columns=COLUMNS_V1,
            raw_yaml=RAW_YAML_V1,
        )
        manager.update_contract(
            pipeline_ref="pipe-001",
            changes={"columns": COLUMNS_V2},
            raw_yaml=RAW_YAML_V2,
            steward_id="nhi_data-steward_alice",
        )

        latest
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 21 lines (0 tokens) of duplicated python code.
- tests/test_contract_validator.py:75
- masking_engine/tests/test_api.py:28
Overall duplication: 17.86%

- **File:** `tests/test_contract_validator.py:75`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 21 lines (0 tokens) of duplicated python code.
- tests/test_contract_validator.py:75
- masking_engine/tests/test_api.py:28
Overall duplication: 17.86%

**Code:**
```python
,
            "classification_version": 1,
        },
        "columns": {
            "customers.id": {"classification": "internal", "pii": False},
            "customers.name": {"classification": "confidential", "pii": True, "pii_type": "PERSON"},
            "customers.email": {"classification": "confidential", "pii": True, "pii_type": "EMAIL"},
            "orders.id": {"classification": "internal", "pii": False},
            "orders.customer_id": {"classification": "internal", "pii": False}
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 17 lines (0 tokens) of duplicated python code.
- tests/test_contract_validator.py:25
- tests/test_data_contract_validate.py:14
Overall duplication: 17.86%

- **File:** `tests/test_contract_validator.py:25`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 17 lines (0 tokens) of duplicated python code.
- tests/test_contract_validator.py:25
- tests/test_data_contract_validate.py:14
Overall duplication: 17.86%

**Code:**
```python
# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_pipeline():
    """Valid pipeline definition."""
    return {
        "apiVersion": "conductor-data/v1",
        "kind": "Pipeline",
        "metadata": {
            "id": "pipe-001",
            "name": "customer-data-extract",
            "created_by": "nhi_data-engineer_test",
        },
        "source": {
         
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 33 lines (0 tokens) of duplicated python code.
- tests/test_lineage_query.py:20
- tests/test_pg_writer.py:11
Overall duplication: 17.86%

- **File:** `tests/test_lineage_query.py:20`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 33 lines (0 tokens) of duplicated python code.
- tests/test_lineage_query.py:20
- tests/test_pg_writer.py:11
Overall duplication: 17.86%

**Code:**
```python
# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_event(
    pipeline_id: str = "pipe-001",
    operation: str = "extract",
    classification: str = "confidential",
    source_table: str = "customers",
    target_table: str = "customers",
    target_tier: str = "staging",
    content_hash: str = "sha256:aabbccdd0011",
    timestamp: str = "2026-03-18T14:32:00Z",
) -> d
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 17 lines (0 tokens) of duplicated python code.
- tests/test_lineage_query.py:16
- tests/test_qdrant_writer.py:16
Overall duplication: 17.86%

- **File:** `tests/test_lineage_query.py:16`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 17 lines (0 tokens) of duplicated python code.
- tests/test_lineage_query.py:16
- tests/test_qdrant_writer.py:16
Overall duplication: 17.86%

**Code:**
```python
,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_event(
    pipeline_id: str = "pipe-001",
    operation: str = "extract",
    classification: str = "confidential",
    source_table: str = "customers",
    target_table: str = "customers",
    target_tier: str = "staging",
    content_hash: str = "sha256:aabbccdd0011",
    timestamp
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 18 lines (0 tokens) of duplicated python code.
- tests/test_pg_writer.py:30
- tests/test_qdrant_writer.py:38
Overall duplication: 17.86%

- **File:** `tests/test_pg_writer.py:30`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 18 lines (0 tokens) of duplicated python code.
- tests/test_pg_writer.py:30
- tests/test_qdrant_writer.py:38
Overall duplication: 17.86%

**Code:**
```python
,
            "pipeline_id": pipeline_id,
            "operation": operation,
            "source": {
                "connector": "airbyte/source-postgres",
                "table": source_table,
                "columns": ["id", "name", "email"],
                "row_count": 1000,
            },
            "target": {
                "connector": "airbyte/destination-postgres",
                "tier": target_tier,
                "table": target_table,
                "masking_applied": True,
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 185 lines (0 tokens) of duplicated python code.
- masking-engine/app/contract_mapper.py:1
- masking_engine/app/contract_mapper.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/contract_mapper.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 185 lines (0 tokens) of duplicated python code.
- masking-engine/app/contract_mapper.py:1
- masking_engine/app/contract_mapper.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Contract Mapper -- loads data contracts and maps columns to classifications.

Reads a data contract YAML (validated against contract.schema.json) and
produces a classification map: column_name -> {classification, pii, pii_type}.

Validates that all columns in the dataset are covered by the contract.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

logger = logging.getLogger(__name__)


class ContractError(Exception
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 172 lines (0 tokens) of duplicated python code.
- masking-engine/app/integrity_checker.py:1
- masking_engine/app/integrity_checker.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/integrity_checker.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 172 lines (0 tokens) of duplicated python code.
- masking-engine/app/integrity_checker.py:1
- masking_engine/app/integrity_checker.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Referential Integrity Checker -- verifies FK consistency post-masking.

After masking, verifies that FK columns across tables share matching
token/FPE values. If customers.id was tokenized to TOKEN_x9, then
orders.customer_id must also be TOKEN_x9.

Accepts FK relationships from pipeline join operations and validates
that the join still holds after masking.
"""

from __future__ import annotations

import logging
from typing import Any

from .models import (
    FKRelationship,
    IntegrityRe
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 274 lines (0 tokens) of duplicated python code.
- masking-engine/app/main.py:1
- masking_engine/app/main.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/main.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 274 lines (0 tokens) of duplicated python code.
- masking-engine/app/main.py:1
- masking_engine/app/main.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Masking Engine -- FastAPI application.

Endpoints:
- POST /mask -- main masking endpoint
- GET /health -- health check
- GET /strategies -- list available masking strategies
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .contract_mapper import ContractError, ContractMapper
from .integrity_checker import IntegrityChecker
from .models import (
    ErrorRespon
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 152 lines (0 tokens) of duplicated python code.
- masking-engine/app/models.py:1
- masking_engine/app/models.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/models.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 152 lines (0 tokens) of duplicated python code.
- masking-engine/app/models.py:1
- masking_engine/app/models.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Pydantic request/response models for the masking engine API."""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class MaskingStrategy(str, Enum):
    """Available masking strategies."""

    FORMAT_PRESERVE_ENCRYPT = "format_preserve_encrypt"
    TOKENIZE = "tokenize"
    REDACT = "redact"
    SYNTHETIC = "synthetic"
    PASSTHROUGH = "passthrough"


class Classification(str, Enum):
    """Data classification
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 288 lines (0 tokens) of duplicated python code.
- masking-engine/app/policy_resolver.py:1
- masking_engine/app/policy_resolver.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/policy_resolver.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 288 lines (0 tokens) of duplicated python code.
- masking-engine/app/policy_resolver.py:1
- masking_engine/app/policy_resolver.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Policy Resolver -- loads masking policy YAML and resolves column strategies.

Implements the precedence order from Section 12.7:
1. Field pattern rules (*.email) -- highest
2. Classification rules (classification: confidential) -- middle
3. Defaults block (defaults.strategy: tokenize) -- lowest

Logs which rule was selected per column for audit trail.
"""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path
from typing import Any, Optional

import yaml


```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 153 lines (0 tokens) of duplicated python code.
- masking-engine/app/strategy_router.py:1
- masking_engine/app/strategy_router.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/strategy_router.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 153 lines (0 tokens) of duplicated python code.
- masking-engine/app/strategy_router.py:1
- masking_engine/app/strategy_router.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Strategy Router -- routes columns to correct transformer per strategy.

Given a column + resolved strategy, delegates to FPE, Tokenizer, or Redactor.
Validates strategy compatibility with data type.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .policy_resolver import ResolvedStrategy
from .transformers.fpe import FPETransformer
from .transformers.redactor import Redactor
from .transformers.tokenizer import Tokenizer

logger = logging.getLogger
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 144 lines (0 tokens) of duplicated python code.
- masking-engine/app/vault_client.py:1
- masking_engine/app/vault_client.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/vault_client.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 144 lines (0 tokens) of duplicated python code.
- masking-engine/app/vault_client.py:1
- masking_engine/app/vault_client.py:1
Overall duplication: 17.86%

**Code:**
```python
"""HashiCorp Vault client with Docker secrets and env var fallback.

Resolution order:
1. HashiCorp Vault (via hvac library)
2. Docker secrets (/run/secrets/)
3. Environment variables (for testing only)

Never logs actual secret values -- only metadata (key names, versions).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class VaultClient:
    """Reads secrets from Vault, Docker secret
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 423 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_api.py:1
- masking_engine/tests/test_api.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/tests/test_api.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 423 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_api.py:1
- masking_engine/tests/test_api.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Tests for the FastAPI masking engine endpoints."""

import os
import pytest
from fastapi.testclient import TestClient


# Set environment variables before importing the app
os.environ.setdefault("MASKING_MASTER_SEED", "test-seed-for-api-tests")
os.environ.setdefault("FPE_KEY", "test-fpe-key-for-api-tests")

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


# Reusable contract and policy fixtures
SAMPLE_CONTRACT = 
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 230 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_distribution_analyzer.py:1
- masking_engine/tests/test_distribution_analyzer.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/tests/test_distribution_analyzer.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 230 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_distribution_analyzer.py:1
- masking_engine/tests/test_distribution_analyzer.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Tests for distribution_analyzer -- per-column statistical analysis."""

import math
from datetime import datetime

import pytest

from app.transformers.distribution_analyzer import DistributionAnalyzer


@pytest.fixture
def analyzer():
    """Create a fresh DistributionAnalyzer."""
    return DistributionAnalyzer()


class TestKnownDataset:
    """Verify correct stats for a known dataset."""

    def test_numeric_stats(self, analyzer):
        """Numeric column should produce correct min/max/
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 473 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_distribution_validator.py:1
- masking_engine/tests/test_distribution_validator.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/tests/test_distribution_validator.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 473 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_distribution_validator.py:1
- masking_engine/tests/test_distribution_validator.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Tests for distribution_validator -- synthetic vs source comparison."""

import pytest

from app.transformers.distribution_validator import (
    DistributionValidator,
)


@pytest.fixture
def validator():
    """Create a DistributionValidator with default tolerances."""
    return DistributionValidator()


class TestMatchingDistributionsPass:
    """Matching or near-matching distributions should pass validation."""

    def test_identical_numeric_passes(self, validator):
        """Identical 
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 333 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_entity_replacer.py:1
- masking_engine/tests/test_entity_replacer.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/tests/test_entity_replacer.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 333 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_entity_replacer.py:1
- masking_engine/tests/test_entity_replacer.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Tests for EntityReplacer -- entity replacement with tokenizer integration."""

import hashlib

import pytest
from app.ner.entity_replacer import EntityReplacer, DEFAULT_PREFIX
from app.ner.presidio_client import MockPresidioClient, RecognizedEntity
from app.ner.text_scanner import ScanResult
from app.transformers.tokenizer import Tokenizer


TEST_MASTER_SEED = "test-master-seed-for-unit-tests-only"
TEST_PIPELINE_ID = "pipe-ner-001"


@pytest.fixture
def tokenizer():
    """Create a pipeline-s
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 308 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_escalation.py:1
- masking_engine/tests/test_escalation.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/tests/test_escalation.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 308 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_escalation.py:1
- masking_engine/tests/test_escalation.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Tests for EscalationEmitter -- classification escalation events."""

from app.ner.escalation import (
    ESCALATION_TIERS,
    EXPECTED_PII_TIERS,
    EscalationEmitter,
    EscalationSeverity,
)
from app.ner.presidio_client import RecognizedEntity
from app.ner.text_scanner import ScanResult


def _make_scan_result(
    table: str = "t",
    column: str = "c",
    classification: str = "public",
    entity_types: list[str] | None = None,
    row_index: int = 0,
) -> ScanResult:
    """Helper
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 157 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_fpe.py:1
- masking_engine/tests/test_fpe.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/tests/test_fpe.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 157 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_fpe.py:1
- masking_engine/tests/test_fpe.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Tests for Format-Preserving Encryption transformer."""

import pytest
from app.transformers.fpe import FPETransformer, _passes_luhn


TEST_KEY = "test-fpe-key-for-unit-tests-only"
TEST_TWEAK = "test-tweak"


@pytest.fixture
def fpe():
    """Create FPE transformer for tests."""
    return FPETransformer(key=TEST_KEY, tweak=TEST_TWEAK)


class TestCreditCard:
    """Credit card FPE tests."""

    def test_luhn_preserved(self, fpe):
        """Encrypted credit card should still pass Luhn valida
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 152 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_integrity_checker.py:1
- masking_engine/tests/test_integrity_checker.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/tests/test_integrity_checker.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 152 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_integrity_checker.py:1
- masking_engine/tests/test_integrity_checker.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Tests for the Referential Integrity Checker."""

import pytest
from app.integrity_checker import IntegrityChecker
from app.models import FKRelationship


@pytest.fixture
def checker():
    """Create integrity checker."""
    return IntegrityChecker()


class TestFKConsistency:
    """Verify FK values match across tables after masking."""

    def test_matching_fk_passes(self, checker):
        """FK values that match PK values should pass."""
        masked = {
            "customers": [
    
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 205 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_policy_resolver.py:1
- masking_engine/tests/test_policy_resolver.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/tests/test_policy_resolver.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 205 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_policy_resolver.py:1
- masking_engine/tests/test_policy_resolver.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Tests for the Policy Resolver -- verifies precedence ordering."""

import pytest
from app.contract_mapper import ColumnClassification
from app.models import PrecedenceLevel
from app.policy_resolver import PolicyError, PolicyResolver


STAGING_POLICY = {
    "apiVersion": "conductor-data/v1",
    "kind": "MaskingPolicy",
    "metadata": {
        "name": "staging-policy",
        "tier": "staging",
        "description": "Masked production data preserving referential integrity",
    },
    "de
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 185 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_presidio_client.py:1
- masking_engine/tests/test_presidio_client.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/tests/test_presidio_client.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 185 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_presidio_client.py:1
- masking_engine/tests/test_presidio_client.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Tests for Presidio client -- uses MockPresidioClient exclusively."""

import pytest
from app.ner.presidio_client import MockPresidioClient, RecognizedEntity


@pytest.fixture
def client():
    """Create a MockPresidioClient for tests."""
    return MockPresidioClient()


class TestEmailDetection:
    """Verify email pattern detection."""

    def test_detect_email(self, client):
        """Should detect a standard email address."""
        results = client.analyze("Contact us at alice@example
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 96 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_redactor.py:1
- masking_engine/tests/test_redactor.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/tests/test_redactor.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 96 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_redactor.py:1
- masking_engine/tests/test_redactor.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Tests for the Redaction transformer."""

import pytest
from app.transformers.redactor import Redactor, REDACTED_STRING


@pytest.fixture
def redactor():
    """Create redactor for tests."""
    return Redactor()


class TestStringRedaction:
    """String values should be replaced with [REDACTED]."""

    def test_string_to_redacted(self, redactor):
        """String value should become [REDACTED]."""
        assert redactor.redact("John Doe") == REDACTED_STRING

    def test_email_to_redacted
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 410 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_synthetic.py:1
- masking_engine/tests/test_synthetic.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/tests/test_synthetic.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 410 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_synthetic.py:1
- masking_engine/tests/test_synthetic.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Tests for synthetic data generator."""

import re
import statistics
from collections import Counter

import pytest

from app.transformers.synthetic import SyntheticGenerator
from app.transformers.distribution_analyzer import DistributionAnalyzer


PIPELINE_ID = "test-pipe-synth-001"


@pytest.fixture
def generator():
    """Create a seeded SyntheticGenerator."""
    return SyntheticGenerator(pipeline_id=PIPELINE_ID)


@pytest.fixture
def analyzer():
    """Create a DistributionAnalyzer."""
  
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 284 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_text_scanner.py:1
- masking_engine/tests/test_text_scanner.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/tests/test_text_scanner.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 284 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_text_scanner.py:1
- masking_engine/tests/test_text_scanner.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Tests for TextScanner -- column identification, confidence thresholds, batch processing."""

import pytest
from app.ner.presidio_client import MockPresidioClient
from app.ner.text_scanner import (
    ScanBatch,
    TextScanner,
)


@pytest.fixture
def mock_client():
    """Create a MockPresidioClient."""
    return MockPresidioClient()


@pytest.fixture
def scanner(mock_client):
    """Create a TextScanner with default thresholds."""
    return TextScanner(client=mock_client)


# -----------
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 139 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_tokenizer.py:1
- masking_engine/tests/test_tokenizer.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/tests/test_tokenizer.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 139 lines (0 tokens) of duplicated python code.
- masking-engine/tests/test_tokenizer.py:1
- masking_engine/tests/test_tokenizer.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Tests for deterministic HMAC-SHA256 tokenizer."""

import pytest
from app.transformers.tokenizer import Tokenizer


TEST_MASTER_SEED = "test-master-seed-for-unit-tests-only"
TEST_PIPELINE_ID = "pipe-001"
ALT_PIPELINE_ID = "pipe-002"


@pytest.fixture
def tokenizer():
    """Create tokenizer for tests."""
    return Tokenizer(
        master_seed=TEST_MASTER_SEED,
        pipeline_id=TEST_PIPELINE_ID,
    )


@pytest.fixture
def alt_tokenizer():
    """Create tokenizer with a different pipelin
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 19 lines (0 tokens) of duplicated python code.
- masking_engine/tests/test_distribution_validator.py:422
- masking_engine/tests/test_distribution_validator.py:133
Overall duplication: 17.86%

- **File:** `masking_engine/tests/test_distribution_validator.py:422`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 19 lines (0 tokens) of duplicated python code.
- masking_engine/tests/test_distribution_validator.py:422
- masking_engine/tests/test_distribution_validator.py:133
Overall duplication: 17.86%

**Code:**
```python
source = {
            "val": {
                "column_type": "numeric",
                "total_count": 100,
                "null_count": 0,
                "null_rate": 0.0,
                "distinct_count": 100,
                "mean": 100.0,
                "stddev": 10.0,
            }
        }
        synthetic = {
            "val": {
                "column_type": "numeric",
                "total_count": 100,
                "null_count": 0,
                "null_rate": 0.0,
         
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 20 lines (0 tokens) of duplicated python code.
- masking_engine/tests/test_distribution_validator.py:300
- masking_engine/tests/test_distribution_validator.py:272
Overall duplication: 17.86%

- **File:** `masking_engine/tests/test_distribution_validator.py:300`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 20 lines (0 tokens) of duplicated python code.
- masking_engine/tests/test_distribution_validator.py:300
- masking_engine/tests/test_distribution_validator.py:272
Overall duplication: 17.86%

**Code:**
```python
source = {
            "constant": {
                "column_type": "numeric",
                "total_count": 50,
                "null_count": 0,
                "null_rate": 0.0,
                "distinct_count": 1,
                "mean": 42.0,
                "stddev": 0.0,
            }
        }
        synthetic = {
            "constant": {
                "column_type": "numeric",
                "total_count": 50,
                "null_count": 0,
                "null_rate": 0.0,
     
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 13 lines (0 tokens) of duplicated python code.
- tests/integration/test_dry_run.py:127
- tests/integration/test_dry_run.py:24
Overall duplication: 17.86%

- **File:** `tests/integration/test_dry_run.py:127`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 13 lines (0 tokens) of duplicated python code.
- tests/integration/test_dry_run.py:127
- tests/integration/test_dry_run.py:24
Overall duplication: 17.86%

**Code:**
```python
from tools.data_extract import execute as data_extract

        simulated = build_simulated_source(customers_data)
        result = data_extract({
            "pipeline_id": "pipe-test-single",
            "connector": "airbyte/source-postgres",
            "tables": single_table_pipeline["source"]["extraction"]["tables"],
            "dry_run": True,
            "simulated_source": simulated,
        })

        assert result["status"] == "success"
        # Dry run should not have lineage_even
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 14 lines (0 tokens) of duplicated python code.
- tests/integration/test_dry_run.py:65
- tests/integration/test_dry_run.py:24
Overall duplication: 17.86%

- **File:** `tests/integration/test_dry_run.py:65`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 14 lines (0 tokens) of duplicated python code.
- tests/integration/test_dry_run.py:65
- tests/integration/test_dry_run.py:24
Overall duplication: 17.86%

**Code:**
```python
from tools.data_extract import execute as data_extract

        simulated = build_simulated_source(customers_data)
        result = data_extract({
            "pipeline_id": "pipe-test-single",
            "connector": "airbyte/source-postgres",
            "tables": single_table_pipeline["source"]["extraction"]["tables"],
            "dry_run": True,
            "simulated_source": simulated,
        })

        assert result["status"] == "success"
        customers_info = result["data"]["table
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 13 lines (0 tokens) of duplicated python code.
- tests/integration/test_dry_run.py:48
- tests/integration/test_dry_run.py:24
Overall duplication: 17.86%

- **File:** `tests/integration/test_dry_run.py:48`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 13 lines (0 tokens) of duplicated python code.
- tests/integration/test_dry_run.py:48
- tests/integration/test_dry_run.py:24
Overall duplication: 17.86%

**Code:**
```python
from tools.data_extract import execute as data_extract

        simulated = build_simulated_source(customers_data)
        result = data_extract({
            "pipeline_id": "pipe-test-single",
            "connector": "airbyte/source-postgres",
            "tables": single_table_pipeline["source"]["extraction"]["tables"],
            "dry_run": True,
            "simulated_source": simulated,
        })

        assert result["status"] == "success"
        customers_info
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 11 lines (0 tokens) of duplicated python code.
- tests/integration/test_error_scenarios.py:178
- tests/integration/test_error_scenarios.py:158
Overall duplication: 17.86%

- **File:** `tests/integration/test_error_scenarios.py:178`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 11 lines (0 tokens) of duplicated python code.
- tests/integration/test_error_scenarios.py:178
- tests/integration/test_error_scenarios.py:158
Overall duplication: 17.86%

**Code:**
```python
bad_data = [dict(row) for row in customers_data[:5]]
        bad_data[0]["email"] = None

        executor = DuckDBExecutor()
        try:
            executor.load_table("customers", bad_data)
            engine = AssertionEngine(executor)

            report = engine.run_assertions(
                assertions=[
                    "customers.email IS NOT NULL",
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 12 lines (0 tokens) of duplicated python code.
- tests/integration/test_multi_table_join.py:283
- tests/integration/test_multi_tier.py:313
Overall duplication: 17.86%

- **File:** `tests/integration/test_multi_table_join.py:283`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 12 lines (0 tokens) of duplicated python code.
- tests/integration/test_multi_table_join.py:283
- tests/integration/test_multi_tier.py:313
Overall duplication: 17.86%

**Code:**
```python
, 100,
                strategy_map=strategy_map, integrity="verified",
            ),
        ]

        cls_map = {cn: cc.classification for cn, cc in classifications.items()}

        pii_validator = make_gate_pii_validator()
        context = PipelineContext(
            pipeline_id=pipeline_id,
            target_tier="staging",
            contract=multi_table_join_contract
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 231 lines (0 tokens) of duplicated python code.
- masking-engine/app/ner/entity_replacer.py:1
- masking_engine/app/ner/entity_replacer.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/ner/entity_replacer.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 231 lines (0 tokens) of duplicated python code.
- masking-engine/app/ner/entity_replacer.py:1
- masking_engine/app/ner/entity_replacer.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Entity replacer -- replaces detected NER entities with deterministic tokens.

Reuses the pipeline-scoped Tokenizer (HMAC-SHA256) from
masking-engine/app/transformers/tokenizer.py to ensure:
1. Same seed derivation as the rest of the masking pipeline
2. Cross-column consistency: same entity text produces the same token
   everywhere in the dataset
3. Deterministic, recomputable replacements
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 217 lines (0 tokens) of duplicated python code.
- masking-engine/app/ner/escalation.py:1
- masking_engine/app/ner/escalation.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/ner/escalation.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 217 lines (0 tokens) of duplicated python code.
- masking-engine/app/ner/escalation.py:1
- masking_engine/app/ner/escalation.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Escalation emitter -- flags PII detected in Public/Internal columns.

When the NER scanner finds PII in columns classified as Public or Internal,
this module emits CLASSIFICATION_ESCALATION events for post-execution review.
It does NOT block masking -- the pipeline continues and the escalation is
recorded for audit and review.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typi
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 277 lines (0 tokens) of duplicated python code.
- masking-engine/app/ner/presidio_client.py:1
- masking_engine/app/ner/presidio_client.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/ner/presidio_client.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 277 lines (0 tokens) of duplicated python code.
- masking-engine/app/ner/presidio_client.py:1
- masking_engine/app/ner/presidio_client.py:1
Overall duplication: 17.86%

**Code:**
```python
"""HTTP client for Presidio analyzer API with a mock implementation for testing.

The PresidioClient sends text to a real Presidio analyzer REST endpoint.
The MockPresidioClient simulates entity detection using regex patterns and
a small built-in name list, returning results in the same Presidio response
format: [{"entity_type": "EMAIL", "start": 10, "end": 25, "score": 0.95}]
"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from dataclasses i
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 307 lines (0 tokens) of duplicated python code.
- masking-engine/app/ner/text_scanner.py:1
- masking_engine/app/ner/text_scanner.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/ner/text_scanner.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 307 lines (0 tokens) of duplicated python code.
- masking-engine/app/ner/text_scanner.py:1
- masking_engine/app/ner/text_scanner.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Text column scanner -- identifies text columns, batches for NER scanning,
and applies confidence thresholds per classification tier.

Confidence thresholds (overridable via policy):
- Restricted:    0.70  (lowest bar -- catch more PII)
- Confidential:  0.85
- Internal:      0.90  (highest bar -- fewer false positives)
- Public:        0.90  (same as Internal for escalation detection)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing i
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 387 lines (0 tokens) of duplicated python code.
- masking-engine/app/transformers/distribution_analyzer.py:1
- masking_engine/app/transformers/distribution_analyzer.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/transformers/distribution_analyzer.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 387 lines (0 tokens) of duplicated python code.
- masking-engine/app/transformers/distribution_analyzer.py:1
- masking_engine/app/transformers/distribution_analyzer.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Distribution Analyzer -- computes per-column statistics from source datasets.

Uses DuckDB for efficient statistical computation over tabular data.
Produces a stats dict that feeds the synthetic generator and distribution validator.

Statistics computed per column type:
- Numeric: min, max, mean, median, stddev, null_count, null_rate
- String: min_length, max_length, avg_length, null_count, null_rate
- Categorical: value_counts (frequency map), null_count, null_rate
- Boolean: true_count, fal
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 356 lines (0 tokens) of duplicated python code.
- masking-engine/app/transformers/distribution_validator.py:1
- masking_engine/app/transformers/distribution_validator.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/transformers/distribution_validator.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 356 lines (0 tokens) of duplicated python code.
- masking-engine/app/transformers/distribution_validator.py:1
- masking_engine/app/transformers/distribution_validator.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Distribution Validator -- compares synthetic vs source statistics.

Validates that synthetic data matches source distributions within tolerance:
- Mean: within 5% of source mean (or absolute tolerance for near-zero means)
- Variance/Stddev: within 5% (or absolute tolerance for near-zero)
- Cardinality (distinct count): within 10%
- Null rate: within 1 percentage point
- Boolean true_ratio: within 5 percentage points
- Categorical: top-N value frequencies within 10%

Returns pass/fail per colu
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 290 lines (0 tokens) of duplicated python code.
- masking-engine/app/transformers/fpe.py:1
- masking_engine/app/transformers/fpe.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/transformers/fpe.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 290 lines (0 tokens) of duplicated python code.
- masking-engine/app/transformers/fpe.py:1
- masking_engine/app/transformers/fpe.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Format-Preserving Encryption (AES-FF1) transformer.

Uses pyffx for FF1 implementation. Preserves input format:
- Credit cards still pass Luhn validation
- Phone numbers maintain their pattern
- SSNs maintain NNN-NN-NNNN format

Deterministic: same key + tweak + input = same output.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

import pyffx

logger = logging.getLogger(__name__)


def _luhn_checksum(card_number: str) -> int:
    """Compute Luhn 
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 82 lines (0 tokens) of duplicated python code.
- masking-engine/app/transformers/redactor.py:1
- masking_engine/app/transformers/redactor.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/transformers/redactor.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 82 lines (0 tokens) of duplicated python code.
- masking-engine/app/transformers/redactor.py:1
- masking_engine/app/transformers/redactor.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Redaction transformer.

For restricted data with zero non-production utility:
- String columns: replace with "[REDACTED]"
- Numeric columns: replace with None (NULL)
- Date columns: replace with None (NULL)
- Boolean columns: replace with None (NULL)

Verifies no residual data after redaction.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Sentinel values
REDACTED_STRING = "[REDACTED]"


class Redactor:
    """
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 308 lines (0 tokens) of duplicated python code.
- masking-engine/app/transformers/synthetic.py:1
- masking_engine/app/transformers/synthetic.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/transformers/synthetic.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 308 lines (0 tokens) of duplicated python code.
- masking-engine/app/transformers/synthetic.py:1
- masking_engine/app/transformers/synthetic.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Synthetic Data Generator -- creates realistic fake data matching source distributions.

Uses Faker for PII-typed columns and statistical distributions for non-PII:
- PERSON -> faker.name()
- EMAIL -> faker.email()
- PHONE -> faker.phone_number()
- ADDRESS -> faker.address()
- Integers: normal distribution matching source mean/stddev
- Floats: normal distribution matching source mean/stddev (preserving variance)
- Dates: uniform within source date range
- Booleans: Bernoulli matching source tr
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 97 lines (0 tokens) of duplicated python code.
- masking-engine/app/transformers/tokenizer.py:1
- masking_engine/app/transformers/tokenizer.py:1
Overall duplication: 17.86%

- **File:** `masking-engine/app/transformers/tokenizer.py:1`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 97 lines (0 tokens) of duplicated python code.
- masking-engine/app/transformers/tokenizer.py:1
- masking_engine/app/transformers/tokenizer.py:1
Overall duplication: 17.86%

**Code:**
```python
"""Deterministic tokenization transformer using HMAC-SHA256.

Per Section 12.5:
- pipeline_derived_seed = HMAC-SHA256(master_seed, pipeline_id)
- token = HMAC-SHA256(pipeline_derived_seed, input_value)
- Truncate hash, add optional prefix (e.g., NAME_a7f3b2)
- No persisted token map -- fully recomputable from inputs.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Default token length (hex cha
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 21 lines (0 tokens) of duplicated yaml code.
- tests/fixtures/contracts/free-text-ner.contract.yaml:5
- tests/fixtures/contracts/single-table.contract.yaml:5
Overall duplication: 17.86%

- **File:** `tests/fixtures/contracts/free-text-ner.contract.yaml:5`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 21 lines (0 tokens) of duplicated yaml code.
- tests/fixtures/contracts/free-text-ner.contract.yaml:5
- tests/fixtures/contracts/single-table.contract.yaml:5
Overall duplication: 17.86%

**Code:**
```yaml
steward: nhi_data-steward_test
  reviewed_at: "2025-06-01T10:00:00Z"
  classification_version: 1

columns:
  customers.id:
    classification: public
    pii: false
  customers.name:
    classification: confidential
    pii: true
    pii_type: PERSON
  customers.email:
    classification: confidential
    pii: true
    pii_type: EMAIL
  customers.phone:
    classification: confidential
    pii: true
    pii_type: PHONE
  notes.id
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 21 lines (0 tokens) of duplicated yaml code.
- tests/fixtures/contracts/multi-table-join.contract.yaml:5
- tests/fixtures/contracts/single-table.contract.yaml:5
Overall duplication: 17.86%

- **File:** `tests/fixtures/contracts/multi-table-join.contract.yaml:5`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 21 lines (0 tokens) of duplicated yaml code.
- tests/fixtures/contracts/multi-table-join.contract.yaml:5
- tests/fixtures/contracts/single-table.contract.yaml:5
Overall duplication: 17.86%

**Code:**
```yaml
steward: nhi_data-steward_test
  reviewed_at: "2025-06-01T10:00:00Z"
  classification_version: 1

columns:
  customers.id:
    classification: public
    pii: false
  customers.name:
    classification: confidential
    pii: true
    pii_type: PERSON
  customers.email:
    classification: confidential
    pii: true
    pii_type: EMAIL
  customers.phone:
    classification: confidential
    pii: true
    pii_type: PHONE
  customers.tier
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] 38 lines (0 tokens) of duplicated yaml code.
- tests/fixtures/contracts/multi-tier.contract.yaml:5
- tests/fixtures/contracts/single-table.contract.yaml:5
Overall duplication: 17.86%

- **File:** `tests/fixtures/contracts/multi-tier.contract.yaml:5`
- **Scanner:** jscpd
- **Rule:** `JSCPD-DUPLICATE`

**What's wrong:** 38 lines (0 tokens) of duplicated yaml code.
- tests/fixtures/contracts/multi-tier.contract.yaml:5
- tests/fixtures/contracts/single-table.contract.yaml:5
Overall duplication: 17.86%

**Code:**
```yaml
steward: nhi_data-steward_test
  reviewed_at: "2025-06-01T10:00:00Z"
  classification_version: 1

columns:
  customers.id:
    classification: public
    pii: false
  customers.name:
    classification: confidential
    pii: true
    pii_type: PERSON
  customers.email:
    classification: confidential
    pii: true
    pii_type: EMAIL
  customers.phone:
    classification: confidential
    pii: true
    pii_type: PHONE
  customers.address:
    classification: confidential
    pii: true
    pii_t
```

**How to fix:** Extract duplicated code into a shared function or module.

**Action:** Plan to fix this issue in your next sprint or release.

---

> ... and 321 more medium findings

## Low Findings (2117)

- **SCORECARD-VULNERABILITIES**: OpenSSF Scorecard: Vulnerabilities (6/10) (N/A)
- **DEEPEVAL-005**: Over-engineered abstraction in tests/integration/conftest.py:287 (`tests/integration/conftest.py:287`)
- **DEEPEVAL-005**: Over-engineered abstraction in gates/post_data_pipeline.py:39 (`gates/post_data_pipeline.py:39`)
- **DEEPEVAL-005**: Over-engineered abstraction in gates/key_rotation.py:101 (`gates/key_rotation.py:101`)
- **DEEPEVAL-005**: Over-engineered abstraction in gates/human_approval.py:64 (`gates/human_approval.py:64`)
- **DEEPEVAL-005**: Over-engineered abstraction in gates/human_approval.py:43 (`gates/human_approval.py:43`)
- **DEEPEVAL-005**: Over-engineered abstraction in gates/gate_registry.py:71 (`gates/gate_registry.py:71`)
- **DEEPEVAL-005**: Over-engineered abstraction in gates/gate_registry.py:48 (`gates/gate_registry.py:48`)
- **DEEPEVAL-005**: Over-engineered abstraction in gates/pii_validator.py:44 (`gates/pii_validator.py:44`)
- **DEEPEVAL-005**: Over-engineered abstraction in lineage/emitter.py:63 (`lineage/emitter.py:63`)
- **DEEPEVAL-005**: Over-engineered abstraction in quality/quality_report.py:15 (`quality/quality_report.py:15`)
- **DEEPEVAL-005**: Over-engineered abstraction in masking-engine/app/contract_mapper.py:29 (`masking-engine/app/contract_mapper.py:29`)
- **DEEPEVAL-005**: Over-engineered abstraction in masking-engine/app/ner/text_scanner.py:46 (`masking-engine/app/ner/text_scanner.py:46`)
- **DEEPEVAL-005**: Over-engineered abstraction in masking-engine/app/ner/presidio_client.py:138 (`masking-engine/app/ner/presidio_client.py:138`)
- **DEEPEVAL-005**: Over-engineered abstraction in masking-engine/app/ner/presidio_client.py:51 (`masking-engine/app/ner/presidio_client.py:51`)
- **DEEPEVAL-005**: Over-engineered abstraction in masking-engine/app/ner/escalation.py:38 (`masking-engine/app/ner/escalation.py:38`)
- **DEEPEVAL-005**: Over-engineered abstraction in contracts/steward_gate.py:59 (`contracts/steward_gate.py:59`)
- **DEEPEVAL-005**: Over-engineered abstraction in contracts/steward_gate.py:49 (`contracts/steward_gate.py:49`)
- **DEEPEVAL-005**: Over-engineered abstraction in contracts/schema_drift_detector.py:69 (`contracts/schema_drift_detector.py:69`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:217`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:216`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:215`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:211`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:210`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:206`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:202`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:198`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:186`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:183`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:180`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:179`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:178`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:177`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:173`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:172`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:168`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:167`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:164`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:161`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:158`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:155`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:152`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:149`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:138`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:129`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:125`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:121`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:116`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:111`)
- **B101**: assert_used: Use of assert detected. The enclosed code will be removed when compiling to opti (`tests/test_workflow_phases.py:99`)

> ... and 2067 more low findings

## Recommendations

1. Schedule remediation for 204 high severity finding(s) within the current sprint

---
*Generated by Code Hardener v0.1.0 | 2026-03-18T17:40:31.241Z*