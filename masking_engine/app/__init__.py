"""Masking-engine FastAPI application package.

The full masking service (FastAPI app, Presidio analyzer/anonymizer wiring,
tokenization/FPE/redaction strategies, Vault-backed key resolution) is built
and run inside the ``masking-engine`` container from this repository's
``masking_engine/Dockerfile``.

Only the *client interface* that the pipeline quality gates code against is
vendored here (see :mod:`masking_engine.app.ner.presidio_client`). This keeps
``gates.pii_validator`` importable and testable without pulling in the heavy
Presidio / spaCy model dependencies of the concrete service.
"""
