# Contributing

Thanks for your interest in improving
**bulletproof-conductor-data-pipeline**.

## Getting Set Up

The full test suite is pure Python — no Docker, database, or network access
required.

```bash
git clone https://github.com/bulletproofsoftware-ai/bulletproof-conductor-data-pipeline.git
cd bulletproof-conductor-data-pipeline
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest          # expect 891 passed
```

If you plan to bring up the Docker stack, copy the environment template first
and replace every `changeme` value:

```bash
cp .env.example .env
```

Never commit `.env`.

Note that the `masking-engine` container cannot start from this repository —
only its client contract is vendored here. See the note at the top of the
[README](README.md).

## Development Workflow

1. **Open an issue first** for anything beyond a small fix, so we can agree on
   the approach before you invest time.
2. **Branch** from `main`.
3. **Write a test** that fails before your change and passes after it. This
   repository treats its own packaging and configuration as testable surface —
   see `tests/test_docker_compose.py`, which asserts that the compose file,
   Dockerfile, `.env.example`, and `.gitignore` stay consistent with the tree.
4. **Keep the suite green.** `python -m pytest` must report 0 failures. CI runs
   the same command and blocks the build on failure.
5. **Open a pull request** describing what changed and why, and how you
   verified it.

## Coding Standards

- Target Python 3.12.
- Match the surrounding style; prefer clarity over cleverness.
- Keep changes surgical — every changed line should trace to the issue you are
  fixing. If you notice unrelated problems, mention them in the PR rather than
  fixing them in the same change.
- Document any new environment variable in `.env.example` **and** in
  `docs/INSTALL.md`. The test suite asserts that required variables are present
  in `.env.example`.

## Security-Sensitive Areas

Take extra care in these areas, and say so explicitly in your PR description if
you touch them:

- **Masking and tokenization** (`masking_engine/`, `gates/pii_validator.py`) —
  a regression here can leak unmasked PII downstream.
- **Approval gates** (`gates/`) — a regression here can let a sensitive step
  run without human sign-off.
- **Lineage** (`lineage/`) — gaps break auditability.

Never include real personal data in tests, fixtures, issues, or PR
descriptions. Use synthetic values.

Do not report vulnerabilities in a public issue or PR — follow
[SECURITY.md](SECURITY.md).

## License

By contributing you agree that your contributions are licensed under the
Apache-2.0 license, as set out in [LICENSE](LICENSE) and [NOTICE](NOTICE).
