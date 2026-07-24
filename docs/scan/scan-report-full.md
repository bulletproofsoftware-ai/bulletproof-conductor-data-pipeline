# Security Scan Report: bulletproof-conductor-data-pipeline

**Scan ID:** `472764fb-dc9e-47e3-9988-334ebbab53ed`
**Date:** 2026-07-24T21:09:09.681Z
**Score:** 1000/1000 (excellent)
**Branch:** main | **Commit:** `N/A`
**Profile:** standard

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 0 |
| Medium | 12 |
| Low | 3 |
| Info | 8 |
| **Total (open)** | **23** |

> **Note:** The counts above reflect _open_ findings only.
> 1 scanner(s) were skipped — see "Skipped Scanners" below.

## Scanners Executed

| Scanner | Status | Findings | Duration | Notes |
|---------|--------|----------|----------|-------|
| trivy | pass | 1 | 2.7s |  |
| gitleaks | pass | 0 | 0.5s |  |
| opengrep | pass | 12 | 6.4s |  |
| checkov | pass | 0 | 3.3s |  |
| grype | pass | 0 | 3.3s |  |
| syft | pass | 2 | 1.4s |  |
| package-validator | pass | 0 | 0.1s |  |
| oxlint | skipped | 0 | 0.0s | _skipped: no_matching_files_ |
| ruff | pass | 0 | 0.0s |  |
| actionlint | pass | 0 | 0.0s |  |
| jscpd | pass | 0 | 0.0s |  |
| typos | pass | 8 | 0.0s |  |
| _file_inventory | pass | 0 | 0.0s |  |

## Medium Findings (12)

### [MEDIUM] Detected a python logger call with a potential hardcoded secret "Credential not found: variable=%s source=%s error=Resolution failed" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.

- **File:** `tools/credential_resolver.py:100`
- **Scanner:** opengrep
- **Rule:** `python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure`
- **CWE:** [CWE-532: Insertion of Sensitive Information into Log File](https://cwe.mitre.org/data/definitions/532.html)
- **OWASP:** A09:2021 - Security Logging and Monitoring Failures

**What's wrong:** Detected a python logger call with a potential hardcoded secret "Credential not found: variable=%s source=%s error=Resolution failed" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.

**Code:**
```python
requires login
```

**How to fix:** Review this finding and apply the appropriate fix based on the description: Detected a python logger call with a potential hardcoded secret "Credential not found: variable=%s source=%s error=Resolution failed" being logged. This may lead to secret credentials being exposed. M

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] Detected possible formatted SQL query. Use parameterized queries instead.

- **File:** `quality/duckdb_executor.py:200`
- **Scanner:** opengrep
- **Rule:** `python.lang.security.audit.formatted-sql-query.formatted-sql-query`
- **CWE:** [CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')](https://cwe.mitre.org/data/definitions/89.html)
- **OWASP:** A01:2017 - Injection

**What's wrong:** Detected possible formatted SQL query. Use parameterized queries instead.

**Code:**
```python
requires login
```

**How to fix:** Review this finding and apply the appropriate fix based on the description: Detected possible formatted SQL query. Use parameterized queries instead.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] Detected possible formatted SQL query. Use parameterized queries instead.

- **File:** `quality/duckdb_executor.py:129`
- **Scanner:** opengrep
- **Rule:** `python.lang.security.audit.formatted-sql-query.formatted-sql-query`
- **CWE:** [CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')](https://cwe.mitre.org/data/definitions/89.html)
- **OWASP:** A01:2017 - Injection

**What's wrong:** Detected possible formatted SQL query. Use parameterized queries instead.

**Code:**
```python
requires login
```

**How to fix:** Review this finding and apply the appropriate fix based on the description: Detected possible formatted SQL query. Use parameterized queries instead.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] Detected possible formatted SQL query. Use parameterized queries instead.

- **File:** `quality/duckdb_executor.py:101`
- **Scanner:** opengrep
- **Rule:** `python.lang.security.audit.formatted-sql-query.formatted-sql-query`
- **CWE:** [CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')](https://cwe.mitre.org/data/definitions/89.html)
- **OWASP:** A01:2017 - Injection

**What's wrong:** Detected possible formatted SQL query. Use parameterized queries instead.

**Code:**
```python
requires login
```

**How to fix:** Review this finding and apply the appropriate fix based on the description: Detected possible formatted SQL query. Use parameterized queries instead.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] Detected possible formatted SQL query. Use parameterized queries instead.

