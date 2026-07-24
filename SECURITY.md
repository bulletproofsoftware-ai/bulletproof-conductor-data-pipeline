# Security Policy

This document describes how to report security vulnerabilities in
**bulletproof-conductor-data-pipeline** and the response commitments of the
maintainers.

## Supported Versions

| Version Range | Supported |
|---------------|-----------|
| `0.1.x` (initial release line) | Yes — receives security fixes |
| Any pre-release / branch builds | No — use only for testing |

When a new minor or major release ships, the previous minor remains supported
for 90 days for security fixes only.

## Reporting a Vulnerability

**Please do NOT open a public GitHub issue for security vulnerabilities.**
Public disclosure before a fix is available puts users at risk.

Report privately via a GitHub security advisory on this repository, or to the
security contact of the organization operating your deployment
(`security@<your-domain>`).

Include:

1. **Affected component** — e.g. a masking policy, an approval gate, the
   lineage emitter, a data contract validator
2. **Vulnerability class** — e.g. masking bypass, approval-gate bypass,
   injection, information disclosure
3. **Impact** — what an adversary can achieve, especially any path that causes
   unmasked PII to reach a downstream sink
4. **Reproduction steps** — a minimal proof of concept. **Do not include real
   personal data**; use synthetic values
5. **Affected version(s)** — git SHA or release tag
6. **Suggested mitigation** (optional)

### Response Targets

| Stage | Target |
|-------|--------|
| Acknowledge receipt | 3 business days |
| Initial severity assessment | 7 business days |
| Fix or documented mitigation for High/Critical | 30 days |
| Public advisory after fix ships | 7 days |

We ask that you allow 90 days before public disclosure, or until a fix ships,
whichever comes first.

## Security Model

### What this pipeline is responsible for

- **Masking and anonymization.** PII is tokenized consistently so the same
  input maps to the same token across columns and runs. A defect that leaks an
  unmasked value, or that makes tokens reversible without the master seed, is a
  High-or-Critical severity issue.
- **Approval gates.** Sensitive steps require a recorded human approval. Any
  path that executes a gated step without a valid approval is a Critical issue.
- **Lineage.** Every transformation emits a lineage event. Silent gaps in the
  lineage record undermine auditability and are treated as security-relevant.

### Critical secrets

| Secret | Why it matters |
|---|---|
| `MASKING_MASTER_SEED` | Determines every token the masking engine produces. Disclosure enables correlation and potential re-identification; rotation invalidates all previously issued tokens and breaks referential integrity. Back it up, restrict it, and rotate only deliberately. |
| `VAULT_TOKEN` | Grants the masking engine access to your Vault secrets. Scope it narrowly; never reuse a root token. |
| `AIRBYTE_DB_PASSWORD` | Protects Airbyte's internal metadata database. |

Provide all of these through `.env` (gitignored) or your orchestrator's secret
store. `.env.example` is a template containing only `changeme` placeholders.

### Deployment posture

- The compose stack runs on an **internal-only** network and publishes no ports
  to the host; access is via the MCP tool layer.
- The `masking-engine` container is **not runnable from this repository** — see
  the note at the top of the README. If you supply your own image, that image
  is inside your PII trust boundary and must be reviewed accordingly.

### Not in scope

- The security of the Airbyte, Vault, Presidio, and unstructured-api upstream
  projects. Report issues in those to their respective maintainers.
- Any masking-engine application code not vendored in this repository.

## Security Practices in This Repository

- Dependencies are declared with minimum-version constraints in
  `requirements.txt`; a CycloneDX SBOM is published at
  `docs/bulletproof-conductor-data-pipeline.cyclonedx.json`.
- CI compiles every Python file and runs the full 891-test suite on every push;
  test failures fail the build.
- GitHub Actions are pinned to full commit SHAs.
- `.gitignore` excludes `.env`, `*.secret`, and `/run/secrets/`; the test suite
  asserts these exclusions so they cannot silently regress.
- No credentials or environment-specific endpoints are committed.
