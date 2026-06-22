# Dependency and license visibility

This document is an operational inventory for technical diligence. It is not legal advice.

## Core runtime dependencies

### Python application dependencies (direct)

From `sidecar/requirements.txt` and `reconciler/requirements.txt`:

- FastAPI (MIT)
- Uvicorn (BSD-3-Clause)
- Pydantic (MIT)
- pydantic-settings (MIT)
- SQLAlchemy (MIT)
- Psycopg + psycopg-binary (LGPL-3.0)
- Redis Python client (`redis`) (MIT)

### Local stack components

- PostgreSQL 16 (PostgreSQL License)
- Redis 7 (Redis Source Available License v2 / SSPLv1 / AGPLv3 licensing model; verify deployment fit for your use case)
- Docker / Docker Compose tooling (Apache-2.0 components)

### Gateway config dependency

- LiteLLM (MIT)

## Re-generating dependency visibility

Recommended reproducible command:

```bash
pip install -r sidecar/requirements.txt -r reconciler/requirements.txt
pip show fastapi uvicorn pydantic pydantic-settings sqlalchemy psycopg redis
```

For full transitive-license inventory, run your preferred SPDX/SBOM tooling in CI and archive the output as a diligence artifact.