- **File:** `quality/duckdb_executor.py:75`
- **Scanner:** opengrep
- **Rule:** `python.lang.security.audit.formatted-sql-query.formatted-sql-query`
- **CWE:** [CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')](https://cwe.mitre.org/data/definitions/89.html)
- **OWASP:** A01:2017 - Injection

**What's wrong:** Detected possible formatted SQL query. Use parameterized queries instead.

**Code:**
```python
requires login
```

**How to fix:** Review this finding and apply the appropriate fix based on the description: Detected possible formatted SQL query. Use parameterized queries instead.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] Detected possible formatted SQL query. Use parameterized queries instead.

- **File:** `quality/duckdb_executor.py:39`
- **Scanner:** opengrep
- **Rule:** `python.lang.security.audit.formatted-sql-query.formatted-sql-query`
- **CWE:** [CWE-89: Improper Neutralization of Special Elements used in an SQL Command ('SQL Injection')](https://cwe.mitre.org/data/definitions/89.html)
- **OWASP:** A01:2017 - Injection

**What's wrong:** Detected possible formatted SQL query. Use parameterized queries instead.

**Code:**
```python
requires login
```

**How to fix:** Review this finding and apply the appropriate fix based on the description: Detected possible formatted SQL query. Use parameterized queries instead.

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] Detected a python logger call with a potential hardcoded secret "AUDIT: token=%s ip=%s decision=%s" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.

- **File:** `gates/human_approval.py:456`
- **Scanner:** opengrep
- **Rule:** `python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure`
- **CWE:** [CWE-532: Insertion of Sensitive Information into Log File](https://cwe.mitre.org/data/definitions/532.html)
- **OWASP:** A09:2021 - Security Logging and Monitoring Failures

**What's wrong:** Detected a python logger call with a potential hardcoded secret "AUDIT: token=%s ip=%s decision=%s" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.

**Code:**
```python
requires login
```

**How to fix:** Review this finding and apply the appropriate fix based on the description: Detected a python logger call with a potential hardcoded secret "AUDIT: token=%s ip=%s decision=%s" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not lo

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] Detected a python logger call with a potential hardcoded secret "Token %s timed out -- automatic rejection for pipeline=%s" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.

- **File:** `gates/human_approval.py:344`
- **Scanner:** opengrep
- **Rule:** `python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure`
- **CWE:** [CWE-532: Insertion of Sensitive Information into Log File](https://cwe.mitre.org/data/definitions/532.html)
- **OWASP:** A09:2021 - Security Logging and Monitoring Failures

**What's wrong:** Detected a python logger call with a potential hardcoded secret "Token %s timed out -- automatic rejection for pipeline=%s" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.

**Code:**
```python
requires login
```

**How to fix:** Review this finding and apply the appropriate fix based on the description: Detected a python logger call with a potential hardcoded secret "Token %s timed out -- automatic rejection for pipeline=%s" being logged. This may lead to secret credentials being exposed. Make sure t

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] Detected a python logger call with a potential hardcoded secret "Approval decision for token %s: %s (pipeline=%s)" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.

- **File:** `gates/human_approval.py:307`
- **Scanner:** opengrep
- **Rule:** `python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure`
- **CWE:** [CWE-532: Insertion of Sensitive Information into Log File](https://cwe.mitre.org/data/definitions/532.html)
- **OWASP:** A09:2021 - Security Logging and Monitoring Failures

**What's wrong:** Detected a python logger call with a potential hardcoded secret "Approval decision for token %s: %s (pipeline=%s)" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.

**Code:**
```python
requires login
```

**How to fix:** Review this finding and apply the appropriate fix based on the description: Detected a python logger call with a potential hardcoded secret "Approval decision for token %s: %s (pipeline=%s)" being logged. This may lead to secret credentials being exposed. Make sure that the l

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] Detected a python logger call with a potential hardcoded secret "Generated approval token %s for pipeline=%s contract=%s (expires in %ds)" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.

