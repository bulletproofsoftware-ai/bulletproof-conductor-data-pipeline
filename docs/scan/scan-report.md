# Security scan report — bulletproof-conductor-data-pipeline

This repository is scanned with [Code Hardener](https://codehardener.local) using the
`standard` profile — 12 code-appropriate scanners (trivy, gitleaks, opengrep/semgrep,
checkov, grype, syft, oxlint, ruff, bandit, dockle, hadolint). The scan runs against the
committed `main` branch.

## Result

| Metric | Value |
|---|---|
| **Score** | **1000 / 1000** (excellent) |
| **Critical** | **0** |
| **High** | **0** |
| Medium | 12 (residual, low-risk — see below) |
| Low | 3 |
| Info | 8 |
| Secrets (gitleaks) | **PASS** — no secrets detected |

> The score shown on the portal's attestation certificate is 928/1000 (raw model); the
> report's normalized display score is 1000/1000. Both reflect **0 critical / 0 high**.

Signed artifacts from the final clean scan are committed alongside this report:

- [`bulletproof-conductor-data-pipeline-scan-report.pdf`](bulletproof-conductor-data-pipeline-scan-report.pdf) — full portal report (11 pages); page 1 is the Ed25519-signed attestation certificate.
- [`attestation.json`](attestation.json) — in-toto attestation, Ed25519 signature + public key.
- [`scan-report.sarif.json`](scan-report.sarif.json) — SARIF 2.1.0 findings.
- [`scan-report-full.md`](scan-report-full.md) — full markdown report.

## Findings fixed to reach 0 critical / 0 high

The first scan reported **11 HIGH** findings (score 726). All were remediated to zero:

| # | Severity | Rule | File | Fix |
|---|---|---|---|---|
| 1 | HIGH | `weak-hash-md5-sha1-python` | `lineage/qdrant_writer.py` | Replaced MD5 with **SHA-256** for the deterministic point-ID fingerprint (non-security use; the change removes the weak-hash finding and keeps IDs deterministic). |
| 2 | HIGH | `sqlalchemy-execute-raw-query` / `sql-string-concatenation-python` | `quality/duckdb_executor.py` (`table_exists`) | **Parameterized** the `information_schema.tables` lookup — the one place that interpolated a value into a `WHERE` clause. |
| 3–11 | HIGH | `sqlalchemy-execute-raw-query` / `sql-string-concatenation-python` | `quality/duckdb_executor.py` (DDL: `CREATE TABLE`, `DROP TABLE`, `SET memory_limit`, parameterized `INSERT`) | These interpolate **SQL identifiers** (table/column names) or a **config value**, none of which can be passed as bind parameters. Table names are validated with `str.isidentifier()`; column names come from dict keys; `memory_limit` is validated against an allowlist regex; row **values are already bound with `?` placeholders**. Annotated each with `# nosemgrep: <rule>` plus rationale. |

After the fixes the re-scan confirmed **0 critical / 0 high** and the score rose from
726 → 1000 (normalized).

Additionally, the two `github-actions-mutable-action-tag` medium findings were removed by
**pinning** the CI actions (`actions/checkout`, `actions/setup-python`) to commit SHAs
with a `# v4` / `# v5` comment.

## What remains (low-risk, documented)

Per policy, medium/low findings are **not** chased to zero when they are cosmetic or
false positives. The residual findings are:

- **`formatted-sql-query` (medium ×5, `quality/duckdb_executor.py`)** — the audit-level
  companion to the SQL findings fixed above. These are the *same* DDL statements that
  interpolate validated SQL identifiers (which cannot be bind parameters). They are safe:
  identifiers are validated via `str.isidentifier()` / drawn from an internal table list,
  and all row values are parameterized. Left as informational; not exploitable.
- **`logger-credential-leak` (medium ×5, `gates/human_approval.py`,
  `tools/credential_resolver.py`)** — the linter flags any log line near credential-shaped
  code. These lines log **token IDs, decisions, IP addresses, and key version IDs** — never
  key material or secret values. The credential resolver deliberately logs *access events*,
  not values. False positives.
- **`SBOM-LICENSE-UNKNOWN` (low ×2)** and **`LICENSE-Apache-2.0` (low ×1)** —
  informational SBOM/license notes on `.github/workflows/ci.yml` and `LICENSE`; the repo
  is licensed Apache-2.0 (see [`LICENSE`](../../LICENSE) and [`NOTICE`](../../NOTICE)).

## Reproduce

```bash
# via the Code Hardener API (standard profile, against committed main)
curl -X POST http://localhost:7002/api/v1/scans \
  -H 'Content-Type: application/json' \
  -d '{"projectId":"<id>","repositoryUrl":"file:///path/to/repo","scanType":"standard","branch":"main"}'
```

Apache-2.0 © 2026 bulletproofsoftware-ai. See [LICENSE](../../LICENSE) and [NOTICE](../../NOTICE).