- **File:** `gates/human_approval.py:225`
- **Scanner:** opengrep
- **Rule:** `python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure`
- **CWE:** [CWE-532: Insertion of Sensitive Information into Log File](https://cwe.mitre.org/data/definitions/532.html)
- **OWASP:** A09:2021 - Security Logging and Monitoring Failures

**What's wrong:** Detected a python logger call with a potential hardcoded secret "Generated approval token %s for pipeline=%s contract=%s (expires in %ds)" being logged. This may lead to secret credentials being exposed. Make sure that the logger is not logging  sensitive information.

**Code:**
```python
requires login
```

**How to fix:** Review this finding and apply the appropriate fix based on the description: Detected a python logger call with a potential hardcoded secret "Generated approval token %s for pipeline=%s contract=%s (expires in %ds)" being logged. This may lead to secret credentials being expos

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] GitHub Actions step uses a mutable tag or branch reference. Tags and branch names can be silently repointed by the action owner, enabling supply-chain attacks — as seen in the trivy-action and kics-github-action compromises. Pin the reference to a full 40-character commit SHA instead, e.g. \`uses: actions/checkout@8ade135a41bc03ea155e62e844d188df1ea18608\`.

- **File:** `.github/workflows/ci.yml:12`
- **Scanner:** opengrep
- **Rule:** `yaml.github-actions.security.github-actions-mutable-action-tag.github-actions-mutable-action-tag`
- **CWE:** [CWE-1357: Reliance on Insufficiently Trustworthy Component](https://cwe.mitre.org/data/definitions/1357.html)
- **OWASP:** A08:2021 - Software and Data Integrity Failures

**What's wrong:** GitHub Actions step uses a mutable tag or branch reference. Tags and branch names can be silently repointed by the action owner, enabling supply-chain attacks — as seen in the trivy-action and kics-github-action compromises. Pin the reference to a full 40-character commit SHA instead, e.g. `uses: actions/checkout@8ade135a41bc03ea155e62e844d188df1ea18608`.

**Code:**
```yaml
requires login
```

**How to fix:** Review this finding and apply the appropriate fix based on the description: GitHub Actions step uses a mutable tag or branch reference. Tags and branch names can be silently repointed by the action owner, enabling supply-chain attacks — as seen in the trivy-action and kics-gi

**Action:** Plan to fix this issue in your next sprint or release.

---

### [MEDIUM] GitHub Actions step uses a mutable tag or branch reference. Tags and branch names can be silently repointed by the action owner, enabling supply-chain attacks — as seen in the trivy-action and kics-github-action compromises. Pin the reference to a full 40-character commit SHA instead, e.g. \`uses: actions/checkout@8ade135a41bc03ea155e62e844d188df1ea18608\`.

- **File:** `.github/workflows/ci.yml:11`
- **Scanner:** opengrep
- **Rule:** `yaml.github-actions.security.github-actions-mutable-action-tag.github-actions-mutable-action-tag`
- **CWE:** [CWE-1357: Reliance on Insufficiently Trustworthy Component](https://cwe.mitre.org/data/definitions/1357.html)
- **OWASP:** A08:2021 - Software and Data Integrity Failures

**What's wrong:** GitHub Actions step uses a mutable tag or branch reference. Tags and branch names can be silently repointed by the action owner, enabling supply-chain attacks — as seen in the trivy-action and kics-github-action compromises. Pin the reference to a full 40-character commit SHA instead, e.g. `uses: actions/checkout@8ade135a41bc03ea155e62e844d188df1ea18608`.

**Code:**
```yaml
requires login
```

**How to fix:** Review this finding and apply the appropriate fix based on the description: GitHub Actions step uses a mutable tag or branch reference. Tags and branch names can be silently repointed by the action owner, enabling supply-chain attacks — as seen in the trivy-action and kics-gi

**Action:** Plan to fix this issue in your next sprint or release.

---

## Low Findings (3)

- **SBOM-LICENSE-UNKNOWN**: Unknown License: actions/setup-python@v5 (`/.github/workflows/ci.yml`)
- **SBOM-LICENSE-UNKNOWN**: Unknown License: actions/checkout@v4 (`/.github/workflows/ci.yml`)
- **LICENSE-Apache-2.0**: License Compliance: Apache-2.0 in  (`LICENSE`)

## Skipped Scanners (1)

Scanners that did not run on this scan, with the reason why and how to enable them.

| Scanner | Reason | How to enable |
|---------|--------|---------------|
| `oxlint` | no_matching_files | No .js/.ts files found — Oxlint requires a JavaScript/TypeScript project |

## Recommendations

1. Update 1 vulnerable dependency/dependencies -- run `npm audit fix` or equivalent

---
*Generated by Code Hardener v0.1.0 | 2026-07-24T21:12:14.240Z*